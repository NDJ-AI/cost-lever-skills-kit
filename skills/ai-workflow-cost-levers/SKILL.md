---
name: ai-workflow-cost-levers
description: 'Decide which cost levers actually apply to an AI-integrated workflow (prompt caching, batch processing, cheaper model tier, executor+advisor model composition, context trimming/retrieval, incremental vs. full-recompute) and which don''t, given constraints like timeliness and output quality. Use whenever a workflow calls an LLM (n8n, Zapier, a script, an agent) and the user asks "how do I make this cheaper," "is this going to be expensive," "which lever should I pull," or is scoping cost for an AI automation. Also trigger when a workflow "regenerates," "recomputes," or "reprocesses" a full dataset every run -- often the real cost driver, independent of model choice. Also relevant when a long-horizon agentic task needs near-frontier quality but frontier cost is the concern -- see the executor+advisor lever. Downstream of agent-architecture-advisor (whether to build) and agent-design-principles (how to structure) -- for once an AI step exists or is planned, deciding what to do about its running cost.'
---

# AI Workflow Cost Levers

## Don't optimize before there's something to measure

If the workflow hasn't run yet, the honest first move is usually: build the plain version, run it, look at what it actually costs. Applying every lever below before a single execution has happened solves a guessed problem with real complexity -- new failure modes, more nodes, more to maintain -- for a cost number nobody's actually seen yet. Reach for the rest of this skill once cost is either a confirmed real number (it ran, and it's expensive) or a legitimate anticipated concern worth reasoning through before building (a client asking what this will cost monthly, for instance).

## Step 1: Name the hard constraints first

Two questions rule things out before the levers are even worth considering:

- **Does this need to return quickly?** A person waiting on it, or a downstream step depending on a fast reply, rules out anything async.
- **Does the quality of the output actually matter here?** If this step is a judgment call, a draft, or anything where a worse answer is a worse product -- not just a cheaper one -- that rules out blindly downgrading model strength.

Naming these first matters because a lever that conflicts with a real constraint isn't a tradeoff worth weighing, it's off the table. Recommending Batch API to someone who needs a fast reply, or a cheaper model to someone whose whole system depends on judgment quality, isn't a real option just because it's theoretically cheaper.

## Step 2: Walk the remaining levers

**Prompt caching** -- reuses a fixed, repeated prompt prefix (system prompt, style/template instructions, anything that doesn't change call to call) so repeat calls aren't billed full price for text that hasn't changed. Real savings are claimed at 50-90% of input cost where it applies.
- Only helps when calls happen close together in time -- the cache has a short lifespan (roughly 5 minutes by default, extendable to an hour at extra cost). Infrequent or widely-spaced calls get no benefit, just added complexity in how the prompt has to be structured to separate the fixed part from the variable part.

**Batch processing** (the formal async batch API, roughly 50% off standard pricing) -- only fits work already confirmed *not* time-sensitive in Step 1. Restructures the workflow itself (submit, then poll, then retrieve, instead of one synchronous call) -- real engineering work, not a settings toggle, and worth weighing against the added nodes and error-handling surface it introduces.

**Cheaper model tier** -- worth considering only after Step 1 confirmed quality isn't the bottleneck for this specific step, and only after actually testing the cheaper model's output against the current one. Assumed savings without a quality check is how a system quietly gets worse while looking cheaper on paper. If quality *is* the bottleneck, don't stop here -- the executor+advisor lever below is the way to keep most of the quality while still paying mostly cheap-model rates.

**Executor + advisor** (model composition -- long-horizon agentic work only) -- instead of picking one model, run a cheap "executor" model for the entire agent loop (tool calls, code, drafting) and expose a stronger "advisor" model as a tool it consults only when it hits a decision above its confidence. Most tokens bill at the cheap executor rate; the advisor is called rarely (often ~once per task) and returns a small amount of guidance. This is the one lever that addresses the quality-vs-cost tension the cheaper-model lever otherwise closes off: reported results keep roughly 90%+ of the frontier model's task performance at a large fraction of its cost, and where the cheap/expensive gap is wide the pair can *beat* the executor running alone (a good early plan prevents wasted attempts and misguided tool calls).
- Scope gate: this only makes sense for long-horizon agentic tasks -- coding, multi-step research, computer use -- where most turns are mechanical but a good plan matters. Skip it entirely for single-turn Q&A: there's no loop to run and nothing to escalate mid-task.
- Executors under-call the advisor by default. Prompt them to consult early (before committing to an approach) and late (before declaring the task done). Cap advisor output (~2,000 tokens is plenty) and enable prompt caching on long loops -- the two stack.
- ⏱ Recently-shipped, fast-moving capability. Some platforms offer it as a near-one-line feature (Anthropic's advisor tool via a beta API header; OpenRouter has a cross-provider version where executor and advisor can be different vendors). Verify current availability, syntax, and pricing before quoting it to a client rather than assuming the above still holds.
- **Measure, don't assume.** This lever and the cheaper-model tier are the two here that can silently degrade quality, so they're the ones worth *testing* rather than guessing. When the model-choice question is live and the task has an objective success check (a test suite, a schema), hand off to the **`cost-lever-eval`** skill: it runs the task under each configuration (cheap-solo, cheap+advisor, stronger) and returns a pass-rate-and-cost table, turning this verdict into a measurement. (Objective/test-suite tasks only; a fuzzy-quality task still needs a hand-built rubric.)

**Context trimming via retrieval** -- send only what's relevant instead of everything by default. The real mechanism: convert content to embeddings (a cheap, separate model from the reasoning call itself), rank by similarity to whatever's being processed right now, and only pass the closest matches into the actual prompt. This is standard retrieval-augmented generation -- the expensive model never sees the raw dataset, only the shortlist an embedding search already narrowed down. Trimming blindly (an arbitrary length cutoff, dropping the oldest content) risks cutting the actual signal instead of the bulk; a real ranking step is what avoids that.

## Step 3: Check for the one that isn't a lever at all -- needless recompute

The most common actual cost driver often isn't which lever got picked, it's whether the workflow reprocesses an entire existing dataset every run instead of only what's new. If someone describes a step as "regenerate the whole thing" or "recompute X" on a recurring trigger, ask whether it's tracking what changed since the last run (a timestamp, a change-tracking token from the source system -- most platforms with a sync/webhook layer have one) and only processing that delta.

This is often what actually resolves an apparent conflict between "needs to be frequent or timely" and "needs to be cheap" -- a delta-based run stays cheap even at high frequency, because each run only touches a small amount of new content rather than reprocessing everything that already existed. Frequency isn't usually the real cost problem; reprocessing unchanged content on every run is.

## Output

Give a situation-grounded verdict, not a generic recitation of every lever. Structure the answer like this:

```
## Constraints
- Timeliness: [does this need to return fast? what that rules out]
- Quality: [does output quality matter here? what that rules out]

## Verdict per lever
- Prompt caching: [apply / doesn't apply] -- [why, tied to their actual call pattern]
- Batch processing: [apply / doesn't apply] -- [why, tied to the timeliness constraint]
- Cheaper model: [apply / doesn't apply] -- [why, tied to the quality constraint + whether it's been tested]
- Executor + advisor: [apply / doesn't apply] -- [why, tied to whether this is long-horizon agentic work and whether quality-at-frontier-cost is the actual tension]
- Context trimming/retrieval: [apply / doesn't apply] -- [why, tied to what's actually being sent today]

## The recompute check
[Is this workflow reprocessing a full dataset every run, or only deltas? Call this out explicitly even if none of the levers above seem to fit -- it's frequently the actual driver.]

## What to actually do first
[The single highest-impact, lowest-risk change given everything above -- not everything at once]
```

A verdict of "doesn't apply" is only useful if it says why, tied to something the user actually described -- not a generic rule recited on its own.

**If the recommendation is to switch model tier or add an advisor, and the task is objective-checkable, don't ship it on assumption -- hand off to the `cost-lever-eval` skill to measure it first.** Those are the only levers here with a real quality risk, so they're the ones that warrant a measured pass-rate/cost comparison rather than a paper verdict. The other levers (caching, batch, trimming, delta-recompute) are cost-only or quality-neutral when done right and don't need an eval.
