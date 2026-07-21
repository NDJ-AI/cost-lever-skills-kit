---
name: org-deployment
description: Architecture and deployment mechanics for rolling Claude out across a team or whole organization — plan selection (Pro/Max vs Team vs Enterprise), org-level connectors, plugin marketplaces, Cowork admin controls, remote MCP servers as the shared integration layer, and the split between chat-surface work and headless Claude API automations. Use this whenever a user is scoping, proposing, pricing, or building any multi-user or company-wide Claude setup — "how do we deploy Claude to the whole company," "Claude Enterprise," "should the client be on Team or Enterprise," seats, admin controls, org rollout, shared connectors, "give everyone the same skills/tools," internal AI system built on Claude, or an engagement moving from architecture to deployment planning. Trigger even when the user mentions only one piece (a plan question, a connector question, a "how do I distribute this to the team" question) — the value of this skill is knowing how the pieces fit, so partial questions still need the whole model.
---

# Claude Org Deployment

How to take Claude from one person's tool to an organization's operating layer. The core insight this skill exists to transmit: **"Claude Enterprise" is not a product you install — it is three layers that get architected separately**, and most deployment mistakes come from putting work in the wrong layer.

Facts marked ⏱ were verified against support.claude.com on 2026-07-19. Plans and pricing change; when a recommendation hinges on a ⏱ fact, re-verify it at the URLs in the Refresh section before committing it to a client.

## The three-layer model

Always establish this model first — with the user, and in any client-facing artifact:

1. **The surface layer (org chat plan)** — claude.ai / Desktop / Cowork / Claude Code seats for humans. This is where people *talk to* the system: ad-hoc questions, document work, chat over connected tools. Managed through a Team or Enterprise plan with central admin.
2. **The shared integration layer (MCP servers)** — one remote MCP server per system of record (accounting platform, CRM, marketing stack), hosted centrally, connected org-wide by an admin. Every surface — chat, Cowork, Claude Code, and the headless layer below — talks to the same tools with the same scopes. This is what makes the result "a system, not a one-off script": integrations are built once, not per-person.
3. **The headless layer (Claude API)** — scheduled and event-driven automations built on the Claude API (Agent SDK, or an orchestrator like n8n), running on server infrastructure. **No desktop involved, no chat plan involved, separately billed.** Anything that must run reliably on a schedule, touch systems of record, or carry audit obligations lives here.

The most common misconception to correct early: Cowork and Desktop are per-machine, so people conclude Claude "can't scale." Right observation, wrong conclusion — you never scale the machine. You scale the *configuration* (layer 1, via admin-distributed connectors and plugins) and you move the always-on work off desktops entirely (layer 3).

## What lives where — the sorting test

When the user describes what the org wants, sort each ask:

| The ask sounds like | Layer | Why |
|---|---|---|
| "Ask questions about our docs/data," "help writing," ad-hoc analysis | 1 — surface | Human-initiated, human-consumed, no schedule |
| "Everyone should have access to the same tools/data" | 2 — MCP + org connectors | Build once, admin-connect, all surfaces inherit |
| "Automated reports," "reconciliations," "runs every morning," "when X happens, do Y" | 3 — headless | Needs reliability, scheduling, audit trails; must not depend on someone's laptop being open |
| "Dashboards leadership can act on" | 3 produces, 1 consumes | Generation is scheduled (headless); consumption is human |
| Anything finance-critical or compliance-sensitive | 3, almost always | You control logging, validation, and review gates in code; desktop sessions store data locally and aren't centrally auditable ⏱ |

## Layer 1: plan selection

Decision tree, in order:

1. **One or two power users, no shared admin needs** → individual Pro/Max seats. Don't sell an org plan to a solo operator.
2. **2–150 people, shared connectors/admin wanted** → **Team plan**. ⏱ As of 2026-07 Team includes what historically justified Enterprise: SSO, domain capture, JIT provisioning, role-based permissioning, spend controls (org and per-user), enterprise search, org-level connectors (Drive, Gmail, Calendar, GitHub, M365, Slack), plus Cowork and Claude Code on every seat. Standard seats ~$25–30/user/mo (annual vs monthly), Premium ~$100–125 with ~5x the usage — mix seat types, giving Premium only to power users. Per-member usage limits with optional prepaid usage credits.
3. **Upgrade to Enterprise when a specific trigger fires**, not by default. ⏱ Real triggers: >150 seats; per-group control (custom roles, per-group Cowork/plugin enablement, group spend limits); audit obligations (audit logs, SCIM, custom data retention, Compliance API, Analytics API); HIPAA-ready configuration with a BAA; customer-managed encryption keys; US-only inference. Also know the billing model difference: Enterprise seats cover *access only* and all usage bills at API rates (no per-seat caps — cost follows consumption), and self-serve Enterprise has a 20-seat minimum (sales-assisted: 50). A 12-person company cannot buy self-serve Enterprise at all — if they genuinely need an Enterprise-only feature (e.g. a BAA), that's a sales conversation.

