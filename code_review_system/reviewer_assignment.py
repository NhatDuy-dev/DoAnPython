"""Kết nối chương trình quản lý PR với reviewer service."""

import json
from pathlib import Path

from reviewer_service.app import database as tv2_database
from reviewer_service.app import service as tv2_service
from reviewer_service.app.schemas import PullRequestIn, ReviewerIn


REVIEWERS_FILE = Path(__file__).resolve().parents[1] / "data" / "reviewers.json"
_duong_dan_da_khoi_tao = None


def load_reviewers():
    """Danh sách ban đầu; thay đổi sau đó được lưu trong SQLite của TV2."""
    with REVIEWERS_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def khoi_tao_tv2():
    global _duong_dan_da_khoi_tao
    duong_dan = str(tv2_database.DB_PATH)
    if _duong_dan_da_khoi_tao == duong_dan:
        return
    tv2_database.init_db()
    for nguoi in load_reviewers():
        if tv2_service.get_reviewer(nguoi["name"]) is None:
            tv2_service.upsert_reviewer(ReviewerIn(
                reviewer_id=nguoi["name"],
                expertise=nguoi.get("skills", []),
                is_available=nguoi.get("active", True),
            ))
    _duong_dan_da_khoi_tao = duong_dan


def _du_lieu_tv2(pr):
    return PullRequestIn(
        pr_id=pr["id"],
        author_id=pr["author"],
        repository="code-review-system",
        changed_files=pr["danh_sach_file"],
        quality_score=pr.get("quality_score"),
        risk_score=min(pr["risk_score"], 100),
        required_reviewers=pr.get("required_reviewers", 1),
    )


def phan_cong_reviewer(pr, pull_requests=None, reviewers=None, bat_buoc=False):
    """Đồng bộ phân công TV2 sang JSON; bat_buoc chọn lại người đánh giá."""
    khoi_tao_tv2()
    da_thay_doi = False
    ban_ghi_cu = tv2_service.get_pr(pr["id"])
    if ban_ghi_cu is not None and pr.get("required_reviewers") != ban_ghi_cu["required_reviewers"]:
        pr["required_reviewers"] = ban_ghi_cu["required_reviewers"]
        da_thay_doi = True
    yeu_cau = _du_lieu_tv2(pr)

    if ban_ghi_cu is None:
        nguoi_da_co = pr.get("reviewers") or ([pr["reviewer"]] if pr.get("reviewer") else [])
        if nguoi_da_co:
            for ten in nguoi_da_co:
                if tv2_service.get_reviewer(ten) is None:
                    tv2_service.upsert_reviewer(ReviewerIn(reviewer_id=ten))
                tv2_service.adopt_assignment(yeu_cau, ten)
        else:
            tv2_service.assign(yeu_cau)
        pr["required_reviewers"] = yeu_cau.required_reviewers or 1
        da_thay_doi = True
    else:
        truong_can_kiem_tra = ("author_id", "repository", "changed_files", "quality_score", "risk_score", "required_reviewers")
        moi = yeu_cau.model_dump()
        if any(ban_ghi_cu[ten] != moi[ten] for ten in truong_can_kiem_tra):
            tv2_service.upsert_pr(yeu_cau)

    if pr["status"] == "MERGED":
        tv2_service.release_assignments(pr["id"])
        if "reviewers" not in pr:
            pr["reviewers"] = [pr["reviewer"]] if pr.get("reviewer") else []
            da_thay_doi = True
        return da_thay_doi

    hien_tai = tv2_service.current_assignments(pr["id"])
    if bat_buoc:
        nguoi_cu = [item.reviewer_id for item in hien_tai]
        ung_vien_khac = [
            nguoi for nguoi in tv2_service.list_reviewers()
            if nguoi["reviewer_id"] not in nguoi_cu
            and nguoi["reviewer_id"] != pr["author"]
            and nguoi["is_available"]
            and nguoi["current_load"] < nguoi["max_load"]
        ]
        if ung_vien_khac:
            tv2_service.assign(yeu_cau, force_reassign=bool(hien_tai), exclude=nguoi_cu)
            hien_tai = tv2_service.current_assignments(pr["id"])

    danh_sach_moi = [item.reviewer_id for item in hien_tai]
    nguoi_dau = danh_sach_moi[0] if danh_sach_moi else None
    if pr.get("reviewers") != danh_sach_moi or pr.get("reviewer") != nguoi_dau:
        pr["reviewers"] = danh_sach_moi
        pr["reviewer"] = nguoi_dau
        da_thay_doi = True
    return da_thay_doi
