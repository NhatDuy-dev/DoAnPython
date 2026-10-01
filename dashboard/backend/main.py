from threading import RLock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from code_review_system.review_manager import find_pr, has_unresolved_comments, load_data, save_data
from code_review_system.quality_checker import tinh_diem_chat_luong
from code_review_system.reviewer_assignment import phan_cong_reviewer


app = FastAPI(title="Pull Request Quality Dashboard")
write_lock = RLock()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PRContent(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    danh_sach_file: list[str] = Field(min_length=1)
    so_dong_them: int = Field(ge=0)
    so_dong_xoa: int = Field(ge=0)
    tests_passed: bool = False
    lint_passed: bool = False

    @field_validator("title")
    @classmethod
    def valid_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Tiêu đề không được để trống.")
        return value

    @field_validator("danh_sach_file")
    @classmethod
    def valid_files(cls, value):
        files = [name.strip() for name in value if name.strip()]
        if not files:
            raise ValueError("Cần ít nhất một file thay đổi.")
        return files


class CreatePR(PRContent):
    author: str = Field(min_length=1)

    @field_validator("author")
    @classmethod
    def valid_author(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Tác giả không được để trống.")
        return value


class NewComment(BaseModel):
    content: str = Field(min_length=1)
    severity: str = "MEDIUM"

    @field_validator("content")
    @classmethod
    def valid_content(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Nội dung nhận xét không được để trống.")
        return value

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, value):
        if value not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError("Mức độ nhận xét không hợp lệ.")
        return value


def get_pr_or_404(data, pr_id):
    pr = find_pr(data, pr_id)
    if pr is None:
        raise HTTPException(404, "Không tìm thấy pull request.")
    return pr


def ensure_editable(pr):
    if pr["status"] == "MERGED":
        raise HTTPException(409, "PR đã gộp, chỉ có thể xem.")


def content_values(payload):
    return {
        "title": payload.title,
        "description": payload.description.strip(),
        "danh_sach_file": payload.danh_sach_file,
        "so_dong_them": payload.so_dong_them,
        "so_dong_xoa": payload.so_dong_xoa,
        "quality_checks": {
            "tests_passed": payload.tests_passed,
            "lint_passed": payload.lint_passed,
        },
    }


def saved_pr(data, pr):
    save_data(data)
    return pr


def build_dashboard():
    prs = load_data()
    total = len(prs)
    stats = {
        "total_pr": total,
        "open": sum(pr["status"] in ("IN_REVIEW", "REQUEST_CHANGES", "OPEN") for pr in prs),
        "approved": sum(pr["status"] == "APPROVED" for pr in prs),
        "rejected": sum(pr["status"] == "REJECTED" for pr in prs),
        "merged": sum(pr["status"] == "MERGED" for pr in prs),
    }
    risk = {
        "low": sum(pr["risk_level"] == "LOW" for pr in prs),
        "medium": sum(pr["risk_level"] == "MEDIUM" for pr in prs),
        "high": sum(pr["risk_level"] == "HIGH" for pr in prs),
    }

    reviewers = {}
    for pr in prs:
        for reviewer in pr.get("reviewers") or [pr["reviewer"] or "Unassigned"]:
            if reviewer not in reviewers:
                reviewers[reviewer] = {"reviews": 0, "average_score": 0}
            reviewers[reviewer]["reviews"] += 1
            reviewers[reviewer]["average_score"] += pr["quality_score"]
    for summary in reviewers.values():
        summary["average_score"] = round(
            summary["average_score"] / summary["reviews"], 2
        )

    return {
        "statistics": stats,
        "risk_score": risk,
        "reviewer": reviewers,
        "metrics": {
            "approval_rate": round(
                sum(pr["approved"] for pr in prs) / total * 100, 2
            ) if total else 0,
            "average_quality_score": round(
                sum(pr["quality_score"] for pr in prs) / total, 2
            ) if total else 0,
        },
        "pull_requests": [
            {
                "id": pr["id"],
                "title": pr["title"],
                "author": pr["author"],
                "description": pr.get("description", ""),
                "danh_sach_file": pr["danh_sach_file"],
                "so_dong_them": pr["so_dong_them"],
                "so_dong_xoa": pr["so_dong_xoa"],
                "reviewer": ", ".join(pr.get("reviewers", [])) or pr["reviewer"],
                "reviewers": pr.get("reviewers", []),
                "comments": pr.get("comments", []),
                "approved": pr.get("approved", False),
                "status": pr["status"],
                "quality_score": pr["quality_score"],
                "quality_checks": tinh_diem_chat_luong(pr)[1],
                "risk_score": pr["risk_score"],
                "risk_level": pr["risk_level"],
            }
            for pr in prs
        ],
    }


@app.get("/")
def home():
    return {"message": "Pull Request Dashboard API"}


@app.get("/dashboard/overview")
def overview():
    return build_dashboard()


@app.get("/dashboard/statistics")
def statistics():
    return build_dashboard()["statistics"]


@app.get("/dashboard/risk-score")
def risk_score():
    return build_dashboard()["risk_score"]


@app.get("/dashboard/reviewer")
def reviewer():
    return build_dashboard()["reviewer"]


@app.get("/dashboard/metrics")
def metrics():
    return build_dashboard()["metrics"]


@app.post("/pull-requests", status_code=201)
def create_pull_request(payload: CreatePR):
    with write_lock:
        data = load_data()
        next_number = max(
            (int(pr["id"][2:]) for pr in data
             if pr["id"].startswith("PR") and pr["id"][2:].isdigit()),
            default=0,
        ) + 1
        pr = {
            "id": f"PR{next_number:03d}",
            "author": payload.author,
            **content_values(payload),
            "reviewer": None,
            "comments": [],
            "approved": False,
            "status": "IN_REVIEW",
        }
        data.append(pr)
        return saved_pr(data, pr)


@app.put("/pull-requests/{pr_id}")
def update_pull_request(pr_id: str, payload: PRContent):
    with write_lock:
        data = load_data()
        pr = get_pr_or_404(data, pr_id)
        ensure_editable(pr)
        values = content_values(payload)
        if any(pr.get(key) != value for key, value in values.items()):
            pr.update(values)
            pr["approved"] = False
            pr["status"] = "IN_REVIEW"
        return saved_pr(data, pr)


@app.post("/pull-requests/{pr_id}/comments", status_code=201)
def add_review_comment(pr_id: str, payload: NewComment):
    with write_lock:
        data = load_data()
        pr = get_pr_or_404(data, pr_id)
        ensure_editable(pr)
        comment = {
            "id": max((item["id"] for item in pr["comments"]), default=0) + 1,
            "content": payload.content,
            "severity": payload.severity,
            "resolved": False,
        }
        pr["comments"].append(comment)
        pr["approved"] = False
        pr["status"] = "IN_REVIEW"
        return saved_pr(data, pr)


@app.patch("/pull-requests/{pr_id}/comments/{comment_id}/resolve")
def resolve_review_comment(pr_id: str, comment_id: int):
    with write_lock:
        data = load_data()
        pr = get_pr_or_404(data, pr_id)
        ensure_editable(pr)
        comment = next((item for item in pr["comments"] if item["id"] == comment_id), None)
        if comment is None:
            raise HTTPException(404, "Không tìm thấy nhận xét.")
        if comment["resolved"]:
            raise HTTPException(409, "Nhận xét đã được xử lý.")
        comment["resolved"] = True
        return saved_pr(data, pr)


@app.post("/pull-requests/{pr_id}/request-changes")
def request_pr_changes(pr_id: str):
    with write_lock:
        data = load_data()
        pr = get_pr_or_404(data, pr_id)
        ensure_editable(pr)
        pr["approved"] = False
        pr["status"] = "REQUEST_CHANGES"
        return saved_pr(data, pr)


@app.post("/pull-requests/{pr_id}/approve")
def approve_pull_request(pr_id: str):
    with write_lock:
        data = load_data()
        pr = get_pr_or_404(data, pr_id)
        ensure_editable(pr)
        if not pr.get("reviewer"):
            raise HTTPException(409, "PR chưa có reviewer.")
        if has_unresolved_comments(pr):
            raise HTTPException(409, "Vẫn còn nhận xét chưa xử lý.")
        pr["approved"] = True
        pr["status"] = "APPROVED"
        return saved_pr(data, pr)


@app.post("/pull-requests/{pr_id}/merge")
def merge_pull_request(pr_id: str):
    with write_lock:
        data = load_data()
        pr = get_pr_or_404(data, pr_id)
        ensure_editable(pr)
        if not pr["approved"]:
            raise HTTPException(409, "PR chưa được phê duyệt.")
        if has_unresolved_comments(pr):
            raise HTTPException(409, "Vẫn còn nhận xét chưa xử lý.")
        pr["status"] = "MERGED"
        return saved_pr(data, pr)


@app.post("/pull-requests/{pr_id}/reassign")
def reassign_reviewer(pr_id: str):
    with write_lock:
        data = load_data()
        pr = get_pr_or_404(data, pr_id)
        ensure_editable(pr)
        if not phan_cong_reviewer(pr, bat_buoc=True):
            raise HTTPException(409, "Không có reviewer phù hợp khác.")
        pr["approved"] = False
        pr["status"] = "IN_REVIEW"
        return saved_pr(data, pr)
