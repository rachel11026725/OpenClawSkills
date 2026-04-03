"""Python port of Pry's ``pry_instance.rb``.

This module provides a Python equivalent of the core Pry REPL session object
(``Pry#PryInstance`` in Ruby).  The mapping between the Ruby API and this
module is intentionally one-to-one so that behaviour described in the
upstream source is easy to cross-reference.

Key concepts ported
-------------------

Ring
    A fixed-size circular buffer – equivalent to ``Pry::Ring``.  Used for
    the ``input_ring`` (last N inputs) and ``output_ring`` (last N results).

HookSet
    A named-event hook registry – equivalent to ``Pry::Hooks``.  Hooks are
    fired at well-known points: ``when_started``, ``before_eval``,
    ``after_eval``, ``after_read``.

Prompt
    A named prompt with a *wait* callable and an *incomplete* callable –
    equivalent to ``Pry::Prompt``.

ReplInstance
    The main session object – equivalent to Ruby's ``Pry`` instance.
    Responsibilities:

    * Maintains a *binding stack* of Python namespace dicts (Ruby: binding
      objects).
    * Buffers partial multi-line input in ``eval_string`` until the expression
      is syntactically complete.
    * Keeps ring-buffered history of inputs and outputs.
    * Provides *sticky locals* (``_in_``, ``_out_``, ``_``, ``__``, …) that
      are injected into every namespace.
    * Routes lines to command processing or to ``evaluate_python``.
    * Fires lifecycle hooks.
    * Implements ``raise_up`` semantics (propagate an exception out of the
      REPL, optionally clearing the entire binding stack).

Reference
---------
https://github.com/pry/pry/blob/master/lib/pry/pry_instance.rb
"""
from __future__ import annotations

import codeop
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, TextIO

from src.registry import Registry


# ---------------------------------------------------------------------------
# Ring – fixed-size circular buffer (Pry::Ring)
# ---------------------------------------------------------------------------


class Ring:
    """Fixed-size circular buffer.

    Equivalent to ``Pry::Ring`` in the Ruby source.  Used to store the last
    *max_size* input lines (``input_ring``) and output values
    (``output_ring``) for a :class:`ReplInstance`.

    Supports ``<<`` assignment (same interface as Ruby's ``Ring#<<``), index
    access and iteration.

    Parameters
    ----------
    max_size:
        Maximum number of items the ring holds.  Once full, the oldest item
        is silently discarded when a new one is appended.

    Examples
    --------
    >>> r = Ring(3)
    >>> r << 1 << 2 << 3 << 4
    <src.pry_instance.Ring ...>
    >>> list(r)
    [2, 3, 4]
    """

    def __init__(self, max_size: int = 100) -> None:
        self.max_size: int = max_size
        self._buf: list[Any] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def push(self, item: Any) -> "Ring":
        """Append *item*, evicting the oldest entry if the ring is full."""
        if len(self._buf) >= self.max_size:
            self._buf.pop(0)
        self._buf.append(item)
        return self

    def __lshift__(self, item: Any) -> "Ring":
        """Alias for :meth:`push`; returns *self* to support chaining."""
        return self.push(item)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def __getitem__(self, index: int) -> Any:
        return self._buf[index]

    def __len__(self) -> int:
        return len(self._buf)

    def __iter__(self):
        return iter(self._buf)

    def __repr__(self) -> str:
        return f"Ring(max_size={self.max_size}, items={self._buf!r})"


# ---------------------------------------------------------------------------
# Exceptions used for non-local flow control
# ---------------------------------------------------------------------------


class CommandError(Exception):
    """Raised when a REPL command fails."""


class ReplBreakout(Exception):
    """Internal signal to break out of the REPL loop (equivalent to Ruby's
    ``throw :breakout``)."""

    def __init__(self, value: Any = None) -> None:
        super().__init__()
        self.value = value


