#!/usr/bin/env python3
"""
Calendar MCP Server - Model Context Protocol server for Google Calendar integration.

Enables Claude Code to create, update, query, and delete Google Calendar events
with HITL (Human-in-the-Loop) enforcement for sensitive operations such as
shared calendar modifications, events with external attendees, and deletions.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Add scripts directory to path for sibling imports
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from approval_workflow import CalendarApprovalManager, ApprovalStatus
from config_manager import CalendarConfig, get_config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("calendar-mcp-server")

# Google Calendar API scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


# ---------------------------------------------------------------------------
# Google Calendar Service Wrapper
# ---------------------------------------------------------------------------
class GoogleCalendarService:
    """Thin wrapper around the Google Calendar API with OAuth2 authentication."""

    def __init__(self, credentials_path: str, token_path: str):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._service = None
        self._creds: Optional[Credentials] = None

    # -- Authentication -----------------------------------------------------

    def authenticate(self) -> None:
        """Authenticate with Google Calendar API using OAuth2."""
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API libraries required. Install with:\n"
                "pip install google-auth-oauthlib google-api-python-client"
            )

        creds = None
        token_path = Path(self.token_path)
        creds_path = Path(self.credentials_path)

        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as exc:
                    logger.warning("Token refresh failed: %s", exc)
                    creds = None

            if not creds:
                if not creds_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {creds_path}\n"
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)

            # Persist token for subsequent runs
            token_path.write_text(creds.to_json())

        self._creds = creds
        self._service = build("calendar", "v3", credentials=self._creds)
        logger.info("Google Calendar API authenticated successfully")

    @property
    def service(self):
        if self._service is None:
            self.authenticate()
        return self._service

    # -- Calendar Operations ------------------------------------------------

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 25,
    ) -> List[Dict[str, Any]]:
        """List upcoming events from the specified calendar."""
        if time_min is None:
            time_min = datetime.now(timezone.utc).isoformat()

        kwargs: Dict[str, Any] = {
            "calendarId": calendar_id,
            "timeMin": time_min,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_max:
            kwargs["timeMax"] = time_max

        try:
            result = self.service.events().list(**kwargs).execute()
            events = result.get("items", [])
            return [self._format_event(e) for e in events]
        except HttpError as exc:
            logger.error("Error listing events: %s", exc)
            raise

    def get_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """Retrieve details of a single event."""
        try:
            event = self.service.events().get(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            return self._format_event(event)
        except HttpError as exc:
            logger.error("Error getting event %s: %s", event_id, exc)
            raise

    def create_event(
        self,
        calendar_id: str,
        summary: str,
        start: str,
        end: str,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        location: Optional[str] = None,
        timezone_str: str = "UTC",
    ) -> Dict[str, Any]:
        """Create a new calendar event."""
        body: Dict[str, Any] = {
            "summary": summary,
            "start": self._build_datetime(start, timezone_str),
            "end": self._build_datetime(end, timezone_str),
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]

        try:
            event = self.service.events().insert(
                calendarId=calendar_id, body=body, sendUpdates="all"
            ).execute()
            logger.info("Event created: %s (%s)", event.get("summary"), event.get("id"))
            return self._format_event(event)
        except HttpError as exc:
            logger.error("Error creating event: %s", exc)
            raise

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        summary: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        timezone_str: str = "UTC",
    ) -> Dict[str, Any]:
        """Update an existing calendar event (partial update via patch)."""
        body: Dict[str, Any] = {}
        if summary is not None:
            body["summary"] = summary
        if start is not None:
            body["start"] = self._build_datetime(start, timezone_str)
        if end is not None:
            body["end"] = self._build_datetime(end, timezone_str)
        if description is not None:
            body["description"] = description
        if location is not None:
            body["location"] = location
        if attendees is not None:
            body["attendees"] = [{"email": a} for a in attendees]

        try:
            event = self.service.events().patch(
                calendarId=calendar_id,
                eventId=event_id,
                body=body,
                sendUpdates="all",
            ).execute()
            logger.info("Event updated: %s (%s)", event.get("summary"), event.get("id"))
            return self._format_event(event)
        except HttpError as exc:
            logger.error("Error updating event %s: %s", event_id, exc)
            raise

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete a calendar event."""
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id, sendUpdates="all"
            ).execute()
            logger.info("Event deleted: %s", event_id)
            return True
        except HttpError as exc:
            logger.error("Error deleting event %s: %s", event_id, exc)
            raise

    def check_availability(
        self,
        calendar_id: str,
        time_min: str,
        time_max: str,
    ) -> Dict[str, Any]:
        """Check free/busy status for a calendar within a time range."""
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": calendar_id}],
        }
        try:
            result = self.service.freebusy().query(body=body).execute()
            calendars = result.get("calendars", {})
            cal_info = calendars.get(calendar_id, {})
            busy_slots = cal_info.get("busy", [])
            return {
                "calendar_id": calendar_id,
                "time_min": time_min,
                "time_max": time_max,
                "busy_slots": busy_slots,
                "is_free": len(busy_slots) == 0,
            }
        except HttpError as exc:
            logger.error("Error checking availability: %s", exc)
            raise

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _build_datetime(dt_str: str, tz: str = "UTC") -> Dict[str, str]:
        """Build a Google Calendar dateTime object from an ISO string."""
        if "T" not in dt_str:
            # Date-only, treat as all-day
            return {"date": dt_str}
        return {"dateTime": dt_str, "timeZone": tz}

    @staticmethod
    def _format_event(event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a raw Google Calendar event into a consistent dict."""
        start = event.get("start", {})
        end = event.get("end", {})
        attendees_raw = event.get("attendees", [])

        return {
            "id": event.get("id", ""),
            "summary": event.get("summary", "(No Title)"),
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "start": start.get("dateTime", start.get("date", "")),
            "end": end.get("dateTime", end.get("date", "")),
            "timezone": start.get("timeZone", ""),
            "status": event.get("status", ""),
            "html_link": event.get("htmlLink", ""),
            "creator": event.get("creator", {}).get("email", ""),
            "organizer": event.get("organizer", {}).get("email", ""),
            "attendees": [
                {
                    "email": a.get("email", ""),
                    "response_status": a.get("responseStatus", ""),
                    "display_name": a.get("displayName", ""),
                }
                for a in attendees_raw
            ],
            "created": event.get("created", ""),
            "updated": event.get("updated", ""),
            "recurring_event_id": event.get("recurringEventId", ""),
        }


# ---------------------------------------------------------------------------
# Calendar MCP Server (orchestration layer with HITL)
# ---------------------------------------------------------------------------
class CalendarMCPServer:
    """
    MCP server that wraps Google Calendar operations and enforces
    HITL approval for sensitive mutations.
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        config: Optional[CalendarConfig] = None,
    ):
        self.config = config or get_config()

        creds_path = credentials_path or self.config.credentials_path
        tok_path = token_path or self.config.token_path

        self.calendar_service = GoogleCalendarService(creds_path, tok_path)
        self.approval_manager = CalendarApprovalManager(
            approval_dir=self.config.approval_dir,
            timeout_seconds=self.config.approval_timeout_seconds,
        )

    # -- Public tool methods ------------------------------------------------

    def list_events(
        self,
        calendar_id: Optional[str] = None,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List upcoming events. No HITL required."""
        cal_id = calendar_id or self.config.default_calendar_id
        max_res = max_results or self.config.max_results_default

        events = self.calendar_service.list_events(
            calendar_id=cal_id,
            time_min=time_min,
            time_max=time_max,
            max_results=max_res,
        )
        return {
            "success": True,
            "calendar_id": cal_id,
            "event_count": len(events),
            "events": events,
        }

    def get_event(
        self, calendar_id: Optional[str] = None, event_id: str = ""
    ) -> Dict[str, Any]:
        """Get a single event's details. No HITL required."""
        cal_id = calendar_id or self.config.default_calendar_id
        event = self.calendar_service.get_event(cal_id, event_id)
        return {"success": True, "event": event}

    def create_event(
        self,
        calendar_id: Optional[str] = None,
        summary: str = "",
        start: str = "",
        end: str = "",
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a calendar event. HITL approval is required when:
        - The calendar is not the primary calendar
        - There are external attendees (outside organization domains)
        """
        cal_id = calendar_id or self.config.default_calendar_id
        needs_approval = self._needs_create_approval(cal_id, attendees)

        if needs_approval:
            request_id = self.approval_manager.request_approval(
                operation="create_event",
                details={
                    "calendar_id": cal_id,
                    "summary": summary,
                    "start": start,
                    "end": end,
                    "description": description or "",
                    "attendees": attendees or [],
                    "location": location or "",
                },
            )
            return {
                "success": False,
                "approval_required": True,
                "approval_request_id": request_id,
                "message": (
                    f"HITL approval required for this calendar operation. "
                    f"Approval file written to {self.config.approval_dir}/calendar/. "
                    f"Change status to 'approved' to proceed."
                ),
            }

        event = self.calendar_service.create_event(
            calendar_id=cal_id,
            summary=summary,
            start=start,
            end=end,
            description=description,
            attendees=attendees,
            location=location,
            timezone_str=self.config.timezone,
        )
        return {"success": True, "event": event}

    def update_event(
        self,
        calendar_id: Optional[str] = None,
        event_id: str = "",
        summary: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an event. HITL approval is always required."""
        cal_id = calendar_id or self.config.default_calendar_id

        request_id = self.approval_manager.request_approval(
            operation="update_event",
            details={
                "calendar_id": cal_id,
                "event_id": event_id,
                "summary": summary,
                "start": start,
                "end": end,
                "description": description,
            },
        )
        return {
            "success": False,
            "approval_required": True,
            "approval_request_id": request_id,
            "message": (
                f"HITL approval required to update event {event_id}. "
                f"Approval file written to {self.config.approval_dir}/calendar/."
            ),
        }

    def delete_event(
        self, calendar_id: Optional[str] = None, event_id: str = ""
    ) -> Dict[str, Any]:
        """Delete an event. HITL approval is always required."""
        cal_id = calendar_id or self.config.default_calendar_id

        request_id = self.approval_manager.request_approval(
            operation="delete_event",
            details={
                "calendar_id": cal_id,
                "event_id": event_id,
            },
        )
        return {
            "success": False,
            "approval_required": True,
            "approval_request_id": request_id,
            "message": (
                f"HITL approval required to delete event {event_id}. "
                f"Approval file written to {self.config.approval_dir}/calendar/."
            ),
        }

    def check_availability(
        self,
        calendar_id: Optional[str] = None,
        time_min: str = "",
        time_max: str = "",
    ) -> Dict[str, Any]:
        """Check free/busy status. No HITL required."""
        cal_id = calendar_id or self.config.default_calendar_id
        result = self.calendar_service.check_availability(cal_id, time_min, time_max)
        return {"success": True, **result}

    def execute_approved_operation(self, request_id: str) -> Dict[str, Any]:
        """
        Check if an approval request has been approved and execute the
        corresponding operation.
        """
        status, details = self.approval_manager.check_approval(request_id)

        if status == ApprovalStatus.PENDING:
            return {
                "success": False,
                "status": "pending",
                "message": "Operation is still awaiting approval.",
            }
        elif status == ApprovalStatus.REJECTED:
            return {
                "success": False,
                "status": "rejected",
                "message": "Operation was rejected by the approver.",
            }
        elif status == ApprovalStatus.EXPIRED:
            return {
                "success": False,
                "status": "expired",
                "message": "Approval request has expired.",
            }

        # status == APPROVED  -- execute the operation
        operation = details.get("operation", "")
        op_details = details.get("details", {})

        if operation == "create_event":
            event = self.calendar_service.create_event(
                calendar_id=op_details.get("calendar_id", "primary"),
                summary=op_details.get("summary", ""),
                start=op_details.get("start", ""),
                end=op_details.get("end", ""),
                description=op_details.get("description"),
                attendees=op_details.get("attendees"),
                location=op_details.get("location"),
                timezone_str=self.config.timezone,
            )
            return {"success": True, "status": "approved", "event": event}

        elif operation == "update_event":
            event = self.calendar_service.update_event(
                calendar_id=op_details.get("calendar_id", "primary"),
                event_id=op_details.get("event_id", ""),
                summary=op_details.get("summary"),
                start=op_details.get("start"),
                end=op_details.get("end"),
                description=op_details.get("description"),
                timezone_str=self.config.timezone,
            )
            return {"success": True, "status": "approved", "event": event}

        elif operation == "delete_event":
            self.calendar_service.delete_event(
                calendar_id=op_details.get("calendar_id", "primary"),
                event_id=op_details.get("event_id", ""),
            )
            return {
                "success": True,
                "status": "approved",
                "message": f"Event {op_details.get('event_id')} deleted.",
            }

        return {
            "success": False,
            "status": "error",
            "message": f"Unknown operation: {operation}",
        }

    # -- Internal helpers ---------------------------------------------------

    def _needs_create_approval(
        self, calendar_id: str, attendees: Optional[List[str]]
    ) -> bool:
        """Determine whether a create operation needs HITL approval."""
        # Personal events on the primary calendar with no attendees are auto-approved
        if (
            self.config.auto_approve_personal
            and calendar_id == "primary"
            and not attendees
        ):
            return False

        # Shared (non-primary) calendars always need approval
        if calendar_id != "primary":
            return True

        # External attendees need approval
        if attendees and self.config.organization_domains:
            for email in attendees:
                domain = email.split("@")[-1].lower()
                if domain not in self.config.organization_domains:
                    return True

        # If there are attendees but no org domains configured, require approval
        if attendees:
            return True

        return False


# ---------------------------------------------------------------------------
# FastMCP integration (optional native MCP transport)
# ---------------------------------------------------------------------------
def create_fastmcp_server(config: Optional[CalendarConfig] = None) -> "FastMCP":
    """Create a FastMCP server instance with all calendar tools registered."""
    if not FASTMCP_AVAILABLE:
        raise ImportError("FastMCP is not installed. Install with: pip install fastmcp")

    mcp = FastMCP("calendar-mcp-server")
    server = CalendarMCPServer(config=config)

    @mcp.tool()
    def list_events(
        calendar_id: str = "primary",
        time_min: str = "",
        time_max: str = "",
        max_results: int = 25,
    ) -> str:
        """List upcoming calendar events within a time range."""
        result = server.list_events(
            calendar_id=calendar_id or None,
            time_min=time_min or None,
            time_max=time_max or None,
            max_results=max_results,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def get_event(calendar_id: str = "primary", event_id: str = "") -> str:
        """Get details of a specific calendar event by its ID."""
        result = server.get_event(
            calendar_id=calendar_id or None, event_id=event_id
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def create_event(
        calendar_id: str = "primary",
        summary: str = "",
        start: str = "",
        end: str = "",
        description: str = "",
        attendees: str = "",
        location: str = "",
    ) -> str:
        """
        Create a new calendar event. HITL approval required for shared
        calendars or events with external attendees.

        Args:
            attendees: Comma-separated email addresses.
        """
        attendee_list = (
            [a.strip() for a in attendees.split(",") if a.strip()] if attendees else None
        )
        result = server.create_event(
            calendar_id=calendar_id or None,
            summary=summary,
            start=start,
            end=end,
            description=description or None,
            attendees=attendee_list,
            location=location or None,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def update_event(
        calendar_id: str = "primary",
        event_id: str = "",
        summary: str = "",
        start: str = "",
        end: str = "",
        description: str = "",
    ) -> str:
        """Update an existing calendar event. HITL approval is always required."""
        result = server.update_event(
            calendar_id=calendar_id or None,
            event_id=event_id,
            summary=summary or None,
            start=start or None,
            end=end or None,
            description=description or None,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def delete_event(calendar_id: str = "primary", event_id: str = "") -> str:
        """Delete a calendar event. HITL approval is always required."""
        result = server.delete_event(
            calendar_id=calendar_id or None, event_id=event_id
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def check_availability(
        calendar_id: str = "primary", time_min: str = "", time_max: str = ""
    ) -> str:
        """Check free/busy status for a calendar within a time range."""
        result = server.check_availability(
            calendar_id=calendar_id or None, time_min=time_min, time_max=time_max
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def execute_approved_operation(request_id: str = "") -> str:
        """Execute a previously approved calendar operation by its request ID."""
        result = server.execute_approved_operation(request_id)
        return json.dumps(result, indent=2, default=str)

    return mcp


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Calendar MCP Server")
    parser.add_argument(
        "--credentials",
        default=os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "credentials.json"),
        help="Path to Google OAuth credentials JSON file",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GOOGLE_CALENDAR_TOKEN", "calendar_token.json"),
        help="Path to store/load OAuth token",
    )
    parser.add_argument(
        "--approval-dir",
        default=os.getenv("CALENDAR_APPROVAL_DIR", "./Pending_Approval"),
        help="Directory for HITL approval files",
    )
    parser.add_argument(
        "--mode",
        choices=["fastmcp", "standalone"],
        default="fastmcp" if FASTMCP_AVAILABLE else "standalone",
        help="Server mode: fastmcp (native MCP) or standalone",
    )

    args = parser.parse_args()

    config = CalendarConfig(
        credentials_path=args.credentials,
        token_path=args.token,
        approval_dir=args.approval_dir,
    )

    if args.mode == "fastmcp":
        mcp = create_fastmcp_server(config)
        logger.info("Starting Calendar MCP Server in FastMCP mode")
        mcp.run()
    else:
        server = CalendarMCPServer(config=config)
        logger.info("Calendar MCP Server initialized in standalone mode")
        logger.info("Use CalendarMCPServer methods directly or integrate with your application.")

        # Quick self-test: attempt authentication
        try:
            server.calendar_service.authenticate()
            logger.info("Authentication successful. Server ready.")
        except Exception as exc:
            logger.error("Authentication failed: %s", exc)
            sys.exit(1)


if __name__ == "__main__":
    main()
