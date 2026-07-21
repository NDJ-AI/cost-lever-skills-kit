---
name: engagement-pipeline
description: >-
  Runs a full AI-integration client engagement end to end: discovery,
  scoping, architecture, build, and a verified deliverable. The top-level
  orchestrator chaining agent-architecture-advisor, ai-integration-architect,
  agent-design-principles, and mcp-builder with explicit handoffs, and
  filling the two gaps none of them cover alone -- client-facing discovery
  before any commitment, and a proof-it-works verification stage at the
  end. Use whenever starting a new prospect conversation, scoping a
  potential engagement, deciding what to build for a client, or turning
  work into a deliverable to hand someone. Trigger on 'new client wants
  help with AI', 'how do I scope this engagement', 'walk me through
  auditing this business', 'what should I build for them', 'package this
  up'. Also trigger proactively whenever a conversation describes a
  company's tools/team/pain points with the apparent intent of proposing
  or building something for them -- don't wait to be asked by name.
---



# Engagement pipeline

## Why this exists

Three skills already exist for pieces of this work -- `agent-architecture-advisor` (should I build this, and what shape), `ai-integration-architect` (company-wide architecture and rollout), `agent-design-principles` (is the internal structure sound) -- plus `mcp-builder` for actually building integrations. Each is genuinely good at its scope. None of them cover the two things that actually determine whether an engagement goes anywhere: whether you understood the prospect's real problem before you started designing anything, and whether what you built actually works, provably, rather than just looking finished.

This skill is the thread that ties the others together and adds those two missing pieces. Read it end to end before starting a new engagement -- it tells you which of the other skills to consult and when, so you don't have to guess.

The reason this matters commercially, not just technically: the build itself is fast now, and getting faster. Anyone with an AI assistant and a few hours can produce something that looks like a working integration. What's still scarce is knowing what a specific business actually needs (not what they first ask for), and being able to prove the result holds up rather than asserting it does. That's what stages 0 and 4 below are for. Don't skip them because they feel like overhead -- they're the actual differentiator.

## The five stages

Work through these in order. Not every engagement needs every stage in full -- a small, single-task ask can move through stages 0-1 quickly and skip straight to build. A company-wide engagement needs all five. Use judgment, but don't skip stage 0 or stage 4 regardless of size; they're cheap and they're what makes the other three stages trustworthy.

### Stage 0 -- Discovery (before any commitment, on either side)

This is different from `ai-integration-architect`'s own Step 1 intake, which assumes you're already engaged and doing a technical audit. Stage 0 happens earlier and lower-stakes: a conversation with a prospect who hasn't hired you yet, where the goal is just to understand their actual situation well enough to know if there's a real engagement here, and to write something back to them that proves you listened.

Ask, in plain language, no jargon:
- What does the business actually do, and who's the person you're talking to (owner, ops lead, someone else)?
- What tools do they currently use day to day? (Not "what's their tech stack" -- ask like a person: "what do you open every morning to get work done?")
- What's the specific thing that's annoying, slow, or broken right now? Push past the first answer -- the first thing someone names is usually a symptom, not the actual bottleneck. Ask "and why does that happen" once or twice more.
- What have they already tried, if anything? (Tells you what NOT to re-propose.)
- Who else has to say yes for anything to actually change? A great technical fix that one stakeholder can quietly veto later is a wasted build.
- What's their actual appetite for this -- a quick fix, or do they sense a bigger problem? Don't assume; ask.

Output a short discovery brief -- half a page, no jargon, something you could read back to the prospect on a call:
```
## What I heard
[2-3 sentences: their business, in their own language, not yours]

## The actual bottleneck
[1-2 sentences -- the thing behind the thing they first named]

## Who needs to be on board
[names/roles]

## What I'd want to look at next
[1-3 specific, low-commitment next steps -- e.g. "a look at how X currently works" -- not a full proposal yet]
```

If this brief doesn't land when you read it back to them ("that's not quite it" / "that's not really the problem"), that's valuable -- go another round on discovery before scoping anything. A wrong discovery brief guarantees a wrong build five stages later.

### Stage 1 -- Decide scope and shape

Once discovery confirms there's a real problem worth solving, decide which of the two judgment skills applies:

