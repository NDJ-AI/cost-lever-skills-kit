---
name: cost-lever-eval
description: 'Run a real, measured comparison of model configurations for an agentic coding task -- cheap executor alone vs. cheap executor + frontier advisor vs. a stronger model -- instead of guessing which to use. Use when someone has a long-horizon agentic task (coding, multi-step tool use) and asks which model to run it on, whether the executor+advisor pattern is worth it here, whether a cheaper model holds up, or wants a pass-rate-and-cost number behind the choice. Downstream of ai-workflow-cost-levers (which names the levers in the abstract) -- this skill measures them against an actual task with the eval harness. Objective/test-suite tasks only for now; fuzzy/quality-judged tasks need a rubric scorer that is not built yet.'
---

# Cost-Lever Eval

Turns "which model configuration should this run on?" from a guess into a measured
answer, using the eval harness in the Cost_Lever_Eval_Harness project. This is the
measurement companion to `ai-workflow-cost-levers`: that skill names the levers
(cheaper model, executor+advisor); this one runs them against a real task and
reports pass-rate and cost per config.

## When this applies (and when it doesn't)

**Applies:** a long-horizon agentic task with an *objective* success check -- a
pytest suite, a schema, a validator -- where "which model config" is a live
question and cost matters. This is the executor+advisor lever measured instead of
assumed.

**Doesn't apply:**
- Single-turn Q&A or any non-loop task -- there's no agent loop and nothing to
  escalate mid-task (the scope gate from `ai-workflow-cost-levers`). Say so and stop.
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
