# LinkedIn Posting Automation - Usage Examples

## Overview
This document provides practical examples of how to use the LinkedIn Posting Automation skill for creating, reviewing, approving, and publishing LinkedIn posts with proper governance and workflow controls.

## Installation and Setup

### Prerequisites
```bash
pip install requests-oauthlib linkedin-api-client celery redis sqlalchemy
```

### Basic Initialization
```python
from linkedin_posting_automation.scripts.linkedin_api_integration import LinkedInAPIIntegration, LinkedInPostManager
from linkedin_posting_automation.scripts.approval_workflow import ApprovalWorkflowEngine, create_approval_workflow_engine
from linkedin_posting_automation.scripts.content_management import ContentManager, create_content_manager
from linkedin_posting_automation.scripts.config_manager import get_config_manager

# Load configuration
config_manager = get_config_manager("./linkedin_config.json")
config = config_manager.config

# Initialize LinkedIn API integration
api_integration = LinkedInAPIIntegration(
    client_id=config.linkedin.oauth_client_id,
    client_secret=config.linkedin.oauth_client_secret,
    redirect_uri=config.linkedin.redirect_uri,
    scopes=config.linkedin.scopes
)

# Initialize managers
post_manager = LinkedInPostManager(api_integration)
workflow_engine = create_approval_workflow_engine()
content_manager = create_content_manager()
```

## Basic Usage Examples

### Setting Up LinkedIn API Connection
```python
# Get authorization URL
auth_url = api_integration.initiate_oauth_flow()
print(f"Visit this URL to authorize: {auth_url}")

# After user authorizes, complete the flow with the code from the redirect
# authorization_code = "code_from_redirect"
# token = api_integration.complete_oauth_flow(authorization_code)

# Or set token directly if already obtained
api_integration.set_access_token("your_access_token_here")
```

### Creating and Managing Content

#### Creating a Content Item
```python
from linkedin_posting_automation.scripts.content_management import ContentCategory

# Create a content item
content_item = content_manager.create_content_item(
    title="Weekly Tech Insights",
    content="Here are this week's key technology trends that are shaping our industry...",
    content_type=ContentType.POST,
    category=ContentCategory.INSIGHTS,
    author="marketing_team",
    hashtags=["#Tech", "#Innovation", "#AI"]
)

if content_item:
    print(f"Content created with ID: {content_item.id}")
```

#### Creating Content from Template
```python
# Create a template for weekly updates
template = content_manager.create_content_template(
    name="Weekly Update Template",
    description="Template for weekly company updates",
    content_structure={
        "sections": ["headline", "summary", "key_points", "call_to_action"],
        "required_fields": ["week_number", "highlights", "quote"]
    },
    category=ContentCategory.NEWS,
    created_by="admin"
)

# Create content from template
weekly_update = content_manager.create_content_from_template(
    template_id=template.id,
    fill_data={
        "week_number": "42",
        "headline": "This Week in Review",
        "highlights": "Major milestone reached in our Q4 goals",
        "quote": "Innovation distinguishes between a leader and a follower.",
        "hashtags": ["#WeeklyUpdate", "#CompanyNews"]
    },
    author="comms_team",
    title="Weekly Update: October 16-20"
)
```

### Approval Workflow Examples

#### Submitting Content for Approval
```python
from linkedin_posting_automation.scripts.approval_workflow import ApprovalLevel, UserRole

# Submit content for approval
approval_request = workflow_engine.create_approval_request(
    post_id=content_item.id,
    requested_by="author_1",
    required_levels=[ApprovalLevel.EDITORIAL, ApprovalLevel.COMPLIANCE],
    approvers_by_level={
        ApprovalLevel.EDITORIAL: ["editor_1", "editor_2"],
        ApprovalLevel.COMPLIANCE: ["compliance_officer_1"]
    }
)

if approval_request:
    print(f"Approval request created: {approval_request.id}")
```

#### Getting and Processing Approval Requests
```python
# Get pending approvals for a specific user
pending_approvals = workflow_engine.get_pending_approvals_for_user(
    user_id="editor_1",
    role=UserRole.CONTENT_EDITOR
)

print(f"Found {len(pending_approvals)} pending approvals")

# Process each approval
for approval in pending_approvals:
    print(f"Reviewing: {approval.post_id}")

    # Review the content (in a real implementation, this would be more thorough)
    # For this example, we'll approve it
    approved = workflow_engine.submit_approval_step(
        request_id=approval.id,
        user_id="editor_1",
        step_id=approval.steps[0].id,  # First step
        action="approve",
        feedback="Content looks good and follows brand guidelines"
    )

    if approved:
        print(f"Approved step for request {approval.id}")
    else:
        print(f"Failed to approve step for request {approval.id}")
```

