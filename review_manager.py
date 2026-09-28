import json
from quality_checker import cap_nhat_chat_luong, tinh_diem_chat_luong
from reviewer_assignment import phan_cong_reviewer
from risk_calculator import FILE_NAME, cap_nhat_rui_ro


# ==============================
# ĐỌC DỮ LIỆU
# ==============================
def load_data():
    try:
        with FILE_NAME.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return []
    if dong_bo_prs(data):
        save_data(data)
    return data


# ==============================
# LƯU DỮ LIỆU
# ==============================
def save_data(data):
    dong_bo_prs(data)
    with FILE_NAME.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def dong_bo_prs(data):
    da_thay_doi = False
    for pr in data:
        thay_doi_rui_ro, _ = cap_nhat_rui_ro(pr)
        thay_doi_chat_luong, _ = cap_nhat_chat_luong(pr)
        da_thay_doi |= thay_doi_rui_ro or thay_doi_chat_luong
    for pr in data:
        da_thay_doi |= phan_cong_reviewer(pr)
    return da_thay_doi


# ==============================
# TÌM PULL REQUEST
# ==============================
def find_pr(data, pr_id):

    for pr in data:
        if pr["id"].lower() == pr_id.lower():
            return pr

    return None


# ==============================
# HIỂN THỊ DANH SÁCH PR
# ==============================
def show_pull_requests(data):

    print("\n========== PULL REQUEST LIST ==========")

    if len(data) == 0:
        print("Không có Pull Request.")
        return

    for pr in data:

        print("---------------------------------------")
        print("PR ID:", pr["id"])
        print("Title:", pr["title"])
        print("Author:", pr["author"])
        print("Reviewer:", ", ".join(pr.get("reviewers", [])) or pr.get("reviewer") or "Chưa phân công")
        print("Quality Score:", pr["quality_score"])
        print("Risk Score:", pr["risk_score"])
        print("Risk Level:", pr["risk_level"])
        print("Status:", pr["status"])
        print("Approved:", pr["approved"])


# ==============================
# XEM CHI TIẾT PR
# ==============================
def show_pr_detail(pr):

    print("\n========== PR DETAIL ==========")

    print("PR ID:", pr["id"])
    print("Title:", pr["title"])
    print("Author:", pr["author"])
    print("Reviewer:", ", ".join(pr.get("reviewers", [])) or pr.get("reviewer") or "Chưa phân công")
    print("Quality Score:", pr["quality_score"])
    print("Description:", pr.get("description", ""))
    print("Quality Checks:", tinh_diem_chat_luong(pr)[1])
    print("Changed Files:", pr["danh_sach_file"])
    print("Lines Added/Deleted:", pr["so_dong_them"], "/", pr["so_dong_xoa"])
    print("Sensitive File:", pr["co_chua_file_nhay_cam"])
    print("Risk Score:", pr["risk_score"])
    print("Risk Level:", pr["risk_level"])
    print("Status:", pr["status"])
    print("Approved:", pr["approved"])

    print("\nCOMMENTS:")

    if len(pr["comments"]) == 0:
        print("Không có comment.")
    else:

        for comment in pr["comments"]:

            status = "RESOLVED" if comment["resolved"] else "OPEN"

            print(
                f'[{comment["id"]}] '
                f'{comment["content"]} | '
                f'Severity: {comment["severity"]} | '
                f'Status: {status}'
            )


# ==============================
# THÊM REVIEW COMMENT
# ==============================
def add_comment(pr):
    if pr["status"] == "MERGED":
        print("PR đã Merge, không thể thêm comment.")
        return

    content = input("Nhập nội dung comment: ")

    print("\nSeverity:")
    print("1. LOW")
    print("2. MEDIUM")
    print("3. HIGH")

    choice = input("Chọn severity: ")

    if choice == "1":
        severity = "LOW"

    elif choice == "2":
        severity = "MEDIUM"

    elif choice == "3":
        severity = "HIGH"

    else:
        print("Severity không hợp lệ.")
        return

    comment = {
        "id": len(pr["comments"]) + 1,
        "content": content,
        "severity": severity,
        "resolved": False
    }

    pr["comments"].append(comment)

    pr["approved"] = False
    pr["status"] = "IN_REVIEW"

    print("\nĐã thêm Review Comment.")


# ==============================
# RESOLVE COMMENT
# ==============================
def resolve_comment(pr):

    if len(pr["comments"]) == 0:
        print("PR chưa có comment.")
        return

    show_pr_detail(pr)

    try:
        comment_id = int(input("\nNhập Comment ID cần Resolve: "))

    except ValueError:
        print("Comment ID không hợp lệ.")
        return

    for comment in pr["comments"]:

        if comment["id"] == comment_id:

            if comment["resolved"]:
                print("Comment này đã được Resolve trước đó.")
                return

            comment["resolved"] = True

            print("Resolve Comment thành công.")
            return

    print("Không tìm thấy Comment ID.")


