# Ticket Lifecycle Management Reference

## Ticket States and Transitions

### Ticket Status Enum

```python
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any

class TicketStatus(Enum):
    NEW = "new"                    # Just created, not yet assigned
    IN_PROGRESS = "in_progress"    # Assigned and being worked on
    WAITING_FOR_CUSTOMER = "waiting_for_customer"  # Waiting for customer response
    AWAITING_APPROVAL = "awaiting_approval"  # Awaiting customer approval for solution
    RESOLVED = "resolved"          # Issue is fixed but not yet confirmed by customer
    CLOSED = "closed"              # Fully closed, no further action needed
    REOPENED = "reopened"          # Previously closed ticket reopened due to ongoing issue

class TicketPriority(Enum):
    LOW = "low"        # Can be addressed when convenient
    MEDIUM = "medium"  # Standard priority
    HIGH = "high"      # Needs attention soon
    URGENT = "urgent"  # Critical issue requiring immediate attention
```

### Ticket State Transition Rules

```python
# Define valid state transitions
VALID_TRANSITIONS = {
    TicketStatus.NEW: [
        TicketStatus.IN_PROGRESS,
        TicketStatus.CLOSED  # If issue is immediately resolved
    ],
    TicketStatus.IN_PROGRESS: [
        TicketStatus.WAITING_FOR_CUSTOMER,
        TicketStatus.AWAITING_APPROVAL,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED
    ],
    TicketStatus.WAITING_FOR_CUSTOMER: [
        TicketStatus.IN_PROGRESS,  # Customer responded
        TicketStatus.CLOSED        # Customer indicated issue is resolved
    ],
    TicketStatus.AWAITING_APPROVAL: [
        TicketStatus.IN_PROGRESS,  # Customer rejected solution
        TicketStatus.RESOLVED,    # Customer approved solution
        TicketStatus.CLOSED       # Customer confirmed resolution
    ],
    TicketStatus.RESOLVED: [
        TicketStatus.CLOSED,      # Final closure
        TicketStatus.REOPENED     # Issue reoccurred
    ],
    TicketStatus.CLOSED: [
        TicketStatus.REOPENED     # Issue reoccurred after closure
    ],
    TicketStatus.REOPENED: [
        TicketStatus.IN_PROGRESS,
        TicketStatus.CLOSED
    ]
}
```

## Database Schema for Tickets

### Core Ticket Table

```sql
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    external_id VARCHAR(255), -- ID from external ticket system
    subject VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    priority VARCHAR(20) DEFAULT 'medium',
    category VARCHAR(100),
    subcategory VARCHAR(100),
    assigned_to UUID REFERENCES users(id),
    created_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    reopened_count INTEGER DEFAULT 0,
    first_resolved_at TIMESTAMP WITH TIME ZONE, -- When ticket was first resolved
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    sla_deadline TIMESTAMP WITH TIME ZONE, -- SLA deadline based on priority
    resolution_time_minutes INTEGER, -- Time from creation to resolution
    response_time_minutes INTEGER, -- Time to first response

    -- Full-text search
    tsvector_col TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(subject || ' ' || description, ''))
    ) STORED
);

-- Indexes for tickets
CREATE INDEX idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX idx_tickets_sla_deadline ON tickets(sla_deadline);
CREATE INDEX idx_tickets_tsvector ON tickets USING GIN(tsvector_col);
```

### Ticket Status Change History

```sql
CREATE TABLE ticket_status_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by VARCHAR(255), -- User ID or system identifier
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason VARCHAR(255), -- Reason for status change
    comment TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Index for status changes
CREATE INDEX idx_ticket_status_changes_ticket_id ON ticket_status_changes(ticket_id);
CREATE INDEX idx_ticket_status_changes_changed_at ON ticket_status_changes(changed_at DESC);
CREATE INDEX idx_ticket_status_changes_new_status ON ticket_status_changes(new_status);
```

### Ticket Activity Timeline

```sql
CREATE TABLE ticket_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL, -- 'comment', 'assignment', 'status_change', 'attachment', etc.
    actor_id VARCHAR(255) NOT NULL, -- User or system that performed action
    actor_role VARCHAR(50), -- 'customer', 'agent', 'system'
    content TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for activities
CREATE INDEX idx_ticket_activities_ticket_id ON ticket_activities(ticket_id);
CREATE INDEX idx_ticket_activities_created_at ON ticket_activities(created_at DESC);
CREATE INDEX idx_ticket_activities_actor_id ON ticket_activities(actor_id);
```