### Post Creation and Publishing

#### Creating a Draft Post
```python
# Get current user profile to use as author
profile = api_integration.get_current_profile()

# Create a draft post
draft_post = post_manager.create_draft_post(
    author_urn=profile.urn,
    text="Join us for our upcoming webinar on digital transformation!",
    visibility="PUBLIC",
    media_files=["path/to/webinar-image.png"],  # Optional media
    scheduled_time=None  # Publish immediately, or set a future time
)

print(f"Draft post created: {draft_post.id}")
```

#### Submitting for Approval
```python
# Submit the draft for approval
submitted_post = post_manager.submit_for_approval(draft_post)
print(f"Post submitted for approval: {submitted_post.id}")
```

#### Publishing Approved Posts
```python
# Approve the post
approved_post = post_manager.approve_post(submitted_post)
print(f"Post approved: {approved_post.id}")

# Publish the approved post
published_post = post_manager.publish_approved_post(approved_post)
print(f"Post published with LinkedIn ID: {published_post.external_id}")
```

### Scheduled Posting
```python
from datetime import datetime, timedelta

# Create a post scheduled for next Tuesday at 9 AM
next_tuesday = datetime.now() + timedelta(days=((7 - datetime.now().weekday()) % 7) + 2)
next_tuesday = next_tuesday.replace(hour=9, minute=0, second=0, microsecond=0)

scheduled_draft = post_manager.create_draft_post(
    author_urn=profile.urn,
    text="Exciting news coming next week!",
    visibility="PUBLIC",
    scheduled_time=next_tuesday
)

# Submit for approval
submitted_scheduled = post_manager.submit_for_approval(scheduled_draft)

# Approve and schedule
approved_scheduled = post_manager.approve_post(submitted_scheduled)
scheduled_post = post_manager.publish_approved_post(approved_scheduled)

print(f"Scheduled post will publish on: {scheduled_post.scheduled_time}")
```

## Advanced Usage Examples

### Content Moderation
```python
from linkedin_posting_automation.scripts.content_management import ContentModerationEngine

# Create moderation engine
moderation_engine = ContentManager().moderation_engine

# Evaluate content
content_to_check = "This is a sample post content that needs moderation."

result = moderation_engine.evaluate_content(content_to_check)

if result.is_approved:
    print("Content passed moderation")
    for suggestion in result.suggestions:
        print(f"Suggestion: {suggestion}")
else:
    print("Content did not pass moderation")
    for violation in result.violations:
        print(f"Violation: {violation}")
```

### Bulk Operations
```python
# Create multiple content items
content_items = []
for i in range(5):
    item = content_manager.create_content_item(
        title=f"Bulk Post {i+1}",
        content=f"This is bulk post number {i+1} with some engaging content.",
        content_type=ContentType.POST,
        category=ContentCategory.NEWS,
        author="bulk_publisher",
        hashtags=["#Bulk", "#Automation"]
    )
    if item:
        content_items.append(item)

print(f"Created {len(content_items)} bulk content items")

# Submit all for approval
approval_requests = []
for item in content_items:
    request = workflow_engine.create_approval_request(
        post_id=item.id,
        requested_by="bulk_submitter",
        required_levels=[ApprovalLevel.EDITORIAL],
        approvers_by_level={ApprovalLevel.EDITORIAL: ["editor_1"]}
    )
    if request:
        approval_requests.append(request)

print(f"Submitted {len(approval_requests)} for approval")
```

### Content Calendar and Scheduling
```python
from datetime import datetime, timedelta

# Get content calendar for next 30 days
start_date = datetime.now()
end_date = start_date + timedelta(days=30)

calendar_items = content_manager.get_content_calendar(start_date, end_date)
print(f"Calendar has {len(calendar_items)} scheduled items:")

for item in calendar_items:
    print(f"  {item.scheduled_for}: {item.title}")

# Search for specific content
search_results = content_manager.search_content("innovation")
print(f"Found {len(search_results)} items matching 'innovation'")
```

