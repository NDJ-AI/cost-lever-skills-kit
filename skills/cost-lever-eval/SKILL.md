---
name: cost-lever-eval
description: 'Measure, instead of guessing, whether a cheaper model (or the executor+advisor pattern) holds up for a real task. Two paths: a LIGHT single-turn spot-check (quick_check.py) for the common case -- one prompt in, one answer out, like a summarize/classify/extract step in an n8n/Zapier/script workflow -- which runs a few real inputs through the current vs. a cheaper model and compares; and a HEAVY agentic harness (run_eval.py) for long-horizon multi-turn tool-using coding tasks, comparing cheap-solo vs. cheap+advisor vs. stronger. Use when someone asks which model to run a step on, whether a cheaper model is good enough, whether the executor+advisor pattern is worth it, or wants a pass-rate-and-cost number instead of a guess. Downstream of ai-workflow-cost-levers, which names the levers in the abstract. Objective/checkable success only for now (label/json/test-suite); fuzzy summary-quality steps get a side-by-side to eyeball, not an auto-score.'
---

# Cost-Lever Eval

Turns "which model configuration should this run on?" from a guess into a measured
answer, using the eval harness in the Cost_Lever_Eval_Harness project. This is the
measurement companion to `ai-workflow-cost-levers`: that skill names the levers
(cheaper model, executor+advisor); this one runs them against a real task and
reports pass-rate and cost per config.

## First: which of the two tools does this task need?

There are two measurement paths in this kit. Pick before doing anything else --
most cost-lever questions are the light one, and running the heavy harness on a
single-turn step is the main way to overbuild here.

- **Single-turn step** -- one prompt in, one answer out: summarize, classify,
  extract fields, rewrite. This is *most* n8n / Zapier / script steps. Use the
  **light path**: `quick_check.py`. No fixture, no agent loop, no reference
  solution. Jump to "Light path" below.
- **Long-horizon agentic task** -- a model runs a multi-turn loop, using tools,
  writing and revising code against a check (e.g. "implement this module until the
  tests pass"). Only this shape needs the full harness (`run_eval.py`) and the
  executor+advisor lever. Continue to "Heavy path" below.

If unsure: does the step call the model **once**, or does it **loop with tools**?
Once → light. Loops → heavy. When someone drops in an n8n/Zapier export, look at
the node: a single LLM node feeding the next step is single-turn; an agent node
that iterates is not.

## Light path: `quick_check.py` (single-turn)

The honest test for "does a cheaper model hold up on this one step" is a
side-by-side on real inputs, not a paragraph of reasoning.

1. **Build a spec** from the workflow step: the prompt (with `{input}` where the
   per-case text goes), the two models (`current` vs `candidate`), a check type,
   and 5-10 *real* inputs pulled from the actual workflow. Check types:
   - `label` / `contains` -- classification or any step with a known right answer
     token (give each case an `expect`). Fully auto-scored.
   - `json` -- extraction / structured output (optional `required_keys` per case).
     Auto-scored on parse + keys present.
   - `none` -- summaries and other subjective steps. No score; prints the pairs
     side by side for the user to read. That *is* the deliverable here.
2. **Run it:**
   ```
   python quick_check.py --spec my_step.json
   python quick_check.py --mock      # offline self-test first, no key, no cost
   ```
3. **Read it:** pass-rate first (objective) or read the pairs (subjective). A
   candidate that matches the current model on real inputs at lower cost is a real
   win; a gap of even 1-2 cases is the signal to keep the current model here.

See `example_specs/` for a `label` spec and a `none` spec to copy. This path is
enough for the large majority of workflow cost questions -- don't escalate to the
heavy harness unless the task genuinely loops.

## Heavy path: when this applies (and when it doesn't)

**Applies:** a long-horizon agentic task with an *objective* success check -- a
pytest suite, a schema, a validator -- where "which model config" is a live
question and cost matters. This is the executor+advisor lever measured instead of
assumed.

**Doesn't apply:**
- Single-turn steps -- use the light path above, not this.
- A task with no objective check yet -- that's the *fuzzy* path (quality judged by
  a rubric + LLM-judge). The harness's fuzzy scorer isn't built. Don't fake an
  objective score for a fuzzy task: either help the user define a rubric and judge
  by hand, or flag it as a later phase.