class ReplRaiseUp(Exception):
    """Internal signal to propagate an exception out of the REPL session
    (equivalent to Ruby's ``throw :raise_up``)."""

    def __init__(self, exception: BaseException) -> None:
        super().__init__()
        self.exception = exception


# ---------------------------------------------------------------------------
# HookSet – named lifecycle hooks (Pry::Hooks)
# ---------------------------------------------------------------------------


class HookSet:
    """Named lifecycle hook registry.

    Equivalent to ``Pry::Hooks`` in the Ruby source.  Multiple callables
    can be registered under the same event name.  When the event is fired
    via :meth:`exec_hook`, all registered callables are invoked in
    registration order.  Any exception raised by a hook is recorded in
    :attr:`errors` rather than propagated.

    Examples
    --------
    >>> hooks = HookSet()
    >>> hooks.add_hook("before_eval", "logger", lambda code, inst: print(code))
    >>> hooks.exec_hook("before_eval", "1 + 1", None)
    1 + 1
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable]] = {}
        #: Exceptions raised by hooks (same attribute name as Ruby's Pry::Hooks).
        self.errors: list[Exception] = []

    def add_hook(self, event: str, key: str, callable_: Callable) -> "HookSet":
        """Register *callable_* under *event*."""
        self._hooks.setdefault(event, []).append(callable_)
        return self

    def delete_hook(self, event: str, key: str) -> "HookSet":
        """Remove the hook at position *key* (index or callable) from *event*.

        If *key* is an integer it is treated as an index into the hook list;
        otherwise the first callable that compares equal to *key* is removed.
        No-op if the event or key does not exist.
        """
        hooks = self._hooks.get(event)
        if hooks is None:
            return self
        if isinstance(key, int):
            try:
                hooks.pop(key)
            except IndexError:
                pass
        else:
            try:
                hooks.remove(key)
            except ValueError:
                pass
        return self

    def exec_hook(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Fire all callables registered under *event*.

        Exceptions are caught, appended to :attr:`errors`, and execution
        continues with the remaining hooks.  Returns the result of the last
        callable, or ``None`` if no hooks are registered.
        """
        result: Any = None
        for hook in self._hooks.get(event, []):
            try:
                result = hook(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                self.errors.append(exc)
        return result


# ---------------------------------------------------------------------------
# Prompt (Pry::Prompt)
# ---------------------------------------------------------------------------


@dataclass
class Prompt:
    """A named prompt with *wait* and *incomplete* callables.

    Equivalent to ``Pry::Prompt`` in the Ruby source.

    Attributes
    ----------
    name:
        Human-readable name for this prompt.
    wait_proc:
        Called when ``eval_string`` is empty (normal prompt).  Signature:
        ``(obj, nesting_level, repl_instance) -> str``.
    incomplete_proc:
        Called when ``eval_string`` is non-empty (continuation prompt).
        Same signature as ``wait_proc``.
    """

    name: str
    wait_proc: Callable = field(
        default_factory=lambda: (
            lambda obj, level, inst: f"[{level}] > "
        )
    )
    incomplete_proc: Callable = field(
        default_factory=lambda: (
            lambda obj, level, inst: f"[{level}]* "
        )
    )


#: The default prompt used when none is specified.
DEFAULT_PROMPT = Prompt(name="default")


# ---------------------------------------------------------------------------
# ReplInstance – Python port of Pry (pry_instance.rb)
# ---------------------------------------------------------------------------


class ReplInstance:
    """Interactive REPL session – Python port of ``Pry#PryInstance``.

    A single ``ReplInstance`` manages one interactive session.  Multiple
    instances can coexist (e.g., nested sessions) without interfering.

    Parameters
    ----------
    target:
        Initial namespace dict pushed onto the binding stack.  If ``None``,
        an empty dict is used (equivalent to Ruby's ``toplevel_binding``).
    memory_size:
        Maximum entries kept in :attr:`input_ring` and :attr:`output_ring`.
        Defaults to 100 (same as ``Pry.config.memory_size``).
    output:
        File-like object receiving printed output.  Defaults to
        ``sys.stdout``.
    hooks:
        Pre-configured :class:`HookSet`.  A new empty set is created when
        not provided.
    prompt:
        Initial :class:`Prompt`.  Defaults to :data:`DEFAULT_PROMPT`.
    suppress_output:
        If ``True``, suppress printing the result of evaluations.

    Attributes
    ----------
    binding_stack:
        Stack of namespace dicts.  The innermost (current) namespace is at
        the top (``binding_stack[-1]``).
    eval_string:
        Buffer accumulating a partial multi-line expression.
    input_ring:
        :class:`Ring` of the last *memory_size* input lines.
    output_ring:
        :class:`Ring` of the last *memory_size* output values.
    last_result:
        The result of the most recent successful evaluation.
    last_file:
        Last file referenced during the session (user-settable).
    last_dir:
        Last directory referenced during the session (user-settable).
    suppress_output:
        When ``True``, :meth:`show_result` is silenced.
    hooks:
        The :class:`HookSet` for this session.
    """

    EMPTY_COMPLETIONS: list[str] = []

    def __init__(
        self,
        target: dict | None = None,
        memory_size: int = 100,
        output: TextIO | None = None,
        hooks: HookSet | None = None,
        prompt: Prompt | None = None,
        suppress_output: bool = False,
    ) -> None:
        # ---- core state ---------------------------------------------------
        self.binding_stack: list[dict] = []
        self.eval_string: str = ""
        self.backtrace: list[str] = []
        self.suppress_output: bool = suppress_output
        self.last_result: Any = None
        self.last_file: str | None = None
        self.last_dir: str | None = None

        self._last_result_is_exception: bool = False
        self._last_exception: BaseException | None = None
        self._exit_value: Any = None
        self._stopped: bool = False
        self._extra_sticky_locals: dict[str, Callable] = {}

        # ---- rings --------------------------------------------------------
        self.input_ring: Ring = Ring(memory_size)
        self.output_ring: Ring = Ring(memory_size)
        # Seed input ring with None (mirrors Ruby: @input_ring << nil)
        self.input_ring << None

        # ---- I/O ----------------------------------------------------------
        self._output: TextIO = output or sys.stdout

        # ---- hooks --------------------------------------------------------
        self.hooks: HookSet = hooks or HookSet()

        # ---- prompt stack -------------------------------------------------
        self._prompt_stack: list[Prompt] = []
        self.push_prompt(prompt or DEFAULT_PROMPT)

        # ---- command registry ---------------------------------------------
        self._registry: Registry = Registry()

        # ---- line buffer (mirrors Pry.line_buffer / Pry.current_line) -----
        self._line_buffer: list[str] = []
        self._current_line: int = 0

        # ---- initialise result tracking -----------------------------------
        self._set_last_result(None)

        # ---- push initial binding -----------------------------------------
        self._push_initial_binding(target)

        # ---- fire when_started hook ---------------------------------------
        self.exec_hook("when_started", target, self)

    # ======================================================================
    # Prompt management  (Pry#prompt, push_prompt, pop_prompt, select_prompt)
    # ======================================================================

    @property
    def prompt(self) -> Prompt:
        """The active prompt (top of the prompt stack)."""
        return self._prompt_stack[-1]

    @prompt.setter
    def prompt(self, new_prompt: Prompt) -> None:
        if self._prompt_stack:
            self._prompt_stack[-1] = new_prompt
        else:
            self.push_prompt(new_prompt)

    def push_prompt(self, new_prompt: Prompt) -> Prompt:
        """Push *new_prompt* onto the prompt stack and return it.

        Equivalent to ``Pry#push_prompt``.
        """
        self._prompt_stack.append(new_prompt)
        return new_prompt

    def pop_prompt(self) -> Prompt:
        """Pop the current prompt, never emptying the stack.

        Equivalent to ``Pry#pop_prompt``.
        """
        if len(self._prompt_stack) > 1:
            return self._prompt_stack.pop()
        return self.prompt

    def select_prompt(self) -> str:
        """Return the current prompt string.

        Uses the *incomplete* proc when ``eval_string`` is non-empty,
        otherwise uses the *wait* proc.  Equivalent to ``Pry#select_prompt``.
        """
        obj = self.current_binding.get("self", None)
        level = len(self.binding_stack) - 1
        if self.eval_string:
            return self.prompt.incomplete_proc(obj, level, self)
        return self.prompt.wait_proc(obj, level, self)

    # ======================================================================
    # Binding (namespace) stack  (Pry#binding_stack, push_binding, …)
    # ======================================================================

    def _push_initial_binding(self, target: dict | None = None) -> None:
        """Push the initial namespace (equivalent to ``push_initial_binding``)."""
        self.push_binding(target if target is not None else {})

    def push_binding(self, namespace: dict) -> None:
        """Push *namespace* onto the binding stack.

        Marks the instance as active (``_stopped = False``), mirroring the
        Ruby implementation.
        """
        self._stopped = False
        self.binding_stack.append(namespace)

    def pop_binding(self) -> dict | None:
        """Pop and return the innermost namespace, or ``None`` if empty."""
        return self.binding_stack.pop() if self.binding_stack else None

    @property
    def current_binding(self) -> dict:
        """The innermost (currently active) namespace dict.

        Equivalent to ``Pry#current_binding`` / ``Pry#current_context``.
        """
        return self.binding_stack[-1] if self.binding_stack else {}

    #: Alias kept for API compatibility with older code.
    current_context = current_binding

    # ======================================================================
    # Memory size  (Pry#memory_size, memory_size=)
    # ======================================================================

    @property
    def memory_size(self) -> int:
        """Maximum entries kept in :attr:`input_ring` and :attr:`output_ring`."""
        return self.input_ring.max_size

    @memory_size.setter
    def memory_size(self, size: int) -> None:
        self.input_ring = Ring(size)
        self.output_ring = Ring(size)

    # ======================================================================
    # Sticky locals  (Pry#sticky_locals, inject_local, inject_sticky_locals!, …)
    # ======================================================================

    @property
    def sticky_locals(self) -> dict[str, Any]:
        """Mapping of sticky local names to their current values.

        Sticky locals are injected into every namespace on each REPL tick.
        Equivalent to ``Pry#sticky_locals``.

        Built-in sticky locals (mirrors Ruby's defaults)
        -------------------------------------------------
        ``_in_``         Input ring.
        ``_out_``        Output ring.
        ``repl_instance``  This :class:`ReplInstance`.
        ``_ex_``         Last exception (or ``None``).
        ``_file_``       :attr:`last_file`.
        ``_dir_``        :attr:`last_dir`.
        ``_``            :attr:`last_result`.
        ``__``           Second-most-recent output value.
        """
        locals_: dict[str, Any] = {
            "_in_": self.input_ring,
            "_out_": self.output_ring,
            "repl_instance": self,
            "_ex_": self._last_exception,
            "_file_": self.last_file,
            "_dir_": self.last_dir,
            "_": self.last_result,
            "__": self.output_ring[-2] if len(self.output_ring) >= 2 else None,
        }
        for name, factory in self._extra_sticky_locals.items():
            locals_[name] = factory() if callable(factory) else factory
        return locals_

    def add_sticky_local(self, name: str, factory: Callable) -> None:
        """Register a sticky local refreshed on every REPL tick.

        Equivalent to ``Pry#add_sticky_local``.

        Parameters
        ----------
        name:
            Variable name (without leading underscore).
        factory:
            Zero-argument callable returning the current value.
        """
        self._extra_sticky_locals[name] = factory

    def inject_local(self, name: str, value: Any, namespace: dict) -> Any:
        """Set ``namespace[name] = value`` (resolving callables first).

        Equivalent to ``Pry#inject_local``.
        """
        resolved = value() if callable(value) else value
        namespace[name] = resolved
        return resolved

    def inject_sticky_locals(self) -> None:
        """Inject all sticky locals into the current namespace.

        Equivalent to ``Pry#inject_sticky_locals!``.
        """
        ns = self.current_binding
        for name, value in self.sticky_locals.items():
            self.inject_local(name, value, ns)

    # ======================================================================
    # Eval-string management  (reset_eval_string)
    # ======================================================================

    def reset_eval_string(self) -> None:
        """Discard any buffered partial expression.

        Equivalent to ``Pry#reset_eval_string``.
        """
        self.eval_string = ""

    # ======================================================================
    # Input history  (update_input_history)
    # ======================================================================

    def _update_input_history(self, code: str) -> None:
        """Record *code* in the input ring and line buffer.

        Equivalent to ``Pry#update_input_history``.
        """
        self.input_ring << code
        if code:
            self._line_buffer.extend(code.splitlines(keepends=True))
            self._current_line += code.count("\n")

    # ======================================================================
    # Result / exception tracking  (set_last_result, last_exception=, …)
    # ======================================================================

    def _set_last_result(self, result: Any, code: str = "") -> None:
        """Record a successful evaluation result.

        Equivalent to ``Pry#set_last_result``.
        """
        self._last_result_is_exception = False
        self.output_ring << result
        if code.strip():
            self.last_result = result

    def _set_last_exception(self, exc: BaseException) -> None:
        """Record an exception as the last result.

        Equivalent to the ``last_exception=`` setter.
        """
        self._last_result_is_exception = True
        self.output_ring << exc
        self._last_exception = exc

    @property
    def last_exception(self) -> BaseException | None:
        """The last exception raised during evaluation."""
        return self._last_exception

    @last_exception.setter
    def last_exception(self, exc: BaseException) -> None:
        self._set_last_exception(exc)

    def last_result_is_exception(self) -> bool:
        """Return ``True`` if the last result was a raised exception.

        Equivalent to ``Pry#last_result_is_exception?``.
        """
        return self._last_result_is_exception

    def should_print(self) -> bool:
        """Return ``True`` if output should be printed.

        Equivalent to ``Pry#should_print?``.
        """
        return not self.suppress_output

    # ======================================================================
    # Command processing  (process_command, process_command_safely, run_command)
    # ======================================================================

    def process_command(self, val: str) -> bool:
        """Try to match and execute *val* as a registered command.

        Returns ``True`` if a command was matched and run, ``False``
        otherwise.  Equivalent to ``Pry#process_command``.
        """
        parts = val.strip().split()
        if not parts:
            return False
        name = parts[0]
        try:
            cmd = self._registry.command(name)
        except KeyError:
            return False
        prompt_tail = val.strip()[len(name):].strip()
        result = cmd.execute(prompt_tail)
        self._set_last_result(result, val)
        return True

    def process_command_safely(self, val: str) -> bool:
        """Like :meth:`process_command` but prints :exc:`CommandError` to output.

        Equivalent to ``Pry#process_command_safely``.
        """
        try:
            return self.process_command(val)
        except CommandError as exc:
            self._output.write(f"Error: {exc}\n")
            return True

    def run_command(self, val: str) -> None:
        """Execute command *val*, raising :exc:`KeyError` if not found.

        Equivalent to ``Pry#run_command``.
        """
        parts = val.strip().split()
        if not parts:
            raise KeyError("empty command")
        name = parts[0]
        cmd = self._registry.command(name)
        prompt_tail = val.strip()[len(name):].strip()
        cmd.execute(prompt_tail)

    # ======================================================================
    # Python evaluation  (evaluate_ruby → evaluate_python, show_result)
    # ======================================================================

    def evaluate_python(self, code: str) -> Any:
        """Evaluate *code* in the current namespace and return the result.

        Fires ``before_eval`` and ``after_eval`` hooks.  Equivalent to
        ``Pry#evaluate_ruby``.

        Expression results are returned directly; statements (e.g. ``x = 1``)
        return ``None``.
        """
        self.inject_sticky_locals()
        self.exec_hook("before_eval", code, self)
        ns = self.current_binding
        result: Any = None
        try:
            try:
                # eval() is intentional here: this is a REPL where the user
                # deliberately executes arbitrary Python code in their own
                # namespace – the same security model as CPython's interactive
                # interpreter or Jupyter kernels.
                result = eval(code, ns)  # noqa: S307
            except SyntaxError:
                exec(code, ns)  # noqa: S102  (same rationale as above)
                result = None
        finally:
            self._update_input_history(code)
            self.exec_hook("after_eval", result, self)
        self._set_last_result(result, code)
        return result

    def show_result(self, result: Any) -> None:
        """Print *result* to output (or the exception if one was raised).

        Equivalent to ``Pry#show_result``.
        """
        if self.last_result_is_exception():
            self._output.write(f"Exception: {result!r}\n")
        elif self.should_print():
            self._output.write(f"=> {result!r}\n")

    # ======================================================================
    # Hooks  (exec_hook)
    # ======================================================================

    def exec_hook(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Fire the named hook, printing any errors to output.

        Equivalent to ``Pry#exec_hook``.
        """
        errors_before = len(self.hooks.errors)
        result = self.hooks.exec_hook(name, *args, **kwargs)
        for exc in self.hooks.errors[errors_before:]:
            self._output.write(
                f"{name} hook failed: {type(exc).__name__}: {exc}\n"
                "(see repl_instance.hooks.errors to debug)\n"
            )
        return result

    # ======================================================================
    # Completions  (complete)
    # ======================================================================

    def complete(self, s: str) -> list[str]:
        """Return completion candidates for the prefix *s*.

        Equivalent to ``Pry#complete``.
        """
        ns = self.current_binding
        candidates: list[str] = [k for k in ns if k.startswith(s)]
        cmd_names = [c.name for c in self._registry.commands]
        candidates += [n for n in cmd_names if n.lower().startswith(s.lower())]
        return sorted(set(candidates)) or self.EMPTY_COMPLETIONS

    # ======================================================================
    # Main eval entry-point  (Pry#eval → ReplInstance.eval)
    # ======================================================================

    def eval(self, line: str | None, generated: bool = False) -> bool:
        """Process a single *line* of input.

        This is the primary public API – equivalent to ``Pry#eval`` in Ruby.

        Parameters
        ----------
        line:
            The text typed by the user, or ``None`` for EOF / Ctrl-D.
        generated:
            When ``True``, the line is not recorded in history.

        Returns
        -------
        bool
            ``True`` if the instance can accept more input, ``False`` once
            it has stopped.

        Raises
        ------
        Exception
            Any exception propagated via :meth:`raise_up`.
        """
        if self._stopped:
            return False
        try:
            self._handle_line(line, generated=generated)
            return not self._stopped
        except ReplBreakout as bo:
            self._stopped = True
            self._exit_value = bo.value
            return False
        except ReplRaiseUp as ru:
            self._stopped = True
            raise ru.exception

    # ======================================================================
    # Internal line handler  (handle_line)
    # ======================================================================

    def _handle_line(self, line: str | None, generated: bool = False) -> None:
        """Process one input line – equivalent to ``Pry#handle_line``.

        Pipeline
        --------
        1. ``None`` → stop the session (Ctrl-D / EOF).
        2. Optionally record in history.
        3. Try command processing.
        4. Otherwise append to ``eval_string`` buffer.
        5. Fire ``after_read`` hook.
        6. Check for a complete expression; if complete, evaluate and show.
        """
        if line is None:
            # EOF / Ctrl-D – equivalent to config.control_d_handler
            self._stopped = True
            return

        if not generated:
            self._line_buffer.append(line)

        self.suppress_output = False
        self.inject_sticky_locals()

        # Try command processing first
        if not self.process_command_safely(line):
            if line or self.eval_string:
                self.eval_string += line.rstrip("\n") + "\n"

        # Fire after_read hook (mirrors Ruby: exec_hook :after_read)
        self.exec_hook("after_read", self.eval_string, self)

        # Check completeness of buffered expression
        if not self._is_complete_expression(self.eval_string):
            return

        # Suppress output for empty / comment-only input
        stripped = self.eval_string.strip()
        if not stripped or stripped.startswith("#"):
            self.suppress_output = True

        code = self.eval_string
        self.reset_eval_string()

        try:
            result = self.evaluate_python(code)
        except Exception as exc:  # noqa: BLE001 – REPL must catch all user errors
            self.last_exception = exc
            result = exc

        self.show_result(result)

        if not self.binding_stack:
            raise ReplBreakout()

    def _is_complete_expression(self, source: str) -> bool:
        """Return ``True`` if *source* is a syntactically complete Python expression.

        Uses :func:`codeop.compile_command` – returns ``None`` for incomplete
        input and raises :exc:`SyntaxError` for invalid input.
        """
        if not source.strip():
            return False
        try:
            compiled = codeop.compile_command(source)
            return compiled is not None
        except SyntaxError:
            # Surface the error on the next evaluation attempt
            return True

    # ======================================================================
    # raise_up  (Pry#raise_up, raise_up!)
    # ======================================================================

    def raise_up(self, exc: BaseException | None = None, *, force: bool = False) -> None:
        """Raise *exc* out of the current REPL session.

        When *force* is ``True`` (or only one binding remains), the entire
        binding stack is cleared and the exception propagates all the way
        out.  Otherwise the innermost binding is popped and the exception is
        re-raised immediately (caught by the enclosing REPL loop).

        Equivalent to ``Pry#raise_up`` (force=False) and ``Pry#raise_up!``
        (force=True).
        """
        if exc is None:
            exc = self._last_exception or RuntimeError()
        if force or len(self.binding_stack) <= 1:
            self.binding_stack.clear()
            raise ReplRaiseUp(exc)
        self.pop_binding()
        raise exc

    # ======================================================================
    # REPL entry-point  (Pry#repl)
    # ======================================================================

    def repl(
        self,
        target: dict | None = None,
        input_: Any = None,
    ) -> Any:
        """Run the interactive read-eval-print loop.

        Reads lines from *input_* (defaults to ``sys.stdin``) and feeds each
        one to :meth:`eval`.  The loop terminates when :meth:`eval` returns
        ``False``.

        Equivalent to ``Pry#repl``.

        Parameters
        ----------
        target:
            Optional additional namespace to push before starting.
        input_:
            File-like object supplying input lines.  Defaults to
            ``sys.stdin``.

        Returns
        -------
        Any
            The session's exit value (set by a ``raise_up`` / breakout).
        """
        if target is not None:
            self.push_binding(target)

        reader = input_ or sys.stdin
        while True:
            try:
                prompt_str = self.select_prompt()
                self._output.write(prompt_str)
                self._output.flush()
                raw = reader.readline()
                line: str | None = raw if raw else None  # EOF → None
            except KeyboardInterrupt:
                self._output.write("\n")
                continue
            if not self.eval(line):
                break
        return self._exit_value

    # ======================================================================
    # Convenience
    # ======================================================================

    @property
    def quiet(self) -> bool:
        """Whether to suppress the startup banner (mirrors ``Pry#quiet?``)."""
        return self.suppress_output

    def __repr__(self) -> str:
        return (
            f"ReplInstance("
            f"bindings={len(self.binding_stack)}, "
            f"memory_size={self.memory_size})"
        )