### Multi-Level Approval Workflow
```python
# Create a complex approval workflow with multiple levels
complex_approval = workflow_engine.create_approval_request(
    post_id=content_item.id,
    requested_by="content_creator",
    required_levels=[
        ApprovalLevel.EDITORIAL,    # First editorial review
        ApprovalLevel.COMPLIANCE,   # Then compliance review
        ApprovalLevel.LEGAL         # Finally legal review
    ],
    approvers_by_level={
        ApprovalLevel.EDITORIAL: ["senior_editor"],
        ApprovalLevel.COMPLIANCE: ["compliance_manager"],
        ApprovalLevel.LEGAL: ["legal_counsel"]
    }
)

print(f"Complex approval workflow created with ID: {complex_approval.id}")

# Each level must approve before the next
# Editorial approves first
workflow_engine.submit_approval_step(
    request_id=complex_approval.id,
    user_id="senior_editor",
    step_id=complex_approval.steps[0].id,
    action="approve",
    feedback="Editorial review complete"
)

# Then compliance approves
workflow_engine.submit_approval_step(
    request_id=complex_approval.id,
    user_id="compliance_manager",
    step_id=complex_approval.steps[1].id,
    action="approve",
    feedback="Compliance review complete"
)

# Finally legal approves
workflow_engine.submit_approval_step(
    request_id=complex_approval.id,
    user_id="legal_counsel",
    step_id=complex_approval.steps[2].id,
    action="approve",
    feedback="Legal review complete"
)

print("All approval levels completed successfully")
```

### Integration with External Systems
```python
# Example of integrating with a CMS or external content system
def sync_external_content():
    """Sync content from an external system"""
    # This would typically connect to an external CMS, blog platform, etc.
    external_content = get_content_from_external_system()

    for content in external_content:
        # Create content item in our system
        content_item = content_manager.create_content_item(
            title=content.get('title', ''),
            content=content.get('body', ''),
            content_type=ContentType.ARTICLE,
            category=ContentCategory.EDUCATIONAL,
            author=content.get('author', 'external_system'),
            hashtags=content.get('tags', [])
        )

        if content_item:
            # Submit for approval automatically
            workflow_engine.create_approval_request(
                post_id=content_item.id,
                requested_by="cms_sync_bot",
                required_levels=[ApprovalLevel.EDITORIAL],
                approvers_by_level={ApprovalLevel.EDITORIAL: ["editor_1"]}
            )

            print(f"Synced and submitted {content_item.title} for approval")

# Example function to get content from external system
def get_content_from_external_system():
    """Mock function to represent getting content from external system"""
    return [
        {
            'title': 'External Article 1',
            'body': 'This is content from an external system.',
            'author': 'external_author',
            'tags': ['#External', '#Integration']
        }
    ]
```

### Error Handling and Monitoring
```python
# Example of proper error handling
def safe_post_publication(post_data):
    """Safely create and publish a post with proper error handling"""
    try:
        # Create draft
        profile = api_integration.get_current_profile()
        draft_post = post_manager.create_draft_post(
            author_urn=profile.urn,
            text=post_data['content'],
            visibility=post_data.get('visibility', 'PUBLIC'),
            scheduled_time=post_data.get('scheduled_time')
        )

        # Submit for approval
        submitted_post = post_manager.submit_for_approval(draft_post)

        # Check moderation
        mod_result = content_manager.moderation_engine.evaluate_content(submitted_post.text)
        if not mod_result.is_approved:
            print(f"Content failed moderation: {mod_result.violations}")
            return None

        # Approve if it passes moderation
        approved_post = post_manager.approve_post(submitted_post)

        # Publish
        published_post = post_manager.publish_approved_post(approved_post)

        print(f"Successfully published post: {published_post.external_id}")
        return published_post

    except Exception as e:
        print(f"Error in post publication: {str(e)}")
        # In a real implementation, you'd log this properly and possibly retry
        return None

# Usage
result = safe_post_publication({
    'content': 'This is a carefully crafted post that follows all guidelines.',
    'visibility': 'PUBLIC'
})
```

## Configuration Examples

### Custom Configuration Loading
```python
from linkedin_posting_automation.scripts.config_manager import ConfigManager

# Load custom configuration
config_manager = ConfigManager("./custom_linkedin_config.json")
custom_config = config_manager.config

# Access specific configuration sections
linkedin_config = config_manager.get_linkedin_config()
approval_config = config_manager.get_approval_config()
posting_config = config_manager.get_posting_config()
```

### Environment-Specific Configuration
```python
import os

# Load configuration based on environment
env = os.getenv("ENVIRONMENT", "development")
config_file = f"./linkedin_config_{env.lower()}.json"

config_manager = ConfigManager(config_file)
config = config_manager.config

print(f"Loaded {env} configuration")
```

These examples demonstrate the comprehensive capabilities of the LinkedIn Posting Automation skill for creating, reviewing, approving, and publishing LinkedIn posts with proper governance and workflow controls.