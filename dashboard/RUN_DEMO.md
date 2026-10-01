# Chạy PR Dashboard

Dashboard đọc `data/pull_requests.json`, cùng dữ liệu với chương trình quản lý PR. Backend tính lại điểm chất lượng và rủi ro, đồng thời đồng bộ reviewer từ TV2 trong `data/tv2.db` mỗi lần đọc dữ liệu. Mã Dashboard demo cũ được giữ trong `examples/legacy_dashboard/` và không cần chạy.

Mở hai terminal tại thư mục gốc `code-review-system`.

Terminal 1 (backend):

```powershell
python -m pip install -r requirements.txt
python -m uvicorn dashboard.backend.main:app --reload --port 8002
```

Terminal 2 (frontend):

```powershell
cd dashboard/frontend
npm.cmd install
npm.cmd run dev
```

Mở http://localhost:5173/. Trang tự cập nhật dữ liệu sau mỗi 5 giây. Muốn đổi dữ liệu PR, sửa `data/pull_requests.json` hoặc chạy `python -m code_review_system.review_manager`; các trường `risk_score`, `risk_level`, `so_file_thay_doi` và `co_chua_file_nhay_cam` được tính từ `danh_sach_file`, `so_dong_them`, `so_dong_xoa`.

## Quản lý PR trên giao diện

- Chọn **Tạo PR** ở trang Tổng quan hoặc Pull requests để nhập tiêu đề, tác giả, file thay đổi, số dòng và kết quả kiểm tra. Điểm chất lượng, rủi ro và reviewer được tính/phân công tự động.
- Mở một PR trong danh sách để sửa thông tin, phân công lại reviewer, thêm nhận xét, xử lý nhận xét, yêu cầu chỉnh sửa, phê duyệt và gộp PR.
- Không thể phê duyệt hoặc gộp khi còn nhận xét chưa xử lý. PR đã gộp chỉ cho phép xem.
- Backend hiện là bản demo chạy cục bộ và chưa có đăng nhập/phân quyền. Chỉ chạy trong môi trường tin cậy.
