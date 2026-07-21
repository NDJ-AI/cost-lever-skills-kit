"""Local tools the executor can call, plus the objective scorer.

Everything here is deterministic filesystem/subprocess work — no model calls.
All file operations are confined to the run's working directory; path escape is
rejected.
"""

import pathlib
import shutil
import subprocess
import sys


# --- Working-directory setup --------------------------------------------------

# Only these are copied into an executor's working dir. NEVER copy solution/.
COPY_ALLOWLIST = ["TASK.md", "calc", "tests"]


def setup_workdir(fixture_dir: str, workdir: str):
    """Create a clean working copy of the fixture containing only task + code + tests."""
    wd = pathlib.Path(workdir)
    if wd.exists():
        shutil.rmtree(wd)
    wd.mkdir(parents=True)
    src = pathlib.Path(fixture_dir)
    for item in COPY_ALLOWLIST:
        s = src / item
        if not s.exists():
            continue
        d = wd / item
        if s.is_dir():
            shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(s, d)


def _safe_path(workdir: str, rel: str) -> pathlib.Path:
    p = (pathlib.Path(workdir) / rel).resolve()
    wd = pathlib.Path(workdir).resolve()
    if wd != p and wd not in p.parents:
        raise ValueError(f"path escapes working directory: {rel!r}")
    return p


# --- Tool schemas (Anthropic tool-use format) ---------------------------------

BASE_TOOL_SCHEMAS = [
    {
        "name": "list_files",
        "description": "List all files in the working directory as a tree.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_file",
        "description": "Read a file's full contents. Path is relative to the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Overwrite a file with new contents. Path is relative to the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_tests",
        "description": "Run the pytest suite and return its output. Use this to check your work as you go.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

ADVISOR_TOOL_SCHEMA = {
    "name": "consult_advisor",
    "description": (
        "Consult a senior engineer for strategic guidance when you are unsure how to "
        "proceed. Ask before committing to an approach, and again before declaring the "
        "task done. Provide a specific question and enough context to answer it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"question": {"type": "string"}},
        "required": ["question"],
    },
}


# --- Local tool dispatch ------------------------------------------------------

def dispatch_local_tool(workdir: str, name: str, tool_input: dict) -> str:
    try:
        if name == "list_files":
            root = pathlib.Path(workdir)
            files = sorted(
                str(p.relative_to(root))
                for p in root.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            )
            return "\n".join(files) if files else "(empty)"
        if name == "read_file":
            p = _safe_path(workdir, tool_input["path"])
            if not p.exists():
                return f"ERROR: file not found: {tool_input['path']}"
            return p.read_text()
        if name == "write_file":
            p = _safe_path(workdir, tool_input["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(tool_input["content"])
            return f"wrote {tool_input['path']} ({len(tool_input['content'])} chars)"
        if name == "run_tests":
            res = _run_pytest(workdir, timeout=120)
            return res["output"]
        return f"ERROR: unknown tool {name!r}"
    except Exception as e:  # tools must return an error string, never crash the loop
        return f"ERROR: {type(e).__name__}: {e}"


# --- Objective scorer ---------------------------------------------------------

def _run_pytest(workdir: str, timeout: int):
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return {"returncode": proc.returncode, "output": out}
    except subprocess.TimeoutExpired:
        return {"returncode": 124, "output": f"TIMEOUT after {timeout}s"}


def score_objective(workdir: str, timeout: int = 120) -> dict:
    """Authoritative score: run pytest, read the exit code. 0 == pass."""
    res = _run_pytest(workdir, timeout=timeout)
    out = res["output"]
    n_pass = _parse_count(out, "passed")
    n_fail = _parse_count(out, "failed") + _parse_count(out, "error")
    return {
        "passed": res["returncode"] == 0,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "returncode": res["returncode"],
        "tail": "\n".join(out.strip().splitlines()[-6:]),
    }


def _parse_count(output: str, word: str) -> int:
    # pytest summary lines look like: "34 passed, 2 failed in 0.10s"
    import re
    m = re.search(rf"(\d+) {word}", output)
    return int(m.group(1)) if m else 0
