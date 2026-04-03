from __future__ import annotations

import io
import subprocess
import sys
import unittest
from pathlib import Path

from src.commands import PORTED_COMMANDS
from src.parity_audit import run_parity_audit
from src.port_manifest import build_port_manifest
from src.pry_instance import (
    DEFAULT_PROMPT,
    HookSet,
    Prompt,
    ReplInstance,
    Ring,
)
from src.query_engine import QueryEnginePort
from src.tools import PORTED_TOOLS


class PortingWorkspaceTests(unittest.TestCase):
    def test_manifest_counts_python_files(self) -> None:
        manifest = build_port_manifest()
        self.assertGreaterEqual(manifest.total_python_files, 20)
        self.assertTrue(manifest.top_level_modules)

    def test_query_engine_summary_mentions_workspace(self) -> None:
        summary = QueryEnginePort.from_workspace().render_summary()
        self.assertIn('Python Porting Workspace Summary', summary)
        self.assertIn('Command surface:', summary)
        self.assertIn('Tool surface:', summary)

    def test_cli_summary_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'summary'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Python Porting Workspace Summary', result.stdout)

    def test_parity_audit_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'parity-audit'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Parity Audit', result.stdout)

    def test_root_file_coverage_is_complete_when_local_archive_exists(self) -> None:
        audit = run_parity_audit()
        if audit.archive_present:
            self.assertEqual(audit.root_file_coverage[0], audit.root_file_coverage[1])
            self.assertGreaterEqual(audit.directory_coverage[0], 28)
            self.assertGreaterEqual(audit.command_entry_ratio[0], 150)
            self.assertGreaterEqual(audit.tool_entry_ratio[0], 100)

    def test_command_and_tool_snapshots_are_nontrivial(self) -> None:
        self.assertGreaterEqual(len(PORTED_COMMANDS), 150)
        self.assertGreaterEqual(len(PORTED_TOOLS), 100)

    def test_commands_and_tools_cli_run(self) -> None:
        commands_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'commands', '--limit', '5', '--query', 'review'],
            check=True,
            capture_output=True,
            text=True,
        )
        tools_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'tools', '--limit', '5', '--query', 'MCP'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Command entries:', commands_result.stdout)
        self.assertIn('Tool entries:', tools_result.stdout)

    def test_subsystem_packages_expose_archive_metadata(self) -> None:
        from src import assistant, bridge, utils

        self.assertGreater(assistant.MODULE_COUNT, 0)
        self.assertGreater(bridge.MODULE_COUNT, 0)
        self.assertGreater(utils.MODULE_COUNT, 100)
        self.assertTrue(utils.SAMPLE_FILES)

    def test_route_and_show_entry_cli_run(self) -> None:
        route_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'route', 'review MCP tool', '--limit', '5'],
            check=True,
            capture_output=True,
            text=True,
        )
        show_command = subprocess.run(
            [sys.executable, '-m', 'src.main', 'show-command', 'review'],
            check=True,
            capture_output=True,
            text=True,
        )
        show_tool = subprocess.run(
            [sys.executable, '-m', 'src.main', 'show-tool', 'MCPTool'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('review', route_result.stdout.lower())
        self.assertIn('review', show_command.stdout.lower())
        self.assertIn('mcptool', show_tool.stdout.lower())

    def test_bootstrap_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'bootstrap', 'review MCP tool', '--limit', '5'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Runtime Session', result.stdout)
        self.assertIn('Startup Steps', result.stdout)
        self.assertIn('Routed Matches', result.stdout)

    def test_bootstrap_session_tracks_turn_state(self) -> None:
        from src.runtime import PortRuntime

        session = PortRuntime().bootstrap_session('review MCP tool', limit=5)
        self.assertGreaterEqual(len(session.turn_result.matched_tools), 1)
        self.assertIn('Prompt:', session.turn_result.output)
        self.assertGreaterEqual(session.turn_result.usage.input_tokens, 1)

    def test_exec_command_and_tool_cli_run(self) -> None:
        command_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'exec-command', 'review', 'inspect security review'],
            check=True,
            capture_output=True,
            text=True,
        )
        tool_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'exec-tool', 'MCPTool', 'fetch resource list'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("Mirrored command 'review'", command_result.stdout)
        self.assertIn("Mirrored tool 'MCPTool'", tool_result.stdout)

    def test_setup_report_and_registry_filters_run(self) -> None:
        setup_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'setup-report'],
            check=True,
            capture_output=True,
            text=True,
        )
        command_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'commands', '--limit', '5', '--no-plugin-commands'],
            check=True,
            capture_output=True,
            text=True,
        )
        tool_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'tools', '--limit', '5', '--simple-mode', '--no-mcp'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Setup Report', setup_result.stdout)
        self.assertIn('Command entries:', command_result.stdout)
        self.assertIn('Tool entries:', tool_result.stdout)

    def test_load_session_cli_runs(self) -> None:
        from src.runtime import PortRuntime

        session = PortRuntime().bootstrap_session('review MCP tool', limit=5)
        session_id = Path(session.persisted_session_path).stem
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'load-session', session_id],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn(session_id, result.stdout)
        self.assertIn('messages', result.stdout)

    def test_tool_permission_filtering_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'tools', '--limit', '10', '--deny-prefix', 'mcp'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Tool entries:', result.stdout)
        self.assertNotIn('MCPTool', result.stdout)

    def test_turn_loop_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'turn-loop', 'review MCP tool', '--max-turns', '2', '--structured-output'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('## Turn 1', result.stdout)
        self.assertIn('stop_reason=', result.stdout)

    def test_remote_mode_clis_run(self) -> None:
        remote_result = subprocess.run([sys.executable, '-m', 'src.main', 'remote-mode', 'workspace'], check=True, capture_output=True, text=True)
        ssh_result = subprocess.run([sys.executable, '-m', 'src.main', 'ssh-mode', 'workspace'], check=True, capture_output=True, text=True)
        teleport_result = subprocess.run([sys.executable, '-m', 'src.main', 'teleport-mode', 'workspace'], check=True, capture_output=True, text=True)
        self.assertIn('mode=remote', remote_result.stdout)
        self.assertIn('mode=ssh', ssh_result.stdout)
        self.assertIn('mode=teleport', teleport_result.stdout)

    def test_flush_transcript_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'flush-transcript', 'review MCP tool'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('flushed=True', result.stdout)

    def test_command_graph_and_tool_pool_cli_run(self) -> None:
        command_graph = subprocess.run([sys.executable, '-m', 'src.main', 'command-graph'], check=True, capture_output=True, text=True)
        tool_pool = subprocess.run([sys.executable, '-m', 'src.main', 'tool-pool'], check=True, capture_output=True, text=True)
        self.assertIn('Command Graph', command_graph.stdout)
        self.assertIn('Tool Pool', tool_pool.stdout)

    def test_setup_report_mentions_deferred_init(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'setup-report'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Deferred init:', result.stdout)
        self.assertIn('plugin_init=True', result.stdout)

    def test_execution_registry_runs(self) -> None:
        from src.execution_registry import build_execution_registry

        registry = build_execution_registry()
        self.assertGreaterEqual(len(registry.commands), 150)
        self.assertGreaterEqual(len(registry.tools), 100)
        self.assertIn('Mirrored command', registry.command('review').execute('review security'))
        self.assertIn('Mirrored tool', registry.tool('MCPTool').execute('fetch mcp resources'))

    def test_bootstrap_graph_and_direct_modes_run(self) -> None:
        graph_result = subprocess.run([sys.executable, '-m', 'src.main', 'bootstrap-graph'], check=True, capture_output=True, text=True)
        direct_result = subprocess.run([sys.executable, '-m', 'src.main', 'direct-connect-mode', 'workspace'], check=True, capture_output=True, text=True)
        deep_link_result = subprocess.run([sys.executable, '-m', 'src.main', 'deep-link-mode', 'workspace'], check=True, capture_output=True, text=True)
        self.assertIn('Bootstrap Graph', graph_result.stdout)
        self.assertIn('mode=direct-connect', direct_result.stdout)
        self.assertIn('mode=deep-link', deep_link_result.stdout)


class RingTests(unittest.TestCase):
    """Tests for the Ring circular-buffer class (port of Pry::Ring)."""

    def test_push_and_len(self) -> None:
        r = Ring(3)
        r << 1 << 2 << 3
        self.assertEqual(len(r), 3)

    def test_eviction_when_full(self) -> None:
        r = Ring(3)
        r << 1 << 2 << 3 << 4
        self.assertEqual(list(r), [2, 3, 4])

    def test_index_access(self) -> None:
        r = Ring(5)
        r << "a" << "b" << "c"
        self.assertEqual(r[0], "a")
        self.assertEqual(r[-1], "c")

    def test_iteration(self) -> None:
        r = Ring(10)
        for i in range(5):
            r << i
        self.assertEqual(list(r), [0, 1, 2, 3, 4])

    def test_max_size_respected(self) -> None:
        r = Ring(2)
        for i in range(10):
            r << i
        self.assertEqual(len(r), 2)
        self.assertEqual(list(r), [8, 9])

    def test_repr_contains_max_size(self) -> None:
        r = Ring(7)
        self.assertIn("7", repr(r))


class HookSetTests(unittest.TestCase):
    """Tests for the HookSet lifecycle-hook registry."""

    def test_hook_is_called(self) -> None:
        called = []
        hooks = HookSet()
        hooks.add_hook("test_event", "k1", lambda *a: called.append(a))
        hooks.exec_hook("test_event", "arg1")
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0], ("arg1",))

    def test_multiple_hooks_called_in_order(self) -> None:
        order = []
        hooks = HookSet()
        hooks.add_hook("ev", "k1", lambda: order.append(1))
        hooks.add_hook("ev", "k2", lambda: order.append(2))
        hooks.exec_hook("ev")
        self.assertEqual(order, [1, 2])

    def test_hook_errors_recorded_not_raised(self) -> None:
        hooks = HookSet()
        hooks.add_hook("ev", "bad", lambda: 1 / 0)
        hooks.exec_hook("ev")
        self.assertEqual(len(hooks.errors), 1)
        self.assertIsInstance(hooks.errors[0], ZeroDivisionError)

    def test_no_hooks_returns_none(self) -> None:
        hooks = HookSet()
        result = hooks.exec_hook("nonexistent")
        self.assertIsNone(result)