# ==============================
# KIỂM TRA COMMENT CHƯA XỬ LÝ
# ==============================
def has_unresolved_comments(pr):

    for comment in pr["comments"]:

        if not comment["resolved"]:
            return True

    return False


# ==============================
# REQUEST CHANGES
# ==============================
def request_changes(pr):
    if pr["status"] == "MERGED":
        print("PR đã Merge, không thể yêu cầu sửa.")
        return

    pr["approved"] = False
    pr["status"] = "REQUEST_CHANGES"

    print("\nReviewer đã yêu cầu Developer sửa code.")
    print("Status: REQUEST_CHANGES")


# ==============================
# APPROVE
# ==============================
def approve_pr(pr):
    if pr["status"] == "MERGED":
        print("PR đã Merge.")
        return

    if not pr.get("reviewer"):
        print("Không thể APPROVE: PR chưa có reviewer.")
        return

    if has_unresolved_comments(pr):

        print("\nKhông thể APPROVE.")
        print("Lý do: Vẫn còn Review Comment chưa Resolve.")

        return

    pr["approved"] = True
    pr["status"] = "APPROVED"

    print("\nPull Request đã được APPROVE.")
    print("Status: APPROVED")


# ==============================
# MERGE
# ==============================
def merge_pr(pr):

    if pr["status"] == "MERGED":

        print("Pull Request này đã Merge.")
        return

    if not pr["approved"]:

        print("\nMERGE BLOCKED")
        print("Lý do: Pull Request chưa được Approve.")

        return

    if has_unresolved_comments(pr):

        print("\nMERGE BLOCKED")
        print("Lý do: Vẫn còn comment chưa Resolve.")

        return

    pr["status"] = "MERGED"

    print("\n================================")
    print("MERGE SUCCESSFUL")
    print("Pull Request:", pr["id"])
    print("================================")


# ==============================
# REVIEW PR
# ==============================
def edit_pr(pr):
    if pr["status"] == "MERGED":
        print("PR đã gộp, không thể chỉnh sửa.")
        return False

    print("\nNhấn Enter để giữ nguyên giá trị hiện tại. Nhập '-' ở mô tả để xóa mô tả.")
    title = input(f"Tiêu đề [{pr['title']}]: ").strip() or pr["title"]
    mo_ta_nhap = input(f"Mô tả [{pr.get('description', '')}]: ").strip()
    description = pr.get("description", "") if not mo_ta_nhap else "" if mo_ta_nhap == "-" else mo_ta_nhap
    files_nhap = input(f"File thay đổi [{', '.join(pr['danh_sach_file'])}]: ").strip()
    danh_sach_file = (
        [ten.strip() for ten in files_nhap.split(",") if ten.strip()]
        if files_nhap else pr["danh_sach_file"]
    )
    if not danh_sach_file:
        print("Danh sách file không được để trống.")
        return False

    try:
        them_nhap = input(f"Số dòng thêm [{pr['so_dong_them']}]: ").strip()
        xoa_nhap = input(f"Số dòng xóa [{pr['so_dong_xoa']}]: ").strip()
        so_dong_them = int(them_nhap) if them_nhap else pr["so_dong_them"]
        so_dong_xoa = int(xoa_nhap) if xoa_nhap else pr["so_dong_xoa"]
        if so_dong_them < 0 or so_dong_xoa < 0:
            raise ValueError
    except ValueError:
        print("Số dòng phải là số nguyên không âm. PR chưa được chỉnh sửa.")
        return False

    checks = pr.get("quality_checks", {})
    tests_nhap = input("Kiểm thử đạt? (c/k, Enter để giữ nguyên): ").strip().lower()
    lint_nhap = input("Kiểm tra mã đạt? (c/k, Enter để giữ nguyên): ").strip().lower()
    if tests_nhap not in ("", "c", "k", "y", "n") or lint_nhap not in ("", "c", "k", "y", "n"):
        print("Chỉ nhập c/k hoặc nhấn Enter. PR chưa được chỉnh sửa.")
        return False
    quality_checks = {
        "tests_passed": checks.get("tests_passed", False) if not tests_nhap else tests_nhap in ("c", "y"),
        "lint_passed": checks.get("lint_passed", False) if not lint_nhap else lint_nhap in ("c", "y"),
    }
    gia_tri_moi = {
        "title": title,
        "description": description,
        "danh_sach_file": danh_sach_file,
        "so_dong_them": so_dong_them,
        "so_dong_xoa": so_dong_xoa,
        "quality_checks": quality_checks,
    }
    if all(pr.get(ten) == gia_tri for ten, gia_tri in gia_tri_moi.items()):
        print("Không có thông tin nào thay đổi.")
        return False

    pr.update(gia_tri_moi)
    pr["approved"] = False
    pr["status"] = "IN_REVIEW"
    print("Đã chỉnh sửa PR. Cần phê duyệt lại trước khi gộp.")
    return True


