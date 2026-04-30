#!/usr/bin/env python3
"""
Odoo MCP Server

FastMCP server providing Odoo ERP integration tools with HITL controls.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    from fastmcp import FastMCP
except ImportError:
    print("fastmcp not installed. Install with: pip install fastmcp")
    sys.exit(1)

from .approval_workflow import OdooApprovalWorkflow
from .models import (
    ApprovalStatus,
    Invoice,
    InvoiceLine,
    MoveType,
    OdooConfig,
    Payment,
)
from .odoo_api_client import OdooAPIClient, OdooAPIError

logger = structlog.get_logger()

# Initialize FastMCP server
mcp = FastMCP("Odoo MCP Server")

# Global instances
_config: Optional[OdooConfig] = None
_client: Optional[OdooAPIClient] = None
_workflow: Optional[OdooApprovalWorkflow] = None


def get_config() -> OdooConfig:
    """Get or create config"""
    global _config
    if _config is None:
        _config = OdooConfig()
    return _config


def get_workflow() -> OdooApprovalWorkflow:
    """Get or create approval workflow"""
    global _workflow
    if _workflow is None:
        _workflow = OdooApprovalWorkflow(get_config())
    return _workflow


async def get_client() -> OdooAPIClient:
    """Get or create Odoo client"""
    global _client
    if _client is None:
        _client = OdooAPIClient(get_config())
        await _client.connect()
    return _client


# ========== MCP Tools ==========

@mcp.tool()
async def odoo_search_records(
    model: str,
    domain: List[Any] = None,
    fields: List[str] = None,
    limit: int = 100,
    offset: int = 0,
    order: str = None
) -> Dict[str, Any]:
    """
    Search any Odoo model with domain filters.

    Args:
        model: Odoo model name (e.g., "account.move", "res.partner")
        domain: Search domain filter (e.g., [("state", "=", "posted")])
        fields: Fields to return (e.g., ["name", "amount_total"])
        limit: Maximum records to return (default: 100)
        offset: Records to skip (default: 0)
        order: Sort order (e.g., "create_date desc")

    Returns:
        Search results with records, count, and pagination info

    Example:
        odoo_search_records(
            model="account.move",
            domain=[("move_type", "=", "out_invoice"), ("state", "=", "posted")],
            fields=["name", "partner_id", "amount_total"],
            limit=10
        )
    """
    try:
        client = await get_client()
        result = await client.search_read(
            model=model,
            domain=domain or [],
            fields=fields or [],
            offset=offset,
            limit=limit,
            order=order
        )

        return {
            "success": True,
            "model": result.model,
            "count": result.count,
            "records": result.records,
            "pagination": {
                "offset": result.offset,
                "limit": result.limit,
                "has_more": result.count > result.offset + len(result.records)
            }
        }
    except OdooAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def odoo_create_invoice(
    partner_id: int,
    move_type: str = "out_invoice",
    invoice_lines: List[Dict[str, Any]] = None,
    invoice_date: str = None,
    invoice_date_due: str = None,
    ref: str = None,
    narration: str = None
) -> Dict[str, Any]:
    """
    Create a draft invoice in Odoo.

    HITL: Requires approval if total amount > $1000

    Args:
        partner_id: Customer/vendor ID
        move_type: Invoice type ("out_invoice", "in_invoice", "out_refund", "in_refund")
        invoice_lines: Line items with product_id, name, quantity, price_unit
        invoice_date: Invoice date (YYYY-MM-DD)
        invoice_date_due: Due date (YYYY-MM-DD)
        ref: Reference number
        narration: Terms and conditions

    Returns:
        Created invoice ID or approval request if HITL required

    Example:
        odoo_create_invoice(
            partner_id=42,
            move_type="out_invoice",
            invoice_lines=[
                {"name": "Consulting Services", "quantity": 10, "price_unit": 150.00}
            ],
            invoice_date="2024-01-15"
        )
    """
    try:
        # Build invoice lines
        lines = []
        total_amount = 0
        for line_data in (invoice_lines or []):
            line = InvoiceLine(
                product_id=line_data.get("product_id"),
                name=line_data.get("name", ""),
                quantity=line_data.get("quantity", 1),
                price_unit=line_data.get("price_unit", 0),
                discount=line_data.get("discount", 0),
                tax_ids=line_data.get("tax_ids", []),
                account_id=line_data.get("account_id")
            )
            lines.append(line)
            total_amount += line.quantity * line.price_unit * (1 - line.discount / 100)

        # Check if approval is required
        workflow = get_workflow()
        if workflow.requires_approval("create_invoice", total_amount):
            # Create approval request
            request = workflow.create_approval_request(
                operation="create_invoice",
                model="account.move",
                data={
                    "partner_id": partner_id,
                    "move_type": move_type,
                    "invoice_lines": invoice_lines,
                    "invoice_date": invoice_date,
                    "invoice_date_due": invoice_date_due,
                    "ref": ref,
                    "narration": narration
                },
                amount=total_amount,
                context={"reason": f"Invoice amount ${total_amount:,.2f} exceeds threshold"}
            )

            return {
                "success": True,
                "requires_approval": True,
                "approval_request_id": request.id,
                "amount": total_amount,
                "message": f"Invoice creation requires approval (amount: ${total_amount:,.2f}). "
                          f"Request ID: {request.id}"
            }

        # Create invoice directly
        invoice = Invoice(
            partner_id=partner_id,
            move_type=MoveType(move_type),
            invoice_line_ids=lines,
            invoice_date=invoice_date,
            invoice_date_due=invoice_date_due,
            ref=ref,
            narration=narration
        )

        client = await get_client()
        invoice_id = await client.create_invoice(invoice)

        return {
            "success": True,
            "requires_approval": False,
            "invoice_id": invoice_id,
            "amount": total_amount,
            "message": f"Invoice created successfully with ID: {invoice_id}"
        }

    except OdooAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def odoo_post_invoice(invoice_id: int) -> Dict[str, Any]:
    """
    Validate and post a draft invoice.

    HITL: Always requires approval

    Args:
        invoice_id: ID of the draft invoice to post

    Returns:
        Success status or approval request

    Example:
        odoo_post_invoice(invoice_id=123)
    """
    try:
        client = await get_client()

        # Get invoice details
        invoice = await client.get_invoice(invoice_id)

        # Always requires approval
        workflow = get_workflow()
        request = workflow.create_approval_request(
            operation="post_invoice",
            model="account.move",
            record_id=invoice_id,
            data={
                "invoice_id": invoice_id,
                "invoice_name": invoice.name,
                "partner_id": invoice.partner_id,
                "amount_total": invoice.amount_total
            },
            amount=invoice.amount_total,
            context={
                "invoice_state": invoice.state.value,
                "invoice_type": invoice.move_type.value
            }
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "invoice_id": invoice_id,
            "invoice_name": invoice.name,
            "amount": invoice.amount_total,
            "message": f"Invoice posting requires approval. Request ID: {request.id}"
        }

    except OdooAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def odoo_create_payment(
    invoice_id: int,
    amount: float,
    payment_date: str,
    journal_id: int,
    ref: str = None
) -> Dict[str, Any]:
    """
    Register a payment for an invoice.

    HITL: Always requires approval

    Args:
        invoice_id: Invoice to pay
        amount: Payment amount
        payment_date: Payment date (YYYY-MM-DD)
        journal_id: Payment journal ID (bank/cash journal)
        ref: Optional payment reference/memo

    Returns:
        Success status or approval request

    Example:
        odoo_create_payment(
            invoice_id=123,
            amount=1500.00,
            payment_date="2024-01-20",
            journal_id=7
        )
    """
    try:
        client = await get_client()

        # Get invoice details
        invoice = await client.get_invoice(invoice_id)

        # Always requires approval
        workflow = get_workflow()
        request = workflow.create_approval_request(
            operation="create_payment",
            model="account.payment",
            data={
                "invoice_id": invoice_id,
                "amount": amount,
                "payment_date": payment_date,
                "journal_id": journal_id,
                "ref": ref
            },
            amount=amount,
            context={
                "invoice_name": invoice.name,
                "invoice_amount_total": invoice.amount_total,
                "invoice_amount_residual": invoice.amount_residual,
                "partner_id": invoice.partner_id
            }
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "invoice_id": invoice_id,
            "payment_amount": amount,
            "message": f"Payment creation requires approval. Request ID: {request.id}"
        }

    except OdooAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def odoo_get_account_balance(
    account_id: int,
    date_from: str = None,
    date_to: str = None
) -> Dict[str, Any]:
    """
    Get balance for an account.

    No HITL required - read-only operation.

    Args:
        account_id: Account ID
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)

    Returns:
        Account balance with debit, credit, and net balance

    Example:
        odoo_get_account_balance(account_id=15, date_from="2024-01-01", date_to="2024-12-31")
    """
    try:
        client = await get_client()
        balance = await client.get_account_balance(account_id, date_from, date_to)

        return {
            "success": True,
            "account_id": balance.account_id,
            "account_code": balance.account_code,
            "account_name": balance.account_name,
            "debit": balance.debit,
            "credit": balance.credit,
            "balance": balance.balance,
            "date_range": {
                "from": balance.date_from,
                "to": balance.date_to
            }
        }

    except OdooAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def odoo_execute_approved_request(approval_request_id: str) -> Dict[str, Any]:
    """
    Execute an approved operation.

    This should be called after a human has approved the request.

    Args:
        approval_request_id: The approval request ID to execute

    Returns:
        Execution result

    Example:
        odoo_execute_approved_request("odoo_approval_abc123")
    """
    try:
        workflow = get_workflow()
        request = workflow.get_request(approval_request_id)

        if not request:
            return {"success": False, "error": "Approval request not found"}

        if request.status != ApprovalStatus.APPROVED:
            return {
                "success": False,
                "error": f"Request is not approved. Current status: {request.status.value}"
            }

        client = await get_client()

        # Execute based on operation type
        if request.operation == "create_invoice":
            data = request.data
            lines = []
            for line_data in data.get("invoice_lines", []):
                line = InvoiceLine(
                    product_id=line_data.get("product_id"),
                    name=line_data.get("name", ""),
                    quantity=line_data.get("quantity", 1),
                    price_unit=line_data.get("price_unit", 0),
                    discount=line_data.get("discount", 0),
                    tax_ids=line_data.get("tax_ids", [])
                )
                lines.append(line)

            invoice = Invoice(
                partner_id=data["partner_id"],
                move_type=MoveType(data.get("move_type", "out_invoice")),
                invoice_line_ids=lines,
                invoice_date=data.get("invoice_date"),
                invoice_date_due=data.get("invoice_date_due"),
                ref=data.get("ref"),
                narration=data.get("narration")
            )

            invoice_id = await client.create_invoice(invoice)
            return {
                "success": True,
                "operation": "create_invoice",
                "invoice_id": invoice_id,
                "message": f"Invoice created with ID: {invoice_id}"
            }

        elif request.operation == "post_invoice":
            invoice_id = request.record_id or request.data.get("invoice_id")
            await client.post_invoice(invoice_id)
            return {
                "success": True,
                "operation": "post_invoice",
                "invoice_id": invoice_id,
                "message": f"Invoice {invoice_id} posted successfully"
            }

        elif request.operation == "create_payment":
            data = request.data
            payment_id = await client.register_payment_for_invoice(
                invoice_id=data["invoice_id"],
                amount=data["amount"],
                payment_date=data["payment_date"],
                journal_id=data["journal_id"],
                ref=data.get("ref")
            )
            return {
                "success": True,
                "operation": "create_payment",
                "payment_id": payment_id,
                "message": f"Payment created with ID: {payment_id}"
            }

        else:
            return {"success": False, "error": f"Unknown operation: {request.operation}"}

    except OdooAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def odoo_get_pending_approvals() -> Dict[str, Any]:
    """
    Get all pending approval requests.

    Returns:
        List of pending approval requests

    Example:
        odoo_get_pending_approvals()
    """
    try:
        workflow = get_workflow()
        requests = workflow.get_pending_requests()

        return {
            "success": True,
            "count": len(requests),
            "requests": [r.to_dict() for r in requests]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def odoo_approve_request(
    approval_request_id: str,
    approved_by: str = "human"
) -> Dict[str, Any]:
    """
    Approve a pending approval request.

    Args:
        approval_request_id: Request to approve
        approved_by: Approver identifier

    Returns:
        Updated approval status

    Example:
        odoo_approve_request("odoo_approval_abc123", approved_by="finance_manager")
    """
    try:
        workflow = get_workflow()
        request = workflow.approve_request(approval_request_id, approved_by)

        if not request:
            return {"success": False, "error": "Request not found or already processed"}

        return {
            "success": True,
            "request_id": request.id,
            "status": request.status.value,
            "approved_by": request.approved_by,
            "approved_at": request.approved_at.isoformat() if request.approved_at else None,
            "message": "Request approved. Use odoo_execute_approved_request to execute."
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def odoo_reject_request(
    approval_request_id: str,
    rejected_by: str = "human",
    reason: str = None
) -> Dict[str, Any]:
    """
    Reject a pending approval request.

    Args:
        approval_request_id: Request to reject
        rejected_by: Rejector identifier
        reason: Rejection reason

    Returns:
        Updated approval status

    Example:
        odoo_reject_request("odoo_approval_abc123", reason="Amount too high, needs revision")
    """
    try:
        workflow = get_workflow()
        request = workflow.reject_request(approval_request_id, rejected_by, reason)

        if not request:
            return {"success": False, "error": "Request not found or already processed"}

        return {
            "success": True,
            "request_id": request.id,
            "status": request.status.value,
            "rejected_by": rejected_by,
            "rejection_reason": reason,
            "message": "Request rejected."
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== Server Lifecycle ==========

@mcp.on_startup()
async def startup():
    """Initialize on server startup"""
    logger.info("Odoo MCP Server starting...")

    # Validate configuration
    config = get_config()
    if not config.url or not config.database:
        logger.warning("Odoo configuration incomplete. Set ODOO_URL, ODOO_DATABASE, etc.")


@mcp.on_shutdown()
async def shutdown():
    """Cleanup on server shutdown"""
    global _client
    if _client:
        await _client.close()
        _client = None
    logger.info("Odoo MCP Server shut down")


def main():
    """Run the MCP server"""
    import uvicorn

    logger.info("Starting Odoo MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
