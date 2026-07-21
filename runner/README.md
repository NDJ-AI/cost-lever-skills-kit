# Runner — cost-lever eval

Two tools, matched to task shape. **Pick the light one first** — it fits most
workflow cost questions, and the heavy one is easy to overbuild with.

## Light path — `quick_check.py` (single-turn)

For a step that calls the model **once** (summarize, classify, extract — most
n8n/Zapier nodes). Runs a handful of real inputs through the current model and a
cheaper candidate and compares: auto-scored for `label`/`json`/`contains` checks,
side-by-side for subjective (`none`) steps. No fixture, no agent loop.

```
python quick_check.py --mock                    # offline self-test, no key/cost
python quick_check.py --spec ../example_specs/classify_sentiment.json   # real run
```

Spec format and check types are documented at the top of `quick_check.py`;
copy-me specs are in `../example_specs/`.

## Heavy path — `run_eval.py` (agentic)

Drives each model configuration through the executor agent loop against a
fixture, scores the result with pytest, aggregates cost, and prints a comparison
table. Only for a task that **loops with tools** (a model writing/revising code
until tests pass). This is the objective (coding/test-suite) core; a fuzzy/rubric
scorer for quality-judged tasks is a natural extension, not built here.

## Files

- `configs.py` — the configs to compare (executor/advisor model pairs), model IDs
  (env-overridable), and the PRICING table. ⏱ Verify model IDs and prices — both drift.
- `tools.py` — the executor's local tools (list/read/write/run_tests), the
  working-dir setup (copies only `TASK.md`, `calc/`, `tests/` — never `solution/`),
  and the objective scorer (`pytest` exit code).
- `executor.py` — the backend-agnostic agent loop and the advisor consult.
- `run_eval.py` — orchestration (N runs per config, fresh workdir each), cost
  aggregation, the report table, the real `AnthropicBackend`, and the CLI.
- `mock_backend.py` — scripted backend + offline self-test for the heavy path (no API key, no cost).
- `quick_check.py` — the light single-turn path + its own offline `--mock` self-test.

## Run it

Offline plumbing test — no key, no spend, proves loop + tools + advisor + scorer + report:

```
pip install -r requirements.txt
python mock_backend.py
```

Real run — needs a key in the environment (never hardcode it anywhere in this code):

```
export ANTHROPIC_API_KEY=sk-...
python run_eval.py --fixture ../example_fixture/fixture_expr_eval --runs 5
```

Optional model overrides (defaults in `configs.py`):

```
export EVAL_HAIKU_MODEL=... EVAL_SONNET_MODEL=... EVAL_OPUS_MODEL=...
```

## Before a real run

1. **Secrets:** the key lives in the environment only, read by the SDK
   (`anthropic.Anthropic()` picks up `ANTHROPIC_API_KEY` automatically) — never
   written into a file in this repo. If you clone this into a synced folder
   (Dropbox, Drive, etc.), that's fine for the code; just don't add a `.env`
   with a real key to anything that syncs or gets committed.
2. **Pricing:** the cost column shows `n/a` until `PRICING` in `configs.py` is
   filled from your provider's current price list.
3. **Point `--fixture` at your own task** once you've validated it (see
   `../example_fixture/`'s own notes on what makes a fixture trustworthy).

## Design notes

- The advisor is wired **manually** (a custom `consult_advisor` tool → a separate
  call to the stronger model with the transcript), not via a provider's native
  advisor tool. This is the version that generalizes (any providers, full cost
  visibility, and it's what a no-code/low-code workflow build would do). A
  provider's native beta advisor tool is an alternative if you'd rather it
  orchestrate server-side.
- Each config runs in its own clean working copy; each run is independent. Run
  3–5+ times per config — models are stochastic and a single run hides real spread.
- A run that hits `--max-turns` without finishing simply fails the score, which is
  the correct signal for a floundering executor.
