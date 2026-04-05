from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src import main
from src.commands import CommandEntry
from src.config import WorkspaceConfig, get_config
from src.filters import filter_commands, filter_tools
from src.logger import get_logger
from src.port_manifest import build_port_manifest
from src.registry import Registry
from src.routing import route_query
from src.runtime import PortRuntime
from src.session_store import SessionStore
from src.tools import ToolEntry


class FilterHelpersTests(unittest.TestCase):
    def test_filter_commands_applies_all_filters_without_mutating_input(self) -> None:
        entries = [
            CommandEntry(name="Review", description="Review code", plugin=False),
            CommandEntry(name="PluginReview", description="Review plugin", plugin=True),
            CommandEntry(name="Analyze", description="Analyze data", plugin=False),
        ]

        result = filter_commands(entries, query="review", no_plugin=True, limit=1)

        self.assertEqual([entry.name for entry in result], ["Review"])
        self.assertEqual([entry.name for entry in entries], ["Review", "PluginReview", "Analyze"])

    def test_filter_tools_applies_combined_filters(self) -> None:
        entries = [
            ToolEntry(name="MCPTool", description="Primary MCP tool", mcp=True, simple=False),
            ToolEntry(name="MockService", description="Mock services", mcp=False, simple=True),
            ToolEntry(name="Monitor", description="Observe systems", mcp=False, simple=True),
        ]

        result = filter_tools(
            entries,
            query="mock",
            no_mcp=True,
            simple_mode=True,
            deny_prefix="mon",
            limit=5,
        )

        self.assertEqual([entry.name for entry in result], ["MockService"])


class LoggerTests(unittest.TestCase):
    def test_info_and_warning_capture_records_and_verbose_output(self) -> None:
        logger = get_logger("workspace", verbose=True)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            logger.info("started", step="bootstrap")
            logger.warning("slow", elapsed_ms=10)

        self.assertEqual(
            logger.records,
            [
                {"level": "INFO", "name": "workspace", "msg": "started", "step": "bootstrap"},
                {"level": "WARNING", "name": "workspace", "msg": "slow", "elapsed_ms": 10},
            ],
        )
        self.assertIn("[INFO] workspace: started", stderr.getvalue())
        self.assertIn("[WARNING] workspace: slow", stderr.getvalue())

    def test_error_always_writes_to_stderr(self) -> None:
        logger = get_logger("workspace", verbose=False)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            logger.error("failed", code=500)

        self.assertEqual(
            logger.records,
            [{"level": "ERROR", "name": "workspace", "msg": "failed", "code": 500}],
        )
        self.assertIn("[ERROR] workspace: failed", stderr.getvalue())


class RegistryTests(unittest.TestCase):
    def test_registry_supports_case_insensitive_lookup(self) -> None:
        registry = Registry()

        self.assertEqual(registry.command("ReViEw").name, "review")
        self.assertEqual(registry.tool("mcptool").name, "MCPTool")
        self.assertTrue(registry.commands)
        self.assertTrue(registry.tools)

    def test_registry_raises_for_missing_entries(self) -> None:
        registry = Registry()

        with self.assertRaisesRegex(KeyError, "Command not found"):
            registry.command("missing-command")
        with self.assertRaisesRegex(KeyError, "Tool not found"):
            registry.tool("missing-tool")


class ConfigTests(unittest.TestCase):
    def test_get_config_returns_singleton_with_expected_defaults(self) -> None:
        first = get_config()
        second = get_config()
        defaults = WorkspaceConfig()

        self.assertIs(first, second)
        self.assertIsInstance(first, WorkspaceConfig)
        self.assertEqual(defaults.root, Path(".").resolve())
        self.assertEqual(defaults.session_dir, Path(".") / ".sessions")
        self.assertEqual(defaults.archive_dir, Path(".") / "archive")
        self.assertEqual(defaults.default_limit, 10)


class SessionStoreTests(unittest.TestCase):
    def test_session_store_save_load_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir))
            path = store.save("session-2", {"messages": [1]})
            store.save("session-1", {"messages": [2]})

            self.assertTrue(path.exists())
            self.assertEqual(store.load("session-2"), {"messages": [1]})
            self.assertEqual(store.list_sessions(), ["session-1", "session-2"])

    def test_session_store_raises_for_missing_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir))

            with self.assertRaisesRegex(FileNotFoundError, "Session not found"):
                store.load("missing")


