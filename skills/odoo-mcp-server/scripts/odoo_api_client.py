#!/usr/bin/env python3
"""
Odoo API Client

JSON-RPC client for Odoo 19+ API integration.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import httpx
import structlog

from .models import (
    AccountBalance,
    Invoice,
    InvoiceLine,
    MoveType,
    OdooConfig,
    Payment,
    SearchResult,
)

logger = structlog.get_logger()


class OdooAPIError(Exception):
    """Custom exception for Odoo API errors"""

    def __init__(self, message: str, code: int = None, data: dict = None):
        super().__init__(message)
        self.code = code
        self.data = data


class OdooAPIClient:
    """
    Async JSON-RPC client for Odoo API.

    Supports Odoo 19+ with API key authentication.
    """

    def __init__(self, config: OdooConfig = None):
        self.config = config or OdooConfig()
        self._load_env_config()

        self.base_url = self.config.url.rstrip("/")
        self.db = self.config.database
        self.username = self.config.username
        self.api_key = self.config.api_key

        self._uid: Optional[int] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0

        self.logger = logger.bind(component="OdooAPIClient")

    def _load_env_config(self):
        """Load configuration from environment variables"""
        if os.getenv("ODOO_URL"):
            self.config.url = os.getenv("ODOO_URL")
        if os.getenv("ODOO_DATABASE"):
            self.config.database = os.getenv("ODOO_DATABASE")
        if os.getenv("ODOO_USERNAME"):
            self.config.username = os.getenv("ODOO_USERNAME")
        if os.getenv("ODOO_API_KEY"):
            self.config.api_key = os.getenv("ODOO_API_KEY")
        if os.getenv("ODOO_APPROVAL_THRESHOLD"):
            self.config.invoice_threshold = float(os.getenv("ODOO_APPROVAL_THRESHOLD"))

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Establish connection and authenticate"""
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            verify=self.config.verify_ssl
        )

        # Authenticate to get UID
        self._uid = await self._authenticate()
        self.logger.info("Connected to Odoo", url=self.base_url, uid=self._uid)

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _authenticate(self) -> int:
        """Authenticate with Odoo and return user ID"""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "authenticate",
                "args": [self.db, self.username, self.api_key, {}]
            },
            "id": self._next_request_id()
        }

        response = await self._make_request("/jsonrpc", payload)

        if not response or not isinstance(response, int):
            raise OdooAPIError("Authentication failed", data={"response": response})

        return response

    async def _make_request(self, endpoint: str, payload: dict) -> Any:
        """Make JSON-RPC request to Odoo"""
        if not self._client:
            raise OdooAPIError("Client not connected. Call connect() first.")

        url = f"{self.base_url}{endpoint}"

        try:
            response = await self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                error = result["error"]
                raise OdooAPIError(
                    error.get("message", "Unknown error"),
                    code=error.get("code"),
                    data=error.get("data")
                )

            return result.get("result")

        except httpx.HTTPStatusError as e:
            raise OdooAPIError(f"HTTP error: {e.response.status_code}", code=e.response.status_code)
        except httpx.RequestError as e:
            raise OdooAPIError(f"Request error: {str(e)}")

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Dict[str, Any] = None
    ) -> Any:
        """
        Execute Odoo model method via JSON-RPC.

        Args:
            model: Odoo model name (e.g., "account.move")
            method: Method to call (e.g., "search_read")
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Method result
        """
        if not self._uid:
            raise OdooAPIError("Not authenticated. Call connect() first.")

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.db,
                    self._uid,
                    self.api_key,
                    model,
                    method,
                    args,
                    kwargs or {}
                ]
            },
            "id": self._next_request_id()
        }

        self.logger.debug("Executing Odoo method", model=model, method=method)
        return await self._make_request("/jsonrpc", payload)

    def _next_request_id(self) -> int:
        """Generate next request ID"""
        self._request_count += 1
        return self._request_count

    # ========== Search Operations ==========

    async def search_read(
        self,
        model: str,
        domain: List[Any] = None,
        fields: List[str] = None,
        offset: int = 0,
        limit: int = 100,
        order: str = None
    ) -> SearchResult:
        """
        Search and read records from Odoo.

        Args:
            model: Odoo model name
            domain: Search domain filter
            fields: Fields to return
            offset: Records to skip
            limit: Maximum records to return
            order: Sort order

        Returns:
            SearchResult with records
        """
        domain = domain or []
        fields = fields or []

        kwargs = {"offset": offset, "limit": limit}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order

        records = await self.execute_kw(model, "search_read", [domain], kwargs)

        # Get total count
        count = await self.execute_kw(model, "search_count", [domain])

        return SearchResult(
            model=model,
            count=count,
            records=records or [],
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit
        )

    async def read(
        self,
        model: str,
        ids: List[int],
        fields: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Read specific records by ID"""
        kwargs = {}
        if fields:
            kwargs["fields"] = fields

        return await self.execute_kw(model, "read", [ids], kwargs)

    async def search(
        self,
        model: str,
        domain: List[Any] = None,
        offset: int = 0,
        limit: int = 100,
        order: str = None
    ) -> List[int]:
        """Search for record IDs"""
        domain = domain or []
        kwargs = {"offset": offset, "limit": limit}
        if order:
            kwargs["order"] = order

        return await self.execute_kw(model, "search", [domain], kwargs)

    # ========== Invoice Operations ==========

    async def create_invoice(self, invoice: Invoice) -> int:
        """
        Create a draft invoice in Odoo.

        Args:
            invoice: Invoice model with data

        Returns:
            Created invoice ID
        """
        vals = invoice.to_odoo_create_vals()
        invoice_id = await self.execute_kw("account.move", "create", [vals])

        self.logger.info("Invoice created", invoice_id=invoice_id, partner_id=invoice.partner_id)
        return invoice_id

    async def post_invoice(self, invoice_id: int) -> bool:
        """
        Post (validate) a draft invoice.

        Args:
            invoice_id: ID of the draft invoice

        Returns:
            True if successful
        """
        await self.execute_kw("account.move", "action_post", [[invoice_id]])
        self.logger.info("Invoice posted", invoice_id=invoice_id)
        return True

    async def get_invoice(self, invoice_id: int) -> Invoice:
        """Get invoice by ID"""
        records = await self.read(
            "account.move",
            [invoice_id],
            [
                "name", "partner_id", "move_type", "invoice_date", "invoice_date_due",
                "state", "amount_untaxed", "amount_tax", "amount_total", "amount_residual",
                "currency_id", "ref", "narration"
            ]
        )

        if not records:
            raise OdooAPIError(f"Invoice {invoice_id} not found")

        return Invoice.from_odoo_record(records[0])

    async def get_invoices_by_partner(
        self,
        partner_id: int,
        move_type: MoveType = None,
        state: str = None,
        limit: int = 50
    ) -> List[Invoice]:
        """Get invoices for a partner"""
        domain = [("partner_id", "=", partner_id)]
        if move_type:
            domain.append(("move_type", "=", move_type.value))
        if state:
            domain.append(("state", "=", state))

        result = await self.search_read(
            "account.move",
            domain=domain,
            fields=[
                "name", "partner_id", "move_type", "invoice_date", "invoice_date_due",
                "state", "amount_untaxed", "amount_tax", "amount_total", "amount_residual"
            ],
            limit=limit,
            order="invoice_date desc"
        )

        return [Invoice.from_odoo_record(r) for r in result.records]

    # ========== Payment Operations ==========

    async def create_payment(self, payment: Payment) -> int:
        """
        Create a payment in Odoo.

        Args:
            payment: Payment model with data

        Returns:
            Created payment ID
        """
        vals = payment.to_odoo_create_vals()
        payment_id = await self.execute_kw("account.payment", "create", [vals])

        self.logger.info("Payment created", payment_id=payment_id, amount=payment.amount)
        return payment_id

    async def post_payment(self, payment_id: int) -> bool:
        """Post a payment"""
        await self.execute_kw("account.payment", "action_post", [[payment_id]])
        self.logger.info("Payment posted", payment_id=payment_id)
        return True

    async def register_payment_for_invoice(
        self,
        invoice_id: int,
        amount: float,
        payment_date: str,
        journal_id: int,
        ref: str = None
    ) -> int:
        """
        Register a payment for an invoice.

        Args:
            invoice_id: Invoice to pay
            amount: Payment amount
            payment_date: Payment date (YYYY-MM-DD)
            journal_id: Payment journal ID
            ref: Optional reference

        Returns:
            Created payment ID
        """
        # Get invoice details
        invoice = await self.get_invoice(invoice_id)

        payment = Payment(
            partner_id=invoice.partner_id,
            amount=amount,
            payment_date=payment_date,
            journal_id=journal_id,
            payment_type="inbound" if invoice.move_type in (MoveType.OUT_INVOICE, MoveType.IN_REFUND) else "outbound",
            partner_type="customer" if invoice.move_type in (MoveType.OUT_INVOICE, MoveType.OUT_REFUND) else "supplier",
            ref=ref
        )

        payment_id = await self.create_payment(payment)
        await self.post_payment(payment_id)

        return payment_id

    # ========== Account Operations ==========

    async def get_account_balance(
        self,
        account_id: int,
        date_from: str = None,
        date_to: str = None
    ) -> AccountBalance:
        """
        Get balance for an account.

        Args:
            account_id: Account ID
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            AccountBalance with debit, credit, balance
        """
        # Get account info
        accounts = await self.read("account.account", [account_id], ["code", "name"])
        if not accounts:
            raise OdooAPIError(f"Account {account_id} not found")

        account = accounts[0]

        # Build domain for move lines
        domain = [("account_id", "=", account_id), ("parent_state", "=", "posted")]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))

        # Get move lines and sum
        lines = await self.search_read(
            "account.move.line",
            domain=domain,
            fields=["debit", "credit", "balance"],
            limit=10000
        )

        total_debit = sum(l.get("debit", 0) for l in lines.records)
        total_credit = sum(l.get("credit", 0) for l in lines.records)
        balance = total_debit - total_credit

        return AccountBalance(
            account_id=account_id,
            account_code=account.get("code", ""),
            account_name=account.get("name", ""),
            debit=total_debit,
            credit=total_credit,
            balance=balance,
            date_from=date_from,
            date_to=date_to
        )

    async def get_chart_of_accounts(self, company_id: int = None) -> List[Dict[str, Any]]:
        """Get chart of accounts"""
        domain = []
        if company_id:
            domain.append(("company_id", "=", company_id))

        result = await self.search_read(
            "account.account",
            domain=domain,
            fields=["code", "name", "account_type", "reconcile"],
            order="code"
        )

        return result.records

    async def get_journals(self, journal_type: str = None) -> List[Dict[str, Any]]:
        """Get accounting journals"""
        domain = []
        if journal_type:
            domain.append(("type", "=", journal_type))

        result = await self.search_read(
            "account.journal",
            domain=domain,
            fields=["name", "code", "type", "default_account_id"],
            order="sequence"
        )

        return result.records

    # ========== Partner Operations ==========

    async def get_partner(self, partner_id: int) -> Dict[str, Any]:
        """Get partner/contact by ID"""
        records = await self.read(
            "res.partner",
            [partner_id],
            ["name", "email", "phone", "street", "city", "country_id", "vat", "is_company"]
        )

        if not records:
            raise OdooAPIError(f"Partner {partner_id} not found")

        return records[0]

    async def search_partners(
        self,
        name: str = None,
        email: str = None,
        is_company: bool = None,
        customer_rank: bool = None,
        supplier_rank: bool = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for partners"""
        domain = []
        if name:
            domain.append(("name", "ilike", name))
        if email:
            domain.append(("email", "ilike", email))
        if is_company is not None:
            domain.append(("is_company", "=", is_company))
        if customer_rank:
            domain.append(("customer_rank", ">", 0))
        if supplier_rank:
            domain.append(("supplier_rank", ">", 0))

        result = await self.search_read(
            "res.partner",
            domain=domain,
            fields=["name", "email", "phone", "is_company", "customer_rank", "supplier_rank"],
            limit=limit
        )

        return result.records


# Convenience function
async def create_odoo_client(config: OdooConfig = None) -> OdooAPIClient:
    """Create and connect an Odoo client"""
    client = OdooAPIClient(config)
    await client.connect()
    return client


async def demo_odoo_client():
    """Demo the Odoo client"""
    print("Odoo API Client Demo")
    print("=" * 40)
    print("Note: This demo requires a running Odoo instance")
    print("Set environment variables: ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_API_KEY")

    # Example usage (without actual connection)
    print("\nExample usage:")
    print("```python")
    print("async with OdooAPIClient() as client:")
    print("    # Search for invoices")
    print("    result = await client.search_read(")
    print("        'account.move',")
    print("        domain=[('move_type', '=', 'out_invoice')],")
    print("        fields=['name', 'partner_id', 'amount_total']")
    print("    )")
    print("")
    print("    # Create invoice")
    print("    invoice = Invoice(")
    print("        partner_id=1,")
    print("        move_type=MoveType.OUT_INVOICE,")
    print("        invoice_lines=[InvoiceLine(name='Service', quantity=1, price_unit=500)]")
    print("    )")
    print("    invoice_id = await client.create_invoice(invoice)")
    print("```")


if __name__ == "__main__":
    asyncio.run(demo_odoo_client())
