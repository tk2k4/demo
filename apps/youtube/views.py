import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
import requests
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache

from tools.auto_add_playlists import run_for_profile, DEFAULT_TARGET_TOTAL


def _run_jobs_in_background(jobs, job_ids, max_workers=4):
    """Chạy ThreadPoolExecutor trong thread nền để tránh block request."""
    def runner():
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for idx, job in enumerate(jobs):
                job_id = job_ids[idx]
                future = executor.submit(_run_single_job, job, job_id)
                futures.append(future)
            
            # best-effort wait để log lỗi nếu có
            for f in futures:
                try:
                    f.result()
                except Exception as e:  # pragma: no cover - log runtime issue
                    print("❌ Worker error:", e)

    t = threading.Thread(target=runner, daemon=True)
    t.start()


def _run_single_job(job, job_id):
    """Chạy một job và cập nhật status."""
    try:
        # Cập nhật status: running
        cache.set(f"job_{job_id}", {
            "status": "running",
            "profile_id": job.get("profile_id"),
            "keyword": job.get("keyword"),
            "name": job.get("name"),
            "error": None,
        }, timeout=3600)  # 1 giờ
        
        # Chạy job
        run_for_profile(job)
        
        # Cập nhật status: success
        cache.set(f"job_{job_id}", {
            "status": "success",
            "profile_id": job.get("profile_id"),
            "keyword": job.get("keyword"),
            "name": job.get("name"),
            "error": None,
        }, timeout=3600)
    except Exception as e:
        # Cập nhật status: failed
        error_msg = str(e)
        cache.set(f"job_{job_id}", {
            "status": "failed",
            "profile_id": job.get("profile_id"),
            "keyword": job.get("keyword"),
            "name": job.get("name"),
            "error": error_msg,
        }, timeout=3600)