## Step 0: locate the harness and check preconditions

- The runner lives wherever the user moved the `Cost_Lever_Eval_Harness` project
  (it holds an API key, so it's kept out of the Drive-synced vault -- e.g.
  `E:\ClaudeWork\Personal\Cost_Lever_Eval_Harness\runner\`). Confirm the actual path.
- `ANTHROPIC_API_KEY` must be set in the environment (never a file in the vault).
- ⏱ In `configs.py`: verify the model IDs are current, and fill in real `PRICING`
  -- the cost column shows `n/a` until prices are set. Model IDs and prices both drift.

## Step 1: classify the task -- objective or fuzzy

Ask (or determine) the one branching question: is success checkable by a test
suite / schema (objective), or is it a quality judgment (fuzzy)? Objective →
continue. Fuzzy → see "Doesn't apply" above.

## Step 2: get or build the fixture -- and validate it both ways

A fixture is: `TASK.md` (the task in plain language) + the code package + a
`tests/` suite. Two sources:

- **The user's real repo** already has a failing test plus a task description →
  point the runner at it. Most useful, because the answer is real work.
- **No fixture yet** → scaffold one like `fixture_expr_eval` (a stub + a real test
  suite + a correct reference solution kept in `solution/`, which the runner never
  copies into an executor's workspace).

Either way, **validate the fixture both ways before trusting any comparison**: the
tests must FAIL on the starting state (task genuinely unsolved) and PASS on a
correct reference (tests are achievable, not contradictory). A fixture that isn't
validated both ways can produce a meaningless result. Also dial difficulty to the
sweet spot: hard enough that the cheap model *sometimes* fails, or there's no
spread between configs to measure.

## Step 3: run the harness

```
python run_eval.py --fixture <path-to-fixture> --runs 5
```

- Configs come from `configs.py` -- by default the triplet the advisor question is
  really about (cheap-solo, cheap+advisor, stronger-solo). Edit that list per task.
- Run 3-5+ times per config. Models are stochastic; a single run hides the spread,
  and pass *rate* (e.g. 2/5 vs 5/5) is the real signal.
- Offline sanity check with no key/spend: `python mock_backend.py`.

## Step 4: read the report with cost-lever judgment

The table gives pass-rate, mean $/task, mean turns, and advisor calls per config.
Interpret it, don't just relay it:

- **Cheap-solo already clears the bar** → use it. Advisor/stronger just add cost.
  (The cheaper-model lever wins outright.)
- **Cheap-solo fails, cheap+advisor closes the gap** at a fraction of the stronger
  model's cost → the executor+advisor lever is paying off. Recommend it.
- **Cheap+advisor still fails** (good advice, but the executor can't carry the
  mechanical turns) → the executor is too weak; a stronger executor is the real
  answer. A good plan can't rescue an executor that can't do the grunt work.
- **Weigh pass-rate first, cost second.** A 2-point pass-rate gain at 3x cost
  usually isn't worth it; a 40-point gain at lower cost obviously is.

## Output

A recommendation tied to the numbers, not a table dump:

```
## Recommendation
[Which config to run this task on, and why -- pass-rate then cost.]

## Which lever this confirms
[Feeds back into ai-workflow-cost-levers: cheaper-model wins / executor+advisor
pays off / executor too weak. State it plainly.]

## Caveats
[Small sample, pricing unverified, or the fixture may not represent the real task.]
```

Never recommend a config off a single run, off an unvalidated fixture, or off an
`n/a` cost column presented as if it were a real dollar figure.
