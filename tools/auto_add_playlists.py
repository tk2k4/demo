import os
import sys
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constants
DJANGO_READY = False
DEFAULT_TARGET_TOTAL = 100
SCROLL_PAUSE = 5
MAX_SCROLL_TIMES = 20
GPM_API_BASE = "http://127.0.0.1:19995/api/v3/profiles"
PROFILE_LOCKS = {}
PROFILE_LOCK = threading.Lock()


def setup_django():
    """Đảm bảo Django được cấu hình để ghi dữ liệu."""
    global DJANGO_READY
    if DJANGO_READY:
        return
    try:
        from django.conf import settings
        if not settings.configured:
            base_dir = Path(__file__).resolve().parents[1]
            if str(base_dir) not in sys.path:
                sys.path.append(str(base_dir))
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "youtubetoolsmanager.settings")
            import django
            django.setup()
        DJANGO_READY = True
    except Exception as e:
        print("⚠️ Không khởi tạo được Django, bỏ qua lưu DB:", e)
        DJANGO_READY = False


def save_result(job: dict, playlist_url: str, number_of_videos: int | None = None):
    """Ghi nhận kết quả vào DB."""
    setup_django()
    if not DJANGO_READY or not playlist_url:
        return
    try:
        from apps.youtube.models import ProfileYoutube, PlaylistYoutube
        profile_id = job.get("profile_id") or job.get("gpm_id")
        keyword = job.get("keyword") or ""
        playlist_title = job.get("playlist_title") or f"{keyword} autoplay"
        name = job.get("name") or job.get("profile_name") or profile_id

        profile_defaults = {
            "name": name,
            "raw_proxy": job.get("raw_proxy"),
            "profile_path": job.get("profile_path") or "",
            "browser_type": job.get("browser_type") or "",
            "browser_version": job.get("browser_version") or "",
            "note": job.get("note"),
        }
        profile, _ = ProfileYoutube.objects.get_or_create(
            gpm_id=str(profile_id),
            defaults=profile_defaults,
        )
        profile.is_done = True
        profile.save(update_fields=["is_done"])

        PlaylistYoutube.objects.update_or_create(
            profile=profile,
            name=playlist_title,
            defaults={
                "youtube_link": playlist_url,
                "number_of_videos": number_of_videos or 0,
            },
        )
    except Exception as e:
        print(f"⚠️ Lỗi lưu DB: {str(e).split(chr(10))[0]}")


def log(thread_name: str, message: str):
    """Helper để log với thread name."""
    print(f"[{thread_name}] {message}")


def start_gpm_profile(profile_id: str, thread_name: str) -> tuple:
    """Mở GPM profile và trả về (remote_address, driver_path)."""
    log(thread_name, f"🚀 BẮT ĐẦU profile {profile_id}")
    log(thread_name, "1. Đang gọi API để mở Profile GPM...")
    
    try:
        resp = requests.get(f"{GPM_API_BASE}/start/{profile_id}").json()
    except Exception as e:
        raise Exception(f"Lỗi gọi API: {str(e).split(chr(10))[0]}")

    if not (resp.get("success") or resp.get("status") == "OK"):
        raise Exception(f"GPM báo lỗi: {resp}")

    data = resp.get("data", {})
    remote_address = data.get("remote_debugging_address")
    driver_path = data.get("driver_path")

    log(thread_name, f"✅ GPM đã mở tại: {remote_address}")
    log(thread_name, f"📂 Driver Path: {driver_path}")
    log(thread_name, "⏳ Đang chờ trình duyệt khởi động ổn định (5s)...")
    time.sleep(5)
    
    return remote_address, driver_path


def create_driver(remote_address: str, driver_path: str, thread_name: str):
    """Tạo Selenium driver attach vào GPM."""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", remote_address)

    try:
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        log(thread_name, "🔗 Selenium đã móc vào trình duyệt thành công!")
        return driver
    except Exception as e:
        raise Exception(f"Lỗi kết nối Selenium: {str(e).split(chr(10))[0]}")


