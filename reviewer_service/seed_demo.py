"""Nạp dữ liệu mẫu và in một lần phân công để demo nhanh."""
import os
import sys
from pathlib import Path

os.environ.setdefault("TV2_DB_PATH", str(Path(__file__).resolve().parents[1] / "data" / "demo_tv2.db"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from reviewer_service.app.database import init_db
from reviewer_service.app.schemas import PullRequestIn, ReviewerIn
from reviewer_service.app.service import assign, upsert_reviewer

init_db()
for reviewer in [
    ReviewerIn(reviewer_id="alice", expertise=["backend/", "api"], max_load=2),
    ReviewerIn(reviewer_id="bob", expertise=["frontend/"], current_load=1, max_load=3),
    ReviewerIn(reviewer_id="carol", expertise=["database/"], is_available=False),
]:
    upsert_reviewer(reviewer)
result = assign(PullRequestIn(pr_id="PR-DEMO-1", author_id="alice", repository="demo/repo",
                              changed_files=["backend/auth.py", "frontend/login.js"], quality_score=82, risk_score=75,
                              required_reviewers=2))
print(result.model_dump_json(indent=2))