class ReplInstanceInitTests(unittest.TestCase):
    """Tests for ReplInstance initialisation."""

    def _make(self, **kwargs) -> tuple[ReplInstance, io.StringIO]:
        buf = io.StringIO()
        inst = ReplInstance(output=buf, **kwargs)
        return inst, buf

    def test_default_construction(self) -> None:
        inst, _ = self._make()
        self.assertIsNotNone(inst)
        self.assertEqual(len(inst.binding_stack), 1)
        self.assertFalse(inst._stopped)

    def test_memory_size_default(self) -> None:
        inst, _ = self._make()
        self.assertEqual(inst.memory_size, 100)

    def test_custom_memory_size(self) -> None:
        inst, _ = self._make(memory_size=42)
        self.assertEqual(inst.memory_size, 42)

    def test_memory_size_setter_replaces_rings(self) -> None:
        inst, _ = self._make()
        old_input_ring = inst.input_ring
        inst.memory_size = 50
        self.assertIsNot(inst.input_ring, old_input_ring)
        self.assertEqual(inst.input_ring.max_size, 50)
        self.assertEqual(inst.output_ring.max_size, 50)

    def test_target_namespace_pushed(self) -> None:
        ns = {"x": 42}
        inst, _ = self._make(target=ns)
        self.assertIn("x", inst.current_binding)

    def test_when_started_hook_fired(self) -> None:
        fired = []
        hooks = HookSet()
        hooks.add_hook("when_started", "k", lambda target, inst: fired.append(True))
        inst, _ = self._make(hooks=hooks)
        self.assertEqual(fired, [True])

    def test_repr(self) -> None:
        inst, _ = self._make()
        r = repr(inst)
        self.assertIn("ReplInstance", r)
        self.assertIn("memory_size=100", r)


