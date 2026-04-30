#!/usr/bin/env python3
"""
Data models for Odoo MCP Server

Pydantic models for Odoo API operations and approval workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MoveType(str, Enum):
    """Odoo invoice/move types"""
    OUT_INVOICE = "out_invoice"  # Customer Invoice
    IN_INVOICE = "in_invoice"    # Vendor Bill
    OUT_REFUND = "out_refund"    # Customer Credit Note
    IN_REFUND = "in_refund"      # Vendor Credit Note
    ENTRY = "entry"              # Journal Entry


class InvoiceState(str, Enum):
    """Odoo invoice states"""
    DRAFT = "draft"
    POSTED = "posted"
    CANCEL = "cancel"


class PaymentState(str, Enum):
    """Odoo payment states"""
    DRAFT = "draft"
    POSTED = "posted"
    CANCEL = "cancel"


class ApprovalStatus(str, Enum):
    """Approval status for HITL workflow"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OdooConfig(BaseModel):
    """Configuration for Odoo connection"""
    url: str = Field(default="http://localhost:8069", description="Odoo server URL")
    database: str = Field(default="odoo", description="Odoo database name")
    username: str = Field(default="", description="Odoo username")
    api_key: str = Field(default="", description="Odoo API key")
    timeout_seconds: int = Field(default=30, description="Request timeout")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    # Approval settings
    invoice_threshold: float = Field(default=1000.0, description="Amount threshold for approval")
    always_require_approval: List[str] = Field(
        default=["post_invoice", "create_payment"],
        description="Operations that always require approval"
    )
    approval_timeout_hours: int = Field(default=24, description="Approval request timeout")

    # Rate limiting
    requests_per_minute: int = Field(default=60, description="Rate limit")
    burst_limit: int = Field(default=10, description="Burst limit")

    class Config:
        extra = "allow"


class InvoiceLine(BaseModel):
    """A single line item on an invoice"""
    product_id: Optional[int] = Field(default=None, description="Product ID")
    name: str = Field(default="", description="Description")
    quantity: float = Field(default=1.0, description="Quantity")
    price_unit: float = Field(default=0.0, description="Unit price")
    discount: float = Field(default=0.0, description="Discount percentage")
    tax_ids: List[int] = Field(default_factory=list, description="Tax IDs")
    account_id: Optional[int] = Field(default=None, description="Account ID")

    def to_odoo_format(self) -> Dict[str, Any]:
        """Convert to Odoo's command format for one2many fields"""
        vals = {
            "name": self.name,
            "quantity": self.quantity,
            "price_unit": self.price_unit,
            "discount": self.discount,
        }
        if self.product_id:
            vals["product_id"] = self.product_id
        if self.tax_ids:
            vals["tax_ids"] = [(6, 0, self.tax_ids)]
        if self.account_id:
            vals["account_id"] = self.account_id
        return (0, 0, vals)


