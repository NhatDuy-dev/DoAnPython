import json
import sqlite3
from typing import List, Optional

from .database import connect, decode, json_value, row_dict
from .schemas import AssignmentResult, AssignmentStatus, AssignmentView, PullRequestIn, ReviewerIn, ReviewerPatch


def upsert_pr(pr: PullRequestIn) -> None:
    with connect() as db:
        db.execute(
            """INSERT INTO pull_requests(pr_id, author_id, repository, changed_files, quality_score, risk_score, required_reviewers)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(pr_id) DO UPDATE SET author_id=excluded.author_id, repository=excluded.repository,
                 changed_files=excluded.changed_files, quality_score=excluded.quality_score,
                 risk_score=excluded.risk_score, required_reviewers=excluded.required_reviewers""",
            (pr.pr_id, pr.author_id, pr.repository, json_value(pr.changed_files), pr.quality_score,
             pr.risk_score, pr.required_reviewers or 1),
        )


def get_pr(pr_id: str) -> Optional[dict]:
    with connect() as db:
        row = row_dict(db.execute("SELECT * FROM pull_requests WHERE pr_id=?", (pr_id,)).fetchone())
    return decode(row) if row else None


def adopt_assignment(pr: PullRequestIn, reviewer_id: str) -> None:
    """Nhập phân công có sẵn từ JSON khi đồng bộ lần đầu."""
    if reviewer_id == pr.author_id:
        raise ValueError("Tác giả PR không thể tự đánh giá.")
    upsert_pr(pr)
    with connect() as db:
        if any(item["reviewer_id"] == reviewer_id for item in _active_assignments(db, pr.pr_id)):
            return
        reviewer = db.execute("SELECT reviewer_id FROM reviewers WHERE reviewer_id=?", (reviewer_id,)).fetchone()
        if reviewer is None:
            raise KeyError(f"Không tìm thấy người đánh giá {reviewer_id}.")
        db.execute(
            "INSERT INTO assignments(pr_id, reviewer_id, status, score, matched_files, reasons) VALUES (?, ?, ?, ?, ?, ?)",
            (pr.pr_id, reviewer_id, AssignmentStatus.ASSIGNED.value, 0, json_value([]),
             json_value(["Đồng bộ phân công có sẵn từ JSON"])),
        )
        db.execute("UPDATE reviewers SET current_load=current_load+1 WHERE reviewer_id=?", (reviewer_id,))


def release_assignments(pr_id: str) -> None:
    """Giải phóng tải của reviewer sau khi PR đã gộp."""
    with connect() as db:
        existing = _active_assignments(db, pr_id)
        for item in existing:
            db.execute("UPDATE assignments SET status=? WHERE assignment_id=?",
                       (AssignmentStatus.RELEASED.value, item["assignment_id"]))
            db.execute("UPDATE reviewers SET current_load=MAX(0, current_load-1) WHERE reviewer_id=?",
                       (item["reviewer_id"],))


def _areas_for_path(path: str) -> set[str]:
    name = path.replace("\\", "/").lower()
    areas = set()
    if any(marker in name for marker in (".env", "config", "secret")):
        areas.add("security")
    if "/tests/" in f"/{name}" or name.split("/")[-1].startswith("test_") or name.endswith((".test.js", ".test.jsx", ".test.ts", ".test.tsx")):
        areas.add("tests")
    if name.endswith((".py", ".go", ".java", ".cs")) or "/api/" in f"/{name}":
        areas.add("backend")
    if name.endswith((".js", ".jsx", ".ts", ".tsx", ".css", ".html")):
        areas.add("frontend")
    if name.endswith((".md", ".rst")):
        areas.add("docs")
    return areas