class ReplInstancePromptTests(unittest.TestCase):
    """Tests for prompt-stack management."""

    def _make(self) -> tuple[ReplInstance, io.StringIO]:
        buf = io.StringIO()
        return ReplInstance(output=buf), buf

    def test_default_prompt_name(self) -> None:
        inst, _ = self._make()
        self.assertEqual(inst.prompt.name, "default")

    def test_push_and_pop_prompt(self) -> None:
        inst, _ = self._make()
        p2 = Prompt(name="custom")
        inst.push_prompt(p2)
        self.assertEqual(inst.prompt.name, "custom")
        popped = inst.pop_prompt()
        self.assertEqual(popped.name, "custom")
        self.assertEqual(inst.prompt.name, "default")

    def test_pop_does_not_empty_stack(self) -> None:
        inst, _ = self._make()
        # Popping the only prompt returns it without removing it
        p = inst.pop_prompt()
        self.assertEqual(p.name, "default")
        self.assertEqual(len(inst._prompt_stack), 1)

    def test_select_prompt_wait_vs_incomplete(self) -> None:
        inst, _ = self._make()
        wait = inst.select_prompt()
        inst.eval_string = "x ="  # partial
        incomplete = inst.select_prompt()
        self.assertNotEqual(wait, incomplete)


class ReplInstanceBindingStackTests(unittest.TestCase):
    """Tests for push/pop binding stack."""

    def _make(self) -> ReplInstance:
        return ReplInstance(output=io.StringIO())

    def test_push_binding_adds_to_stack(self) -> None:
        inst = self._make()
        initial_depth = len(inst.binding_stack)
        inst.push_binding({"y": 99})
        self.assertEqual(len(inst.binding_stack), initial_depth + 1)
        self.assertIn("y", inst.current_binding)

    def test_pop_binding_restores_previous(self) -> None:
        inst = self._make()
        inst.push_binding({"inner": True})
        inst.pop_binding()
        self.assertNotIn("inner", inst.current_binding)

    def test_push_binding_clears_stopped(self) -> None:
        inst = self._make()
        inst._stopped = True
        inst.push_binding({})
        self.assertFalse(inst._stopped)


