import json

from .risk_calculator import FILE_NAME


# Điểm dựa trên kết quả kiểm tra được ghi trong JSON và thông tin của PR.
TRONG_SO = {
    "tests_passed": 35,
    "lint_passed": 30,
    "test_files_changed": 20,
    "has_description": 15,
}


def la_file_test(ten_file):
    ten = ten_file.replace("\\", "/").lower()
    ten_cuoi = ten.split("/")[-1]
    return (
        ten_cuoi.startswith("test_")
        or "/tests/" in f"/{ten}"
        or ten.endswith((".test.js", ".test.jsx", ".test.ts", ".test.tsx"))
    )


def tinh_diem_chat_luong(pr):
    checks = pr.get("quality_checks", {})
    ket_qua = {
        "tests_passed": checks.get("tests_passed") is True,
        "lint_passed": checks.get("lint_passed") is True,
        "test_files_changed": any(la_file_test(ten_file) for ten_file in pr["danh_sach_file"]),
        "has_description": bool(pr.get("description", "").strip()),
    }
    diem = sum(TRONG_SO[ten] for ten, dat in ket_qua.items() if dat)
    return diem, ket_qua


def cap_nhat_chat_luong(pr):
    diem, ket_qua = tinh_diem_chat_luong(pr)
    da_thay_doi = pr.get("quality_score") != diem
    pr["quality_score"] = diem
    return da_thay_doi, ket_qua


if __name__ == "__main__":
    with FILE_NAME.open("r", encoding="utf-8") as file:
        pull_requests = json.load(file)

    can_luu = False
    for pr in pull_requests:
        da_thay_doi, chi_tiet = cap_nhat_chat_luong(pr)
        can_luu = can_luu or da_thay_doi
        print(f"{pr['id']} - {pr['title']}: {pr['quality_score']}/100")
        print(f"  Chi tiet: {chi_tiet}")

    if can_luu:
        with FILE_NAME.open("w", encoding="utf-8") as file:
            json.dump(pull_requests, file, indent=4, ensure_ascii=False)
