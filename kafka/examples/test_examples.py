import base64
import io
import json
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, closing, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import check_environment as environment
from common import InvalidEvent, ReliableProducer, decode_event, make_event
from consumer import dead_letter, open_store, process_event, process_with_retry
from consumer import main as consume


class EventTests(unittest.TestCase):
    def test_valid_event_and_contract_rejections(self):
        event = make_event("order-1")
        self.assertEqual(decode_event(json.dumps(event), b"order-1"), event)
        for value, key in [
            (None, b"order-1"),
            (b"\xff", b"order-1"),
            (b"[]", b"order-1"),
            (json.dumps(event), b"wrong-key"),
            (json.dumps({**event, "amount_cents": True}), b"order-1"),
            (json.dumps({**event, "schema_version": True}), b"order-1"),
            (json.dumps({**event, "occurred_at": "yesterday"}), b"order-1"),
            (json.dumps({**event, "status": "unknown"}), b"order-1"),
        ]:
            with self.subTest(value=value), self.assertRaises(InvalidEvent):
                decode_event(value, key)

    def test_replay_does_not_repeat_business_effect_and_conflicts_fail(self):
        with closing(open_store(":memory:")) as connection:
            event = make_event("order-1")
            self.assertTrue(process_event(connection, event))
            self.assertFalse(process_event(connection, event))
            with self.assertRaises(InvalidEvent):
                process_event(connection, {**event, "amount_cents": 1})
            self.assertEqual(
                connection.execute("SELECT event_count FROM order_totals").fetchone()[0], 1
            )

    def test_business_failure_rolls_back_deduplication_marker(self):
        with closing(open_store(":memory:")) as connection:
            connection.execute("DROP TABLE order_totals")
            with self.assertRaises(sqlite3.OperationalError):
                process_event(connection, make_event("order-1"))
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM processed_events").fetchone()[0], 0
            )

    def test_database_retry_is_bounded_and_exhaustion_surfaces(self):
        with patch("consumer.process_event", side_effect=sqlite3.OperationalError("locked")) as process:
            sleep = Mock()
            with self.assertRaises(sqlite3.OperationalError):
                process_with_retry(Mock(), make_event("order-1"), sleep=sleep)
            self.assertEqual(process.call_count, 3)
            self.assertEqual(sleep.call_count, 2)

    def test_dead_letter_preserves_binary_data_and_waits_for_delivery(self):
        message = Mock()
        message.topic.return_value = "orders"
        message.partition.return_value = 2
        message.offset.return_value = 7
        message.key.return_value = b"\xff"
        message.value.return_value = b"\x00\xff"
        message.headers.return_value = [("optional", None)]
        producer = Mock()
        dead_letter(producer, "orders.dlt", message, InvalidEvent("bad"))
        topic, key, body = producer.send.call_args.args
        envelope = json.loads(body)
        self.assertEqual(topic, "orders.dlt")
        self.assertEqual(key, b"orders:2:7")
        self.assertEqual(base64.b64decode(envelope["value_base64"]), b"\x00\xff")
        self.assertEqual(envelope["headers_base64"], [["optional", None]])
        producer.flush.assert_called_once()

    def test_producer_delivery_failure_is_not_reported_as_success(self):
        with patch("common.Producer") as client:
            client.return_value.flush.return_value = 0
            producer = ReliableProducer("unused:9092")
            producer._delivered("broker rejected record", Mock())
            with self.assertRaises(RuntimeError):
                producer.flush()

    def test_dead_letter_failure_does_not_commit_source_offset(self):
        message = Mock()
        message.error.return_value = None
        message.value.return_value = b"not-json"
        message.key.return_value = b"order-1"
        message.headers.return_value = []
        message.topic.return_value = "orders"
        message.partition.return_value = 0
        message.offset.return_value = 1
        with (
            patch("sys.argv", ["consumer.py", "--max-messages", "1"]),
            patch("consumer.open_store") as store,
            patch("consumer.Consumer") as client,
            patch("consumer.ReliableProducer") as producer,
        ):
            client.return_value.poll.return_value = message
            producer.return_value.flush.side_effect = RuntimeError("DLT unavailable")
            with self.assertRaisesRegex(RuntimeError, "DLT unavailable"):
                consume()
            client.return_value.commit.assert_not_called()
            client.return_value.close.assert_called_once()
            store.return_value.close.assert_called_once()


