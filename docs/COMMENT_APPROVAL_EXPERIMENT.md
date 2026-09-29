# Log thực nghiệm TV4: comment, Approval và Merge

## Chạy lại thực nghiệm

Mở PowerShell tại thư mục dự án rồi chạy:

```powershell
cd D:\DoAnPy\code-review-system
python -m pip install -r requirements.txt
python -m code_review_system.experiment_comment_approval
```

Script dùng bản sao tạm của `data/pull_requests.json` và cơ sở dữ liệu SQLite tạm. Nó chọn PR001, thêm một comment chưa xử lý, kiểm tra Approval bị chặn, resolve comment, phê duyệt lại rồi merge. Mỗi trạng thái quan trọng được kiểm tra trên dữ liệu đã lưu. Dữ liệu mẫu trong dự án không bị sửa. Nếu một điều kiện kiểm tra sai, lệnh kết thúc với mã lỗi khác 0.

## Log chạy thực tế

```text
Bước 1: Thêm comment vào PR001 (nội dung: Cần bổ sung kiểm tra dữ liệu đầu vào; severity: HIGH).

Severity:
1. LOW
2. MEDIUM
3. HIGH

Đã thêm Review Comment.
Sau khi thêm: comment #1 resolved=False; approved=False; status=IN_REVIEW
Bước 2: Thử phê duyệt khi comment còn OPEN.
Không thể APPROVE.
Lý do: Vẫn còn Review Comment chưa Resolve.
Sau khi thử phê duyệt: approved=False; status=IN_REVIEW; comment #1 resolved=False
Bước 3: Resolve comment #1.
Resolve Comment thành công.
Bước 4: Phê duyệt lại và Merge PR001.

Pull Request đã được APPROVE.
Status: APPROVED

================================
MERGE SUCCESSFUL
Pull Request: PR001
================================
Trạng thái cuối: approved=True; status=MERGED; comment #1 resolved=True
Kết quả cuối:
Status: MERGED
Approved: True
Comments resolved: True
KẾT QUẢ: PASS — comment mở chặn Approval; sau khi Resolve, PR được Approve và Merge.
Dữ liệu trong thư mục data/ của dự án không thay đổi.
```

Kết quả: `approve_pr` từ chối khi `has_unresolved_comments` tìm thấy comment có `resolved=False`. Sau lần thử đầu, `approved` vẫn là `False` và trạng thái PR vẫn là `IN_REVIEW`. Sau khi resolve, PR được phê duyệt và gộp thành công với `status=MERGED`, `approved=True`; toàn bộ comment đã được xử lý.

## Thao tác bằng menu

Chạy `python -m code_review_system.review_manager` từ thư mục dự án. Chọn `2` (đánh giá PR), nhập `PR001`, rồi thực hiện lần lượt:

1. Chọn `1` để thêm nhận xét. Để khớp ảnh minh họa, nhập `Cần bổ sung kiểm tra dữ liệu đầu vào`, rồi chọn severity `3` (`HIGH`).
2. Chọn `4` để phê duyệt. Màn hình báo `Không thể APPROVE` khi comment vẫn `OPEN`.
3. Chọn `2`, nhập ID comment hiển thị trong phần `COMMENTS` để đánh dấu đã xử lý.
4. Chọn `4` lần nữa. Khi không còn comment mở và PR có reviewer, phê duyệt thành công.
5. Chọn `5` để gộp PR. Phần chi tiết sẽ hiển thị `Status: MERGED` và `Approved: True`.

Menu này lưu thay đổi vào `data/pull_requests.json`; dùng lệnh thực nghiệm ở trên nếu cần chạy lại mà không thay đổi dữ liệu mẫu.