def upsert_reviewer(reviewer: ReviewerIn) -> dict:
    with connect() as db:
        db.execute(
            """INSERT INTO reviewers(reviewer_id, expertise, is_available, current_load, max_load)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(reviewer_id) DO UPDATE SET expertise=excluded.expertise,
                 is_available=excluded.is_available, current_load=excluded.current_load, max_load=excluded.max_load""",
            (reviewer.reviewer_id, json_value(reviewer.expertise), int(reviewer.is_available),
             reviewer.current_load, reviewer.max_load),
        )
    return get_reviewer(reviewer.reviewer_id)


def update_reviewer(reviewer_id: str, patch: ReviewerPatch) -> dict:
    current = get_reviewer(reviewer_id)
    if not current:
        raise KeyError("reviewer not found")
    values = patch.model_dump(exclude_none=True)
    if "expertise" in values:
        values["expertise"] = json_value(values["expertise"])
    if "is_available" in values:
        values["is_available"] = int(values["is_available"])
    if not values:
        return current
    with connect() as db:
        db.execute("UPDATE reviewers SET " + ", ".join(f"{k}=?" for k in values) + " WHERE reviewer_id=?",
                   (*values.values(), reviewer_id))
    return get_reviewer(reviewer_id)


def get_reviewer(reviewer_id: str) -> Optional[dict]:
    with connect() as db:
        row = row_dict(db.execute("SELECT * FROM reviewers WHERE reviewer_id=?", (reviewer_id,)).fetchone())
    return decode(row) if row else None


def list_reviewers() -> List[dict]:
    with connect() as db:
        rows = db.execute("SELECT * FROM reviewers ORDER BY reviewer_id").fetchall()
    return [decode(dict(row)) for row in rows]


def _active_assignments(db: sqlite3.Connection, pr_id: str) -> List[dict]:
    rows = db.execute("SELECT * FROM assignments WHERE pr_id=? AND status=? ORDER BY assignment_id",
                      (pr_id, AssignmentStatus.ASSIGNED.value)).fetchall()
    return [decode(dict(row)) for row in rows]


def _view(item: dict) -> AssignmentView:
    return AssignmentView(assignment_id=item["assignment_id"], pr_id=item["pr_id"], reviewer_id=item["reviewer_id"],
                          status=item["status"], score=item["score"], matched_files=item["matched_files"],
                          reasons=item["reasons"])


