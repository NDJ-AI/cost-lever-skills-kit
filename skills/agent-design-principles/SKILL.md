---
name: agent-design-principles
description: 'Judgment for designing the internal structure of a multi-agent system or agentic workflow well, once the decision to build has already been made. Not whether to build (see agent-architecture-advisor) and not company-wide rollout (see ai-integration-architect) -- this is about whether an already-decided agent/workflow design will actually hold up: failure modes, incentive alignment, autonomy calibration, escalation paths, interface contracts between agents, and granularity of scope. Trigger when designing or reviewing a multi-agent system, an agentic workflow, a chain of AI Agent nodes in n8n, a subagent delegation structure, or any setup where multiple agents or workflow steps hand off to each other. Also trigger on "how should I structure these agents," "what could go wrong with this agent design," "is this agent doing too much/too little," or "review this workflow design."'
---

# Agent Design Principles

Six questions about the internal structure of a multi-agent system or agentic workflow, asked once the decision to build one is already made. Each names a place a design silently breaks even when every individual agent or node works correctly in isolation -- the same way good user research finds the gap between how a system is supposed to behave and how it actually will, once something goes slightly wrong.

## 1. Failure mode enumeration, before the build
Ask what happens when an agent is wrong, a tool call fails, or upstream data arrives malformed -- before wiring anything, not after the first production failure. If the honest answer is "we'll find out," that's a gap to close now, not later.

## 2. Incentive alignment
An agent optimizes for whatever objective it's actually given, not the one implied or intended. A misspecified objective produces confident, wrong output with no internal signal anything is off. Name the actual objective explicitly rather than assuming it's obvious from context -- especially for any step where the metric is easy to satisfy without doing the real job (an agent told to "resolve the ticket" can close it without solving it).

## 3. Autonomy calibration
Every step sits somewhere on a spectrum: fully autonomous, checkpoint-and-confirm, or read-only-and-report. The right point isn't fixed -- it should track how reversible the action is and how well-understood its failure modes are. Too much autonomy for an irreversible action risks a costly silent mistake; too little for a low-stakes, well-understood one adds friction nobody wanted. Re-check this calibration whenever a step's blast radius changes (e.g. moving from a sandbox to production credentials).

## 4. Escalation paths
When an agent gets stuck, uncertain, or blocked, exactly one of three things should happen: it guesses, it asks a human, or it halts. If a design doesn't specify which, for which situations, that's an undefined escalation path -- a warning that exists but has nothing listening for it.

## 5. Interface discipline between agents
The handoff between two agents, or two workflow steps, is a contract whether or not anyone wrote it down. What gets passed explicitly versus assumed-but-unstated determines whether the handoff holds up under a case nobody tested. Prefer explicit, minimal, self-contained handoffs over ones that quietly depend on shared context the receiving agent never actually gets.

## 6. Granularity
How much should one agent be responsible for? Too broad, and it holds too much context to reason about any of it well. Too narrow, and coordination overhead between agents eats whatever specialization was gained. There's no universal right answer -- only a judgment about where the natural seams in the problem actually sit, and that judgment should be revisited if the task's shape changes.

## How to apply this

When reviewing or designing a multi-agent system or agentic workflow, run it against these six in order and flag which ones are actually answered versus assumed. A design doesn't need a perfect answer to all six before shipping -- but every one of them should have a *deliberate* answer, even if that answer is "we're accepting the risk here because X." The failure mode this Skill guards against is a design that looks complete because every node works, while one of these six was never actually decided.
