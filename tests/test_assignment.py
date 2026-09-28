import os

os.environ["TV2_DB_PATH"] = "test_tv2.db"

import pytest

from reviewer_service.app.database import init_db
from reviewer_service.app.schemas import PullRequestIn, ReviewerIn
from reviewer_service.app.service import assign, current_assignments, reassign, stats, upsert_reviewer


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    path = tmp_path / "tv2.db"
    monkeypatch.setenv("TV2_DB_PATH", str(path))
    import reviewer_service.app.database as database
    database.DB_PATH = str(path)
    init_db()


def pr(**kwargs):
    data = dict(pr_id="PR-1", author_id="author", repository="org/repo", changed_files=["backend/a.py"], required_reviewers=1)
    data.update(kwargs)
    return PullRequestIn(**data)


def test_does_not_assign_author_and_prefers_expertise():
    upsert_reviewer(ReviewerIn(reviewer_id="author", expertise=["backend/"], max_load=3))
    upsert_reviewer(ReviewerIn(reviewer_id="general", expertise=[], max_load=3))
    upsert_reviewer(ReviewerIn(reviewer_id="expert", expertise=["backend/"], max_load=3))
    result = assign(pr())
    assert result.assignments[0].reviewer_id == "expert"
    assert result.assignments[0].reviewer_id != "author"


def test_balances_load_and_skips_unavailable_or_full():
    upsert_reviewer(ReviewerIn(reviewer_id="busy", expertise=["backend/"], current_load=2, max_load=2))
    upsert_reviewer(ReviewerIn(reviewer_id="away", expertise=["backend/"], is_available=False))
    upsert_reviewer(ReviewerIn(reviewer_id="free", expertise=["backend/"], current_load=0, max_load=3))
    assert assign(pr()).assignments[0].reviewer_id == "free"


def test_high_risk_is_explained_and_multiple_reviewers_supported():
    upsert_reviewer(ReviewerIn(reviewer_id="r1", expertise=["backend/"], max_load=3))
    upsert_reviewer(ReviewerIn(reviewer_id="r2", expertise=["backend/"], max_load=3))
    result = assign(pr(risk_score=90, required_reviewers=2))
    assert result.assigned == 2
    assert any("risk_score cao" in reason for reason in result.assignments[0].reasons)


def test_resubmitting_same_pr_is_idempotent_and_shortage_is_explicit():
    upsert_reviewer(ReviewerIn(reviewer_id="only", max_load=3))
    first = assign(pr())
    second = assign(pr())
    assert first.assignments[0].reviewer_id == second.assignments[0].reviewer_id
    assert second.status == "already_assigned"
    shortage = assign(pr(pr_id="PR-2", required_reviewers=2))
    assert shortage.status == "partial"
    assert "không tự động" in shortage.message


def test_reassign_releases_old_load_and_selects_new_reviewer():
    upsert_reviewer(ReviewerIn(reviewer_id="r1", max_load=3))
    upsert_reviewer(ReviewerIn(reviewer_id="r2", max_load=3))
    first = assign(pr())
    replacement = reassign("PR-1", first.assignments[0].reviewer_id)
    assert replacement.assigned == 1
    assert replacement.assignments[0].reviewer_id != first.assignments[0].reviewer_id
    assert len(current_assignments("PR-1")) == 1
    assert stats()["rejected_assignments"] == 1