def find_and_click(driver, selector: str = None, xpath: str = None, 
                   js_finder: str = None, error_msg: str = ""):
    """Helper để tìm và click element."""
    wait = WebDriverWait(driver, 10)
    
    try:
        if js_finder:
            btn = wait.until(lambda d: d.execute_script(js_finder))
        elif xpath:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        else:
            btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        
        try:
            btn.click()
        except:
            driver.execute_script("arguments[0].click();", btn)
        return True
    except Exception as e:
        raise Exception(f"{error_msg}: {str(e).split(chr(10))[0]}")


def open_youtube_tab(driver, thread_name: str):
    """Mở tab YouTube mới."""
    log(thread_name, f"👀 Số lượng tab đang mở ban đầu: {len(driver.window_handles)}")
    driver.execute_script("window.open('https://www.youtube.com', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    log(thread_name, "🌍 Đang thử truy cập YouTube...")
    time.sleep(5)


def click_extension_button(driver, thread_name: str):
    """Click nút extension msfy-toggle-bar-button."""
    selector = "div[id^='msfy-toggle-bar-button-'] yt-icon-button button"
    find_and_click(driver, selector=selector, 
                   error_msg="⚠️ Không tìm thấy nút extension")
    log(thread_name, "✍️  Đã click nút extension.")


def search_keyword(driver, keyword: str, thread_name: str):
    """Tìm kiếm keyword trên YouTube."""
    try:
        search_box = driver.find_element(By.NAME, "search_query")
        search_box.click()
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.ENTER)
        log(thread_name, f"✍️  Đã nhập '{keyword}' vào ô tìm kiếm.")
    except Exception as e:
        raise Exception(f"⚠️ Không tìm thấy ô tìm kiếm: {str(e).split(chr(10))[0]}")


def get_total_count(driver):
    """Lấy số phía sau dấu / trong yt-formatted-string#selection."""
    raw = driver.execute_script("""
        const el = document.querySelector("yt-formatted-string#selection");
        return el ? el.textContent : null;
    """)
    if not raw:
        return None
    try:
        parts = raw.split("/")
        return int(parts[1].strip()) if len(parts) == 2 else None
    except:
        return None


def scroll_until_target(driver, thread_name: str, target_total: int) -> int | None:
    """Scroll để load đủ video, hạn chế scroll thừa. Trả về tổng video cuối cùng (nếu có)."""
    time.sleep(2)

    # Kiểm tra ngay từ đầu nếu đã đủ
    initial_total = get_total_count(driver)
    if initial_total and initial_total >= target_total:
        log(thread_name, f"✅ Tổng video ban đầu ({initial_total}) >= {target_total}, không cần scroll.")
        return initial_total

    last_height = 0
    scroll_count = 0
    latest_total = initial_total

    while scroll_count < MAX_SCROLL_TIMES:
        # Scroll xuống đáy
        driver.execute_script("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'smooth'});")
        time.sleep(SCROLL_PAUSE)

        new_height = driver.execute_script("return document.documentElement.scrollHeight;")
        total = get_total_count(driver)
        latest_total = total if total is not None else latest_total

        log(thread_name, f"📊 scroll #{scroll_count+1}, height={new_height}, total={total}")

        if total and total >= target_total:
            log(thread_name, f"✅ Tổng video ({total}) >= {target_total}, dừng scroll.")
            break

        if new_height == last_height:
            log(thread_name, f"⚠️ scrollHeight không tăng nữa (={new_height}), dừng scroll.")
            break

        last_height = new_height
        scroll_count += 1

    if scroll_count >= MAX_SCROLL_TIMES:
        log(thread_name, f"⚠️ Đã scroll tối đa {MAX_SCROLL_TIMES} lần.")
    return latest_total


def select_all_videos(driver, thread_name: str):
    """Click nút select-all của extension."""
    js_finder = """
        const icon = document.querySelector("yt-icon[icon='msfy:msfy-select-all']");
        if (!icon) return null;
        return icon.closest('button');
    """
    find_and_click(driver, js_finder=js_finder, 
                   error_msg="⚠️ Không tìm thấy icon select-all")
    log(thread_name, "✍️  Đã click vào nút select all.")


def open_more_menu(driver, thread_name: str):
    """Click nút more_vert."""
    js_finder = """
        const icon = document.querySelector("yt-icon[icon='more_vert']");
        if (!icon) return null;
        return icon.closest('button');
    """
    find_and_click(driver, js_finder=js_finder, 
                   error_msg="⚠️ Không tìm thấy nút more_vert")
    log(thread_name, "✍️  Đã click vào nút more_vert.")


