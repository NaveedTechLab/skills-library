---
name: odoo-mcp-server
description: Integrate with Odoo ERP systems via MCP to perform accounting, invoicing, and financial operations with HITL approval controls. Use when connecting Claude Code to Odoo for business process automation.
---

# Odoo MCP Server

## Description
The Odoo MCP Server provides Model Context Protocol integration with Odoo ERP systems (version 19+), enabling Claude Code to interact with accounting, invoicing, and financial operations through a secure, HITL (Human-in-the-Loop) controlled interface.

## Purpose
This skill enables Claude Code to perform accounting operations in Odoo while maintaining strict approval workflows for financial transactions. It provides read access to account data and requires human approval for any operations that create or modify financial records.

## Key Features

### Accounting Operations
- Search and read Odoo records (any model)
- Create draft invoices with HITL approval
- Post/validate invoices with mandatory approval
- Register payments with mandatory approval
- Query account balances and reports

### Human-in-the-Loop Controls
| Operation | HITL Required | Threshold |
|-----------|---------------|-----------|
| Search records | No | - |
| Get account balance | No | - |
| Create invoice | Yes (>$1000) | Amount threshold |
| Post invoice | Yes (always) | - |
| Create payment | Yes (always) | - |

### Security
- JSON-RPC over HTTPS
- API key authentication
- Rate limiting
- Full audit logging
- Sensitive data masking

## Configuration

### Environment Variables
```bash
ODOO_URL=https://your-odoo-instance.com
ODOO_DATABASE=your_database
ODOO_USERNAME=api_user
ODOO_API_KEY=your_api_key
ODOO_APPROVAL_THRESHOLD=1000.00
```

### Default Configuration
```json
{
  "odoo": {
    "url": "https://localhost:8069",
    "database": "odoo_db",
    "username": "",
    "api_key": "",
    "timeout_seconds": 30,
    "verify_ssl": true
  },
  "approval": {
    "invoice_threshold": 1000.00,
    "always_require_approval": ["post_invoice", "create_payment"],
    "approval_timeout_hours": 24
  },
  "rate_limiting": {
    "requests_per_minute": 60,
    "burst_limit": 10
  }
}
```

## MCP Tools

### odoo_search_records
Search any Odoo model with domain filters.

**Parameters:**
- `model` (string): Odoo model name (e.g., "account.move", "res.partner")
- `domain` (array): Search domain filter
- `fields` (array): Fields to return
- `limit` (int): Maximum records to return
- `offset` (int): Records to skip

**Example:**
```python
await odoo_search_records(
    model="account.move",
    domain=[("move_type", "=", "out_invoice"), ("state", "=", "posted")],
    fields=["name", "partner_id", "amount_total", "invoice_date"],
    limit=10
)
```

### odoo_create_invoice
Create a draft invoice in Odoo.

**Parameters:**
- `partner_id` (int): Customer/vendor ID
- `move_type` (string): Invoice type ("out_invoice", "in_invoice", etc.)
- `invoice_lines` (array): Line items
- `invoice_date` (string): Invoice date (YYYY-MM-DD)

**HITL:** Required if total amount > $1000

### odoo_post_invoice
Validate and post a draft invoice.

**Parameters:**
- `invoice_id` (int): ID of the draft invoice to post

**HITL:** Always required

### odoo_create_payment
Register a payment for an invoice.

**Parameters:**
- `invoice_id` (int): Invoice to pay
- `amount` (float): Payment amount
- `payment_date` (string): Payment date
- `journal_id` (int): Payment journal ID

**HITL:** Always required

### odoo_get_account_balance
Get balance for an account.

**Parameters:**
- `account_id` (int): Account ID
- `date_from` (string): Start date
- `date_to` (string): End date

**HITL:** Not required

## Usage Scenarios

### Query Customer Invoices
```python
# Get all posted invoices for a customer
invoices = await odoo_search_records(
    model="account.move",
    domain=[
        ("partner_id", "=", 42),
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted")
    ],
    fields=["name", "amount_total", "amount_residual", "invoice_date"]
)
```

### Create and Approve Invoice
```python
# Create draft invoice
invoice_id = await odoo_create_invoice(
    partner_id=42,
    move_type="out_invoice",
    invoice_lines=[
        {"product_id": 1, "quantity": 5, "price_unit": 100.00}
    ]
)
# Note: If amount > $1000, will require human approval

# Post invoice (always requires approval)
await odoo_post_invoice(invoice_id=invoice_id)
```

## Integration Points

### With Audit Logger
All operations are logged with:
- Timestamp
- Operation type
- Target records
- Approval status
- User/approver information

### With Safety Enforcer
Financial operations respect safety boundaries:
- FINANCIAL_EXECUTION boundary for payments
- DATA_ACCESS boundary for queries

### With Vault System
Approval requests are stored in:
- `/vault/Pending_Approval/odoo/` for pending
- `/vault/Approved/odoo/` after approval
- `/vault/Rejected/odoo/` if rejected

## Docker Setup (Odoo 19 Community)

```yaml
# docker-compose.yml
version: '3'
services:
  odoo:
    image: odoo:19
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    volumes:
      - odoo-data:/var/lib/odoo
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
      - POSTGRES_DB=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  odoo-data:
  postgres-data:
```

## Dependencies
- `httpx` for async HTTP requests
- `fastmcp` for MCP server
- `pydantic` for data validation
- Integration with phase-3 audit_logger
- Integration with phase-3 safety_enforcer

## When NOT to Use This Skill

- **Non-Odoo ERP systems** (SAP, NetSuite, QuickBooks) — this skill is Odoo-specific; other ERP systems require separate integrations
- **Fully automated financial posting without human review** — all financial write operations require HITL approval; this skill is not suitable for zero-touch automation
- **Read-heavy analytics workloads** — if you only need reporting data, direct database read access via `database-postgresql-design` may be more efficient than the MCP overhead

## Common Mistakes

- Hardcoding the Odoo server URL — use environment variables for the host and port; hardcoded URLs break when migrating between staging and production instances
- Not validating account codes before creating journal entries — Odoo will reject entries referencing non-existent accounts; always look up valid accounts before posting
- Not handling Odoo JSON-RPC session expiry — Odoo sessions expire after inactivity; implement automatic re-authentication when session errors occur

## Related Skills

- [`crm-database-management`](../crm-database-management/SKILL.md) — Manage the CRM database that Odoo integrates with
- [`audit-logging-system`](../audit-logging-system/SKILL.md) — Log all financial operations for compliance
- [`mcp-builder`](../mcp-builder/SKILL.md) — Build the MCP infrastructure this Odoo server runs on
