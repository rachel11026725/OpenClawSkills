"""Third-party dependency registry for the Python porting workspace.

Mirrors the structure of ``scripts/releases/ios-prebuild/dependencies.js``
in the upstream React Native repository.  Each :class:`Dependency` entry
captures the name, version, and canonical download URL for a vendored C++
library so that tooling can fetch and validate the correct source archives.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Dependency:
    """A vendored third-party C++ dependency."""

    name: str
    version: str
    url: str
    sources: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dependency list – keep entries sorted alphabetically by name.
# ---------------------------------------------------------------------------

DEPENDENCIES: list[Dependency] = [
    Dependency(
        name="boost",
        version="1_83_0",
        url="https://archives.boost.io/release/1.83.0/source/boost_1_83_0.tar.gz",
        sources=["boost/"],
    ),
    Dependency(
        name="doubleconversion",
        version="1.1.6",
        url="https://github.com/google/double-conversion/archive/refs/tags/v1.1.6.tar.gz",
        sources=["double-conversion/"],
    ),
    Dependency(
        name="fast_float",
        version="8.0.0",
        url="https://github.com/fastfloat/fast_float/archive/refs/tags/v8.0.0.tar.gz",
        sources=["include/fast_float/*.h"],
    ),
    Dependency(
        name="fmt",
        version="12.1.0",
        url="https://github.com/fmtlib/fmt/archive/refs/tags/12.1.0.tar.gz",
        sources=["src/format.cc", "include/fmt/*.h"],
    ),
    Dependency(
        name="folly",
        version="2024.11.18.00",
        url="https://github.com/facebook/folly/archive/refs/tags/v2024.11.18.00.tar.gz",
        sources=["folly/"],
    ),
    Dependency(
        name="gflags",
        version="2.2.0",
        url="https://github.com/gflags/gflags/archive/refs/tags/v2.2.0.tar.gz",
        sources=["src/", "include/"],
    ),
    Dependency(
        name="glog",
        version="0.3.5",
        url="https://github.com/google/glog/archive/refs/tags/v0.3.5.tar.gz",
        sources=["src/", "src/glog/*.h"],
    ),
]


def get_dependency(name: str) -> Dependency:
    """Return the :class:`Dependency` with the given *name* (case-insensitive).

    Raises :exc:`KeyError` when the dependency is not found.
    """
    key = name.lower()
    for dep in DEPENDENCIES:
        if dep.name.lower() == key:
            return dep
    raise KeyError(f"Dependency not found: {name!r}")