def review_menu(data):

    pr_id = input("\nNhập PR ID: ")

    pr = find_pr(data, pr_id)

    if pr is None:

        print("Không tìm thấy Pull Request.")
        return

    while True:

        show_pr_detail(pr)

        print("\n========== MENU ĐÁNH GIÁ PR ==========")
        if pr["status"] == "MERGED":
            print("PR này đã gộp. Chỉ có thể xem thông tin; hãy chọn PR khác để thao tác.")
            print("0. Quay lại")
            if input("Nhập 0 rồi nhấn Enter: ").strip() == "0":
                break
            continue

        print("--- Nhận xét ---")
        print("1. Thêm nhận xét")
        print("2. Đánh dấu nhận xét đã xử lý")
        print("--- Quy trình duyệt ---")
        print("3. Yêu cầu chỉnh sửa")
        print("4. Phê duyệt PR")
        print("5. Gộp PR")
        print("--- Thông tin PR ---")
        print("6. Tự động phân công người đánh giá")
        print("7. Chỉnh sửa thông tin PR")
        print("0. Quay lại")

        choice = input("Nhập số chức năng rồi nhấn Enter: ").strip()

        if choice == "1":

            add_comment(pr)
            save_data(data)

        elif choice == "2":

            resolve_comment(pr)
            save_data(data)

        elif choice == "3":

            request_changes(pr)
            save_data(data)

        elif choice == "4":

            approve_pr(pr)
            save_data(data)

        elif choice == "5":

            merge_pr(pr)
            save_data(data)

        elif choice == "6":

            if pr["status"] == "MERGED":
                print("PR đã Merge, không thể đổi reviewer.")
            elif phan_cong_reviewer(pr, bat_buoc=True):
                print("Reviewer mới:", ", ".join(pr["reviewers"]) or "Chưa phân công")
                save_data(data)
            else:
                print("Không có reviewer phù hợp hơn.")

        elif choice == "7":

            if edit_pr(pr):
                save_data(data)
                print(f"Điểm mới: chất lượng {pr['quality_score']}/100, rủi ro {pr['risk_score']} ({pr['risk_level']}).")

        elif choice == "0":

            break

        else:

            print("Lựa chọn không hợp lệ.")


# ==============================
# MAIN
# ==============================
def create_pr(data):
    title = input("Title: ").strip()
    author = input("Author: ").strip()
    danh_sach_file = [ten.strip() for ten in input("Changed files (cách nhau bằng dấu phẩy): ").split(",") if ten.strip()]
    if not title or not author or not danh_sach_file:
        print("Title, Author và Changed files không được để trống.")
        return

    try:
        so_dong_them = int(input("Lines added: "))
        so_dong_xoa = int(input("Lines deleted: "))
        if so_dong_them < 0 or so_dong_xoa < 0:
            raise ValueError
    except ValueError:
        print("Số dòng phải là số nguyên không âm.")
        return

    description = input("Description (có thể bỏ trống): ").strip()
    tests_passed = input("Tests passed? (y/N): ").strip().lower() == "y"
    lint_passed = input("Lint passed? (y/N): ").strip().lower() == "y"
    so_id = max((int(pr["id"][2:]) for pr in data if pr["id"].startswith("PR") and pr["id"][2:].isdigit()), default=0) + 1
    pr = {
        "id": f"PR{so_id:03d}",
        "title": title,
        "author": author,
        "description": description,
        "danh_sach_file": danh_sach_file,
        "so_dong_them": so_dong_them,
        "so_dong_xoa": so_dong_xoa,
        "quality_checks": {"tests_passed": tests_passed, "lint_passed": lint_passed},
        "reviewer": None,
        "comments": [],
        "approved": False,
        "status": "IN_REVIEW",
    }
    data.append(pr)
    save_data(data)
    print(f"Đã tạo {pr['id']} | Reviewer: {pr['reviewer'] or 'chưa có'} | Quality: {pr['quality_score']} | Risk: {pr['risk_score']} ({pr['risk_level']})")


def main():
    while True:
        data = load_data()

        print("\n======================================")
        print(" QUẢN LÝ ĐÁNH GIÁ PR")
        print("======================================")
        print("1. Xem danh sách PR")
        print("2. Đánh giá PR")
        print("3. Tạo PR mới")
        print("0. Thoát")

        choice = input("Nhập số chức năng rồi nhấn Enter: ").strip()

        if choice == "1":

            show_pull_requests(data)

        elif choice == "2":

            review_menu(data)

        elif choice == "3":

            create_pr(data)

        elif choice == "0":

            print("Exit...")
            break

        else:

            print("Lựa chọn không hợp lệ.")


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
