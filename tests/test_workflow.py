import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]

from dashboard.backend import main as dashboard_api
from code_review_system import review_manager
from code_review_system.reviewer_assignment import phan_cong_reviewer
from reviewer_service.app import database as tv2_database
from reviewer_service.app import service as tv2_service
from reviewer_service.app.main import app as tv2_app
from reviewer_service.app.schemas import PullRequestIn


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.data_file = Path(self.folder.name) / "pull_requests.json"
        self.data_file.write_text(
            (ROOT / "tests" / "fixtures" / "pull_requests.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.file_patch = patch.object(review_manager, "FILE_NAME", self.data_file)
        self.file_patch.start()
        self.db_patch = patch.object(tv2_database, "DB_PATH", str(Path(self.folder.name) / "tv2.db"))
        self.db_patch.start()

    def tearDown(self):
        self.file_patch.stop()
        self.db_patch.stop()
        self.folder.cleanup()

    def test_create_review_merge_and_dashboard(self):
        data = review_manager.load_data()
        merged_before = sum(pr["status"] == "MERGED" for pr in data)
        answers = [
            "Frontend update", "Duy", "src/App.jsx,tests/App.test.jsx",
            "30", "5", "Add dashboard view", "y", "y",
        ]
        with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
            review_manager.create_pr(data)

        pr = data[-1]
        self.assertEqual((pr["id"], pr["reviewer"]), ("PR003", "Chi"))
        self.assertEqual(pr["quality_score"], 100)
        self.assertEqual((pr["risk_score"], pr["risk_level"]), (9, "LOW"))

        with patch("builtins.input", side_effect=["Fix layout", "3"]), contextlib.redirect_stdout(io.StringIO()):
            review_manager.add_comment(pr)
        with contextlib.redirect_stdout(io.StringIO()):
            review_manager.approve_pr(pr)
        self.assertFalse(pr["approved"])

        with patch("builtins.input", return_value="1"), contextlib.redirect_stdout(io.StringIO()):
            review_manager.resolve_comment(pr)
        with contextlib.redirect_stdout(io.StringIO()):
            review_manager.approve_pr(pr)
            review_manager.merge_pr(pr)
        review_manager.save_data(data)

        saved = json.loads(self.data_file.read_text(encoding="utf-8"))[-1]
        self.assertEqual(saved["status"], "MERGED")
        self.assertTrue(saved["approved"])
        self.assertEqual(saved["reviewers"], ["Chi"])
        self.assertEqual(tv2_service.current_assignments("PR003"), [])
        overview = dashboard_api.build_dashboard()
        self.assertEqual(overview["statistics"]["merged"], merged_before + 1)
        self.assertEqual(overview["pull_requests"][-1]["quality_score"], 100)

    def test_changed_json_recalculates_quality_and_risk(self):
        data = json.loads(self.data_file.read_text(encoding="utf-8"))
        data[0]["danh_sach_file"].append("config/app.env")
        data[0]["quality_checks"]["tests_passed"] = False
        self.data_file.write_text(json.dumps(data), encoding="utf-8")

        overview = dashboard_api.build_dashboard()
        first = overview["pull_requests"][0]
        self.assertEqual((first["risk_score"], first["risk_level"]), (49, "MEDIUM"))
        self.assertEqual(first["quality_score"], 45)
        self.assertEqual(overview["risk_score"]["high"], 1)
        saved = json.loads(self.data_file.read_text(encoding="utf-8"))[0]
        self.assertEqual(saved["risk_score"], 49)
        self.assertEqual(saved["quality_score"], 45)
        self.assertEqual(tv2_service.get_pr("PR001")["risk_score"], 49)

    def test_tv2_reassignment_updates_json_and_dashboard(self):
        data = review_manager.load_data()
        original_reviewer = data[0]["reviewer"]
        self.assertEqual(tv2_service.current_assignments("PR001")[0].reviewer_id, original_reviewer)
        with TestClient(tv2_app) as client:
            response = client.post(f"/pull-requests/PR001/assignments/{original_reviewer}/reassign")
            self.assertEqual(response.status_code, 200)
            result = response.json()
        self.assertEqual(result["assigned"], 1)
        nguoi_moi = result["assignments"][0]["reviewer_id"]
        self.assertNotEqual(nguoi_moi, original_reviewer)

        overview = dashboard_api.build_dashboard()
        self.assertEqual(overview["pull_requests"][0]["reviewer"], nguoi_moi)
        saved = json.loads(self.data_file.read_text(encoding="utf-8"))[0]
        self.assertEqual(saved["reviewers"], [nguoi_moi])

    def test_tv2_replaces_one_of_multiple_reviewers(self):
        review_manager.load_data()
        request = PullRequestIn(
            pr_id="PR003", author_id="Duy", repository="code-review-system",
            changed_files=["frontend/App.jsx"], required_reviewers=2,
        )
        first = tv2_service.assign(request)
        self.assertEqual(first.assigned, 2)
        rejected = first.assignments[0].reviewer_id
        replacement = tv2_service.reassign("PR003", rejected)
        self.assertEqual(replacement.assigned, 2)
        self.assertNotIn(rejected, [item.reviewer_id for item in replacement.assignments])

    def test_multiple_reviewers_are_mirrored_to_dashboard(self):
        data = review_manager.load_data()
        pr = {
            "id": "PR003", "title": "API update", "author": "Duy",
            "description": "Update API", "danh_sach_file": ["src/api.py"],
            "so_dong_them": 20, "so_dong_xoa": 5,
            "quality_checks": {"tests_passed": True, "lint_passed": True},
            "required_reviewers": 2, "reviewer": None,
            "comments": [], "approved": False, "status": "IN_REVIEW",
        }
        data.append(pr)
        review_manager.save_data(data)
        self.assertEqual(len(pr["reviewers"]), 2)
        self.assertEqual(pr["reviewers"], [item.reviewer_id for item in tv2_service.current_assignments("PR003")])
        overview = dashboard_api.build_dashboard()
        self.assertEqual(overview["pull_requests"][-1]["reviewer"], ", ".join(pr["reviewers"]))

    def test_manager_reassignment_updates_tv2(self):
        data = review_manager.load_data()
        pr = data[0]
        original_reviewer = pr["reviewer"]
        self.assertTrue(phan_cong_reviewer(pr, bat_buoc=True))
        self.assertNotEqual(pr["reviewer"], original_reviewer)
        self.assertEqual(pr["reviewer"], tv2_service.current_assignments(pr["id"])[0].reviewer_id)
        review_manager.save_data(data)
        saved = json.loads(self.data_file.read_text(encoding="utf-8"))[0]
        self.assertEqual(saved["reviewer"], pr["reviewer"])

    def test_review_menu_runs_all_actions_and_edits_pr(self):
        data = review_manager.load_data()
        answers = [
            "PR001", "1", "Cần sửa lỗi", "2", "3", "4", "2", "1",
            "7", "Tiêu đề mới", "", "src/new.py,tests/test_new.py",
            "20", "2", "c", "c", "6", "4", "5", "0",
        ]
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(output):
            review_manager.review_menu(data)

        pr = review_manager.load_data()[0]
        self.assertIn("Không thể APPROVE", output.getvalue())
        self.assertEqual(pr["title"], "Tiêu đề mới")
        self.assertEqual(pr["status"], "MERGED")
        self.assertTrue(pr["comments"][0]["resolved"])
        self.assertEqual(pr["risk_score"], 9)
        self.assertEqual(tv2_service.current_assignments(pr["id"]), [])


if __name__ == "__main__":
    unittest.main()
