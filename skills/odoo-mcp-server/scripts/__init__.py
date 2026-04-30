"""
Odoo MCP Server - Accounting System Integration

Provides MCP tools for Odoo ERP integration with HITL controls.
"""

from .odoo_api_client import OdooAPIClient, OdooAPIError
from .models import (
    OdooConfig,
    InvoiceLine,
    Invoice,
    Payment,
    AccountBalance,
    ApprovalRequest,
)
from .approval_workflow import OdooApprovalWorkflow

__all__ = [
    "OdooAPIClient",
    "OdooAPIError",
    "OdooConfig",
    "InvoiceLine",
    "Invoice",
    "Payment",
    "AccountBalance",
    "ApprovalRequest",
    "OdooApprovalWorkflow",
]
