# Hệ thống đánh giá Pull Request

Năm phần trong bài dùng chung `pull_requests.json`:

| Phần | Tệp chính | Chức năng |
| --- | --- | --- |
| Chất lượng PR | `quality_checker.py` | Tính `quality_score` từ test, lint, file test và mô tả PR |
| Phân công reviewer | `group/`, `reviewer_assignment.py` | TV2 chọn người theo chuyên môn và tải; file cầu nối đồng bộ với JSON |
| Risk Score | `risk_calculator.py` | Tính điểm theo file thay đổi, số dòng và file nhạy cảm |
| Review và Merge | `review_manager.py` | Tạo PR, comment, resolve, yêu cầu sửa, approve và merge |
| Dashboard | `PR-Dashboard/` | Thống kê và hiển thị dữ liệu mới nhất từ JSON |

## Chạy chương trình quản lý

Từ thư mục `code-review-system`, cài thư viện của TV2 rồi chạy:

```powershell
python -m pip install -r .\group\requirements.txt
python .\review_manager.py
```

Chọn `3` để tạo PR. Nhập danh sách file thay đổi, số dòng thêm/xóa, mô tả và kết quả test/lint. Chương trình tự tính chất lượng, rủi ro, chọn reviewer rồi lưu vào JSON. Chọn `2`, nhập mã PR để mở menu đánh giá. Đây là menu trong terminal: **gõ số chức năng rồi nhấn Enter**, chữ trên màn hình không phải nút bấm chuột.

Trong menu đánh giá, mục `3` chỉ ghi nhận yêu cầu chỉnh sửa. Mục `7` dùng để sửa thật các trường của PR (tiêu đề, mô tả, file, số dòng, kết quả test/lint); nhấn Enter để giữ giá trị cũ. Sau khi sửa, điểm được tính lại và PR cần phê duyệt lại. Mục `6` phân công lại reviewer. PR đã gộp chỉ có thể xem; hãy chọn PR001 hoặc tạo PR mới để thử các thao tác.

Có thể chạy riêng hai phần tính điểm:

```powershell
python .\quality_checker.py
python .\risk_calculator.py
```

Hướng dẫn chạy giao diện: [PR-Dashboard/RUN_DEMO.md](PR-Dashboard/RUN_DEMO.md).

## Quy tắc chấm điểm chất lượng

Điểm tối đa 100: test pass **35**, lint pass **30**, có file test trong danh sách thay đổi **20**, có mô tả PR **15**. Hai kết quả test/lint lấy từ `quality_checks` trong JSON hoặc từ câu trả lời khi tạo PR. Chúng là dữ liệu do người dùng cung cấp; chương trình chưa chạy CI hoặc phân tích mã nguồn thật. Nếu thiếu kết quả test/lint, tiêu chí tương ứng nhận 0 điểm.

`reviewers.json` là danh sách nạp ban đầu vào `group/tv2.db`. Từ đó, TV2 trong `group` lưu và quyết định phân công; `reviewer_assignment.py` đồng bộ người được chọn sang `pull_requests.json`. Khi API TV2 phân công lại, chương trình quản lý và Dashboard nhận kết quả mới ở lần đọc tiếp theo. Sau khi gộp PR, TV2 giải phóng tải của reviewer và JSON giữ tên người đã đánh giá để xem lịch sử.

Muốn mở API TV2 song song với Dashboard, chạy từ thư mục `group`: `python -m uvicorn app.main:app --reload --port 8001`, rồi mở `http://127.0.0.1:8001/docs`. Hãy chạy chương trình quản lý một lần trước để nạp danh sách reviewer mẫu.

Các giá trị trong hai PR có sẵn chỉ là dữ liệu mẫu. Hãy thay tên file và kết quả test/lint bằng dữ liệu thực trước khi dùng để đánh giá PR thật.