class ReplInstanceStickyLocalsTests(unittest.TestCase):
    """Tests for sticky local variables."""

    def _make(self) -> ReplInstance:
        return ReplInstance(output=io.StringIO())

    def test_sticky_locals_keys(self) -> None:
        inst = self._make()
        sl = inst.sticky_locals
        for key in ("_in_", "_out_", "repl_instance", "_ex_", "_file_", "_dir_", "_", "__"):
            self.assertIn(key, sl)

    def test_repl_instance_sticky_local_is_self(self) -> None:
        inst = self._make()
        self.assertIs(inst.sticky_locals["repl_instance"], inst)

    def test_add_sticky_local(self) -> None:
        inst = self._make()
        inst.add_sticky_local("counter", lambda: 42)
        self.assertEqual(inst.sticky_locals["counter"], 42)

    def test_inject_sticky_locals_updates_namespace(self) -> None:
        inst = self._make()
        inst.inject_sticky_locals()
        self.assertIn("repl_instance", inst.current_binding)

    def test_inject_local(self) -> None:
        inst = self._make()
        ns: dict = {}
        inst.inject_local("foo", lambda: "bar", ns)
        self.assertEqual(ns["foo"], "bar")

    def test_inject_local_non_callable(self) -> None:
        inst = self._make()
        ns: dict = {}
        inst.inject_local("x", 99, ns)
        self.assertEqual(ns["x"], 99)