class EnvironmentTests(unittest.TestCase):
    def test_missing_executable_names_the_tool_and_installation_guide(self):
        with patch.object(environment.subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaisesRegex(environment.PrerequisiteError, "docker not found.*environment-setup"):
                environment.command("docker", "info")

    def test_preflight_reports_all_blockers_and_returns_failure(self):
        names = (
            "check_checkout", "check_python", "check_client", "check_tools", "check_storage",
            "check_context", "check_docker", "check_compose", "check_configuration",
            "check_ports",
        )
        for failing_check, error, expected in (
            ("check_context", FileNotFoundError("docker missing from PATH"), "docker missing"),
            ("check_client", ModuleNotFoundError("confluent_kafka missing"), "confluent_kafka missing"),
            ("check_docker", subprocess.TimeoutExpired("docker info", 30), "timed out"),
        ):
            with self.subTest(check=failing_check), ExitStack() as stack:
                checks = {
                    name: stack.enter_context(patch.object(environment, name, return_value="ok"))
                    for name in names
                }
                checks[failing_check].side_effect = error
                output = stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(environment.main(["--profile", "cluster"]), 1)
                self.assertIn(expected, output.getvalue())
                self.assertIn("NOT READY", output.getvalue())
                self.assertNotIn("READY for", output.getvalue())
                checks["check_ports"].assert_called_once_with("cluster")

    def test_python_and_client_versions_must_match_workshop(self):
        with patch.object(environment.sys, "version_info", (3, 12)):
            with self.assertRaisesRegex(environment.PrerequisiteError, "3.13"):
                environment.check_python()
        client = Mock()
        client.__version__ = "2.11.0"
        with patch.object(environment.importlib, "import_module", return_value=client):
            with self.assertRaisesRegex(environment.PrerequisiteError, "pinned requirements"):
                environment.check_client()

    def test_old_compose_and_windows_containers_fail_explicitly(self):
        for version in ("2.19.9", "unparseable"):
            with self.subTest(version=version), patch.object(environment, "command", return_value=version):
                with self.assertRaisesRegex(environment.PrerequisiteError, "2.20.0"):
                    environment.check_compose()
        with patch.object(environment, "command", return_value='{"OSType":"windows"}'):
            with self.assertRaisesRegex(environment.PrerequisiteError, "Linux containers"):
                environment.check_docker("single")

    def test_remote_endpoint_and_override_are_rejected(self):
        context = json.dumps([{
            "Name": "default", "Endpoints": {"docker": {"Host": "unix:///var/run/docker.sock"}},
        }])
        with (
            patch.object(environment, "command", return_value=context),
            patch.dict(environment.os.environ, {"DOCKER_HOST": "ssh://remote", "DOCKER_CONTEXT": ""}),
        ):
            with self.assertRaisesRegex(environment.PrerequisiteError, "not a local"):
                environment.check_context()

    def test_busy_port_surfaces_owner_guidance(self):
        with patch.object(environment.socket, "socket") as socket_factory:
            socket_factory.return_value.__enter__.return_value.bind.side_effect = OSError("in use")
            with self.assertRaisesRegex(environment.PrerequisiteError, "9092.*in use"):
                environment.check_ports("single")

    def test_successful_preflight_uses_local_non_destructive_checks(self):
        context = [{"Name": "local", "Endpoints": {"docker": {"Host": "unix:///docker.sock"}}}]
        info = {
            "OSType": "linux", "Architecture": "x86_64", "MemTotal": 16 * environment.GIB,
            "ServerVersion": "test",
        }

        def docker_command(*args):
            if args in (("git", "--version"), ("uv", "--version")):
                return "test"
            if args[:3] == ("docker", "context", "inspect"):
                return json.dumps(context)
            if args[:2] == ("docker", "info"):
                return json.dumps(info)
            if args == ("docker", "compose", "version", "--short"):
                return "v2.20.0"
            self.assertEqual(args[:3], ("docker", "compose", "-f"))
            self.assertEqual(args[-2:], ("config", "--quiet"))
            return ""

        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder).resolve()
            state = root / ".state"
            state.mkdir()
            stack.enter_context(patch.object(environment, "ROOT", root))
            stack.enter_context(patch.object(environment.Path, "cwd", return_value=root))
            stack.enter_context(patch.object(environment, "check_python", return_value="3.13 venv"))
            stack.enter_context(patch.object(environment, "check_client", return_value="2.12.2"))
            stack.enter_context(patch.object(environment.platform, "machine", return_value="AMD64"))
            stack.enter_context(patch.object(environment.shutil, "disk_usage", return_value=Mock(free=20 * environment.GIB)))
            stack.enter_context(patch.dict(environment.os.environ, {"DOCKER_HOST": "", "DOCKER_CONTEXT": ""}))
            command = stack.enter_context(patch.object(environment, "command", side_effect=docker_command))
            socket_factory = stack.enter_context(patch.object(environment.socket, "socket"))
            output = stack.enter_context(redirect_stdout(io.StringIO()))
            self.assertEqual(environment.main(["--profile", "cluster"]), 0)
            self.assertIn("READY for", output.getvalue())
            self.assertIn("WARN:", output.getvalue())
            self.assertIn(f"transaction succeeded in {state}", output.getvalue())
            self.assertEqual(list(root.iterdir()), [state])
            self.assertEqual(list(state.iterdir()), [])
            self.assertEqual(command.call_count, 7)
            self.assertEqual(
                [call.args for call in socket_factory.return_value.__enter__.return_value.bind.call_args_list],
                [(("127.0.0.1", port),) for port in (19092, 29092, 39092)],
            )


if __name__ == "__main__":
    unittest.main()