@csrf_exempt
@staff_member_required
def import_tool_run(request):
    """
    Nhận mảng dữ liệu Excel (sheet_to_json) từ frontend để chạy tool.
    Payload mẫu:
    {
        "filename": "file.xlsx",
        "rows": [ { "profile_id": "...", "keyword": "...", "playlist_title": "..." }, ... ]
    }
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Payload không hợp lệ"}, status=400)

    rows = data.get("rows") or []
    filename = data.get("filename") or ""
    max_workers = data.get("max_workers", 30)  # Mặc định 30
    target_total = data.get("target_total", DEFAULT_TARGET_TOTAL)

    # Validate target_total (số video tối thiểu cần load)
    try:
        target_total = int(target_total)
        if target_total < 1:
            target_total = DEFAULT_TARGET_TOTAL
    except (ValueError, TypeError):
        target_total = DEFAULT_TARGET_TOTAL

    # Validate max_workers
    try:
        max_workers = int(max_workers)
        if max_workers < 1:
            max_workers = 1
        if max_workers > 100:
            max_workers = 100
    except (ValueError, TypeError):
        max_workers = 30

    if not isinstance(rows, list) or len(rows) == 0:
        return JsonResponse({"success": False, "error": "Không có dữ liệu để xử lý"}, status=400)

    jobs = []
    for row in rows:
        profile_id = row.get("profile_id") or row.get("profile") or row.get("gpm_id")
        keyword = row.get("keyword")
        playlist_title = row.get("playlist_title") or row.get("title")
        name = row.get("name") or row.get("profile_name")
        raw_proxy = row.get("raw_proxy")
        profile_path = row.get("profile_path")
        browser_type = row.get("browser_type")
        browser_version = row.get("browser_version")
        note = row.get("note")
        # Cho phép override target_total từng dòng, fallback về giá trị chung
        row_target_total = row.get("target_total", target_total)
        try:
            row_target_total = int(row_target_total)
            if row_target_total < 1:
                row_target_total = target_total
        except (ValueError, TypeError):
            row_target_total = target_total

        if profile_id and keyword:
            jobs.append(
                {
                    "profile_id": str(profile_id).strip(),
                    "keyword": str(keyword).strip(),
                    "playlist_title": str(playlist_title).strip() if playlist_title else None,
                    "name": str(name).strip() if name else None,
                    "raw_proxy": str(raw_proxy).strip() if raw_proxy else None,
                    "profile_path": str(profile_path).strip() if profile_path else None,
                    "browser_type": str(browser_type).strip() if browser_type else None,
                    "browser_version": str(browser_version).strip() if browser_version else None,
                    "note": str(note).strip() if note else None,
                    "target_total": row_target_total,
                }
            )

    if not jobs:
        return JsonResponse({"success": False, "error": "Không tìm thấy profile_id/keyword hợp lệ"}, status=400)

    # Tạo job IDs cho mỗi job
    job_ids = [str(uuid.uuid4()) for _ in jobs]
    session_id = str(uuid.uuid4())
    
    # Lưu danh sách job IDs vào cache với session_id
    cache.set(f"session_{session_id}", job_ids, timeout=3600)
    
    # Khởi tạo status cho tất cả jobs là "pending"
    for idx, job in enumerate(jobs):
        cache.set(f"job_{job_ids[idx]}", {
            "status": "pending",
            "profile_id": job.get("profile_id"),
            "keyword": job.get("keyword"),
            "name": job.get("name"),
            "error": None,
        }, timeout=3600)

    _run_jobs_in_background(jobs, job_ids, max_workers=min(max_workers, len(jobs)))

    return JsonResponse(
        {
            "success": True,
            "message": f"Đã queue {len(jobs)} job, đang chạy nền.",
            "filename": filename,
            "session_id": session_id,
            "job_ids": job_ids,
            "total_jobs": len(jobs),
        }
    )


@staff_member_required
def get_data_gpm(request):
    """
    Proxy lấy danh sách profiles từ GPM để tránh CORS trên frontend.
    """
    try:
        resp = requests.get("http://127.0.0.1:19995/api/v3/profiles", timeout=10)
        data = resp.json()
        return JsonResponse(data, status=resp.status_code, safe=False)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"GPM request failed: {e}"}, status=500)


@csrf_exempt
@staff_member_required
def import_gpm_profiles(request):
    """
    Import danh sách profiles từ GPM vào database.
    Tạo mới nếu chưa có, cập nhật nếu đã tồn tại (dựa trên gpm_id).
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    try:
        resp = requests.get("http://127.0.0.1:19995/api/v3/profiles", timeout=10)
        resp.raise_for_status()
        gpm_profiles = resp.json()
    except requests.RequestException as e:
        return JsonResponse({"success": False, "error": f"Không thể kết nối GPM: {e}"}, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Lỗi khi lấy dữ liệu GPM: {e}"}, status=500)

    if not isinstance(gpm_profiles, dict) or not isinstance(gpm_profiles.get("data"), list):
        return JsonResponse({"success": False, "error": "Dữ liệu GPM không hợp lệ"}, status=400)

    from .models import ProfileYoutube

    created_count = 0
    updated_count = 0

    for item in gpm_profiles.get("data", []):
        gpm_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        
        if not gpm_id:
            continue

        # Lấy các trường khác từ GPM response nếu có
        raw_proxy = item.get("raw_proxy", "") or ""
        profile_path = item.get("profile_path", "") or ""
        browser_type = item.get("browser_type", "") or ""
        browser_version = item.get("browser_version", "") or ""
        note = item.get("note", "") or ""

        # Kiểm tra profile đã tồn tại chưa
        try:
            profile = ProfileYoutube.objects.get(gpm_id=gpm_id)
            profile.name = name
            profile.raw_proxy = raw_proxy
            profile.profile_path = profile_path
            profile.browser_type = browser_type
            profile.browser_version = browser_version
            profile.note = note
            profile.save(
                update_fields=[
                    "name",
                    "raw_proxy",
                    "profile_path",
                    "browser_type",
                    "browser_version",
                    "note",
                ]
            )
            updated_count += 1
        except ProfileYoutube.DoesNotExist:
            ProfileYoutube.objects.create(
                gpm_id=gpm_id,
                name=name,
                raw_proxy=raw_proxy,
                profile_path=profile_path,
                browser_type=browser_type,
                browser_version=browser_version,
                note=note,
                is_done=False,
            )
            created_count += 1

    return JsonResponse({
        "success": True,
        "message": f"Đã import {created_count + updated_count} profiles",
        "created": created_count,
        "updated": updated_count,
    })


@staff_member_required
def get_jobs_status(request):
    """
    Lấy status của các jobs theo session_id hoặc job_ids.
    """
    session_id = request.GET.get("session_id")
    job_ids_str = request.GET.get("job_ids", "")
    
    if not session_id and not job_ids_str:
        return JsonResponse({"success": False, "error": "Thiếu session_id hoặc job_ids"}, status=400)
    
    # Lấy job_ids từ session_id nếu có
    if session_id:
        job_ids = cache.get(f"session_{session_id}", [])
    else:
        job_ids = [jid.strip() for jid in job_ids_str.split(",") if jid.strip()]
    
    jobs_status = []
    for job_id in job_ids:
        job_data = cache.get(f"job_{job_id}")
        if job_data:
            jobs_status.append({
                "job_id": job_id,
                **job_data
            })
        else:
            jobs_status.append({
                "job_id": job_id,
                "status": "unknown",
                "profile_id": None,
                "keyword": None,
                "name": None,
                "error": "Job không tồn tại hoặc đã hết hạn",
            })
    
    # Tính toán thống kê
    stats = {
        "total": len(jobs_status),
        "pending": sum(1 for j in jobs_status if j["status"] == "pending"),
        "running": sum(1 for j in jobs_status if j["status"] == "running"),
        "success": sum(1 for j in jobs_status if j["status"] == "success"),
        "failed": sum(1 for j in jobs_status if j["status"] == "failed"),
        "unknown": sum(1 for j in jobs_status if j["status"] == "unknown"),
    }
    
    return JsonResponse({
        "success": True,
        "jobs": jobs_status,
        "stats": stats,
    })


@csrf_exempt
@staff_member_required
def run_tool_for_profile(request):
    """
    Chạy tool cho một profile cụ thể với keyword và playlist_title.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Payload không hợp lệ"}, status=400)

    profile_id = data.get("profile_id")
    keyword = (data.get("keyword") or "").strip()
    playlist_title = data.get("playlist_title")
    if playlist_title:
        playlist_title = str(playlist_title).strip() or None
    else:
        playlist_title = None
    target_total = data.get("target_total", DEFAULT_TARGET_TOTAL)
    try:
        target_total = int(target_total)
        if target_total < 1:
            target_total = DEFAULT_TARGET_TOTAL
    except (ValueError, TypeError):
        target_total = DEFAULT_TARGET_TOTAL

    if not profile_id:
        return JsonResponse({"success": False, "error": "Thiếu profile_id"}, status=400)

    if not keyword:
        return JsonResponse({"success": False, "error": "Thiếu keyword"}, status=400)

    # Lấy thông tin profile từ database
    from .models import ProfileYoutube
    try:
        profile = ProfileYoutube.objects.get(pk=profile_id)
    except ProfileYoutube.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profile không tồn tại"}, status=404)

    # Tạo job ID để track
    job_id = str(uuid.uuid4())
    
    # Tạo job để chạy tool
    job = {
        "profile_id": str(profile.gpm_id),
        "keyword": keyword,
        "playlist_title": playlist_title,
        "name": profile.name,
        "raw_proxy": profile.raw_proxy,
        "profile_path": profile.profile_path,
        "browser_type": profile.browser_type,
        "browser_version": profile.browser_version,
        "note": profile.note,
        "target_total": target_total,
    }

    # Khởi tạo status là pending
    cache.set(f"job_{job_id}", {
        "status": "pending",
        "profile_id": str(profile.gpm_id),
        "keyword": keyword,
        "name": profile.name,
        "error": None,
    }, timeout=3600)

    # Chạy tool trong background
    def run_in_background():
        try:
            # Cập nhật status: running
            cache.set(f"job_{job_id}", {
                "status": "running",
                "profile_id": str(profile.gpm_id),
                "keyword": keyword,
                "name": profile.name,
                "error": None,
            }, timeout=3600)
            
            run_for_profile(job)
            
            # Cập nhật status: success
            cache.set(f"job_{job_id}", {
                "status": "success",
                "profile_id": str(profile.gpm_id),
                "keyword": keyword,
                "name": profile.name,
                "error": None,
            }, timeout=3600)
        except Exception as e:
            # Chỉ lấy message ngắn gọn, không lấy stacktrace
            error_msg = str(e).split('\n')[0] if hasattr(e, '__str__') else str(e)
            # Cập nhật status: failed
            cache.set(f"job_{job_id}", {
                "status": "failed",
                "profile_id": str(profile.gpm_id),
                "keyword": keyword,
                "name": profile.name,
                "error": error_msg,
            }, timeout=3600)
            print(f"❌ Error running tool for profile {profile.gpm_id}: {error_msg}")

    import threading
    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()

    return JsonResponse({
        "success": True,
        "message": f"Đã bắt đầu chạy tool cho profile {profile.name}",
        "job_id": job_id,
    })


@staff_member_required
def dashboard_stats(request):
    """
    Lấy thống kê cho dashboard.
    """
    from .models import ProfileYoutube, PlaylistYoutube, VideoYoutube
    from django.db.models import Count, Q
    from django.utils import timezone
    from datetime import timedelta

    # Thống kê cơ bản
    total_profiles = ProfileYoutube.objects.count()
    done_profiles = ProfileYoutube.objects.filter(is_done=True).count()
    pending_profiles = ProfileYoutube.objects.filter(is_done=False).count()
    total_playlists = PlaylistYoutube.objects.count()
    total_videos = VideoYoutube.objects.count()

    # Thống kê theo browser type
    browser_types = ProfileYoutube.objects.values('browser_type').annotate(
        count=Count('id')
    ).order_by('-count')
    browser_types_dict = {item['browser_type']: item['count'] for item in browser_types if item['browser_type']}

    # Profiles gần đây (7 ngày)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_profiles = ProfileYoutube.objects.filter(
        created_at__gte=seven_days_ago
    ).order_by('-created_at')[:10]
    
    recent_profiles_data = [
        {
            'name': p.name,
            'gpm_id': p.gpm_id,
            'created_at': p.created_at.strftime('%d/%m/%Y %H:%M') if p.created_at else '',
        }
        for p in recent_profiles
    ]

    return JsonResponse({
        "success": True,
        "stats": {
            "total_profiles": total_profiles,
            "done_profiles": done_profiles,
            "pending_profiles": pending_profiles,
            "total_playlists": total_playlists,
            "total_videos": total_videos,
        },
        "browser_types": browser_types_dict,
        "recent_profiles": recent_profiles_data,
    })


@staff_member_required
def export_excel(request):
    """
    Xuất file Excel với format: STT, profile_id, name, playlist name, playlist link
    Gom nhóm các playlist của cùng profile vào 1 dòng
    Chỉ lấy profiles có is_done=True
    """
    from .models import ProfileYoutube, PlaylistYoutube

    # Chỉ lấy profiles có is_done=True
    profiles = ProfileYoutube.objects.filter(is_done=True).prefetch_related('playlistyoutube_set').all().order_by('id')

    # Tạo workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Profiles & Playlists"

    # Headers
    headers = ['STT', 'Profile ID', 'Name', 'Tên Danh Sách Phát', 'Link Danh Sách Phát']
    ws.append(headers)

    # Style headers
    header_font = Font(bold=True, size=12)
    header_alignment = Alignment(horizontal='center', vertical='center')
    for cell in ws[1]:
        cell.font = header_font
        cell.alignment = header_alignment

    # Dữ liệu - gom nhóm các playlist trùng lặp vào 1 ô, các playlist khác nhau mỗi cái 1 dòng
    stt = 1
    for profile in profiles:
        playlists = profile.playlistyoutube_set.all().order_by('id')
        
        # Loại bỏ các playlist trùng lặp (cùng tên và cùng link), chỉ giữ lại unique
        seen_playlists = set()
        unique_playlists = []
        
        for playlist in playlists:
            # Tạo key từ tên và link để kiểm tra trùng lặp
            playlist_key = (playlist.name or '', playlist.youtube_link or '')
            if playlist_key not in seen_playlists:
                seen_playlists.add(playlist_key)
                unique_playlists.append(playlist)
        
        # Nếu có playlist, mỗi playlist unique 1 dòng
        if unique_playlists:
            for playlist in unique_playlists:
                ws.append([
                    stt,
                    profile.gpm_id,
                    profile.name,
                    playlist.name or '',
                    playlist.youtube_link or '',
                ])
                stt += 1
        else:
            # Nếu không có playlist, vẫn thêm dòng với profile info
            ws.append([
                stt,
                profile.gpm_id,
                profile.name,
                '',
                '',
            ])
            stt += 1

    # Auto adjust column widths
    column_widths = {
        'A': 8,   # STT
        'B': 40,  # Profile ID
        'C': 30,  # Name
        'D': 40,  # Tên Danh Sách Phát
        'E': 50,  # Link Danh Sách Phát
    }
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    # Tạo response
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"youtube_profiles_playlists_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response