def assign(pr: PullRequestIn, force_reassign: bool = False, exclude: Optional[List[str]] = None,
           fill_missing: bool = False) -> AssignmentResult:
    upsert_pr(pr)
    excluded = set(exclude or [])
    with connect() as db:
        existing = _active_assignments(db, pr.pr_id)
        if existing and not force_reassign and not fill_missing:
            return AssignmentResult(pr_id=pr.pr_id, status="already_assigned", requested=pr.required_reviewers or 1,
                                    assigned=len(existing), message="PR đã có phân công đang hoạt động; giữ nguyên để tránh trùng.",
                                    assignments=[_view(x) for x in existing])
        if force_reassign:
            db.execute("UPDATE assignments SET status=? WHERE pr_id=? AND status=?",
                       (AssignmentStatus.RELEASED.value, pr.pr_id, AssignmentStatus.ASSIGNED.value))
            for item in existing:
                db.execute("UPDATE reviewers SET current_load=MAX(0, current_load-1) WHERE reviewer_id=?", (item["reviewer_id"],))
            existing = []
        if fill_missing:
            excluded.update(item["reviewer_id"] for item in existing)

        reviewers = db.execute("SELECT * FROM reviewers").fetchall()
        candidates = []
        for raw in reviewers:
            reviewer = decode(dict(raw))
            reasons = []
            if reviewer["reviewer_id"] == pr.author_id:
                continue
            if reviewer["reviewer_id"] in excluded:
                continue
            if not reviewer["is_available"]:
                continue
            if reviewer["current_load"] >= reviewer["max_load"]:
                continue
            matched = [
                path for path in pr.changed_files
                if any(
                    path.lower().startswith(skill) or skill in path.lower() or skill in _areas_for_path(path)
                    for skill in reviewer["expertise"]
                )
            ]
            expertise_points = min(60, len(matched) * 20)
            load_points = round(40 * (1 - reviewer["current_load"] / reviewer["max_load"]), 2)
            score = expertise_points + load_points
            reasons.append(f"Chuyên môn khớp {len(matched)} file (+{expertise_points:g})")
            reasons.append(f"Cân bằng tải: {reviewer['current_load']}/{reviewer['max_load']} (+{load_points:g})")
            if pr.risk_score is not None and pr.risk_score >= 50:
                reasons.append(f"PR có risk_score cao ({pr.risk_score:g}); cần review kỹ")
            candidates.append((score, len(matched), -reviewer["current_load"], reviewer, matched, reasons))
        candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]["reviewer_id"]), reverse=True)
        requested = pr.required_reviewers or 1
        selected = candidates[:max(0, requested - len(existing))]
        assignment_rows = list(existing)
        for score, _, _, reviewer, matched, reasons in selected:
            db.execute("INSERT INTO assignments(pr_id, reviewer_id, status, score, matched_files, reasons) VALUES (?, ?, ?, ?, ?, ?)",
                       (pr.pr_id, reviewer["reviewer_id"], AssignmentStatus.ASSIGNED.value, score, json_value(matched), json_value(reasons)))
            db.execute("UPDATE reviewers SET current_load=current_load+1 WHERE reviewer_id=?", (reviewer["reviewer_id"],))
            row = db.execute("SELECT * FROM assignments WHERE assignment_id=last_insert_rowid()").fetchone()
            assignment_rows.append(decode(dict(row)))
        tong_da_phan_cong = len(assignment_rows)
        status = "assigned" if tong_da_phan_cong == requested else "partial"
        message = "Đã phân công đủ reviewer." if status == "assigned" else f"Chỉ tìm được {tong_da_phan_cong}/{requested} reviewer phù hợp; không tự động giao người không phù hợp."
        return AssignmentResult(pr_id=pr.pr_id, status=status, requested=requested, assigned=tong_da_phan_cong, message=message,
                                assignments=[_view(x) for x in assignment_rows])


def current_assignments(pr_id: str) -> List[AssignmentView]:
    with connect() as db:
        return [_view(x) for x in _active_assignments(db, pr_id)]


def reassign(pr_id: str, reviewer_id: str) -> AssignmentResult:
    with connect() as db:
        pr_row = db.execute("SELECT * FROM pull_requests WHERE pr_id=?", (pr_id,)).fetchone()
        if not pr_row:
            raise KeyError("pull request not found")
        existing = _active_assignments(db, pr_id)
        target = next((x for x in existing if x["reviewer_id"] == reviewer_id), None)
        if not target:
            raise KeyError("active assignment not found")
        db.execute("UPDATE assignments SET status=? WHERE assignment_id=?", (AssignmentStatus.REJECTED.value, target["assignment_id"]))
        db.execute("UPDATE reviewers SET current_load=MAX(0, current_load-1) WHERE reviewer_id=?", (reviewer_id,))
        pr = decode(dict(pr_row))
    request = PullRequestIn(**pr)
    return assign(request, exclude=[reviewer_id] + [x.reviewer_id for x in current_assignments(pr_id)],
                  fill_missing=True)


def stats() -> dict:
    with connect() as db:
        totals = db.execute("SELECT COUNT(*) AS total, SUM(status='assigned') AS active, SUM(status='rejected') AS rejected FROM assignments").fetchone()
        loads = [dict(row) for row in db.execute("SELECT reviewer_id, current_load, max_load, is_available FROM reviewers ORDER BY reviewer_id")]
    return {"assignments_total": totals["total"], "active_assignments": totals["active"] or 0,
            "rejected_assignments": totals["rejected"] or 0, "reviewer_loads": loads}