## Ticket Management Implementation

### Ticket Service Class

```python
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
import uuid

class TicketService:
    def __init__(self, db: Session):
        self.db = db

    def create_ticket(
        self,
        customer_id: uuid.UUID,
        subject: str,
        description: str,
        priority: TicketPriority = TicketPriority.MEDIUM,
        category: str = None,
        assigned_to: uuid.UUID = None,
        created_by: uuid.UUID = None,
        external_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> uuid.UUID:
        """
        Create a new ticket.
        """
        ticket_id = uuid.uuid4()

        # Calculate SLA deadline based on priority
        sla_deadline = self._calculate_sla_deadline(priority)

        # Insert ticket
        result = self.db.execute(
            text("""
            INSERT INTO tickets (
                id, customer_id, subject, description, priority,
                category, assigned_to, created_by, external_id,
                status, sla_deadline, metadata
            ) VALUES (
                :id, :customer_id, :subject, :description, :priority,
                :category, :assigned_to, :created_by, :external_id,
                'new', :sla_deadline, :metadata
            )
            """),
            {
                "id": ticket_id,
                "customer_id": customer_id,
                "subject": subject,
                "description": description,
                "priority": priority.value,
                "category": category,
                "assigned_to": assigned_to,
                "created_by": created_by,
                "external_id": external_id,
                "sla_deadline": sla_deadline,
                "metadata": metadata or {}
            }
        )

        # Log status change
        self._log_status_change(
            ticket_id, None, TicketStatus.NEW,
            changed_by=created_by or "system",
            reason="Ticket created"
        )

        # Log activity
        self._log_activity(
            ticket_id, "ticket_created", created_by or "system",
            "customer" if not created_by else "agent",
            f"Ticket created with subject: {subject}"
        )

        self.db.commit()
        return ticket_id

    def update_ticket_status(
        self,
        ticket_id: uuid.UUID,
        new_status: TicketStatus,
        changed_by: str,
        reason: str = None,
        comment: str = None
    ) -> bool:
        """
        Update ticket status with validation and audit logging.
        """
        # Get current ticket
        ticket = self.db.execute(
            text("SELECT status FROM tickets WHERE id = :ticket_id"),
            {"ticket_id": ticket_id}
        ).fetchone()

        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        current_status = TicketStatus(ticket.status)

        # Validate transition
        if new_status not in VALID_TRANSITIONS.get(current_status, []):
            raise ValueError(
                f"Invalid status transition: {current_status.value} -> {new_status.value}"
            )

        # Update ticket
        update_fields = ["updated_at = NOW()"]
        params = {"ticket_id": ticket_id}

        if new_status == TicketStatus.RESOLVED and current_status != TicketStatus.RESOLVED:
            # First time resolving this ticket
            update_fields.append("resolved_at = NOW()")
            if not self.db.execute(
                text("SELECT first_resolved_at FROM tickets WHERE id = :ticket_id"),
                {"ticket_id": ticket_id}
            ).fetchone().first_resolved_at:
                update_fields.append("first_resolved_at = NOW()")
        elif new_status == TicketStatus.CLOSED and current_status != TicketStatus.CLOSED:
            update_fields.append("closed_at = NOW()")
        elif new_status == TicketStatus.REOPENED:
            update_fields.append("reopened_count = COALESCE(reopened_count, 0) + 1")
            update_fields.append("resolved_at = NULL")
            update_fields.append("closed_at = NULL")

        # Update status
        update_fields.append("status = :new_status")
        params["new_status"] = new_status.value

        self.db.execute(
            text(f"UPDATE tickets SET {', '.join(update_fields)} WHERE id = :ticket_id"),
            params
        )

        # Log status change
        self._log_status_change(
            ticket_id, current_status, new_status,
            changed_by=changed_by,
            reason=reason,
            comment=comment
        )

        # Log activity
        activity_content = f"Status changed from {current_status.value} to {new_status.value}"
        if reason:
            activity_content += f". Reason: {reason}"
        if comment:
            activity_content += f". Comment: {comment}"

        self._log_activity(
            ticket_id, "status_change", changed_by,
            "agent" if "@" in changed_by else "system",
            activity_content
        )

        self.db.commit()
        return True

    def assign_ticket(
        self,
        ticket_id: uuid.UUID,
        assigned_to: uuid.UUID,
        assigned_by: str,
        comment: str = None
    ) -> bool:
        """
        Assign a ticket to an agent.
        """
        self.db.execute(
            text("UPDATE tickets SET assigned_to = :assigned_to, updated_at = NOW() WHERE id = :ticket_id"),
            {"assigned_to": assigned_to, "ticket_id": ticket_id}
        )

        # Log activity
        self._log_activity(
            ticket_id, "assignment", assigned_by, "agent",
            f"Ticket assigned to agent {assigned_to}",
            metadata={"assigned_to": str(assigned_to)}
        )

        if comment:
            self.add_comment(ticket_id, assigned_by, comment)

        self.db.commit()
        return True

    def add_comment(
        self,
        ticket_id: uuid.UUID,
        author_id: str,
        content: str,
        author_role: str = "agent"
    ) -> uuid.UUID:
        """
        Add a comment to a ticket.
        """
        comment_id = uuid.uuid4()

        self.db.execute(
            text("""
            INSERT INTO ticket_activities (
                id, ticket_id, activity_type, actor_id, actor_role, content
            ) VALUES (
                :id, :ticket_id, 'comment', :actor_id, :actor_role, :content
            )
            """),
            {
                "id": comment_id,
                "ticket_id": ticket_id,
                "actor_id": author_id,
                "actor_role": author_role,
                "content": content
            }
        )

        self.db.commit()
        return comment_id

    def get_ticket_timeline(self, ticket_id: uuid.UUID) -> List[Dict]:
        """
        Get complete timeline of ticket activities.
        """
        # Get status changes
        status_changes = self.db.execute(
            text("""
            SELECT
                changed_at,
                CONCAT('Status changed from ', COALESCE(old_status, 'NULL'), ' to ', new_status) as activity,
                changed_by,
                'system' as role,
                reason,
                comment
            FROM ticket_status_changes
            WHERE ticket_id = :ticket_id
            ORDER BY changed_at ASC
            """),
            {"ticket_id": ticket_id}
        ).fetchall()

        # Get other activities
        activities = self.db.execute(
            text("""
            SELECT
                created_at,
                content as activity,
                actor_id as changed_by,
                actor_role as role,
                NULL as reason,
                NULL as comment
            FROM ticket_activities
            WHERE ticket_id = :ticket_id
            ORDER BY created_at ASC
            """),
            {"ticket_id": ticket_id}
        ).fetchall()

        # Combine and sort
        all_events = []
        for event in status_changes:
            all_events.append({
                "timestamp": event.changed_at,
                "activity": event.activity,
                "actor": event.changed_by,
                "role": event.role,
                "reason": event.reason,
                "comment": event.comment
            })

        for event in activities:
            all_events.append({
                "timestamp": event.created_at,
                "activity": event.activity,
                "actor": event.changed_by,
                "role": event.role,
                "reason": None,
                "comment": None
            })

        # Sort by timestamp
        all_events.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_events

    def _log_status_change(
        self,
        ticket_id: uuid.UUID,
        old_status: Optional[TicketStatus],
        new_status: TicketStatus,
        changed_by: str,
        reason: str = None,
        comment: str = None
    ):
        """
        Log a status change to the audit trail.
        """
        self.db.execute(
            text("""
            INSERT INTO ticket_status_changes (
                ticket_id, old_status, new_status, changed_by, reason, comment
            ) VALUES (
                :ticket_id, :old_status, :new_status, :changed_by, :reason, :comment
            )
            """),
            {
                "ticket_id": ticket_id,
                "old_status": old_status.value if old_status else None,
                "new_status": new_status.value,
                "changed_by": changed_by,
                "reason": reason,
                "comment": comment
            }
        )

    def _log_activity(
        self,
        ticket_id: uuid.UUID,
        activity_type: str,
        actor_id: str,
        actor_role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ):
        """
        Log an activity to the ticket timeline.
        """
        self.db.execute(
            text("""
            INSERT INTO ticket_activities (
                ticket_id, activity_type, actor_id, actor_role, content, metadata
            ) VALUES (
                :ticket_id, :activity_type, :actor_id, :actor_role, :content, :metadata
            )
            """),
            {
                "ticket_id": ticket_id,
                "activity_type": activity_type,
                "actor_id": actor_id,
                "actor_role": actor_role,
                "content": content,
                "metadata": metadata or {}
            }
        )

    def _calculate_sla_deadline(self, priority: TicketPriority) -> datetime:
        """
        Calculate SLA deadline based on priority.
        """
        from datetime import timedelta

        sla_times = {
            TicketPriority.URGENT: timedelta(hours=4),
            TicketPriority.HIGH: timedelta(hours=24),
            TicketPriority.MEDIUM: timedelta(days=3),
            TicketPriority.LOW: timedelta(days=7)
        }

        return datetime.utcnow() + sla_times[priority]
```

