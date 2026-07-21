"""Orchestrate the eval: run each config N times, score, aggregate, report.

Usage (real, needs ANTHROPIC_API_KEY in the environment):
    python run_eval.py --fixture ../example_fixture/fixture_expr_eval --runs 5

Offline plumbing test (no key, no cost):
    python mock_backend.py
"""

import argparse
import os
import statistics
import tempfile

from configs import CONFIGS, cost_for
from executor import run_config
from tools import setup_workdir, score_objective


# --- Backends -----------------------------------------------------------------

class AnthropicBackend:
    """Thin wrapper over the Anthropic SDK. Reads ANTHROPIC_API_KEY from env."""

    def __init__(self):
        import anthropic  # imported lazily so mock runs need no dependency
        self.client = anthropic.Anthropic()

    def create(self, model, max_tokens, system, tools, messages):
        kwargs = dict(model=model, max_tokens=max_tokens, system=system, messages=messages)
        if tools:
            kwargs["tools"] = tools
        return self.client.messages.create(**kwargs)


# --- Cost -------------------------------------------------------------------

def combined_cost(config, usage):
    """Dollar cost of one run: executor tokens + advisor tokens. None if pricing unset."""
    ein, eout = usage["executor"]
    ain, aout = usage["advisor"]
    ce = cost_for(config.executor_model, ein, eout)
    ca = 0.0 if not config.advisor_model else cost_for(config.advisor_model, ain, aout)
    if ce is None or ca is None:
        return None
    return ce + ca


# --- Suite ------------------------------------------------------------------

def run_suite(backend, fixture_dir, configs, n_runs, max_turns, workroot):
    """Run every config n_runs times, each in its own clean working dir."""
    results = {}
    for config in configs:
        runs = []
        for i in range(n_runs):
            wd = os.path.join(workroot, f"{config.name}_run{i}")
            setup_workdir(fixture_dir, wd)
            outcome = run_config(backend, config, wd, max_turns=max_turns)
            score = score_objective(wd)
            runs.append({
                "score": score,
                "usage": outcome["usage"],
                "turns": outcome["turns"],
                "advisor_calls": outcome["advisor_calls"],
                "stop": outcome["stop"],
                "cost": combined_cost(config, outcome["usage"]),
            })
        results[config.name] = runs
    return results


# --- Report -----------------------------------------------------------------

def _mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def report(results, configs):
    by_name = {c.name: c for c in configs}
    rows = []
    for name, runs in results.items():
        n = len(runs)
        n_pass = sum(1 for r in runs if r["score"]["passed"])
        pass_rate = n_pass / n if n else 0.0
        mean_cost = _mean([r["cost"] for r in runs])
        mean_turns = _mean([r["turns"] for r in runs])
        mean_adv = _mean([r["advisor_calls"] for r in runs])
        rows.append({
            "name": name, "pass_rate": pass_rate, "n_pass": n_pass, "n": n,
            "mean_cost": mean_cost, "mean_turns": mean_turns, "mean_adv": mean_adv,
        })

    # "best value": highest pass rate, tie-break on lowest known cost
    def value_key(r):
        return (r["pass_rate"], -(r["mean_cost"] if r["mean_cost"] is not None else 1e9))
    best = max(rows, key=value_key)["name"] if rows else None

    lines = []
    lines.append("")
    lines.append(f"{'config':<14}{'pass rate':>11}{'mean $/task':>14}{'mean turns':>12}{'adv calls':>11}  verdict")
    lines.append("-" * 78)
    for r in rows:
        cost = f"${r['mean_cost']:.4f}" if r["mean_cost"] is not None else "n/a"
        turns = f"{r['mean_turns']:.1f}" if r["mean_turns"] is not None else "-"
        adv = f"{r['mean_adv']:.1f}" if r["mean_adv"] is not None else "-"
        verdict = "← best value" if r["name"] == best else ""
        frac = f"{r['n_pass']}/{r['n']}"
        lines.append(
            f"{r['name']:<14}{frac:>11}{cost:>14}{turns:>12}{adv:>11}  {verdict}"
        )
    lines.append("-" * 78)
    if any(r["mean_cost"] is None for r in rows):
        lines.append("note: cost shows 'n/a' where PRICING isn't set in configs.py — fill it in for real $ figures.")
    lines.append("")
    return "\n".join(lines)


# --- CLI --------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Cost-lever eval harness")
    ap.add_argument("--fixture", required=True, help="path to a fixture dir (with TASK.md, calc/, tests/)")
    ap.add_argument("--runs", type=int, default=5, help="runs per config (pass rate needs repeats)")
    ap.add_argument("--max-turns", type=int, default=25)
    ap.add_argument("--workroot", default=None, help="where to create working copies (default: temp dir)")
    args = ap.parse_args()

    backend = AnthropicBackend()
    workroot = args.workroot or tempfile.mkdtemp(prefix="eval_")
    results = run_suite(backend, args.fixture, CONFIGS, args.runs, args.max_turns, workroot)
    print(report(results, CONFIGS))


if __name__ == "__main__":
    main()
