# Cost-Lever Skills Kit

Two Claude Code skills, plus a reference doc and a worked example, for one
question: **for this AI-integrated workflow, which cost levers actually apply —
and for the ones that risk quality, can we prove it instead of guessing?**

Built for n8n/Zapier/agent workflows using Claude (or similar LLM APIs), but the
reasoning isn't platform-specific.

## What's in here

```
skills/
  ai-workflow-cost-levers/SKILL.md   — names the levers, given constraints
  cost-lever-eval/SKILL.md           — measures the two levers with real quality risk
runner/
  configs.py, tools.py, executor.py, run_eval.py, mock_backend.py, README.md
                                      — the actual harness cost-lever-eval drives
example_fixture/
  fixture_expr_eval/                 — a validated example task (stub + tests + reference solution)
docs/
  Claude_API_Cost_Optimization_Reference.md   — the standalone reference version
  EXAMPLE_AUDIT.md                            — a full worked example, start to finish
```

### `ai-workflow-cost-levers`

Given a workflow and a cost concern, names the hard constraints first
(does this need to return fast? does output quality actually matter here?),
walks the remaining levers against those constraints — prompt caching, batch
processing, cheaper model tier, executor+advisor model composition, context
trimming/retrieval — and separately checks for needless recompute (a workflow
that reprocesses everything, or fires an expensive step, on every run
regardless of whether anything actually changed). Ends in a situation-grounded
verdict, not a generic list.

### `cost-lever-eval`

The measurement companion. Two of the levers above — cheaper model tier, and
executor+advisor — are the ones that can quietly degrade output quality, which
makes "did we test it" the load-bearing question. This skill drives a small
eval harness: build (or point at) a fixture with an objective success check (a
test suite, a schema), run it under 2-3 model configurations, and report a
pass-rate-and-cost table instead of a guess. Scope-gated to objective/
test-suite tasks for now — a fuzzy/quality-judged task needs a rubric scorer,
which isn't built yet.

The harness itself (`runner/`) is included — it holds no secrets anywhere in the
code. It reads an API key from the environment at run time (`ANTHROPIC_API_KEY`,
picked up automatically by the Anthropic SDK); nothing is hardcoded or stored in
any file here. See `runner/README.md` for the two things to do before a real
(non-mock) run: fill in current pricing, and never write a key into a file that
gets committed.

## Install

The skills are plain Claude Code skills — a single `SKILL.md` each, no
dependencies. Package a folder as a `.skill` (zip it) and install via
Settings > Capabilities, or use the `SKILL.md` directly if your setup reads
skill sources from a folder.

The harness is plain Python (`pip install -r runner/requirements.txt`).

## See it work

Two ways:

- **Read it:** `docs/EXAMPLE_AUDIT.md` walks a full worked example — a
  representative n8n workflow (two triggers of different urgency feeding one
  AI reasoning node, downstream of a diff step) through the entire skill
  output: constraints, a verdict on every lever, the recompute check, and a
  concrete one-node fix. Fictionalized, but the finding pattern (a diff gets
  computed and then ignored) is common enough to be worth having a template for.
- **Run it:** `cd runner && python mock_backend.py` — an offline, scripted
  self-test with no API key and no cost. It proves the whole harness (agent
  loop, tools, advisor consult, pytest scorer, cost aggregation, report table)
  against `example_fixture/fixture_expr_eval/`, and asserts that a buggy
  implementation fails while a correct one (with or without an advisor consult)
  passes — i.e., that the scorer actually discriminates.

## Why this exists

Most "make your AI workflow cheaper" advice is a flat list of tricks applied
regardless of the situation. The actual discipline is narrower: name what's
non-negotiable (speed, quality) before anything else, rule levers in or out
against those, and reserve real measurement for the one or two levers where
guessing wrong actually costs something — output quality, not just money.