## Ticket Lifecycle Automation

### SLA Monitoring

```python
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

class SLAMonitor:
    def __init__(self, db: Session):
        self.db = db

    def get_overdue_tickets(self) -> List[Dict]:
        """
        Get tickets that have exceeded their SLA deadline.
        """
        overdue_tickets = self.db.execute(
            text("""
            SELECT
                t.id,
                t.subject,
                t.priority,
                t.status,
                t.sla_deadline,
                t.customer_id,
                t.assigned_to,
                EXTRACT(EPOCH FROM (NOW() - t.sla_deadline))/3600 as hours_overdue
            FROM tickets t
            WHERE t.sla_deadline < NOW()
              AND t.status NOT IN ('resolved', 'closed')
            ORDER BY t.sla_deadline ASC
            """)
        ).fetchall()

        return [
            {
                "ticket_id": ticket.id,
                "subject": ticket.subject,
                "priority": ticket.priority,
                "status": ticket.status,
                "sla_deadline": ticket.sla_deadline,
                "hours_overdue": ticket.hours_overdue,
                "customer_id": ticket.customer_id,
                "assigned_to": ticket.assigned_to
            }
            for ticket in overdue_tickets
        ]

    def get_approaching_sla_tickets(self, hours: int = 2) -> List[Dict]:
        """
        Get tickets that are approaching their SLA deadline.
        """
        threshold_time = datetime.utcnow() + timedelta(hours=hours)

        approaching_tickets = self.db.execute(
            text("""
            SELECT
                t.id,
                t.subject,
                t.priority,
                t.status,
                t.sla_deadline,
                t.customer_id,
                t.assigned_to,
                EXTRACT(EPOCH FROM (t.sla_deadline - NOW()))/3600 as hours_remaining
            FROM tickets t
            WHERE t.sla_deadline BETWEEN NOW() AND :threshold_time
              AND t.status NOT IN ('resolved', 'closed')
            ORDER BY t.sla_deadline ASC
            """),
            {"threshold_time": threshold_time}
        ).fetchall()

        return [
            {
                "ticket_id": ticket.id,
                "subject": ticket.subject,
                "priority": ticket.priority,
                "status": ticket.status,
                "sla_deadline": ticket.sla_deadline,
                "hours_remaining": ticket.hours_remaining,
                "customer_id": ticket.customer_id,
                "assigned_to": ticket.assigned_to
            }
            for ticket in approaching_tickets
        ]
```

