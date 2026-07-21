---
name: agent-architecture-advisor
description: 'Decide whether an automation, agent, or integration is actually worth building, and if so, which shape it should take (single-agent loop, subagent delegation, scheduled/triggered task, MCP server/tool, or a Skill). Use this whenever the user is deciding whether to build a tool, script, bot, workflow, integration, or "agent" for a task -- especially before reaching for n8n, Make, Zapier, a custom MCP server, or any automation platform. Also trigger when the user asks things like "should I build an agent for this," "what type of automation do I need," "is this overkill," "do I need a tool for this or can I just ask you," or describes a recurring manual task and wonders how to automate it. Push back proactively -- the most common failure this skill guards against is building infrastructure for a task that a plain conversation with Claude already solves, or reaching for a heavier pattern (n8n, a custom server) than the task actually needs.'
---

# Agent Architecture Advisor

Two questions, asked in order. Skipping the first and jumping straight to "which architecture" is the most common mistake this skill exists to prevent.

## Question 1: Does this need to be built at all?

An LLM in conversation already does a lot without any infrastructure: read something, reason about it, summarize it, draft something, answer a question that depends on judgment rather than a fixed rule. Building a tool, script, or agent around a task only pays for itself when conversation alone doesn't satisfy a real constraint. Name the constraint before building anything:

- **Unattended execution.** The task has to happen without a human remembering to ask -- on a schedule, or triggered by an event (a new file, a webhook, a form submission). This is the single strongest reason to build something. If nobody needs it to run without being asked, this constraint doesn't apply.
- **Reuse across many future invocations.** Not "I did this once and it was useful," but "this exact capability will be needed repeatedly, by me or by others, in a form more durable than a saved conversation."
- **Deterministic reliability.** The task involves a step that must produce the exact same output from the exact same input every time (a calculation, a data transform, a lookup), where letting a language model redo the reasoning each time introduces variance that matters.
- **Scale or volume.** The task needs to happen to hundreds of items, not because a human describing it once and getting one answer wouldn't work, but because doing that manually N times is the actual bottleneck.

If none of these apply, the honest answer is: don't build anything. Just do the task, or ask Claude to do it, when it's needed.

**The trap to watch for:** native capabilities get reinvented as custom infrastructure surprisingly often, because building feels more productive than checking first. Before designing anything, check whether the platform already does this natively -- a scheduled task instead of a cron job you host yourself, a Skill instead of a bespoke script, a existing per-channel memory feature instead of a database you'd build and maintain. A real example: a multi-week plan to build three private AI workspaces, a governance-tracking layer, and a custom escalation system for a Slack-based organization turned out to be mostly reinventing features the chat platform's own AI integration already shipped -- persistent memory per channel, retrieval over connected documents. What survived the check was a channel reorganization and a small dashboard. That's the shape a good triage produces: most of the imagined build disappears, and what's left is small and concrete.

**The other trap:** building the infrastructure before confirming the need is real. It's possible to correctly conclude "this would benefit from automation" for a task nobody has actually confirmed is a real, current pain point -- and then build a working scaffold for a guess. If the task itself is speculative ("this seems like it'd be annoying to do by hand" rather than "I do this every week and it costs me an hour"), say so plainly, and suggest confirming the need before investing in question 2.

## Question 2: If yes, which shape?

Once a real constraint justifies building something, the choice between architectures is a tradeoff, not a hierarchy. More moving parts is not more sophisticated -- it's more to maintain. Pick the lightest pattern that satisfies the constraint identified above.

**Single-agent tool-use loop (the default).** One continuous context, one agent, a list of tools it can call, iterating until done. This is what's happening any time you're talking to an agent directly and it's calling tools on your behalf. Reach for this when the task benefits from a human steering mid-task -- correcting direction, answering a clarifying question, stopping early. The cost of every other pattern below is some loss of this steerability, so it's the right default whenever nothing else is pushing you away from it.

**Subagent delegation.** A coordinating agent hands a scoped, self-contained piece of work to a fresh agent instance with its own context, and gets back a summary without seeing the intermediate steps. Reach for this when: the sub-task is genuinely self-contained (a summary of the outcome is enough, the steps in between don't need review), several independent pieces of work can run in parallel, or the main context would get cluttered by the sub-task's own back-and-forth. Don't reach for this by default -- it trades away the ability to interrupt and redirect partway through, which matters more often than it first appears, especially for exploratory or ambiguous work where the human is likely to want to change direction once they see intermediate results.

**Scheduled or triggered task.** The thing that actually makes something "automation" rather than "an agent you talk to" is that a human isn't the one initiating each run. Two flavors: time-based (runs every morning, every Monday) or event-based (runs when a webhook fires, a file lands, a message arrives). Reach for this only once "unattended execution" from Question 1 is the confirmed constraint -- if a human would be prompting it anyway, this adds a trigger mechanism for no reason.

Within this category, prefer the lightest tool that satisfies the trigger:
- A built-in scheduled task (if the platform has one) needs no separate hosting, credentials, or maintenance -- use it whenever the logic is "run this same request periodically."
- A dedicated automation platform (n8n, Make, Zapier, etc.) earns its complexity when the workflow chains multiple external services with real branching logic between steps, needs to survive independently of any particular chat session, or needs to be handed to someone who isn't going to operate it through a conversational agent at all. Building one of these means real ongoing maintenance: credentials, error handling, versioning. Don't reach for it just because it's the more "engineered"-feeling option.

**MCP server or tool.** This is the right call when what's actually being built is a new *capability* -- a way for any agent to call some external system -- meant to be reused across many different future tasks and sessions, not to encode one specific workflow. If the thing you're building only makes sense wired up end-to-end for one particular process, it's a workflow (the automation-platform case above), not a tool.

**A Skill.** Use this when what needs to be captured is judgment, a procedure, or domain knowledge that should get pulled into context automatically when relevant -- not a callable capability, but a way of reasoning about a class of problems so it doesn't need to be re-explained or re-derived each time. This document is an instance of its own category: it exists because "how do I decide what to build" turned out to be a recurring, reasoning-heavy question worth writing down once rather than re-deriving in every conversation.

## Output

Produce a short written recommendation, not just a conversational answer -- it should hold up if shown to someone else (a client, a teammate) without the surrounding chat. Structure:

```
# Build Recommendation: [task name]

## The task
[1-2 sentences: what's actually needed]

## Verdict
[Build / Don't build -- and if the need itself is unconfirmed, say so here explicitly]

## If building: recommended shape
[Which pattern(s) from Question 2, and why -- name the specific constraint from Question 1 driving the choice]

## Tradeoffs
[What's given up by this choice -- steerability, maintenance burden, latency, etc.]

## What would change this
[The condition under which you'd revisit -- e.g. "if this becomes daily rather than occasional, reconsider a scheduled task"]
```

Keep it short. The point is a clear, defensible call, not a survey of every opti