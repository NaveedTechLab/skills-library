---
name: internal-comms
description: A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).
license: Complete terms in LICENSE.txt
---

## When to use this skill
To write internal communications, use this skill for:
- 3P updates (Progress, Plans, Problems)
- Company newsletters
- FAQ responses
- Status reports
- Leadership updates
- Project updates
- Incident reports

## How to use this skill

To write any internal communication:

1. **Identify the communication type** from the request
2. **Load the appropriate guideline file** from the `examples/` directory:
    - `examples/3p-updates.md` - For Progress/Plans/Problems team updates
    - `examples/company-newsletter.md` - For company-wide newsletters
    - `examples/faq-answers.md` - For answering frequently asked questions
    - `examples/general-comms.md` - For anything else that doesn't explicitly match one of the above
3. **Follow the specific instructions** in that file for formatting, tone, and content gathering

If the communication type doesn't match any existing guideline, ask for clarification or more context about the desired format.

## Keywords
3P updates, company newsletter, company comms, weekly update, faqs, common questions, updates, internal comms

## When NOT to Use This Skill

- **External customer communications** — internal comms templates are not appropriate for customer-facing messaging; use `email-mcp-server` or `slack-mcp-server` for outbound customer comms
- **Legal notices or compliance communications** — internal comms skills don't account for legal language requirements; involve legal review for regulatory communications
- **Crisis communications** — high-stakes communications during incidents require human judgment, not templated AI generation

## Common Mistakes

- Using the same tone for all internal audiences — communications to the engineering team vs. executive leadership require different levels of technical detail and formality
- Not including a clear call to action — internal comms that inform but don't specify next steps get ignored
- Sending communications without proofreading for organizational context — AI-generated internal comms can miss organizational jargon, team names, or product terminology

## Related Skills

- [`slack-mcp-server`](../slack-mcp-server/SKILL.md) — Deliver internal comms via Slack channels
- [`email-mcp-server`](../email-mcp-server/SKILL.md) — Deliver internal comms via email
- [`summary-generator`](../summary-generator/SKILL.md) — Generate meeting summaries and update digests for internal distribution