### Ticket Aging and Escalation

```python
class TicketEscalationService:
    def __init__(self, db: Session, ticket_service: TicketService):
        self.db = db
        self.ticket_service = ticket_service

    def run_escalation_checks(self):
        """
        Run periodic escalation checks for tickets.
        """
        # Escalate high-priority tickets that haven't been assigned
        self._escalate_unassigned_high_priority_tickets()

        # Escalate overdue tickets
        self._escalate_overdue_tickets()

        # Escalate tickets waiting for customer too long
        self._escalate_long_waiting_tickets()

    def _escalate_unassigned_high_priority_tickets(self):
        """
        Escalate high-priority tickets that remain unassigned.
        """
        unassigned_tickets = self.db.execute(
            text("""
            SELECT id, priority, created_at
            FROM tickets
            WHERE assigned_to IS NULL
              AND status = 'new'
              AND priority IN ('high', 'urgent')
              AND created_at < NOW() - INTERVAL '2 hours'
            """)
        ).fetchall()

        for ticket in unassigned_tickets:
            # Auto-assign to next available agent or escalate to supervisor
            self._auto_assign_ticket(ticket.id)
            self.ticket_service.add_comment(
                ticket.id,
                "system",
                f"Ticket escalated: remained unassigned for more than 2 hours. Auto-assigned.",
                "system"
            )

    def _escalate_overdue_tickets(self):
        """
        Escalate overdue tickets to supervisors.
        """
        monitor = SLAMonitor(self.db)
        overdue_tickets = monitor.get_overdue_tickets()

        for ticket_data in overdue_tickets:
            # Add escalation comment
            self.ticket_service.add_comment(
                ticket_data["ticket_id"],
                "system",
                f"SLA deadline exceeded by {ticket_data['hours_overdue']:.1f} hours. Escalating to supervisor.",
                "system"
            )

            # Potentially reassign to supervisor or escalate channel
            self._escalate_to_supervisor(ticket_data["ticket_id"])

    def _escalate_long_waiting_tickets(self):
        """
        Escalate tickets waiting for customer response for too long.
        """
        long_waiting_tickets = self.db.execute(
            text("""
            SELECT id, status, updated_at
            FROM tickets
            WHERE status = 'waiting_for_customer'
              AND updated_at < NOW() - INTERVAL '7 days'
            """)
        ).fetchall()

        for ticket in long_waiting_tickets:
            self.ticket_service.add_comment(
                ticket.id,
                "system",
                "Customer response awaited for 7+ days. Closing ticket due to inactivity.",
                "system"
            )
            self.ticket_service.update_ticket_status(
                ticket.id,
                TicketStatus.CLOSED,
                "system",
                "Closed due to customer inactivity"
            )
```

