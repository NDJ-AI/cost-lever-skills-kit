# Cost-Lever Skills Kit

Seven Claude Code skills covering two things: running a full AI-integration
engagement end to end (discovery through a verified deliverable), and one
narrower question inside it — **for this AI-integrated workflow, which cost
levers actually apply, and for the ones that risk quality, can we prove it
instead of guessing?**

Built for n8n/Zapier/agent workflows using Claude (or similar LLM APIs), but the
reasoning isn't platform-specific.

## What's in here

```
skills/
  engagement-pipeline/SKILL.md          — orchestrator: discovery → scoping → architecture → build → verification
  agent-architecture-advisor/SKILL.md   — should this even get built, and what shape
  ai-integration-architect/SKILL.md     — org-wide "where does Claude actually sit"
  agent-design-principles/SKILL.md      — is a multi-agent design actually sound
  org-deployment/SKILL.md               — rolling Claude out across a team (plans, seats, connectors)
    + benchmark.md, evals.json          — the with-skill vs. no-skill eval this one was built against
  ai-workflow-cost-levers/SKILL.md      — names the cost levers, given constraints
  cost-lever-eval/SKILL.md              — measures the two levers with real quality risk
runner/
  quick_check.py                      — LIGHT path: single-turn cheaper-model spot-check
  configs.py, tools.py, executor.py, run_eval.py, mock_backend.py, README.md
                                      — HEAVY path: the agentic harness cost-lever-eval drives
example_specs/
  classify_sentiment.json, summarize_subjective.json  — copy-me specs for quick_check
example_fixture/
  fixture_expr_eval/                 — a validated example task for the heavy harness (stub + tests + reference solution)
docs/
  Claude_API_Cost_Optimization_Reference.md   — the standalone reference version
  EXAMPLE_AUDIT.md                            — a full worked example, start to finish
```

Every skill folder above also ships a pre-built `.skill` file next to its
`SKILL.md` — see Install below. The one exception is `engagement-pipeline`,
which also calls a sixth skill, **`mcp-builder`**, at its build stage (for when
the plan calls for a new reusable capability rather than a one-off workflow).
That one isn't bundled here — it isn't this kit's own skill, and no local copy
of it exists to include; if `engagement-pipeline` reaches that stage, `mcp-builder`
needs to be available separately.

## Discovery-to-delivery engagement stack

Five skills, one flow — the shape every real engagement moves through: figure
out if something's worth building, decide what it should look like, design it
so it doesn't fall over, get it deployed to the people who'll use it, and (via
the orchestrator) prove it works before calling it done. Skip a stage and you
either overbuild something nobody needed, or ship something nobody can verify.

- **`engagement-pipeline`** — the orchestrator. Runs the other skills in
  sequence with explicit handoffs: discovery → scoping → architecture → build →
  a verified deliverable. Reaches for `mcp-builder` (external, see above) at the
  build stage when the answer is "new reusable capability," not "one workflow."
- **`agent-architecture-advisor`** — the skeptic. Before any build: is this
  worth building at all, and if so, what's the lightest shape (single-agent
  loop, subagent delegation, a scheduled task, an MCP server, or a Skill)?
  Pushes back on reaching for n8n/a custom server/a whole agent system when a
  plain conversation with Claude already solves it.
- **`ai-integration-architect`** — the org-wide version. Given a company's
  existing tools, team, and goals, produces an integration architecture and
  rollout plan — not a single automation spec. Not for a one-off build request
  (that's `agent-architecture-advisor`).
- **`agent-design-principles`** — once the decision to build is made, checks
  whether the internal design actually holds up: failure modes, incentive
  alignment, autonomy calibration, escalation paths, interface contracts
  between agents, and whether each piece's scope is sized right.
- **`org-deployment`** — the mechanics of rolling Claude out across a team:
  plan selection (Pro/Max vs. Team vs. Enterprise), org-level connectors,
  plugin marketplaces, Cowork admin controls, and the chat-surface-vs-headless-
  API split. Includes the eval (`benchmark.md`, `evals.json`) it was built and
  scored against — 100% vs. 56% assertion pass rate with-skill vs. without.

## Cost-lever kit

Two skills, plus a reference doc and a worked example, for the narrower
question above — which AI-workflow cost levers actually apply, and can the
risky ones be measured rather than guessed at.

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
makes "did we test it" the load-bearing question. It has two paths, matched to
the task shape:

- **Light — `quick_check.py`** (most cases): a *single-turn* step (one prompt in,
  one answer out — summarize, classify, extract, i.e. most n8n/Zapier nodes).
  Feed it a handful of real inputs and two models; it runs both and compares —
  auto-scored for label/JSON/field checks, side-by-side for subjective ones. No
  fixture, no agent loop.
- **Heavy — `run_eval.py`** (rare): a *long-horizon agentic* task, a model looping
  with tools against an objective check (a test suite). Compares cheap-solo vs.
  cheap+advisor vs. stronger and reports a pass-rate-and-cost table. This is the
  one that needs a validated fixture.

Sending a single-turn model swap through the heavy harness is the main way to
overbuild — the skill routes you to the light path first. Fuzzy quality-judged
tasks still get a side-by-side to eyeball, not an auto-score; a rubric scorer
isn't built yet.

The harness itself (`runner/`) is included — it holds no secrets anywhere in the
code. It reads an API key from the environment at run time (`ANTHROPIC_API_KEY`,
picked up automatically by the Anthropic SDK); nothing is hardcoded or stored in
any file here. See `runner/README.md` for the two things to do before a real
(non-mock) run: fill in current pricing, and never write a key into a file that
gets committed.

## Install

Each skill folder includes a pre-built `.skill` file (a zip archive under a
different extension — nothing to build yourself). Upload it directly: attach
it to a chat message, or Settings > Capabilities > Skills > "+" > Create skill
> Upload (Cowork: Customize > Skills). The `SKILL.md` sitting next to it is
the same content unpacked — read it directly if your setup reads skill
sources from a folder instead of an upload.

The harness is plain Python (`pip install -r runner/requirements.txt`).

## See it work

Two ways:

- **Read it:** `docs/EXAMPLE_AUDIT.md` walks a full worked example — a
  representative n8n workflow (two triggers of different urgency feeding one
  AI reasoning node, downstream of a diff step) through the entire skill
  output: constraints, a verdict on every lever, the recompute check, and a
  concrete one-node fix. Fictionalized, but the finding pattern (a diff gets
  computed and then ignored) is common enough to be worth having a template for.
- **Run the light path:** `cd runner && python quick_check.py --mock` — an
  offline, scripted self-test with no API key and no cost. It runs a sentiment
  step through a good and a deliberately bad "model" and asserts the scorer
  separates them (5/5 vs 2/5), showing exactly which inputs the weak one botches.
  Then copy a spec from `example_specs/` and run it for real with `--spec`.
- **Run the heavy path:** `cd runner && python mock_backend.py` — an offline,
  scripted self-test that proves the whole agentic harness (agent loop, tools,
  advisor consult, pytest scorer, cost aggregation, report table) against
  `example_fixture/fixture_expr_eval/`, and asserts that a buggy implementation
  fails while a correct one (with or without an advisor consult) passes — i.e.,
  that the scorer actually discriminates.

## Why this exists

Most "make your AI workflow cheaper" advice is a flat list of tricks applied
regardless of the situation. The actual discipline is narrower: name what's
non-negotiable (speed, quality) before anything else, rule levers in or out
against those, and reserve real measurement for the one or two levers where
guessing wrong actually costs something — output quality, not just money.
