import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "plugins" / "linc" / "common" / "scripts" / "linc_api.py"
SPEC = importlib.util.spec_from_file_location("linc_api", MODULE_PATH)
linc_api = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(linc_api)


class LincApiTests(unittest.TestCase):
    def test_host_requires_clean_https_origin(self):
        self.assertEqual(linc_api.validate_host("https://linc.example"), "https://linc.example")
        for bad in (
            "http://linc.example",
            "https://user@linc.example",
            "https://linc.example/api",
            "https://linc.example?next=evil",
        ):
            with self.subTest(bad=bad), self.assertRaises(linc_api.LincError):
                linc_api.validate_host(bad)

    def test_path_rejects_absolute_or_non_api_targets(self):
        self.assertEqual(linc_api.validate_api_path("/api/auth/me"), "/api/auth/me")
        for bad in ("https://evil.example/api/auth/me", "/health", "api/auth/me"):
            with self.subTest(bad=bad), self.assertRaises(linc_api.LincError):
                linc_api.validate_api_path(bad)

    def test_extract_rejects_missing_or_empty_field(self):
        self.assertEqual(linc_api.extract({"data": {"id": "task-1"}}, "data.id"), "task-1")
        for payload in ({}, {"data": {}}, {"data": {"id": ""}}):
            with self.assertRaises(linc_api.LincError):
                linc_api.extract(payload, "data.id")

    def test_state_is_atomic_and_operation_ids_are_unique(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "LINC-demo.json"
            old_host = os.environ.get("LINC_HOST")
            os.environ["LINC_HOST"] = "https://linc.example"
            try:
                linc_api.command_state_init(
                    type("Args", (), {"file": str(path), "project_name": "demo", "force": False})()
                )
            finally:
                if old_host is None:
                    os.environ.pop("LINC_HOST", None)
                else:
                    os.environ["LINC_HOST"] = old_host
            args = type(
                "Args",
                (),
                {
                    "file": str(path),
                    "operation_id": "task-1",
                    "operation_type": "media_task",
                    "poll_path": "/api/ai/tasks/task-1",
                    "scope": '{"kind":"image"}',
                    "status": "submitted",
                    "estimated_credits": "10",
                    "json": '{"model":"model-1"}',
                    "json_file": None,
                },
            )()
            linc_api.command_record_operation(args)
            with self.assertRaises(linc_api.LincError):
                linc_api.command_record_operation(args)
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["operations"][0]["poll_path"], "/api/ai/tasks/task-1")
            self.assertNotIn("model-1", json.dumps(state, ensure_ascii=False))

    def test_secret_redaction(self):
        secret = "cak_" + "a" * 48
        self.assertNotIn(secret, linc_api.redact(f"bad {secret}"))

    def test_request_checks_business_code_and_keeps_target_on_host(self):
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *unused):
                return False

            def read(self):
                return json.dumps(self.payload).encode()

        opener = mock.Mock()
        opener.open.return_value = Response({"code": 0, "data": {"id": "task-1"}})
        env = {"LINC_HOST": "https://linc.example", "LINC_API_KEY": "cak_" + "a" * 48}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            linc_api.urllib.request, "build_opener", return_value=opener
        ):
            payload = linc_api.request_json("POST", "/api/ai/image/task", {"prompt": "it's safe"})
        self.assertEqual(payload["data"]["id"], "task-1")
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://linc.example/api/ai/image/task")
        self.assertIn("Bearer cak_", request.headers["Authorization"])

        opener.open.return_value = Response({"code": 40001, "message": "InvalidParameter"})
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            linc_api.urllib.request, "build_opener", return_value=opener
        ), self.assertRaises(linc_api.LincError):
            linc_api.request_json("POST", "/api/ai/image/task", {})

    def test_submit_records_pipeline_and_resources_before_returning(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "LINC-demo.json"
            env = {"LINC_HOST": "https://linc.example"}
            with mock.patch.dict(os.environ, env, clear=True):
                linc_api.command_state_init(
                    type("Args", (), {"file": str(path), "project_name": "demo", "force": False})()
                )
            args = type(
                "Args",
                (),
                {
                    "method": "POST",
                    "path": "/api/storyboards/auto-produce",
                    "json": '{"prompt":"demo"}',
                    "json_file": None,
                    "timeout": 60,
                    "state": str(path),
                    "id_field": "data.pipeline_id",
                    "poll_path": "/api/storyboards/auto-produce?id={operation_id}",
                    "operation_type": "auto_produce",
                    "scope": '{"kind":"full_drama"}',
                    "resource": ["storyboard_id=data.storyboard_id"],
                    "estimated_credits": "100",
                },
            )()
            payload = {"code": 0, "data": {"pipeline_id": "pl-1", "storyboard_id": "sb-1"}}
            with mock.patch.object(linc_api, "request_json", return_value=payload), mock.patch("sys.stdout"):
                linc_api.command_submit(args)
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["resources"]["storyboard_id"], "sb-1")
            self.assertEqual(state["operations"][0]["operation_type"], "auto_produce")
            self.assertEqual(
                state["operations"][0]["poll_path"],
                "/api/storyboards/auto-produce?id=pl-1",
            )


if __name__ == "__main__":
    unittest.main()