class ReplInstanceEvalStringTests(unittest.TestCase):
    """Tests for eval_string buffering and reset."""

    def _make(self) -> ReplInstance:
        return ReplInstance(output=io.StringIO())

    def test_reset_eval_string(self) -> None:
        inst = self._make()
        inst.eval_string = "partial"
        inst.reset_eval_string()
        self.assertEqual(inst.eval_string, "")


class ReplInstanceCommandTests(unittest.TestCase):
    """Tests for command processing (process_command, run_command)."""

    def _make(self) -> tuple[ReplInstance, io.StringIO]:
        buf = io.StringIO()
        return ReplInstance(output=buf), buf

    def test_process_command_returns_true_for_known_command(self) -> None:
        inst, _ = self._make()
        result = inst.process_command("review some code")
        self.assertTrue(result)

    def test_process_command_returns_false_for_unknown(self) -> None:
        inst, _ = self._make()
        result = inst.process_command("nonexistent_xyz_command")
        self.assertFalse(result)

    def test_process_command_safely_catches_command_error(self) -> None:
        from src.pry_instance import CommandError
        inst, buf = self._make()
        # Override process_command to raise CommandError
        def _bad_process(val):
            raise CommandError("oops")
        inst.process_command = _bad_process
        result = inst.process_command_safely("anything")
        self.assertTrue(result)
        self.assertIn("Error:", buf.getvalue())

    def test_run_command_executes_known_command(self) -> None:
        inst, _ = self._make()
        # Should not raise
        inst.run_command("review inspect this")

    def test_run_command_raises_for_unknown(self) -> None:
        inst, _ = self._make()
        with self.assertRaises(KeyError):
            inst.run_command("totally_unknown_cmd")


class ReplInstanceEvaluateTests(unittest.TestCase):
    """Tests for evaluate_python and show_result."""

    def _make(self) -> tuple[ReplInstance, io.StringIO]:
        buf = io.StringIO()
        return ReplInstance(output=buf), buf

    def test_evaluate_simple_expression(self) -> None:
        inst, _ = self._make()
        result = inst.evaluate_python("1 + 1")
        self.assertEqual(result, 2)

    def test_evaluate_statement_returns_none(self) -> None:
        inst, _ = self._make()
        result = inst.evaluate_python("x = 10")
        self.assertIsNone(result)
        self.assertEqual(inst.current_binding.get("x"), 10)

    def test_evaluate_updates_last_result(self) -> None:
        inst, _ = self._make()
        inst.evaluate_python("42")
        self.assertEqual(inst.last_result, 42)

    def test_evaluate_fires_before_after_hooks(self) -> None:
        events = []
        hooks = HookSet()
        hooks.add_hook("before_eval", "k", lambda code, inst: events.append("before"))
        hooks.add_hook("after_eval", "k", lambda result, inst: events.append("after"))
        inst, _ = self._make()
        inst.hooks = hooks
        inst.evaluate_python("1")
        self.assertIn("before", events)
        self.assertIn("after", events)

    def test_show_result_writes_to_output(self) -> None:
        inst, buf = self._make()
        inst._set_last_result(99, "99")
        inst.show_result(99)
        self.assertIn("99", buf.getvalue())

    def test_show_result_suppressed_when_flag_set(self) -> None:
        inst, buf = self._make()
        inst.suppress_output = True
        inst._set_last_result(99, "99")
        inst.show_result(99)
        self.assertEqual(buf.getvalue(), "")

    def test_show_result_exception_output(self) -> None:
        inst, buf = self._make()
        exc = ValueError("bad")
        inst._set_last_exception(exc)
        inst.show_result(exc)
        self.assertIn("Exception:", buf.getvalue())


