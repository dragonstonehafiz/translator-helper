"""Utilities for validating frontend runtime dependencies."""

from __future__ import annotations

from importlib import import_module
from typing import Iterable, List

import streamlit as st

# Core libraries the frontend expects. Extend as needed.
REQUIRED_LIBRARIES: Iterable[str] = (
    "streamlit",
    "pysubs2",
    "torch",
    "openai",
    "tqdm",
)


def missing_libraries(required: Iterable[str] = REQUIRED_LIBRARIES) -> List[str]:
    """Return a list of library names that cannot be imported."""
    failures: List[str] = []
    for library in required:
        try:
            import_module(library)
        except Exception:
            failures.append(library)
    return failures


def guard_dependencies(required: Iterable[str] = REQUIRED_LIBRARIES) -> None:
    """Show an error and halt rendering if any required library is missing."""
    failures = missing_libraries(required)
    if failures:
        st.error(
            "Missing required libraries: "
            + ", ".join(failures)
            + ". Install them via requirements.txt or individually before proceeding."
        )
        st.stop()
