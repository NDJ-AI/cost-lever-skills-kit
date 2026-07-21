# Worked Example: Running a Real Workflow Through `ai-workflow-cost-levers`

This is a fictionalized but representative example, built to show what the
skill's output actually looks like against a real n8n export — not a
hypothetical description. The workflow shape (two triggers of different
urgency, a diff step whose output goes unused, one AI reasoning node) is a
pattern that shows up often enough to be worth a template of its own.

## The workflow

**"Team Status Digest"** — an n8n workflow with 11 nodes:

- **Two triggers:** a daily Schedule Trigger (8am, nobody waiting) and a Slack
  slash-command Webhook (someone typed `/team-status` and is waiting on a reply).
- **Four sequential HTTP Request nodes** pulling current state from an internal
  project-tracker API: a team/unit record, its members, its open projects, its
  open checklist/action items.
- **A Code node** that flattens that data into a snapshot, compares it against
  the snapshot saved from the last run (via workflow static data), and computes
  a diff: unfilled roles, project status changes, new checklist items.
- **One AI Agent node** (Claude), given both the full current snapshot *and*
  the diff, producing: unresolved/unfilled items, a plain-English changes list,
  risk/drift flags (does the data suggest anything is quietly off), and a
  one-paragraph summary.
- **A parse/format Code node**, then a **Slack post**.

Both triggers feed the same AI Agent node.

## Running it through the skill

### Constraints

**Timeliness:** two triggers converge on one AI Agent node — a daily schedule
(not time-sensitive) and an on-demand slash command (a person is waiting). The
node inherits the *stricter* constraint: it must return quickly, for both paths,
because they share the same node.

**Quality:** the digest has four parts, not one uniform task. The unresolved-items
list and the changes list are close to mechanical — the diff step already
computed the underlying facts. The risk/drift flags are a genuine judgment
call — inferring whether the data suggests something is off. That's the one
piece where a worse model gives a worse product, not just a cheaper one.

### Verdict per lever

- **Prompt caching:** doesn't apply. Calls aren't clustered in time (once daily,
  plus occasional on-demand hits hours apart) — the cache window won't survive
  the gap.
- **Batch processing:** doesn't apply, and can't be made to apply without
  splitting the workflow. The on-demand path needs a synchronous reply; Batch's
  async turnaround is incompatible with a person waiting, and both triggers
  share one node.
- **Cheaper model tier:** worth testing, not assuming — and only for part of the
  output. The mechanical parts would likely hold up on a cheaper model; the
  risk/drift flags are the part to actually test before switching, since that's
  where quality genuinely matters.
- **Executor + advisor:** doesn't apply. This node makes one request and gets
  one response — there's no multi-turn agent loop with tool calls to escalate
  mid-task. The scope gate rules this out cleanly.
- **Context trimming/retrieval:** doesn't apply. This is already scoped to one
  team's current state, not a larger corpus being narrowed down.

### The recompute check — the actual finding

The diff step already computes what changed since the last run. But the AI
Agent prompt sends the **full current snapshot** every time regardless, and the
workflow calls the AI Agent on every scheduled run whether or not the diff is
empty. On a quiet day where nothing changed, the schedule trigger still burns a
full LLM call to produce a "nothing changed" digest.

Most operational data doesn't change every single day. If a meaningful fraction
of days have no real changes, that fraction of calls isn't just cheaper to
avoid — it's fully skippable, with zero information loss.

### What to actually do first

Add one gate (an IF/Filter node) between the diff step and the AI Agent,
**on the scheduled-trigger path only**:

- If the diff is empty (no unfilled/status/checklist changes) and it isn't the
  first run → skip the AI Agent call; post a short static "no changes" line, or
  skip the post entirely.
- Otherwise → proceed to the AI Agent as normal.
- The on-demand slash-command path must **always** reach the AI Agent — a human
  explicitly asked, so it always gets an answer, even if the answer is "nothing
  changed."

This is a single-node structural fix, not a lever swap — and it typically has
more impact than any of the five levers above, none of which applied here.

## The general lesson

A diff/dedup step existing in a workflow doesn't mean it's actually being used
to control cost. Check whether the expensive step is *gated* on the diff, not
just whether a diff is computed — those are two different things, and it's easy
to build the first without the second.