State the upgrade triggers explicitly in proposals. "Start on Team; here are the three events that would move you to Enterprise" reads as judgment and costs nothing.

## Layer 1: what admins actually control

The mechanics that make one config serve every machine ⏱:

- **Org connectors** — an Owner connects workplace tools once with admin credentials under Organization settings > Connectors; members use them without individual setup.
- **Plugin marketplaces** — Owners curate plugins (bundles of skills, connectors, commands) per org with four states: *required* (auto-installed, can't uninstall), *installed by default* (auto-installed, removable), *available* (self-serve catalog), *not available* (hidden). This is the distribution mechanism for skills and working agreements — the answer to "how do I push the same setup to everyone." Enterprise can vary these per group.
- **Cowork controls** — org-wide on/off toggle; Enterprise can scope by group. Write-capable connector tools require per-task human approval unless the org enables "always allow" (off by default — leave it off for finance data).
- **Network egress** — org code-execution network settings apply to Cowork sessions (but not to web search/fetch or Claude in Chrome — separate toggles).
- **Monitoring** — Team and Enterprise can stream Cowork events (tool calls, file access, approval decisions) to a SIEM via OpenTelemetry. Two honest caveats to surface in any compliance conversation: Cowork conversation data is stored locally per-machine and can't be centrally exported, and Cowork activity is not in the Compliance API. This is exactly why compliance-sensitive automation belongs in layer 3.

## Layer 2: the integration layer

- One remote MCP server per system of record; host centrally (cloud, not someone's machine); admin-connect it org-wide as a custom connector.
- Scope credentials at the server, narrowly: the accounting MCP gets read scopes plus exactly the write operations the workflows need, nothing more. The server is where access control lives — every surface above it inherits the boundary.
- Prefer official/vendor MCP servers where they exist; build custom ones only for systems without.
- Layer 3 workflows can use the same MCP servers or call vendor APIs directly — but when both humans and automations need the same system, the shared MCP server keeps one integration, one scope set, one audit point.

## Layer 3: the headless layer

- Runs on the **Claude API** (direct, via the Agent SDK, or through an orchestrator like n8n) on server infrastructure with its own billing — completely independent of the chat plan.
- Apply the hybrid pattern: deterministic steps collect data and deliver results; the model does only the bounded work (extraction, judgment-with-review, drafting, routing); validate model output against a schema before anything writes to a system of record.
- Human review gates live where the team already works (e.g. Slack approval before a write lands). The gate is architecture, not a temporary training wheel.
- Log every run: inputs, model output, validation result, reviewer decision. This — not the chat plan's admin panel — is the audit trail for automated work.

## Deployment sequence

Phase the rollout; never big-bang it:

- **Phase 0 — Discovery.** Map the processes, systems, compliance surfaces, and the humans (who operates this later, at what technical ceiling). No architecture before this.
- **Phase 1 — Foundation (days).** Stand up the org plan per the decision tree; admin-connect org connectors; set Cowork/write-approval/network policies; distribute the starter plugin/skill set via a marketplace; write per-team working agreements (a CLAUDE.md-style standing instruction file per project/team).
- **Phase 2 — First headless build.** One workflow, chosen for small blast radius + visible payoff, in the hybrid pattern with a review gate. Verify behaviorally against real data (show what it flagged and how the gate caught the miss — that builds more trust than a clean demo).
- **Phase 3 — Integration promotion.** Promote the first build's integration into a proper shared MCP server; connect it org-wide so humans can query what the automation touches. Extend to the next workflow lane.
- **Phase 4 — Handoff.** Runbooks, train-the-operator sessions, documented escalation paths, and the working agreements as living documents. Success criterion: the org runs and extends it without you in the room.

## Common traps

- **Scaling the desktop.** Trying to make one Cowork/Desktop instance serve a team, or putting scheduled work in a desktop session that dies when the laptop sleeps. Desktops are for humans; schedules belong in layer 3.
- **Plan-first thinking.** Choosing Team vs Enterprise before discovery. The plan is a consequence of the requirements (seats, groups, audit, BAA), not the starting decision.
- **Finance-critical flows in chat surfaces.** Local storage, no Compliance API coverage, no run logs. Anything an auditor might walk goes headless.
- **Per-person integrations.** Ten people each wiring their own connector to the CRM = ten scope sets and no audit point. Admin-connect once, or stand up the MCP server.
- **Forgetting the API layer is separate billing.** Client budgets the seats, then the automation costs surprise them. Quote both from the start.
- **Enterprise by reflex.** It costs more, bills usage at API rates, and has seat minimums. Recommend it only when a named trigger fires.

## Refresh

Verify current facts before client commitments: Team plan (support.claude.com/en/articles/9266767), Enterprise plan (9797531), Cowork on Team/Enterprise (13455879), pricing (claude.com/pricing). If a fact here contradicts the live docs, the live docs win — and this skill should be updated.