class RoutingAndManifestTests(unittest.TestCase):
    def test_route_query_delegates_to_query_engine(self) -> None:
        engine = MagicMock()
        engine.route.return_value = [("tool", ToolEntry(name="MockService"))]

        with patch("src.routing.QueryEnginePort.from_workspace", return_value=engine):
            result = route_query("mock prompt", limit=3)

        engine.route.assert_called_once_with("mock prompt", limit=3)
        self.assertEqual(result, [("tool", ToolEntry(name="MockService"))])

    def test_build_port_manifest_uses_custom_root_and_detects_top_level_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            package_dir = root / "package_dir"
            package_dir.mkdir()
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
            (package_dir / "module.py").write_text("x = 1\n", encoding="utf-8")
            (root / "standalone.py").write_text("y = 2\n", encoding="utf-8")
            (root / "notes.txt").write_text("ignore\n", encoding="utf-8")

            manifest = build_port_manifest(root)

        self.assertEqual(manifest.total_python_files, 3)
        self.assertEqual(manifest.top_level_modules, ["package_dir", "standalone"])
        self.assertEqual(manifest.root_path, root)


class RuntimeTests(unittest.TestCase):
    def test_bootstrap_session_falls_back_to_direct_tool_query_when_route_has_no_tools(self) -> None:
        runtime = PortRuntime()
        fallback_tool = ToolEntry(name="MockService", description="Mock services")
        engine = MagicMock()
        engine.route.return_value = [("command", CommandEntry(name="review", description="Review code"))]
        engine.query_tools.return_value = [fallback_tool]
        runtime._engine = engine

        session = runtime.bootstrap_session("review mock", limit=2)

        engine.route.assert_called_once_with("review mock", limit=2)
        engine.query_tools.assert_called_once_with("review mock", limit=2)
        self.assertEqual(session.turn_result.matched_tools, [fallback_tool])


class MainEntryPointTests(unittest.TestCase):
    def test_main_returns_one_and_prints_help_without_subcommand(self) -> None:
        parser = MagicMock()
        parser.parse_args.return_value = SimpleNamespace(subcommand=None)

        with patch("src.main._build_parser", return_value=parser):
            result = main.main([])

        parser.print_help.assert_called_once_with()
        self.assertEqual(result, 1)

    def test_main_returns_one_for_missing_handler(self) -> None:
        parser = MagicMock()
        parser.parse_args.return_value = SimpleNamespace(subcommand="ghost")
        stderr = io.StringIO()

        with patch("src.main._build_parser", return_value=parser), redirect_stderr(stderr):
            result = main.main(["ghost"])

        self.assertEqual(result, 1)
        self.assertIn("Unknown subcommand: ghost", stderr.getvalue())

    def test_public_cli_exits_for_missing_registry_entries(self) -> None:
        for argv, expected in (
            (["show-command", "missing-command"], "Command not found"),
            (["show-tool", "missing-tool"], "Tool not found"),
            (["exec-command", "missing-command", "hello"], "Command not found"),
            (["exec-tool", "missing-tool", "hello"], "Tool not found"),
        ):
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with redirect_stderr(io.StringIO()), patch("sys.stdout", stdout):
                    with self.assertRaises(SystemExit) as exc:
                        main.main(argv)

                self.assertEqual(exc.exception.code, 1)
                self.assertIn(expected, stdout.getvalue())

    def test_public_cli_exits_for_missing_session(self) -> None:
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            with self.assertRaises(SystemExit) as exc:
                main.main(["load-session", "missing-session"])

        self.assertEqual(exc.exception.code, 1)
        self.assertIn("Session not found", stdout.getvalue())

    def test_public_cli_turn_loop_uses_plain_output_when_structured_output_is_disabled(self) -> None:
        runtime = MagicMock()
        runtime.bootstrap_session.return_value = SimpleNamespace(
            turn_result=SimpleNamespace(
                output="plain output",
                stop_reason="end_turn",
                usage=SimpleNamespace(input_tokens=1, output_tokens=1),
            )
        )
        stdout = io.StringIO()

        with patch("src.runtime.PortRuntime", return_value=runtime):
            with patch("sys.stdout", stdout):
                result = main.main(["turn-loop", "review", "tool", "--max-turns", "2"])

        self.assertEqual(result, 0)
        self.assertEqual(runtime.bootstrap_session.call_count, 2)
        self.assertEqual(stdout.getvalue().strip().splitlines(), ["Turn 1: plain output", "Turn 2: plain output"])


if __name__ == "__main__":
    unittest.main()
