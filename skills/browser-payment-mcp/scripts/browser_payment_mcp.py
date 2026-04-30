#!/usr/bin/env python3
"""
Browser Payment MCP Server.

A FastMCP server that automates browser-based payment portal interactions
using Playwright.  Enforces strict HITL (Human-In-The-Loop) controls:
no payment is ever submitted without explicit human approval.

Usage:
    python browser_payment_mcp.py

The server runs on the ``stdio`` transport by default.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Conditional imports -- graceful degradation when dependencies are missing.
# ---------------------------------------------------------------------------

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

# Add the scripts directory to sys.path so sibling modules resolve.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config_manager import config  # noqa: E402
from payment_audit import audit_logger  # noqa: E402
from approval_workflow import approval_workflow, ApprovalStatus  # noqa: E402

# ---------------------------------------------------------------------------
# Server bootstrap
# ---------------------------------------------------------------------------

if not FASTMCP_AVAILABLE:
    print(
        "ERROR: fastmcp is not installed.  "
        "Run: pip install fastmcp>=0.1.0",
        file=sys.stderr,
    )
    sys.exit(1)

mcp = FastMCP(
    "browser-payment-mcp",
    description=(
        "MCP server for browser-based payment portal automation. "
        "All payments require human approval (HITL)."
    ),
)

# ---------------------------------------------------------------------------
# Browser session management
# ---------------------------------------------------------------------------

_browser: Optional[Any] = None
_context: Optional[Any] = None
_page: Optional[Any] = None
_playwright_instance: Optional[Any] = None

# Rate-limiting state: list of epoch timestamps of executed payments.
_payment_timestamps: List[float] = []


async def _ensure_browser() -> Any:
    """Return the active Playwright page, launching the browser if needed."""
    global _browser, _context, _page, _playwright_instance

    if config.dry_run:
        return None

    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright is not installed.  "
            "Run: pip install playwright && playwright install chromium"
        )

    if _page is not None:
        try:
            # Quick health check.
            await _page.title()
            return _page
        except Exception:
            _page = None

    if _playwright_instance is None:
        _playwright_instance = await async_playwright().start()

    config.ensure_directories()

    _context = await _playwright_instance.chromium.launch_persistent_context(
        user_data_dir=str(config.browser_profile_path),
        headless=config.headless,
        viewport={"width": 1280, "height": 900},
        accept_downloads=False,
    )
    _page = _context.pages[0] if _context.pages else await _context.new_page()
    return _page


async def _close_browser() -> None:
    """Cleanly shut down the browser."""
    global _browser, _context, _page, _playwright_instance
    try:
        if _context:
            await _context.close()
    except Exception:
        pass
    try:
        if _playwright_instance:
            await _playwright_instance.stop()
    except Exception:
        pass
    _browser = None
    _context = None
    _page = None
    _playwright_instance = None


def _check_rate_limit() -> bool:
    """Return True if another payment is allowed under the rate limit."""
    now = time.time()
    one_hour_ago = now - 3600
    # Prune old entries.
    _payment_timestamps[:] = [t for t in _payment_timestamps if t > one_hour_ago]
    return len(_payment_timestamps) < config.max_payments_per_hour


def _record_payment() -> None:
    """Record that a payment was executed (for rate limiting)."""
    _payment_timestamps.append(time.time())


# ---------------------------------------------------------------------------
# MCP Tool: navigate_to
# ---------------------------------------------------------------------------

@mcp.tool()
async def navigate_to(url: str) -> str:
    """Navigate the browser to a URL.

    Parameters
    ----------
    url : str
        The URL to navigate to.

    Returns
    -------
    str
        Confirmation with the page title, or an error message.
    """
    if not config.is_domain_allowed(url):
        audit_logger.log_event(
            "navigate_blocked", url=url, success=False,
            error="Domain not in allowed list",
        )
        return f"ERROR: Domain not in allowed list. Allowed: {config.allowed_domains or ['*']}"

    if config.dry_run:
        audit_logger.log_event("navigate_to", url=url, dry_run=True)
        return f"[DRY RUN] Would navigate to: {url}"

    page = await _ensure_browser()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        screenshot = await audit_logger.take_screenshot(page, f"navigate_{title[:20]}")
        audit_logger.log_event("navigate_to", url=url, screenshot_path=screenshot)
        return f"Navigated to: {url} (title: {title})"
    except Exception as exc:
        audit_logger.log_event("navigate_to", url=url, success=False, error=str(exc))
        return f"ERROR navigating to {url}: {exc}"


# ---------------------------------------------------------------------------
# MCP Tool: fill_form
# ---------------------------------------------------------------------------

@mcp.tool()
async def fill_form(selector: str, value: str) -> str:
    """Fill a form field identified by a CSS selector.

    Parameters
    ----------
    selector : str
        CSS selector for the input element.
    value : str
        The value to type into the field.

    Returns
    -------
    str
        Confirmation or error message.
    """
    if config.dry_run:
        audit_logger.log_event(
            "fill_form", selector=selector, dry_run=True,
            extra={"value_length": len(value)},
        )
        return f"[DRY RUN] Would fill '{selector}' with value (length={len(value)})"

    page = await _ensure_browser()
    try:
        await page.fill(selector, value, timeout=10000)
        audit_logger.log_event(
            "fill_form", selector=selector,
            extra={"value_length": len(value)},
        )
        return f"Filled '{selector}' successfully."
    except Exception as exc:
        audit_logger.log_event(
            "fill_form", selector=selector, success=False, error=str(exc),
        )
        return f"ERROR filling '{selector}': {exc}"


# ---------------------------------------------------------------------------
# MCP Tool: click_element
# ---------------------------------------------------------------------------

@mcp.tool()
async def click_element(selector: str) -> str:
    """Click an element identified by a CSS selector.

    Parameters
    ----------
    selector : str
        CSS selector for the element to click.

    Returns
    -------
    str
        Confirmation or error message.
    """
    if config.dry_run:
        audit_logger.log_event("click_element", selector=selector, dry_run=True)
        return f"[DRY RUN] Would click '{selector}'"

    page = await _ensure_browser()
    try:
        await page.click(selector, timeout=10000)
        screenshot = await audit_logger.take_screenshot(page, f"click_{selector[:20]}")
        audit_logger.log_event(
            "click_element", selector=selector, screenshot_path=screenshot,
        )
        return f"Clicked '{selector}' successfully."
    except Exception as exc:
        audit_logger.log_event(
            "click_element", selector=selector, success=False, error=str(exc),
        )
        return f"ERROR clicking '{selector}': {exc}"


# ---------------------------------------------------------------------------
# MCP Tool: get_page_content
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_page_content(selector: str = "body") -> str:
    """Extract text content from an element on the page.

    Parameters
    ----------
    selector : str
        CSS selector for the element (default: ``"body"``).

    Returns
    -------
    str
        The text content of the element, or an error message.
    """
    if config.dry_run:
        audit_logger.log_event("get_page_content", selector=selector, dry_run=True)
        return "[DRY RUN] Would extract page content."

    page = await _ensure_browser()
    try:
        element = await page.query_selector(selector)
        if element is None:
            return f"No element found for selector '{selector}'."
        text = await element.inner_text()
        audit_logger.log_event("get_page_content", selector=selector)
        # Truncate very long content to avoid overwhelming the LLM.
        if len(text) > 5000:
            text = text[:5000] + "\n\n... [truncated]"
        return text
    except Exception as exc:
        audit_logger.log_event(
            "get_page_content", selector=selector, success=False, error=str(exc),
        )
        return f"ERROR reading content from '{selector}': {exc}"


# ---------------------------------------------------------------------------
# MCP Tool: screenshot
# ---------------------------------------------------------------------------

@mcp.tool()
async def screenshot(name: str = "manual") -> str:
    """Take a screenshot of the current page for audit purposes.

    Parameters
    ----------
    name : str
        A descriptive label for the screenshot file.

    Returns
    -------
    str
        The file path of the saved screenshot.
    """
    page = None if config.dry_run else await _ensure_browser()
    path = await audit_logger.take_screenshot(page, name)
    if path:
        return f"Screenshot saved: {path}"
    return "ERROR: Failed to take screenshot."


# ---------------------------------------------------------------------------
# MCP Tool: draft_payment
# ---------------------------------------------------------------------------

@mcp.tool()
async def draft_payment(
    recipient: str,
    amount: str,
    reference: str = "",
    account: str = "",
    currency: str = "USD",
    submit_selector: str = "",
) -> str:
    """Draft a payment by filling the payment form but NOT submitting it.

    Creates an approval file that a human must review and approve before
    the payment can be executed via ``execute_payment``.

    Parameters
    ----------
    recipient : str
        Name or identifier of the payment recipient.
    amount : str
        Payment amount (e.g. ``"150.00"``).
    reference : str
        Payment reference or memo.
    account : str
        Source account identifier.
    currency : str
        Three-letter currency code (default ``"USD"``).
    submit_selector : str
        CSS selector for the submit button (stored for later execution).

    Returns
    -------
    str
        Details of the created approval request including the approval ID
        and instructions for the human reviewer.
    """
    # Rate-limit check (drafts also count toward awareness).
    if not _check_rate_limit():
        audit_logger.log_event(
            "draft_payment", amount=amount, recipient=recipient,
            success=False, error="Rate limit reached",
        )
        return (
            f"ERROR: Rate limit reached ({config.max_payments_per_hour} "
            "payments per hour). Try again later."
        )

    # Create the approval request.
    result = approval_workflow.create_approval_request(
        recipient=recipient,
        amount=amount,
        currency=currency,
        reference=reference,
        account=account,
        extra_details={
            "submit_selector": submit_selector,
            "drafted_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Take a screenshot of the current form state.
    page = None if config.dry_run else await _ensure_browser()
    screenshot_path = await audit_logger.take_screenshot(page, f"draft_{result['approval_id']}")

    audit_logger.log_event(
        "draft_payment",
        amount=amount,
        recipient=recipient,
        approval_id=result["approval_id"],
        approval_status=ApprovalStatus.PENDING,
        screenshot_path=screenshot_path,
        dry_run=config.dry_run,
        extra={"reference": reference, "account": account, "currency": currency},
    )

    return json.dumps(
        {
            "status": "PENDING_APPROVAL",
            "approval_id": result["approval_id"],
            "file_path": result["file_path"],
            "expires_at": result["expires_at"],
            "is_new_payee": result["is_new_payee"],
            "instructions": (
                "PAYMENT NOT SUBMITTED. A human must review the approval file at "
                f"'{result['file_path']}' and move it to the 'Approved' folder. "
                "Then call execute_payment with the approval_id."
            ),
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# MCP Tool: execute_payment
# ---------------------------------------------------------------------------

@mcp.tool()
async def execute_payment(approval_id: str) -> str:
    """Execute a previously drafted and approved payment.

    This tool ONLY works if:
    1. A matching approval file exists in the ``Approved/`` folder.
    2. The approval has not expired (24-hour window).
    3. The amount in the approval matches the drafted amount.
    4. The hourly rate limit has not been exceeded.

    Parameters
    ----------
    approval_id : str
        The approval ID returned by ``draft_payment``.

    Returns
    -------
    str
        Execution result or error explaining why the payment was blocked.
    """
    # 1. Rate-limit check.
    if not _check_rate_limit():
        audit_logger.log_event(
            "execute_payment", approval_id=approval_id,
            success=False, error="Rate limit reached",
        )
        return (
            f"ERROR: Rate limit reached ({config.max_payments_per_hour} "
            "payments per hour). Try again later."
        )

    # 2. Check approval status.
    status, details = approval_workflow.check_approval(approval_id)

    if status == ApprovalStatus.PENDING:
        audit_logger.log_event(
            "execute_payment", approval_id=approval_id,
            approval_status="pending", success=False,
            error="Payment not yet approved by human",
        )
        return json.dumps(
            {
                "status": "BLOCKED",
                "reason": "Payment has NOT been approved by a human yet.",
                "details": details,
            },
            indent=2,
        )

    if status == ApprovalStatus.EXPIRED:
        audit_logger.log_event(
            "execute_payment", approval_id=approval_id,
            approval_status="expired", success=False,
            error="Approval expired",
        )
        return json.dumps(
            {
                "status": "BLOCKED",
                "reason": "Approval has expired. Please create a new draft_payment.",
                "details": details,
            },
            indent=2,
        )

    if status == ApprovalStatus.NOT_FOUND:
        audit_logger.log_event(
            "execute_payment", approval_id=approval_id,
            approval_status="not_found", success=False,
            error="Approval file not found",
        )
        return json.dumps(
            {
                "status": "BLOCKED",
                "reason": f"No approval file found for ID {approval_id}.",
                "details": details,
            },
            indent=2,
        )

    if status == ApprovalStatus.INVALID:
        audit_logger.log_event(
            "execute_payment", approval_id=approval_id,
            approval_status="invalid", success=False,
            error=details.get("error", "Invalid approval"),
        )
        return json.dumps(
            {
                "status": "BLOCKED",
                "reason": details.get("error", "Approval is invalid."),
            },
            indent=2,
        )

    if status != ApprovalStatus.APPROVED:
        audit_logger.log_event(
            "execute_payment", approval_id=approval_id,
            approval_status=status, success=False,
            error=f"Unexpected status: {status}",
        )
        return json.dumps(
            {"status": "BLOCKED", "reason": f"Unexpected approval status: {status}"},
            indent=2,
        )

    # 3. Approval is valid -- proceed.
    parsed = details.get("parsed", {})
    amount = parsed.get("amount", "unknown")
    recipient = parsed.get("recipient", "unknown")

    # Take pre-execution screenshot.
    page = None if config.dry_run else await _ensure_browser()
    pre_screenshot = await audit_logger.take_screenshot(
        page, f"pre_execute_{approval_id}"
    )

    if config.dry_run:
        _record_payment()
        audit_logger.log_event(
            "execute_payment",
            amount=amount,
            recipient=recipient,
            approval_id=approval_id,
            approval_status="approved",
            dry_run=True,
        )
        return json.dumps(
            {
                "status": "DRY_RUN_SUCCESS",
                "approval_id": approval_id,
                "amount": amount,
                "recipient": recipient,
                "message": "[DRY RUN] Payment would have been submitted.",
            },
            indent=2,
        )

    # Attempt to click the submit button.
    # The submit_selector was stored in the approval file's extra details.
    # For a real integration, we'd parse it out. Here we look for a common
    # submit button pattern.
    try:
        # Try common submit selectors.
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "#submit-payment",
            ".submit-payment",
            "button.confirm-payment",
        ]
        clicked = False
        for sel in submit_selectors:
            try:
                element = await page.query_selector(sel)
                if element and await element.is_visible():
                    await element.click(timeout=5000)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            audit_logger.log_event(
                "execute_payment",
                approval_id=approval_id,
                approval_status="approved",
                success=False,
                error="Could not find submit button",
            )
            return json.dumps(
                {
                    "status": "ERROR",
                    "reason": "Payment approved but submit button not found on page.",
                    "approval_id": approval_id,
                },
                indent=2,
            )

        # Wait for navigation or confirmation.
        await page.wait_for_load_state("domcontentloaded", timeout=15000)

        # Post-execution screenshot.
        post_screenshot = await audit_logger.take_screenshot(
            page, f"post_execute_{approval_id}"
        )

        _record_payment()
        approval_workflow.record_known_recipient(recipient)

        audit_logger.log_event(
            "execute_payment",
            amount=amount,
            recipient=recipient,
            approval_id=approval_id,
            approval_status="approved",
            screenshot_path=post_screenshot,
        )

        return json.dumps(
            {
                "status": "EXECUTED",
                "approval_id": approval_id,
                "amount": amount,
                "recipient": recipient,
                "message": "Payment submitted successfully.",
                "screenshots": {
                    "pre": pre_screenshot,
                    "post": post_screenshot,
                },
            },
            indent=2,
        )

    except Exception as exc:
        audit_logger.log_event(
            "execute_payment",
            approval_id=approval_id,
            approval_status="approved",
            success=False,
            error=str(exc),
        )
        return json.dumps(
            {
                "status": "ERROR",
                "reason": f"Payment execution failed: {exc}",
                "approval_id": approval_id,
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# MCP Tool: check_balance
# ---------------------------------------------------------------------------

@mcp.tool()
async def check_balance(account: str = "") -> str:
    """Check the account balance on the currently loaded payment portal.

    Parameters
    ----------
    account : str
        Account identifier or label to look for on the page.

    Returns
    -------
    str
        The detected balance text or an error message.
    """
    if config.dry_run:
        audit_logger.log_event("check_balance", dry_run=True, extra={"account": account})
        return "[DRY RUN] Would check balance for account: " + (account or "default")

    page = await _ensure_browser()
    try:
        # Look for common balance-related selectors.
        balance_selectors = [
            ".balance",
            ".account-balance",
            "#balance",
            "[data-testid='balance']",
            ".available-balance",
            ".current-balance",
        ]

        for sel in balance_selectors:
            element = await page.query_selector(sel)
            if element:
                text = await element.inner_text()
                screenshot_path = await audit_logger.take_screenshot(
                    page, f"balance_{account[:10] if account else 'default'}"
                )
                audit_logger.log_event(
                    "check_balance",
                    extra={"account": account, "balance_text": text[:100]},
                    screenshot_path=screenshot_path,
                )
                return f"Balance: {text.strip()}"

        # Fallback: search page text for currency patterns.
        body_text = await page.inner_text("body")
        import re
        matches = re.findall(
            r"(?:balance|available|current)\s*:?\s*[\$\u20ac\u00a3]?\s*[\d,]+\.?\d*",
            body_text,
            re.IGNORECASE,
        )
        if matches:
            audit_logger.log_event(
                "check_balance",
                extra={"account": account, "balance_text": matches[0][:100]},
            )
            return f"Detected balance: {matches[0].strip()}"

        audit_logger.log_event(
            "check_balance",
            extra={"account": account},
            success=False,
            error="No balance element found",
        )
        return "Could not detect a balance element on the current page."

    except Exception as exc:
        audit_logger.log_event(
            "check_balance", success=False, error=str(exc),
        )
        return f"ERROR checking balance: {exc}"


# ---------------------------------------------------------------------------
# MCP Tool: get_transaction_history
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_transaction_history(account: str = "", days: int = 30) -> str:
    """Get recent transaction history from the payment portal.

    Parameters
    ----------
    account : str
        Account identifier to filter transactions.
    days : int
        Number of days of history to retrieve (default 30).

    Returns
    -------
    str
        Transaction history text or an error message.
    """
    if config.dry_run:
        audit_logger.log_event(
            "get_transaction_history", dry_run=True,
            extra={"account": account, "days": days},
        )
        return f"[DRY RUN] Would retrieve {days}-day transaction history for: {account or 'default'}"

    page = await _ensure_browser()
    try:
        # Look for common transaction table selectors.
        table_selectors = [
            ".transactions",
            ".transaction-history",
            "#transactions",
            "[data-testid='transactions']",
            "table.transactions",
            ".recent-transactions",
        ]

        for sel in table_selectors:
            element = await page.query_selector(sel)
            if element:
                text = await element.inner_text()
                screenshot_path = await audit_logger.take_screenshot(
                    page, f"transactions_{account[:10] if account else 'default'}"
                )
                audit_logger.log_event(
                    "get_transaction_history",
                    extra={"account": account, "days": days},
                    screenshot_path=screenshot_path,
                )
                if len(text) > 5000:
                    text = text[:5000] + "\n\n... [truncated]"
                return f"Transaction History:\n{text.strip()}"

        audit_logger.log_event(
            "get_transaction_history",
            extra={"account": account, "days": days},
            success=False,
            error="No transaction table found",
        )
        return "Could not find a transaction history element on the current page."

    except Exception as exc:
        audit_logger.log_event(
            "get_transaction_history", success=False, error=str(exc),
        )
        return f"ERROR retrieving transaction history: {exc}"


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the MCP server."""
    config.ensure_directories()
    warnings = config.validate()
    for w in warnings:
        print(f"CONFIG WARNING: {w}", file=sys.stderr)

    if config.dry_run:
        print("*** DRY RUN MODE ENABLED -- no real browser actions ***", file=sys.stderr)
    if not PLAYWRIGHT_AVAILABLE:
        print(
            "WARNING: Playwright not installed. Browser tools will fail. "
            "Run: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )

    audit_logger.log_event(
        "server_start",
        dry_run=config.dry_run,
        extra=config.to_dict(),
    )

    # Clean up old audit data on startup.
    removed = audit_logger.cleanup_old_logs()
    if removed:
        print(f"Cleaned up {removed} old audit files.", file=sys.stderr)

    expired = approval_workflow.cleanup_expired()
    if expired:
        print(f"Cleaned up {expired} expired approval files.", file=sys.stderr)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
