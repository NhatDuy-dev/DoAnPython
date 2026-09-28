# Chạy PR Dashboard

Dashboard đọc `../pull_requests.json`, cùng dữ liệu với `review_manager.py`, `quality_checker.py` và `risk_calculator.py`. Backend tính lại điểm chất lượng và rủi ro, đồng thời đồng bộ reviewer từ TV2 trong `../group/tv2.db` mỗi lần đọc dữ liệu. SQLite `backend/pr_dashboard.db` và `backend/seed.py` là dữ liệu Dashboard demo cũ, không cần chạy.

Mở hai terminal tại thư mục `PR-Dashboard`.

Terminal 1 (backend):

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Terminal 2 (frontend):

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Mở http://localhost:5173/. Trang tự cập nhật dữ liệu sau mỗi 5 giây. Muốn đổi dữ liệu PR, sửa `../pull_requests.json` hoặc dùng `review_manager.py`; các trường `risk_score`, `risk_level`, `so_file_thay_doi` và `co_chua_file_nhay_cam` được tính từ `danh_sach_file`, `so_dong_them`, `so_dong_xoa`.
