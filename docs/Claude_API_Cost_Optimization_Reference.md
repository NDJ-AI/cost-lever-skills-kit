# Claude API Cost Optimization — When and How

*A reusable reference, not tied to one project or client. Written to be checked before building any Claude-in-n8n (or similar agentic) workflow — the levers below, and the judgment calls around them, apply the same way regardless of what the workflow is for.*

## The core rule: build simple first, measure, then optimize the real bottleneck

None of the levers below are "always turn this on." Each one only helps under specific usage conditions, and each carries a real tradeoff — cost, latency, quality, or complexity. Applying them all by default, before a workflow has even run once, is premature optimization: added complexity for a cost problem that hasn't been confirmed at the scale the workflow will actually run at. The right sequence is: build the plain version, run it for real, look at actual per-execution cost and frequency, then apply only the specific lever that addresses the actual bottleneck.

This mirrors the same judgment call an "should we even build this" pass already applies to deciding whether to build automation at all — don't build for a guess, and don't optimize for a guess either.

## The levers

**Prompt caching** — reuses a fixed prompt prefix (system prompt, style instructions, taxonomy/template context that doesn't change call to call) so repeat calls aren't billed full price for unchanged text. Anthropic's own figures claim 50-90% input cost reduction where it applies.
- Drawback: the cache has a short TTL — around 5 minutes by default, extendable to an hour at extra cost. It only helps when calls happen close together in time. Space executions far apart (e.g. a few times a day) and the cache expires between them — no benefit, just added prompt-structuring complexity (explicit cache_control breakpoints, careful separation of fixed vs. variable content) for nothing.
- Applies when: high call frequency, large shared fixed context, calls clustered in time.

**Batch API** — async processing at roughly 50% off standard per-token pricing.
- Drawback: not immediate — batch jobs can take a long time (sometimes hours) to complete. Only fits work with no real-time expectation. Also restructures the workflow itself: submit → poll → retrieve instead of one synchronous call, which is more nodes and more error-handling surface to build and maintain.
- Applies when: the step genuinely doesn't need to return quickly — e.g. a nightly or batched-throughout-the-day summarization step, not something a person is waiting on mid-task.

**Cheaper model tier (e.g. Haiku instead of Sonnet/Opus)** — the most direct cost lever, but the one with the most real risk.
- Drawback: genuine quality tradeoff. A weaker model can produce worse drafts, miss subtler connections, or make worse judgment calls — which matters most exactly where the step's value depends on judgment quality (a worse proposal is a worse product, not just a cheaper one).
- Applies when: tested and confirmed the cheaper model's output quality holds up for that specific step — never assumed.
- If quality *is* the bottleneck, don't stop here — the executor+advisor lever below keeps most of the quality while still paying mostly cheap-model rates.

**Executor + advisor (model composition — long-horizon agentic work only)** — instead of picking one model, run a cheap "executor" model for the whole agent loop (tool calls, code, drafting) and expose a stronger "advisor" model as a tool it consults only when it hits a decision above its confidence. Most tokens bill at the cheap executor rate; the advisor is called rarely (often ~once per task) and returns a small chunk of guidance. This is the lever that addresses the quality-vs-cost tension the cheaper-model lever otherwise closes off: reported results keep roughly 90%+ of the frontier model's task performance at a fraction of its cost, and where the cheap/expensive gap is wide the pair can *beat* the executor alone (a good early plan prevents wasted attempts and misguided tool calls).
- Drawback / scope gate: only makes sense for long-horizon agentic tasks — coding, multi-step research, computer use — where most turns are mechanical but a good plan matters. Useless for single-turn Q&A: there's no loop to run and nothing to escalate mid-task. Also adds a second model/provider to wire and reason about.
- Practical: executors under-call the advisor by default — prompt them to consult early (before committing to an approach) and late (before declaring done). Cap advisor output (~2,000 tokens) and stack prompt caching on long loops.
- ⏱ Fast-moving, recently-shipped capability. Some platforms offer it near-one-line (Anthropic's advisor tool via a beta API header; OpenRouter has a cross-provider version where executor and advisor can be different vendors). Verify current availability, syntax, and pricing before quoting it to a client rather than assuming the above still holds.
- Applies when: a long-horizon agentic step needs near-frontier quality but frontier cost is the concern, and the cheap executor can reliably carry the mechanical turns on its own (test this first — a good plan can't rescue an executor that can't do the grunt work). For an objective/test-suite task, this is measurable rather than guessed — see the companion eval harness.

**Trimming context per call** — sending only the relevant slice of information instead of a large default context (e.g. only the most relevant few existing records instead of scanning a whole corpus for connections).
- Drawback: cuts input tokens directly, but overly aggressive trimming risks losing exactly the cross-references that make a synthesis/judgment step valuable in the first place. Needs a real retrieval/ranking step to trim irrelevant bulk without trimming relevant signal — not just "send less."
- Applies when: the current context sent per call is clearly larger than what the step actually needs, confirmed by looking at what's actually being sent (not assumed).
- **Mechanism (how "what to keep" actually gets decided):** semantic retrieval, not a fixed rule. Every record gets converted into an embedding (a vector representation of its meaning) at capture time — a separate, much cheaper model/API than the reasoning call itself. When new content needs processing, it gets embedded too, then compared against existing embeddings by similarity (cosine distance is the usual measure). Only the closest matches — top-N, or above a similarity threshold — get pulled into the actual prompt. This is the standard retrieval-augmented-generation pattern: the reasoning model only ever sees the shortlist an embedding search already narrowed down, never the raw corpus.

## Frequency isn't the cost driver — needless recompute is

A workflow that needs to stay timely (can't tolerate Batch API's delay) doesn't have to be expensive if it's built right. The actual expensive pattern is recomputing something from the *entire* corpus (or re-running an AI step every trigger regardless of whether anything changed) rather than only processing what's new since the last run. Fix: incremental / delta processing.

- Track a "last processed" marker (e.g. a source system's native change-tracking token, or a simple stored timestamp/snapshot from the last run).
- Each run asks "what changed since I last checked," gets back a small delta instead of the whole dataset, and only embeds/processes/updates that delta — not everything that already existed.
- This is what actually resolves a timeliness-vs-cost conflict: the workflow can still run frequently (timely, no Batch API delay) because each run is cheap by construction — small delta in, small delta processed — rather than cheap only because it runs rarely.
- Applies whenever a step is described as "regenerate/recompute the whole thing" on a recurring trigger — that phrase is usually the tell that delta processing hasn't been applied yet, independent of which of the levers above also apply.
- **A subtler version of the same trap:** a workflow can compute a diff/delta correctly and then *ignore it* — sending the full current state to the AI step regardless, and firing that step every run even when the diff is empty. The fix there isn't a different lever, it's actually gating the expensive step on whether the diff has anything in it (with an explicit carve-out for any on-demand/human-initiated trigger, which should always get an answer even when nothing changed).

## Where this actually gets implemented

This is workflow-editing work (n8n or otherwise), not a console setting — most of it means restructuring nodes/steps (batch submit/poll/retrieve, cache_control fields added to the request, a model dropdown change, adjusted retrieval logic, or an added gate/branch node), which fits a normal build-and-edit workflow rather than a single toggle. Model tier swap is the one exception — often just a dropdown/config change, no code needed.

Anthropic Console does **not** offer a per-API-key dollar spend cap — only one account-wide monthly spend limit plus email alerts, under Organization settings → Billing. Verify current billing/limit mechanics directly before relying on this, since platform details like this change.

**Prompt caching mechanic, not just the concept:** actually enabling it requires a `cache_control` marker on the specific content block you want cached (typically the end of a fixed system prompt) in the raw API request. Whether a given no-code/low-code platform's built-in AI/agent node exposes that field directly varies — it may require a raw HTTP request node with hand-built JSON instead of the standard node. Verify against the actual node/integration before assuming caching "just works" through it.

## Companion tooling

- **`ai-workflow-cost-levers` skill** — encodes this same reasoning as a repeatable procedure: name the hard constraints (timeliness, quality) first, walk the levers against them, then check for needless recompute, ending in a situation-grounded verdict rather than a generic recitation.
- **`cost-lever-eval` skill + harness** — the measurement companion for the two levers with real quality risk (cheaper model, executor+advisor): runs an actual objective/test-suite task under each model configuration and reports a pass-rate-and-cost table, so "does the cheaper option hold up" is answered with data instead of assumed.
