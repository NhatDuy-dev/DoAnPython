from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Query

from .database import init_db
from .schemas import AssignmentResult, AssignmentView, PullRequestIn, ReviewerIn, ReviewerPatch
from .service import assign, current_assignments, get_reviewer, list_reviewers, reassign, stats, update_reviewer, upsert_reviewer


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="TV2 - Automatic Reviewer Assignment", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "module": "TV2"}


@app.post("/reviewers", response_model=dict)
def create_reviewer(payload: ReviewerIn):
    return upsert_reviewer(payload)


@app.get("/reviewers", response_model=List[dict])
def reviewers():
    return list_reviewers()


@app.patch("/reviewers/{reviewer_id}", response_model=dict)
def patch_reviewer(reviewer_id: str, payload: ReviewerPatch):
    try:
        return update_reviewer(reviewer_id, payload)
    except KeyError as exc:
        raise HTTPException(404, str(exc))


@app.post("/assignments", response_model=AssignmentResult)
def create_assignments(payload: PullRequestIn, force_reassign: bool = Query(False)):
    return assign(payload, force_reassign=force_reassign)


@app.get("/pull-requests/{pr_id}/assignments", response_model=List[AssignmentView])
def get_assignments(pr_id: str):
    return current_assignments(pr_id)


@app.post("/pull-requests/{pr_id}/assignments/{reviewer_id}/reassign", response_model=AssignmentResult)
def reassign_reviewer(pr_id: str, reviewer_id: str):
    try:
        return reassign(pr_id, reviewer_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))


@app.get("/stats")
def get_stats():
    return stats()