## Reporting and Analytics

### Ticket Metrics

```python
from datetime import datetime, timedelta
from typing import Dict, List

class TicketAnalytics:
    def __init__(self, db: Session):
        self.db = db

    def get_ticket_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Get comprehensive ticket metrics for a date range.
        """
        metrics = {}

        # Total tickets created
        total_created = self.db.execute(
            text("""
            SELECT COUNT(*) as count
            FROM tickets
            WHERE created_at BETWEEN :start_date AND :end_date
            """),
            {"start_date": start_date, "end_date": end_date}
        ).fetchone().count

        # Tickets by status
        status_counts = self.db.execute(
            text("""
            SELECT status, COUNT(*) as count
            FROM tickets
            WHERE created_at BETWEEN :start_date AND :end_date
            GROUP BY status
            """),
            {"start_date": start_date, "end_date": end_date}
        ).fetchall()

        # Tickets by priority
        priority_counts = self.db.execute(
            text("""
            SELECT priority, COUNT(*) as count
            FROM tickets
            WHERE created_at BETWEEN :start_date AND :end_date
            GROUP BY priority
            """),
            {"start_date": start_date, "end_date": end_date}
        ).fetchall()

        # Average resolution time
        avg_resolution_time = self.db.execute(
            text("""
            SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/3600) as avg_hours
            FROM tickets
            WHERE created_at BETWEEN :start_date AND :end_date
              AND resolved_at IS NOT NULL
            """),
            {"start_date": start_date, "end_date": end_date}
        ).fetchone().avg_hours

        # SLA compliance
        sla_compliance = self.db.execute(
            text("""
            SELECT
                COUNT(*) as total_resolved,
                COUNT(CASE WHEN resolved_at <= sla_deadline THEN 1 END) as within_sla
            FROM tickets
            WHERE created_at BETWEEN :start_date AND :end_date
              AND resolved_at IS NOT NULL
              AND sla_deadline IS NOT NULL
            """),
            {"start_date": start_date, "end_date": end_date}
        ).fetchone()

        metrics.update({
            "total_created": total_created,
            "status_distribution": {row.status: row.count for row in status_counts},
            "priority_distribution": {row.priority: row.count for row in priority_counts},
            "average_resolution_time_hours": avg_resolution_time or 0,
            "sla_compliance_rate": (
                sla_compliance.within_sla / sla_compliance.total_resolved * 100
                if sla_compliance.total_resolved > 0 else 0
            ),
            "sla_compliance_details": {
                "within_sla": sla_compliance.within_sla,
                "total_resolved": sla_compliance.total_resolved
            }
        })

        return metrics

    def get_agent_performance(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get agent performance metrics.
        """
        agent_stats = self.db.execute(
            text("""
            SELECT
                assigned_to,
                COUNT(*) as tickets_assigned,
                COUNT(CASE WHEN status = 'resolved' THEN 1 END) as tickets_resolved,
                COUNT(CASE WHEN status = 'closed' THEN 1 END) as tickets_closed,
                AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/3600) as avg_resolution_time
            FROM tickets
            WHERE assigned_to IS NOT NULL
              AND created_at BETWEEN :start_date AND :end_date
            GROUP BY assigned_to
            """),
            {"start_date": start_date, "end_date": end_date}
        ).fetchall()

        return [
            {
                "agent_id": stat.assigned_to,
                "tickets_assigned": stat.tickets_assigned,
                "tickets_resolved": stat.tickets_resolved,
                "tickets_closed": stat.tickets_closed,
                "average_resolution_time_hours": stat.avg_resolution_time or 0
            }
            for stat in agent_stats
        ]
```

This comprehensive ticket lifecycle management system provides full visibility into ticket status, automated SLA monitoring, escalation procedures, and detailed analytics for performance tracking.