class Invoice(BaseModel):
    """Odoo invoice model"""
    id: Optional[int] = None
    name: str = Field(default="/", description="Invoice number")
    partner_id: int = Field(..., description="Partner/Customer ID")
    move_type: MoveType = Field(default=MoveType.OUT_INVOICE, description="Invoice type")
    invoice_date: Optional[str] = Field(default=None, description="Invoice date (YYYY-MM-DD)")
    invoice_date_due: Optional[str] = Field(default=None, description="Due date (YYYY-MM-DD)")
    invoice_line_ids: List[InvoiceLine] = Field(default_factory=list, description="Invoice lines")
    state: InvoiceState = Field(default=InvoiceState.DRAFT, description="Invoice state")
    amount_untaxed: float = Field(default=0.0, description="Untaxed amount")
    amount_tax: float = Field(default=0.0, description="Tax amount")
    amount_total: float = Field(default=0.0, description="Total amount")
    amount_residual: float = Field(default=0.0, description="Amount due")
    currency_id: Optional[int] = Field(default=None, description="Currency ID")
    ref: Optional[str] = Field(default=None, description="Reference")
    narration: Optional[str] = Field(default=None, description="Terms and conditions")

    def to_odoo_create_vals(self) -> Dict[str, Any]:
        """Convert to Odoo create values"""
        vals = {
            "partner_id": self.partner_id,
            "move_type": self.move_type.value,
        }
        if self.invoice_date:
            vals["invoice_date"] = self.invoice_date
        if self.invoice_date_due:
            vals["invoice_date_due"] = self.invoice_date_due
        if self.invoice_line_ids:
            vals["invoice_line_ids"] = [line.to_odoo_format() for line in self.invoice_line_ids]
        if self.currency_id:
            vals["currency_id"] = self.currency_id
        if self.ref:
            vals["ref"] = self.ref
        if self.narration:
            vals["narration"] = self.narration
        return vals

    @classmethod
    def from_odoo_record(cls, record: Dict[str, Any]) -> "Invoice":
        """Create Invoice from Odoo record"""
        return cls(
            id=record.get("id"),
            name=record.get("name", "/"),
            partner_id=record.get("partner_id", [0, ""])[0] if isinstance(record.get("partner_id"), list) else record.get("partner_id", 0),
            move_type=MoveType(record.get("move_type", "out_invoice")),
            invoice_date=record.get("invoice_date"),
            invoice_date_due=record.get("invoice_date_due"),
            state=InvoiceState(record.get("state", "draft")),
            amount_untaxed=record.get("amount_untaxed", 0.0),
            amount_tax=record.get("amount_tax", 0.0),
            amount_total=record.get("amount_total", 0.0),
            amount_residual=record.get("amount_residual", 0.0),
            currency_id=record.get("currency_id", [0, ""])[0] if isinstance(record.get("currency_id"), list) else record.get("currency_id"),
            ref=record.get("ref"),
            narration=record.get("narration"),
        )


class Payment(BaseModel):
    """Odoo payment model"""
    id: Optional[int] = None
    name: str = Field(default="/", description="Payment reference")
    partner_id: int = Field(..., description="Partner ID")
    amount: float = Field(..., description="Payment amount")
    payment_date: str = Field(..., description="Payment date (YYYY-MM-DD)")
    journal_id: int = Field(..., description="Journal ID")
    payment_type: str = Field(default="inbound", description="inbound or outbound")
    partner_type: str = Field(default="customer", description="customer or supplier")
    state: PaymentState = Field(default=PaymentState.DRAFT, description="Payment state")
    ref: Optional[str] = Field(default=None, description="Reference/Memo")
    currency_id: Optional[int] = Field(default=None, description="Currency ID")

    def to_odoo_create_vals(self) -> Dict[str, Any]:
        """Convert to Odoo create values"""
        vals = {
            "partner_id": self.partner_id,
            "amount": self.amount,
            "date": self.payment_date,
            "journal_id": self.journal_id,
            "payment_type": self.payment_type,
            "partner_type": self.partner_type,
        }
        if self.ref:
            vals["ref"] = self.ref
        if self.currency_id:
            vals["currency_id"] = self.currency_id
        return vals


class AccountBalance(BaseModel):
    """Account balance information"""
    account_id: int
    account_code: str
    account_name: str
    debit: float = 0.0
    credit: float = 0.0
    balance: float = 0.0
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Approval request for HITL workflow"""
    id: str = Field(..., description="Unique approval request ID")
    operation: str = Field(..., description="Operation type (create_invoice, post_invoice, etc.)")
    model: str = Field(default="account.move", description="Odoo model")
    record_id: Optional[int] = Field(default=None, description="Record ID if updating")
    data: Dict[str, Any] = Field(default_factory=dict, description="Operation data")
    amount: float = Field(default=0.0, description="Financial amount involved")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Approval status")
    requested_by: str = Field(default="claude", description="Requester")
    requested_at: datetime = Field(default_factory=datetime.now, description="Request timestamp")
    approved_by: Optional[str] = Field(default=None, description="Approver")
    approved_at: Optional[datetime] = Field(default=None, description="Approval timestamp")
    rejection_reason: Optional[str] = Field(default=None, description="Rejection reason")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration time")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "operation": self.operation,
            "model": self.model,
            "record_id": self.record_id,
            "data": self.data,
            "amount": self.amount,
            "status": self.status.value,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "context": self.context,
        }


class SearchResult(BaseModel):
    """Search result wrapper"""
    model: str
    count: int
    records: List[Dict[str, Any]]
    domain: List[Any]
    fields: List[str]
    offset: int
    limit: int


class OdooError(BaseModel):
    """Odoo error response"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
