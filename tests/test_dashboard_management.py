import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from code_review_system import review_manager
from dashboard.backend.main import app
from reviewer_service.app import database as reviewer_database


def test_admin_pr_workflow():
    with tempfile.TemporaryDirectory() as folder:
        data_file = Path(folder) / "prs.json"
        data_file.write_text("[]", encoding="utf-8")
        with patch.object(review_manager, "FILE_NAME", data_file), patch.object(
            reviewer_database, "DB_PATH", str(Path(folder) / "reviewers.db")
        ), TestClient(app) as client:
            body = {
                "title": "Cập nhật API",
                "author": "Duy",
                "description": "Bổ sung endpoint",
                "danh_sach_file": ["src/api.py", "tests/test_api.py"],
                "so_dong_them": 30,
                "so_dong_xoa": 5,
                "tests_passed": True,
                "lint_passed": True,
            }
            created = client.post("/pull-requests", json=body)
            assert created.status_code == 201, created.text
            pr = created.json()
            assert pr["id"] == "PR001"
            assert pr["reviewer"]
            assert pr["quality_score"] == 100
            assert client.get("/dashboard/overview").json()["statistics"]["total_pr"] == 1

            changed = client.put("/pull-requests/PR001", json={**body, "title": "API mới"})
            assert changed.status_code == 200
            assert changed.json()["title"] == "API mới"
            comment = client.post("/pull-requests/PR001/comments", json={
                "content": "Cần bổ sung kiểm tra", "severity": "HIGH"
            })
            assert comment.status_code == 201
            assert client.post("/pull-requests/PR001/approve").status_code == 409
            assert client.patch("/pull-requests/PR001/comments/1/resolve").status_code == 200
            assert client.post("/pull-requests/PR001/request-changes").json()["status"] == "REQUEST_CHANGES"
            assert client.post("/pull-requests/PR001/approve").json()["approved"] is True
            assert client.post("/pull-requests/PR001/merge").json()["status"] == "MERGED"
            assert client.put("/pull-requests/PR001", json=body).status_code == 409
            assert client.post("/pull-requests/PR001/comments", json={
                "content": "Too late", "severity": "LOW"
            }).status_code == 409
            saved = json.loads(data_file.read_text(encoding="utf-8"))[0]
            assert saved["status"] == "MERGED"
            assert saved["comments"][0]["resolved"] is True


def test_admin_validation_and_reassignment():
    with tempfile.TemporaryDirectory() as folder:
        data_file = Path(folder) / "prs.json"
        data_file.write_text("[]", encoding="utf-8")
        with patch.object(review_manager, "FILE_NAME", data_file), patch.object(
            reviewer_database, "DB_PATH", str(Path(folder) / "reviewers.db")
        ), TestClient(app) as client:
            body = {
                "title": "Frontend update", "author": "Duy", "description": "",
                "danh_sach_file": ["src/App.jsx"], "so_dong_them": 2,
                "so_dong_xoa": 1, "tests_passed": False, "lint_passed": False,
            }
            assert client.post("/pull-requests", json={**body, "danh_sach_file": []}).status_code == 422
            pr = client.post("/pull-requests", json=body).json()
            original = pr["reviewer"]
            reassigned = client.post(f"/pull-requests/{pr['id']}/reassign")
            assert reassigned.status_code == 200, reassigned.text
            assert reassigned.json()["reviewer"] != original
            assert client.post("/pull-requests/UNKNOWN/approve").status_code == 404