class ReplInstanceEvalTests(unittest.TestCase):
    """Tests for the main eval() / _handle_line() pipeline."""

    def _make(self) -> tuple[ReplInstance, io.StringIO]:
        buf = io.StringIO()
        return ReplInstance(output=buf), buf

    def test_eval_simple_expression(self) -> None:
        inst, buf = self._make()
        still_alive = inst.eval("1 + 1")
        self.assertTrue(still_alive)
        self.assertIn("2", buf.getvalue())

    def test_eval_none_stops_instance(self) -> None:
        inst, _ = self._make()
        result = inst.eval(None)
        self.assertFalse(result)
        self.assertTrue(inst._stopped)

    def test_eval_returns_false_once_stopped(self) -> None:
        inst, _ = self._make()
        inst.eval(None)
        self.assertFalse(inst.eval("1 + 1"))

    def test_eval_command_line(self) -> None:
        inst, buf = self._make()
        inst.eval("review some code")
        # Command output stored in result ring; no exception
        self.assertFalse(inst.last_result_is_exception())

    def test_eval_multiline_expression(self) -> None:
        inst, buf = self._make()
        inst.eval("x = (1 +")   # incomplete
        self.assertFalse(inst._stopped)
        self.assertTrue(inst.eval_string)  # still buffering partial expression
        inst.eval("2)")  # complete
        self.assertEqual(inst.current_binding.get("x"), 3)

    def test_after_read_hook_fires(self) -> None:
        fired = []
        hooks = HookSet()
        hooks.add_hook("after_read", "k", lambda es, inst: fired.append(True))
        inst, _ = self._make()
        inst.hooks = hooks
        inst.eval("1 + 1")
        self.assertTrue(fired)

    def test_comment_suppresses_output(self) -> None:
        inst, buf = self._make()
        inst.eval("# just a comment\n")
        self.assertEqual(buf.getvalue(), "")


class ReplInstanceRaiseUpTests(unittest.TestCase):
    """Tests for raise_up semantics."""

    def _make(self) -> ReplInstance:
        return ReplInstance(output=io.StringIO())

    def test_raise_up_propagates_exception(self) -> None:
        from src.pry_instance import ReplRaiseUp
        inst = self._make()
        exc = RuntimeError("test")
        with self.assertRaises(ReplRaiseUp) as ctx:
            inst.raise_up(exc, force=True)
        self.assertIs(ctx.exception.exception, exc)

    def test_raise_up_clears_binding_stack_when_forced(self) -> None:
        inst = self._make()
        inst.push_binding({"a": 1})
        from src.pry_instance import ReplRaiseUp
        with self.assertRaises(ReplRaiseUp):
            inst.raise_up(ValueError("x"), force=True)
        self.assertEqual(inst.binding_stack, [])

    def test_raise_up_pops_binding_when_not_forced(self) -> None:
        inst = self._make()
        inst.push_binding({"inner": True})
        depth_before = len(inst.binding_stack)
        with self.assertRaises(ValueError):
            inst.raise_up(ValueError("pop"), force=False)
        self.assertEqual(len(inst.binding_stack), depth_before - 1)


class ReplInstanceCompleteTests(unittest.TestCase):
    """Tests for tab-completion."""

    def _make(self) -> ReplInstance:
        return ReplInstance(output=io.StringIO())

    def test_complete_returns_list(self) -> None:
        inst = self._make()
        result = inst.complete("re")
        self.assertIsInstance(result, list)

    def test_complete_matches_commands(self) -> None:
        inst = self._make()
        # "review" command should be in completions for prefix "rev"
        result = inst.complete("rev")
        self.assertIn("review", result)

    def test_complete_empty_prefix_returns_candidates(self) -> None:
        inst = self._make()
        result = inst.complete("")
        # All commands plus any namespace vars
        self.assertGreater(len(result), 0)

    def test_complete_no_match_returns_empty(self) -> None:
        inst = self._make()
        result = inst.complete("zzz_no_match")
        self.assertEqual(result, [])


class ReplInstanceHookTests(unittest.TestCase):
    """Tests for exec_hook error reporting."""

    def test_hook_error_printed_to_output(self) -> None:
        buf = io.StringIO()
        hooks = HookSet()
        hooks.add_hook("my_event", "bad", lambda: 1 / 0)
        inst = ReplInstance(output=buf, hooks=hooks)
        inst.exec_hook("my_event")
        output = buf.getvalue()
        self.assertIn("my_event hook failed", output)


if __name__ == '__main__':
    unittest.main()
