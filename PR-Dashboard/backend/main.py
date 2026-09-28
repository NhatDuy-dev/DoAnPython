import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# Chia sẻ nguồn dữ liệu và công thức rủi ro với chương trình quản lý PR.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from review_manager import load_data  # noqa: E402
from quality_checker import tinh_diem_chat_luong  # noqa: E402


app = FastAPI(title="Pull Request Quality Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
                "reviewer": ", ".join(pr.get("reviewers", [])) or pr["reviewer"],
                "reviewers": pr.get("reviewers", []),
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
