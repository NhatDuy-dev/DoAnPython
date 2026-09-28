# Chạy PR Dashboard

Dashboard đọc `data/pull_requests.json`, cùng dữ liệu với chương trình quản lý PR. Backend tính lại điểm chất lượng và rủi ro, đồng thời đồng bộ reviewer từ TV2 trong `data/tv2.db` mỗi lần đọc dữ liệu. Mã Dashboard demo cũ được giữ trong `examples/legacy_dashboard/` và không cần chạy.

Mở hai terminal tại thư mục gốc `code-review-system`.

Terminal 1 (backend):

```powershell
python -m pip install -r requirements.txt
python -m uvicorn dashboard.backend.main:app --reload
```

Terminal 2 (frontend):

```powershell
cd dashboard/frontend
npm.cmd install
npm.cmd run dev
```

Mở http://localhost:5173/. Trang tự cập nhật dữ liệu sau mỗi 5 giây. Muốn đổi dữ liệu PR, sửa `data/pull_requests.json` hoặc chạy `python -m code_review_system.review_manager`; các trường `risk_score`, `risk_level`, `so_file_thay_doi` và `co_chua_file_nhay_cam` được tính từ `danh_sach_file`, `so_dong_them`, `so_dong_xoa`.
