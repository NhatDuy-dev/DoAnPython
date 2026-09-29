"""Thực nghiệm thêm comment và chặn phê duyệt trên bản sao dữ liệu mẫu."""

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from . import review_manager
from reviewer_service.app import database as tv2_database


def main():
    source = Path(__file__).resolve().parents[1] / "data" / "pull_requests.json"

    with tempfile.TemporaryDirectory() as folder:
        data_file = Path(folder) / "pull_requests.json"
        data_file.write_bytes(source.read_bytes())

        with (
            patch.object(review_manager, "FILE_NAME", data_file),
            patch.object(tv2_database, "DB_PATH", str(Path(folder) / "tv2.db")),
        ):
            data = review_manager.load_data()
            pr = review_manager.find_pr(data, "PR001")
            if pr is None or not pr.get("reviewer") or pr["status"] == "MERGED":
                raise RuntimeError("PR001 phải tồn tại, có reviewer và chưa được gộp.")

            print("Bước 1: Thêm comment vào PR001 (nội dung: Cần bổ sung kiểm tra dữ liệu đầu vào; severity: HIGH).")
            with patch("builtins.input", side_effect=["Cần bổ sung kiểm tra dữ liệu đầu vào", "3"]):
                review_manager.add_comment(pr)
            review_manager.save_data(data)

            comment = pr["comments"][-1]
            print(f"Sau khi thêm: comment #{comment['id']} resolved={comment['resolved']}; "
                  f"approved={pr['approved']}; status={pr['status']}")
            if comment["resolved"] or pr["approved"] or pr["status"] != "IN_REVIEW":
                raise AssertionError("Trạng thái sau khi thêm comment không đúng.")

            print("Bước 2: Thử phê duyệt khi comment còn OPEN.")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                review_manager.approve_pr(pr)
            message = output.getvalue().strip()
            print(message)
            review_manager.save_data(data)

            saved = next(item for item in json.loads(data_file.read_text(encoding="utf-8"))
                         if item["id"] == "PR001")
            print(f"Sau khi thử phê duyệt: approved={saved['approved']}; "
                  f"status={saved['status']}; comment #{comment['id']} "
                  f"resolved={saved['comments'][-1]['resolved']}")
            if ("Không thể APPROVE" not in message or saved["approved"]
                    or saved["status"] != "IN_REVIEW"
                    or saved["comments"][-1]["resolved"]):
                raise AssertionError("Hệ thống đã không chặn Approval như mong đợi.")

            print(f"Bước 3: Resolve comment #{comment['id']}.")
            output = io.StringIO()
            with patch("builtins.input", return_value=str(comment["id"])), contextlib.redirect_stdout(output):
                review_manager.resolve_comment(pr)
            if "Resolve Comment thành công." not in output.getvalue() or not comment["resolved"]:
                raise AssertionError("Không resolve được comment.")
            print("Resolve Comment thành công.")

            print("Bước 4: Phê duyệt lại và Merge PR001.")
            review_manager.approve_pr(pr)
            if not pr["approved"] or pr["status"] != "APPROVED":
                raise AssertionError("PR chưa được phê duyệt sau khi resolve comment.")
            review_manager.merge_pr(pr)
            review_manager.save_data(data)
            saved = next(item for item in json.loads(data_file.read_text(encoding="utf-8"))
                         if item["id"] == "PR001")
            print(f"Trạng thái cuối: approved={saved['approved']}; status={saved['status']}; "
                  f"comment #{comment['id']} resolved={saved['comments'][-1]['resolved']}")
            if (not saved["approved"] or saved["status"] != "MERGED"
                    or not saved["comments"][-1]["resolved"]):
                raise AssertionError("Trạng thái cuối sau khi Merge không đúng.")

            print("Kết quả cuối:")
            print(f"Status: {saved['status']}")
            print(f"Approved: {saved['approved']}")
            print(f"Comments resolved: {all(item['resolved'] for item in saved['comments'])}")
            print("KẾT QUẢ: PASS — comment mở chặn Approval; sau khi Resolve, PR được Approve và Merge.")
            print("Dữ liệu trong thư mục data/ của dự án không thay đổi.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
