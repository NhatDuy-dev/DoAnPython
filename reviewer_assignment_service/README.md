# TV2 - Tự động phân công reviewer

Module TV2 cho đồ án “Hệ thống quản lý code review và chất lượng Pull Request”. TV2 dùng FastAPI, Pydantic và SQLite để phân công reviewer. `../reviewer_assignment.py` kết nối TV2 với chương trình quản lý PR và Dashboard; phần chấm chất lượng, tính rủi ro và quy trình review vẫn thuộc các module khác.

## 1. Cài đặt và chạy

Yêu cầu Python 3.10 trở lên.

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
```

Mở `http://127.0.0.1:8001/docs` để demo Swagger. Mặc định API dùng `tv2.db` trong thư mục `group`, cùng file với chương trình quản lý PR. Hãy chạy `python ../review_manager.py` một lần trước để nạp reviewer mẫu và các PR hiện có. `python seed_demo.py` là demo riêng (tạo `demo_tv2.db`), không đồng bộ với chương trình quản lý. Có thể chọn file DB khác bằng biến môi trường `TV2_DB_PATH`, nhưng hai chương trình phải trỏ đến cùng file nếu muốn đồng bộ.

## 2. Hợp đồng dữ liệu tích hợp

Đây là quy ước hiện tại của nhóm và được định nghĩa tập trung trong `app/schemas.py`.

| Đối tượng | Bắt buộc | Tùy chọn / quy ước |
|---|---|---|
| Pull Request | `pr_id`, `author_id`, `repository`, `changed_files` | `quality_score`, `risk_score`, `required_reviewers`; score dùng thang 0-100 |
| Reviewer | `reviewer_id` | `expertise` là prefix đường dẫn hoặc từ khóa; `is_available` mặc định true; `current_load` mặc định 0; `max_load` mặc định 3 |
| Assignment | `pr_id`, `reviewer_id`, `status`, `score`, `matched_files`, `reasons` | `status`: `assigned`, `rejected`, `released` |

TV1 và TV3 không cần hoàn thành trước TV2: bỏ qua hai score là hợp lệ. `required_reviewers` mặc định 1. Điểm phân công nội bộ không phải quality/risk score: tối đa 60 điểm chuyên môn (20 điểm cho mỗi file khớp, tối đa 60) và 40 điểm cân bằng tải. Điểm cao hơn được chọn trước; tiếp theo ưu tiên số file khớp, tải hiện tại thấp hơn và cuối cùng là ID để kết quả ổn định.

## 3. Quy tắc phân công

TV2 loại tác giả PR, reviewer không sẵn sàng, reviewer đã đạt `current_load >= max_load`, reviewer bị loại khi phân công lại và reviewer đã có assignment hoạt động cho PR đó. Reviewer được sắp xếp theo điểm minh bạch; mỗi response trả về `matched_files` và `reasons`.

TV2 ghi chú PR rủi ro cao khi `risk_score >= 50`, cùng ngưỡng với `risk_calculator.py`.

Nếu số ứng viên ít hơn `required_reviewers`, response có `status=partial`, số lượng `assigned` thực tế và thông báo rõ ràng. Module không giao người không phù hợp để cố đạt đủ số lượng. Gửi lại cùng PR khi đã có assignment hoạt động trả về `already_assigned` và giữ nguyên kết quả. Dùng `force_reassign=true` chỉ khi muốn giải phóng phân công cũ và chọn lại.

## 4. API chính

- `POST /reviewers`: thêm hoặc cập nhật reviewer.
- `GET /reviewers`: danh sách reviewer và tải hiện tại.
- `PATCH /reviewers/{reviewer_id}`: cập nhật chuyên môn, availability hoặc tải.
- `POST /assignments`: nhận PR và phân công; query `force_reassign=true` để phân công lại toàn bộ.
- `GET /pull-requests/{pr_id}/assignments`: TV4 lấy assignment đang hoạt động.
- `POST /pull-requests/{pr_id}/assignments/{reviewer_id}/reassign`: đánh dấu reviewer từ chối và chọn người thay thế.
- `GET /stats`: TV5 lấy tổng assignment, assignment active/rejected và tải từng reviewer.
- `GET /health`: health check.

Ví dụ request:

```json
{
  "pr_id": "PR-101",
  "author_id": "u01",
  "repository": "group/review-system",
  "changed_files": ["backend/auth.py", "frontend/login.js"],
  "quality_score": 84,
  "risk_score": 72,
  "required_reviewers": 2
}
```

Ví dụ response rút gọn:

```json
{
  "pr_id": "PR-101", "status": "assigned", "requested": 2, "assigned": 2,
  "message": "Đã phân công đủ reviewer.",
  "assignments": [{
    "reviewer_id": "u07", "status": "assigned", "score": 100,
    "matched_files": ["backend/auth.py"],
    "reasons": ["Chuyên môn khớp 1 file (+20)", "Cân bằng tải: 0/3 (+40)"]
  }]
}
```

## 5. Kết nối các module

`pull_requests.json` là nguồn dữ liệu PR. Khi chương trình quản lý hoặc Dashboard đọc file, `reviewer_assignment.py` gửi thông tin PR và điểm từ TV1/TV3 sang TV2, rồi chép phân công hiện tại về JSON. TV4 có thể gọi API reassign; Dashboard tự đọc lại JSON sau tối đa 5 giây. TV2 quản lý trạng thái phân công trong `tv2.db` và không gọi GitHub. PR chỉ được tạo qua API TV2 sẽ không xuất hiện trên Dashboard vì thiếu dữ liệu review và rủi ro trong JSON.

## 6. Kiểm thử

```bash
pytest -q
```

Test bao phủ loại tác giả, ưu tiên chuyên môn, cân bằng tải, reviewer không sẵn sàng/đầy tải, PR risk cao, gửi lại idempotent, thiếu reviewer và phân công lại.

## 7. Giả định cần nhóm xác nhận

Nhóm cần thống nhất tên trường ID, score 0-100, ý nghĩa `expertise` (prefix path hay taxonomy), số reviewer mặc định, và việc TV2 chỉ báo risk cao hay có được thay đổi số reviewer theo risk. Bản hiện tại chỉ ghi nhận risk cao trong lý do, không tự quyết định số reviewer.
