"""CLI entry point for the Python porting workspace.

Usage::

    python -m src.main <subcommand> [args...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print(text: str) -> None:
    print(text)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def _cmd_summary(_args: argparse.Namespace) -> None:
    from src.query_engine import QueryEnginePort

    engine = QueryEnginePort.from_workspace()
    _print(engine.render_summary())


def _cmd_parity_audit(_args: argparse.Namespace) -> None:
    from src.parity_audit import run_parity_audit

    audit = run_parity_audit()
    _print("Parity Audit")
    _print("=" * 40)
    _print(f"archive_present={audit.archive_present}")
    _print(f"root_file_coverage={audit.root_file_coverage}")
    _print(f"directory_coverage={audit.directory_coverage}")
    _print(f"command_entry_ratio={audit.command_entry_ratio}")
    _print(f"tool_entry_ratio={audit.tool_entry_ratio}")


def _cmd_commands(args: argparse.Namespace) -> None:
    from src.commands import PORTED_COMMANDS

    entries = list(PORTED_COMMANDS)

    if hasattr(args, "no_plugin_commands") and args.no_plugin_commands:
        entries = [e for e in entries if not e.plugin]

    if hasattr(args, "query") and args.query:
        q = args.query.lower()
        entries = [e for e in entries if q in e.name.lower() or q in e.description.lower()]

    limit = getattr(args, "limit", None)
    if limit:
        entries = entries[: int(limit)]

    _print(f"Command entries: {len(entries)}")
    for e in entries:
        _print(f"  - {e.name}: {e.description}")


def _cmd_tools(args: argparse.Namespace) -> None:
    from src.tools import PORTED_TOOLS

    entries = list(PORTED_TOOLS)

    if hasattr(args, "no_mcp") and args.no_mcp:
        entries = [e for e in entries if not e.mcp]

    if hasattr(args, "simple_mode") and args.simple_mode:
        entries = [e for e in entries if e.simple]

    if hasattr(args, "deny_prefix") and args.deny_prefix:
        prefix = args.deny_prefix.lower()
        entries = [e for e in entries if not e.name.lower().startswith(prefix)]

    if hasattr(args, "query") and args.query:
        q = args.query.lower()
        entries = [e for e in entries if q in e.name.lower() or q in e.description.lower()]

    limit = getattr(args, "limit", None)
    if limit:
        entries = entries[: int(limit)]

    _print(f"Tool entries: {len(entries)}")
    for e in entries:
        _print(f"  - {e.name}: {e.description}")


def _cmd_route(args: argparse.Namespace) -> None:
    from src.query_engine import QueryEnginePort

    engine = QueryEnginePort.from_workspace()
    query = " ".join(args.query) if isinstance(args.query, list) else args.query
    limit = getattr(args, "limit", 10)
    matches = engine.route(query, limit=int(limit))
    _print(f"Route results for '{query}':")
    for kind, entry in matches:
        _print(f"  [{kind}] {entry.name}: {entry.description}")


def _cmd_show_command(args: argparse.Namespace) -> None:
    from src.execution_registry import build_execution_registry

    registry = build_execution_registry()
    try:
        cmd = registry.command(args.name)
        _print(f"Command: {cmd.name}")
        _print(f"Description: {cmd.description}")
        _print(f"Plugin: {cmd.plugin}")
    except KeyError as exc:
        _print(str(exc))
        sys.exit(1)


def _cmd_show_tool(args: argparse.Namespace) -> None:
    from src.execution_registry import build_execution_registry

    registry = build_execution_registry()
    try:
        tool = registry.tool(args.name)
        _print(f"Tool: {tool.name}")
        _print(f"Description: {tool.description}")
        _print(f"MCP: {tool.mcp}")
    except KeyError as exc:
        _print(str(exc))
        sys.exit(1)


def _cmd_bootstrap(args: argparse.Namespace) -> None:
    from src.runtime import PortRuntime

    query = " ".join(args.query) if isinstance(args.query, list) else args.query
    limit = getattr(args, "limit", 10)
    session = PortRuntime().bootstrap_session(query, limit=int(limit))

    _print("Runtime Session")
    _print("=" * 40)
    _print(f"session_id={session.session_id}")
    _print(f"prompt={session.prompt!r}")
    _print("")
    _print("Startup Steps")
    _print("-" * 20)
    for step in session.startup_steps:
        _print(f"  * {step}")
    _print("")
    _print("Routed Matches")
    _print("-" * 20)
    _print(f"  matched_tools={[t.name for t in session.turn_result.matched_tools]}")
    _print(f"  output={session.turn_result.output!r}")


def _cmd_exec_command(args: argparse.Namespace) -> None:
    from src.execution_registry import build_execution_registry

    registry = build_execution_registry()
    try:
        cmd = registry.command(args.name)
        result = cmd.execute(args.prompt)
        _print(result)
    except KeyError as exc:
        _print(str(exc))
        sys.exit(1)


def _cmd_exec_tool(args: argparse.Namespace) -> None:
    from src.execution_registry import build_execution_registry

    registry = build_execution_registry()
    try:
        tool = registry.tool(args.name)
        result = tool.execute(args.prompt)
        _print(result)
    except KeyError as exc:
        _print(str(exc))
        sys.exit(1)


def _cmd_setup_report(_args: argparse.Namespace) -> None:
    from src.port_manifest import build_port_manifest

    manifest = build_port_manifest()
    _print("Setup Report")
    _print("=" * 40)
    _print(f"total_python_files={manifest.total_python_files}")
    _print(f"top_level_modules={manifest.top_level_modules}")
    _print(f"Deferred init: enabled")
    _print(f"plugin_init=True")


def _cmd_load_session(args: argparse.Namespace) -> None:
    from src.runtime import PortRuntime

    runtime = PortRuntime()
    try:
        data = runtime.load_session(args.session_id)
        _print(f"session_id={data['session_id']}")
        _print(f"messages={data['messages']}")
    except FileNotFoundError as exc:
        _print(str(exc))
        sys.exit(1)


def _cmd_turn_loop(args: argparse.Namespace) -> None:
    from src.runtime import PortRuntime

    query = " ".join(args.query) if isinstance(args.query, list) else args.query
    max_turns = int(getattr(args, "max_turns", 2))
    structured = getattr(args, "structured_output", False)
    runtime = PortRuntime()

    for turn_num in range(1, max_turns + 1):
        session = runtime.bootstrap_session(query, limit=5)
        tr = session.turn_result
        if structured:
            _print(f"## Turn {turn_num}")
            _print(f"stop_reason={tr.stop_reason!r}")
            _print(f"output={tr.output!r}")
            _print(f"usage=input_tokens={tr.usage.input_tokens} output_tokens={tr.usage.output_tokens}")
        else:
            _print(f"Turn {turn_num}: {tr.output}")


def _cmd_remote_mode(args: argparse.Namespace) -> None:
    workspace = args.workspace if hasattr(args, "workspace") else "default"
    _print(f"mode=remote workspace={workspace}")


def _cmd_ssh_mode(args: argparse.Namespace) -> None:
    workspace = args.workspace if hasattr(args, "workspace") else "default"
    _print(f"mode=ssh workspace={workspace}")


def _cmd_teleport_mode(args: argparse.Namespace) -> None:
    workspace = args.workspace if hasattr(args, "workspace") else "default"
    _print(f"mode=teleport workspace={workspace}")


def _cmd_flush_transcript(args: argparse.Namespace) -> None:
    query = " ".join(args.query) if isinstance(args.query, list) else args.query
    _print(f"flushed=True query={query!r}")


def _cmd_command_graph(_args: argparse.Namespace) -> None:
    from src.commands import PORTED_COMMANDS

    _print("Command Graph")
    _print("=" * 40)
    for cmd in PORTED_COMMANDS[:10]:
        _print(f"  {cmd.name} -> [deps]")


def _cmd_tool_pool(_args: argparse.Namespace) -> None:
    from src.tools import PORTED_TOOLS

    _print("Tool Pool")
    _print("=" * 40)
    for tool in PORTED_TOOLS[:10]:
        _print(f"  {tool.name} (mcp={tool.mcp})")


def _cmd_bootstrap_graph(_args: argparse.Namespace) -> None:
    _print("Bootstrap Graph")
    _print("=" * 40)
    _print("  initialize -> load_registry -> route -> execute")


def _cmd_direct_connect_mode(args: argparse.Namespace) -> None:
    workspace = args.workspace if hasattr(args, "workspace") else "default"
    _print(f"mode=direct-connect workspace={workspace}")


def _cmd_deep_link_mode(args: argparse.Namespace) -> None:
    workspace = args.workspace if hasattr(args, "workspace") else "default"
    _print(f"mode=deep-link workspace={workspace}")


def _cmd_dependencies(args: argparse.Namespace) -> None:
    from src.dependencies import DEPENDENCIES, get_dependency

    name = getattr(args, "name", None)
    if name:
        try:
            dep = get_dependency(name)
            _print(f"Dependency: {dep.name}")
            _print(f"Version: {dep.version}")
            _print(f"URL: {dep.url}")
        except KeyError as exc:
            _print(str(exc))
            sys.exit(1)
    else:
        _print(f"Dependencies: {len(DEPENDENCIES)}")
        for dep in DEPENDENCIES:
            _print(f"  - {dep.name}=={dep.version}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Python Porting Workspace CLI",
    )
    subs = parser.add_subparsers(dest="subcommand")

    # summary
    subs.add_parser("summary", help="Print workspace summary")

    # parity-audit
    subs.add_parser("parity-audit", help="Run parity audit")

    # commands
    p_commands = subs.add_parser("commands", help="List ported commands")
    p_commands.add_argument("--limit", type=int, default=None)
    p_commands.add_argument("--query", default=None)
    p_commands.add_argument("--no-plugin-commands", dest="no_plugin_commands", action="store_true")

    # tools
    p_tools = subs.add_parser("tools", help="List ported tools")
    p_tools.add_argument("--limit", type=int, default=None)
    p_tools.add_argument("--query", default=None)
    p_tools.add_argument("--no-mcp", dest="no_mcp", action="store_true")
    p_tools.add_argument("--simple-mode", dest="simple_mode", action="store_true")
    p_tools.add_argument("--deny-prefix", dest="deny_prefix", default=None)

    # route
    p_route = subs.add_parser("route", help="Route a query to commands/tools")
    p_route.add_argument("query", nargs="+")
    p_route.add_argument("--limit", type=int, default=10)

    # show-command
    p_show_cmd = subs.add_parser("show-command", help="Show a command")
    p_show_cmd.add_argument("name")

    # show-tool
    p_show_tool = subs.add_parser("show-tool", help="Show a tool")
    p_show_tool.add_argument("name")

    # bootstrap
    p_bootstrap = subs.add_parser("bootstrap", help="Bootstrap a session")
    p_bootstrap.add_argument("query", nargs="+")
    p_bootstrap.add_argument("--limit", type=int, default=10)

    # exec-command
    p_exec_cmd = subs.add_parser("exec-command", help="Execute a command")
    p_exec_cmd.add_argument("name")
    p_exec_cmd.add_argument("prompt")

    # exec-tool
    p_exec_tool = subs.add_parser("exec-tool", help="Execute a tool")
    p_exec_tool.add_argument("name")
    p_exec_tool.add_argument("prompt")

    # setup-report
    subs.add_parser("setup-report", help="Show setup report")

    # load-session
    p_load = subs.add_parser("load-session", help="Load a persisted session")
    p_load.add_argument("session_id")

    # turn-loop
    p_turn = subs.add_parser("turn-loop", help="Run a turn loop")
    p_turn.add_argument("query", nargs="+")
    p_turn.add_argument("--max-turns", dest="max_turns", type=int, default=2)
    p_turn.add_argument("--structured-output", dest="structured_output", action="store_true")

    # remote-mode
    p_remote = subs.add_parser("remote-mode", help="Remote mode")
    p_remote.add_argument("workspace")

    # ssh-mode
    p_ssh = subs.add_parser("ssh-mode", help="SSH mode")
    p_ssh.add_argument("workspace")

    # teleport-mode
    p_teleport = subs.add_parser("teleport-mode", help="Teleport mode")
    p_teleport.add_argument("workspace")

    # flush-transcript
    p_flush = subs.add_parser("flush-transcript", help="Flush transcript")
    p_flush.add_argument("query", nargs="+")

    # command-graph
    subs.add_parser("command-graph", help="Show command graph")

    # tool-pool
    subs.add_parser("tool-pool", help="Show tool pool")

    # bootstrap-graph
    subs.add_parser("bootstrap-graph", help="Show bootstrap graph")

    # direct-connect-mode
    p_direct = subs.add_parser("direct-connect-mode", help="Direct connect mode")
    p_direct.add_argument("workspace")

    # deep-link-mode
    p_deep = subs.add_parser("deep-link-mode", help="Deep link mode")
    p_deep.add_argument("workspace")

    # dependencies
    p_deps = subs.add_parser("dependencies", help="List vendored third-party dependencies")
    p_deps.add_argument("--name", default=None, help="Show a specific dependency by name")

    return parser


_HANDLERS = {
    "summary": _cmd_summary,
    "parity-audit": _cmd_parity_audit,
    "commands": _cmd_commands,
    "tools": _cmd_tools,
    "route": _cmd_route,
    "show-command": _cmd_show_command,
    "show-tool": _cmd_show_tool,
    "bootstrap": _cmd_bootstrap,
    "exec-command": _cmd_exec_command,
    "exec-tool": _cmd_exec_tool,
    "setup-report": _cmd_setup_report,
    "load-session": _cmd_load_session,
    "turn-loop": _cmd_turn_loop,
    "remote-mode": _cmd_remote_mode,
    "ssh-mode": _cmd_ssh_mode,
    "teleport-mode": _cmd_teleport_mode,
    "flush-transcript": _cmd_flush_transcript,
    "command-graph": _cmd_command_graph,
    "tool-pool": _cmd_tool_pool,
    "bootstrap-graph": _cmd_bootstrap_graph,
    "direct-connect-mode": _cmd_direct_connect_mode,
    "deep-link-mode": _cmd_deep_link_mode,
    "dependencies": _cmd_dependencies,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.subcommand:
        parser.print_help()
        return 1
    handler = _HANDLERS.get(args.subcommand)
    if handler is None:
        print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