def add_to_playlist(driver, thread_name: str):
    """Click 'Save to playlist'."""
    find_and_click(driver, selector="div#msfy-action-add-to-playlist",
                   error_msg="⚠️ Không tìm thấy nút add to playlist")
    log(thread_name, "✍️  Đã click vào nút add to playlist.")


def click_new_playlist(driver, thread_name: str):
    """Click 'New playlist' (EN hoặc VI)."""
    try:
        xpath = "//button[.//span[contains(normalize-space(.), 'New playlist')]]"
        find_and_click(driver, xpath=xpath)
        log(thread_name, "✍️  Đã click vào nút New playlist.")
    except:
        log(thread_name, "⚠️ Không tìm thấy nút New playlist (EN), thử bản tiếng Việt")
        xpath = "//button[.//span[contains(normalize-space(.), 'Danh sách phát mới')]]"
        find_and_click(driver, xpath=xpath)
        log(thread_name, "✍️  Đã click vào nút Danh sách phát mới.")


def fill_playlist_title(driver, playlist_title: str, thread_name: str):
    """Điền tên playlist."""
    wait = WebDriverWait(driver, 10)
    placeholders = ['Choose a title', 'Chọn một tiêu đề']
    
    for placeholder in placeholders:
        try:
            container = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.ytStandardsTextareaShapeTextareaContainer")
            ))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
            driver.execute_script("arguments[0].click();", container)

            title_box = container.find_element(By.CSS_SELECTOR, f"textarea[placeholder='{placeholder}']")
            title_box.clear()
            title_box.send_keys(playlist_title)

            driver.execute_script("""
                const ta = arguments[0];
                const val = arguments[1];
                ta.value = val;
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                ta.dispatchEvent(new Event('change', { bubbles: true }));
            """, title_box, playlist_title)

            log(thread_name, f"✅ Đã điền tên playlist: {playlist_title}")
            return
        except:
            continue
    
    raise Exception("⚠️ Không điền được tên playlist")


def set_visibility_public(driver, thread_name: str):
    """Đặt playlist thành Public."""
    # Mở dropdown
    wait = WebDriverWait(driver, 10)
    visibility_dropdown = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "div.ytDropdownViewModelDropdownContainer[role='combobox']")
    ))
    visibility_dropdown.click()
    log(thread_name, "✅ Đã mở dropdown Visibility.")

    # Chọn Public/Công khai
    js_finder = """
        const nodes = Array.from(document.querySelectorAll('span, yt-formatted-string, div'));
        return nodes.find(el => {
            const t = el.textContent.trim();
            return t === 'Public' || t === 'Công khai';
        }) || null;
    """
    public_el = wait.until(lambda d: d.execute_script(js_finder))
    driver.execute_script("arguments[0].click();", public_el)
    log(thread_name, "✅ Đã chọn Visibility = Public/Công khai.")


def click_create_button(driver, thread_name: str):
    """Click nút Create/Tạo."""
    wait = WebDriverWait(driver, 10)
    xpaths = [
        ("//button[@aria-label='Cancel']/ancestor::div[contains(@class,'yt-spec-dialog-layout__dialog-layout-footer-container')]//button[@aria-label='Create']", "EN"),
        ("//button[@aria-label='Hủy']/ancestor::div[contains(@class,'yt-spec-dialog-layout__dialog-layout-footer-container')]//button[@aria-label='Tạo']", "VI")
    ]
    
    for xpath, lang in xpaths:
        try:
            create_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", create_btn)
            log(thread_name, f"✅ Đã click nút Create/Tạo ({lang}).")
            return
        except:
            continue
    
    raise Exception("⚠️ Không tìm thấy nút Create/Tạo")


def get_playlist_url(driver, profile_id: str, thread_name: str) -> str:
    """Lấy URL playlist vừa tạo."""
    time.sleep(3)
    
    playlist_url = WebDriverWait(driver, 10).until(
        lambda d: d.execute_script("""
            const links = Array.from(document.querySelectorAll("a[href^='/playlist?list=']"));
            if (!links.length) return null;
            const last = links[links.length - 1];
            return last.href;
        """)
    )
    
    if not playlist_url:
        raise Exception(f"⚠️ Không lấy được link playlist cho profile {profile_id}")
    
    log(thread_name, f"🔗 Playlist mới của profile {profile_id}: {playlist_url}")
    return playlist_url


