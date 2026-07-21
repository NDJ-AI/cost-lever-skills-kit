"""The executor agent loop and the advisor consult.

The loop is backend-agnostic: it calls `backend.create(...)`, which mimics
Anthropic's `client.messages.create`. The real backend (run_eval.AnthropicBackend)
wraps the SDK; the mock backend (mock_backend.MockBackend) scripts responses so
the whole loop, tools, scorer, and report can be exercised with no API key.
"""

import json

from tools import BASE_TOOL_SCHEMAS, ADVISOR_TOOL_SCHEMA, dispatch_local_tool


EXECUTOR_SYSTEM = (
    "You are a coding agent working inside a fixed working directory. You have "
    "tools to list, read, and write files and to run the test suite. Read TASK.md "
    "first, implement the required code, run the tests, and iterate until they all "
    "pass. When every test passes, stop and say so. Do not edit the test files."
)

ADVISOR_SYSTEM = (
    "You are a senior software engineer advising a junior engineer who is doing the "
    "hands-on work. You cannot see or edit files yourself. Based on the transcript "
    "and their question, give concise, concrete guidance — a plan, a correction, or "
    "a 'you appear done / not yet done' signal. Be brief; a short answer beats a long one."
)


def _blocks_to_dicts(content):
    """Normalize SDK block objects (or dicts) into plain, uniform dicts."""
    out = []
    for b in content:
        btype = getattr(b, "type", None) or (b.get("type") if isinstance(b, dict) else None)
        if btype == "text":
            out.append({"type": "text", "text": getattr(b, "text", None) if not isinstance(b, dict) else b.get("text", "")})
        elif btype == "tool_use":
            if isinstance(b, dict):
                out.append({"type": "tool_use", "id": b.get("id"), "name": b.get("name"), "input": b.get("input", {})})
            else:
                out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    return out


def _transcript_text(messages):
    """Compact serialization of the running transcript, for advisor context."""
    lines = []
    for m in messages:
        role, content = m["role"], m["content"]
        if isinstance(content, str):
            lines.append(f"{role}: {content}")
            continue
        for b in content:
            t = b.get("type")
            if t == "text":
                lines.append(f"{role}: {b['text']}")
            elif t == "tool_use":
                lines.append(f"{role} calls {b['name']}({json.dumps(b['input'])[:400]})")
            elif t == "tool_result":
                lines.append(f"tool_result: {str(b['content'])[:400]}")
    return "\n".join(lines)


def consult_advisor(backend, advisor_model, messages, question, max_tokens=2000):
    """One advisor call: hand the transcript + question to the stronger model."""
    ctx = _transcript_text(messages)
    resp = backend.create(
        model=advisor_model,
        max_tokens=max_tokens,
        system=ADVISOR_SYSTEM,
        tools=[],
        messages=[{
            "role": "user",
            "content": f"Transcript so far:\n{ctx}\n\nExecutor's question: {question}\n\nGive concise guidance.",
        }],
    )
    text = "".join(b["text"] for b in _blocks_to_dicts(resp.content) if b["type"] == "text")
    return (text or "(no advice)"), (resp.usage.input_tokens, resp.usage.output_tokens)


def run_config(backend, config, workdir, max_turns=25, executor_max_tokens=4096):
    """Run one config's executor loop to completion (or max_turns) in workdir."""
    tools = list(BASE_TOOL_SCHEMAS)
    if config.advisor_model:
        tools.append(ADVISOR_TOOL_SCHEMA)

    messages = [{
        "role": "user",
        "content": "Your task is described in TASK.md in the working directory. Read it, then implement the solution and make the tests pass.",
    }]
    usage = {"executor": [0, 0], "advisor": [0, 0]}
    stop_reason, turns, advisor_calls = None, 0, 0

    for turns in range(1, max_turns + 1):
        resp = backend.create(
            model=config.executor_model,
            max_tokens=executor_max_tokens,
            system=EXECUTOR_SYSTEM,
            tools=tools,
            messages=messages,
        )
        usage["executor"][0] += resp.usage.input_tokens
        usage["executor"][1] += resp.usage.output_tokens
        stop_reason = resp.stop_reason

        content = _blocks_to_dicts(resp.content)
        messages.append({"role": "assistant", "content": content})
        tool_uses = [b for b in content if b["type"] == "tool_use"]

        if stop_reason != "tool_use" or not tool_uses:
            break

        results = []
        for tu in tool_uses:
            if tu["name"] == "consult_advisor" and config.advisor_model:
                advisor_calls += 1
                ans, (ai, ao) = consult_advisor(backend, config.advisor_model, messages, tu["input"].get("question", ""))
                usage["advisor"][0] += ai
                usage["advisor"][1] += ao
                results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": ans})
            else:
                out = dispatch_local_tool(workdir, tu["name"], tu["input"])
                results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": out})
        messages.append({"role": "user", "content": results})

    return {"usage": usage, "turns": turns, "stop": stop_reason, "advisor_calls": advisor_calls}