- **Single, narrow task** ("automate this one report," "have something watch this inbox") -> consult `agent-architecture-advisor`. It'll tell you honestly whether this needs building at all, and if so, which shape (single-agent loop, subagent, scheduled task, MCP server, or a Skill).
- **Multiple tools, multiple people, or "how should AI fit into how we work" scope** -> consult `ai-integration-architect`. It runs the full company-level framework: hub-and-spoke architecture, native-feature check, per-role interface assignment, blocker sequencing, phased rollout.

Don't guess which one applies from the prospect's own framing -- prospects often ask for a narrow fix when the real opportunity is company-wide, and vice versa. Stage 0's discovery brief is what tells you which one it actually is.

### Stage 2 -- Architecture and rollout plan

If Stage 1 routed to `ai-integration-architect`, this is where its three output docs get produced: situation summary, architecture, rollout strategy. Its Phase 0 ("proof not proposal" -- a throwaway test on fake data before touching anything real) is not optional color; it's what Stage 4 below formalizes into an actual, repeatable method. Treat that phase as a placeholder that Stage 4 fills in properly, not as a box already checked.

If a multi-agent or multi-step system is part of the plan, run it past `agent-design-principles` before building -- failure modes, incentive alignment, autonomy calibration, escalation paths. Cheaper to catch a bad internal structure on paper than after it's built.

### Stage 3 -- Build

Whatever Stage 1/2 decided needs building, hand off to `mcp-builder` if it's an integration against a real external system (which most useful work ends up being) -- its four-phase process (research/plan, implement, review/test, evaluations) is exactly the discipline that caught the real, live API problems in the Shopify project (variant creation flow, SKU field location, idempotency requirements, concurrency checks). Those weren't hypothetical edge cases -- they were things that only surfaced by actually running the build against the real system, which is the whole reason this stage exists as a distinct step rather than being folded into Stage 2's planning.

For builds that aren't MCP servers (an n8n workflow, a dashboard, a script), the same discipline still applies even without that specific skill: build against real data as early as possible, don't trust that something works because the code looks right.

### Stage 4 -- Verify (this is the stage that's usually skipped, and shouldn't be)

Don't call something finished because it ran once and looked right. Generalize the pattern from the Shopify MCP evaluation:

1. If the build touches a system with existing real data, use that. If it's a fresh system (a new integration, an empty store, a blank workspace), seed a small set of deliberately varied test data yourself first -- variety matters more than volume; five distinct, different records beat fifty near-identical ones for actually testing whether something works.
2. Write a handful of realistic questions or test cases that require the build to actually be used correctly to answer -- not things solvable by guessing or by reading a title.
3. Solve them yourself, using only the tool/system you built, before showing anything to the client. This produces a real answer key, not a hoped-for one.
4. Where something doesn't come back right, that's the build's actual bugs, found before the client finds them.

The output of this stage is a proof artifact -- a report, a scored eval, a short "here's what I tested and here's what came back" note -- not just a claim that it works. This is what makes Stage 5's deliverable credible instead of a polished assertion.

### Stage 5 -- Package as a deliverable

Turn the verified build and its proof into something the client (or a portfolio, if this is speculative work) actually receives. For a formal write-up, this is where a document-creation skill (docx/pdf) comes in -- and for anything client-facing, use the coral/white "thale" brand established in the Shopify MCP case study (Poppins/Lato pairing, coral accent rule, white cover) so every deliverable reads as coming from the same practice rather than a one-off.

A good deliverable states, in this order: what the actual problem was (from Stage 0, in their language, proving you understood it), what was built, and what was proven to work (from Stage 4, with specifics -- not "thoroughly tested," but the actual test cases and results). In that order, not build-first -- the problem statement is what makes a stranger reading this care about the rest of it.

## What "done" looks like

An engagement that went through all five stages produces four things worth keeping: the discovery brief (Stage 0), the architecture/scope doc (Stage 1-2), the working build (Stage 3), and the verification artifact (Stage 4) -- all rolled into the final deliverable (Stage 5). If any engagement is missing the discovery brief or the verification artifact, it's not actually finished yet, regardless of whether the build runs.
