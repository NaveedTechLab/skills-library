---
name: browser-payment-mcp
description: MCP server for browser-based payment portal automation using Playwright. Supports navigating payment sites, filling forms, drafting payments with mandatory HITL approval before execution. Never auto-approves payments. Use when Claude needs to interact with payment portals, banking websites, or any web-based financial operations requiring human oversight.
---

# Browser Payment MCP Server

## Overview

This skill provides a FastMCP server that automates browser-based payment portal
interactions using Playwright. It enforces strict Human-In-The-Loop (HITL) controls
so that no payment is ever executed without explicit human approval.

## Prerequisites

- **Python 3.10+**
- **Playwright** (`pip install playwright`) with Chromium browser installed
  (`playwright install chromium`)
- **FastMCP** (`pip install fastmcp>=0.1.0`)

Install all dependencies:

```bash
pip install -r .claude/skills/browser-payment-mcp/assets/requirements.txt
playwright install chromium
```

## HITL Controls

All payment operations follow a strict approval workflow:

1. **Draft Phase** -- `draft_payment` fills the payment form in the browser but
   does NOT click submit. It creates an approval file under
   `demo_vault/Pending_Approval/`.
2. **Human Review** -- A human must review the approval file, verify the details,
   and move it to `demo_vault/Approved/`.
3. **Execute Phase** -- `execute_payment` checks that a valid, non-expired approval
   file exists in the `Approved` folder before clicking submit.

**Hard rules (cannot be overridden):**

- ALL payments require human approval regardless of amount.
- Payments to new (previously unseen) recipients always require approval.
- Amounts above $100 always require approval (this is every payment by rule above).
- Approval files expire after 24 hours.
- Maximum 3 payments executed per rolling hour.

## Security

- **No credential storage in vault.** Browser sessions use Playwright persistent
  context so credentials are managed by the browser profile, never written to disk
  by this skill.
- **DRY_RUN mode** -- Set `PAYMENT_DRY_RUN=true` to prevent any real browser
  interactions. All tools return simulated responses and still create audit logs
  tagged as dry-run.
- **Allowed domains** -- Configure `PAYMENT_ALLOWED_DOMAINS` to restrict which
  URLs the browser may navigate to.
- **Screenshots** -- Every significant action captures a screenshot stored in the
  audit directory for post-hoc review.

## Supported Operations

| Tool                     | Description                                      | HITL Required |
|--------------------------|--------------------------------------------------|---------------|
| `navigate_to`            | Navigate to a URL                                | No            |
| `fill_form`              | Fill a form field by CSS selector                | No            |
| `click_element`          | Click an element by CSS selector                 | No            |
| `get_page_content`       | Extract text content from selector               | No            |
| `screenshot`             | Take a named screenshot                          | No            |
| `draft_payment`          | Fill payment form, create approval file           | Creates file  |
| `execute_payment`        | Submit an approved payment                       | **YES**       |
| `check_balance`          | Read account balance from portal                 | No            |
| `get_transaction_history`| Read recent transactions from portal             | No            |

## Configuration

Environment variables (or `.env`):

| Variable                     | Default                              | Description                          |
|------------------------------|--------------------------------------|--------------------------------------|
| `PAYMENT_DRY_RUN`           | `false`                              | Simulate all browser actions         |
| `PAYMENT_HEADLESS`          | `true`                               | Run Chromium in headless mode        |
| `PAYMENT_SCREENSHOT_DIR`    | `demo_vault/Logs/payments/screenshots` | Where screenshots are saved        |
| `PAYMENT_MAX_PER_HOUR`      | `3`                                  | Max payments per rolling hour        |
| `PAYMENT_APPROVAL_EXPIRY_H` | `24`                                 | Hours before approval file expires   |
| `PAYMENT_ALLOWED_DOMAINS`   | `*`                                  | Comma-separated allowed domains      |
| `PAYMENT_VAULT_DIR`         | `demo_vault`                         | Root vault directory                 |
| `PAYMENT_AUDIT_RETENTION_DAYS` | `90`                              | Days to retain audit logs            |

## Running the Server

```bash
python .claude/skills/browser-payment-mcp/scripts/browser_payment_mcp.py
```

The server starts on `stdio` transport by default (suitable for MCP client
integration).
