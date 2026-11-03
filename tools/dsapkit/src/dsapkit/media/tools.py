"""Running ffmpeg and ffprobe: found on the PATH, called with an argument list (never through a shell), and
turned into a BuildError with their own message when they fail."""

from __future__ import annotations

import shutil
import subprocess
from typing import Callable, Sequence

from ..errors import BuildError

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def find_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise BuildError(f"{name} is not installed (macOS: brew install ffmpeg)")
    return found


def run_checked(run: Runner, args: Sequence[str], timeout: int, what: str) -> str:
    done = run(list(args), check=False, capture_output=True, text=True, timeout=timeout)
    if done.returncode != 0:
        raise BuildError(f"{what} failed:\n  {(done.stderr or done.stdout).strip()[:800]}")
    return done.stdout