def cleanup(driver, profile_id: str, thread_name: str):
    """Đóng driver và stop GPM profile."""
    # Đóng driver
    try:
        if driver:
            driver.quit()
            log(thread_name, "🔒 Đã đóng Chrome driver.")
    except Exception as e:
        log(thread_name, f"⚠️ Lỗi khi đóng driver: {e}")
    
    # Stop GPM
    try:
        resp = requests.get(f"{GPM_API_BASE}/close/{profile_id}", timeout=5)
        if resp.status_code == 200:
            log(thread_name, f"🔒 Đã gọi API stop GPM profile {profile_id}.")
        else:
            log(thread_name, f"⚠️ GPM API stop trả về status {resp.status_code}.")
    except Exception as e:
        log(thread_name, f"⚠️ Không thể gọi API stop GPM: {e}")


def run_for_profile(job: dict):
    """Chạy toàn bộ flow YouTube cho 1 profile."""
    profile_id = job["profile_id"]
    keyword = job["keyword"]
    playlist_title = job.get("playlist_title") or f"{keyword} autoplay"
    target_total = job.get("target_total")
    try:
        target_total = int(target_total)
        if target_total < 1:
            target_total = DEFAULT_TARGET_TOTAL
    except (TypeError, ValueError):
        target_total = DEFAULT_TARGET_TOTAL
    thread_name = threading.current_thread().name
    driver = None
    lock = None

    try:
        with PROFILE_LOCK:
            if profile_id not in PROFILE_LOCKS:
                PROFILE_LOCKS[profile_id] = threading.Lock()
            lock = PROFILE_LOCKS[profile_id]
        # blocking=True để các job cùng profile_id xếp hàng, không bị bỏ qua
        lock.acquire(blocking=True)
        log(thread_name, f"🔒 Đã giữ lock cho profile {profile_id}, sẽ chạy tuần tự.")

        # 1. Mở GPM
        remote_address, driver_path = start_gpm_profile(profile_id, thread_name)
        
        # 2. Tạo driver
        driver = create_driver(remote_address, driver_path, thread_name)
        
        # 3. Mở YouTube
        open_youtube_tab(driver, thread_name)
        
        # 4. Click extension
        click_extension_button(driver, thread_name)
        
        # 5. Search
        search_keyword(driver, keyword, thread_name)
        
        # 6. Scroll để load video
        total_videos = scroll_until_target(driver, thread_name, target_total)
        
        # 7. Select all
        select_all_videos(driver, thread_name)
        
        # 8. Mở menu
        open_more_menu(driver, thread_name)
        
        # 9. Add to playlist
        add_to_playlist(driver, thread_name)
        
        # 10. New playlist
        click_new_playlist(driver, thread_name)
        
        # 11. Điền tên
        fill_playlist_title(driver, playlist_title, thread_name)
        
        # 12. Set public
        set_visibility_public(driver, thread_name)
        
        # 13. Create
        click_create_button(driver, thread_name)
        
        # 14. Lấy URL và lưu
        playlist_url = get_playlist_url(driver, profile_id, thread_name)
        save_result(job, playlist_url, number_of_videos=total_videos or 0)

    except Exception as e:
        error_msg = f"[{thread_name}] 💥 Lỗi: {str(e).split(chr(10))[0]}"
        print(error_msg)
        raise Exception(error_msg) from None
    finally:
        cleanup(driver, profile_id, thread_name)
        # Nghỉ ngắn để GPM kịp đóng hẳn trước khi job khác cùng profile chạy
        time.sleep(2)
        if lock:
            lock.release()


# ================= MULTITHREAD ENTRYPOINT =================

JOBS = [
    {
        "profile_id": "b4e9ca70-cb37-48b7-a6d0-efc83c142ad8",
        "keyword": "muốn nói với em",
    },
    {
        "profile_id": "a77eafbd-7d43-4b04-ac9b-2dd10e890b48",
        "keyword": "kiếm đâu bây giờ",
    },
]


def main():
    max_workers = min(len(JOBS), 4)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_for_profile, job) for job in JOBS]
        
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print("❌ Worker bị lỗi:", e)


if __name__ == "__main__":
    main()