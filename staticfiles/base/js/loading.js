document.addEventListener('DOMContentLoaded', function () {
    // Khi trang được tải, ẩn overlay loading
    const loadingOverlay = document.getElementById('loading-overlay');
    console.log(loadingOverlay);

    // Hiển thị overlay loading khi người dùng điều hướng
    window.addEventListener('beforeunload', function () {
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
    });

    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
});
