# LinkedIn Posting Automation Skill

## Overview
The LinkedIn Posting Automation skill implements automated, approval-gated LinkedIn posting capability as defined in Silver tier requirements. This skill provides a comprehensive system for creating, reviewing, approving, and publishing LinkedIn posts with proper governance and workflow controls.

## Features

### Automated Posting
- Scheduled post publishing with optimal timing
- Bulk post management and content calendar
- Auto-publishing capabilities with safety controls
- Rich media attachment support

### Approval Workflows
- Multi-level approval processes (editorial, compliance, legal)
- Role-based access controls and permissions
- Review and feedback cycles with audit trails
- Automated expiration and rejection of pending approvals

### Content Management
- Post template system with customizable fields
- Content library management with tagging and categorization
- Hashtag and keyword optimization
- Content moderation and compliance checking

### LinkedIn API Integration
- Official LinkedIn API integration with proper OAuth 2.0
- Post publishing and management capabilities
- Engagement tracking and analytics
- Profile and company page support

### Governance Controls
- Brand compliance checking and content guidelines enforcement
- Permission management and access controls
- Activity logging and monitoring
- Risk assessment and compliance validation

## Components

### Core Modules
- `linkedin_api_integration.py`: LinkedIn API integration and post management
- `approval_workflow.py`: Multi-level approval workflow engine
- `content_management.py`: Content creation, templates, and moderation
- `config_manager.py`: Configuration management system
- `SKILL.md`: Main skill documentation

### Reference Materials
- `references/usage_examples.md`: Comprehensive usage examples
- `assets/example_config.json`: Example configuration file
- `assets/requirements.txt`: Dependencies

### Test Suite
- `test_linkedin_posting_automation.py`: Comprehensive test suite

## Installation

### Prerequisites
```bash
pip install -r .claude/skills/linkedin-posting-automation/assets/requirements.txt
```

### LinkedIn App Setup
1. Create a LinkedIn App in the LinkedIn Developer Portal
2. Configure OAuth 2.0 with your redirect URI
3. Obtain your Client ID and Client Secret
4. Add required permissions (w_member_social, w_organization_social, rw_organization_admin)

## Usage

### Basic Setup
```python
from linkedin_posting_automation.scripts.config_manager import ConfigManager
from linkedin_posting_automation.scripts.linkedin_api_integration import LinkedInAPIIntegration, LinkedInPostManager
from linkedin_posting_automation.scripts.approval_workflow import create_approval_workflow_engine
from linkedin_posting_automation.scripts.content_management import create_content_manager

# Load configuration
config_manager = ConfigManager("./linkedin_config.json")
config = config_manager.config

# Initialize LinkedIn API
api_integration = LinkedInAPIIntegration(
    client_id=config.linkedin.oauth_client_id,
    client_secret=config.linkedin.oauth_client_secret,
    redirect_uri=config.linkedin.redirect_uri
)

# Complete OAuth flow (this requires user interaction)
auth_url = api_integration.initiate_oauth_flow()
print(f"Visit this URL to authorize: {auth_url}")

# After user authorizes, complete the flow with the code from the redirect
# authorization_code = "code_from_redirect"
# token = api_integration.complete_oauth_flow(authorization_code)

# Initialize managers
post_manager = LinkedInPostManager(api_integration)
workflow_engine = create_approval_workflow_engine()
content_manager = create_content_manager()
```

### Creating and Publishing Content
```python
# Create a content item
content_item = content_manager.create_content_item(
    title="Company Announcement",
    content="We're excited to announce our new product launch!",
    content_type=ContentType.POST,
    category=ContentCategory.ANNOUNCEMENTS,
    author="marketing_team",
    hashtags=["#ProductLaunch", "#Innovation", "#CompanyNews"]
)

# Submit for approval
approval_request = workflow_engine.create_approval_request(
    post_id=content_item.id,
    requested_by="marketing_team",
    required_levels=[ApprovalLevel.EDITORIAL, ApprovalLevel.COMPLIANCE],
    approvers_by_level={
        ApprovalLevel.EDITORIAL: ["editor1", "editor2"],
        ApprovalLevel.COMPLIANCE: ["compliance_officer"]
    }
)

# After approval, create and publish the post
if approval_request.status == ApprovalStatus.APPROVED:
    # Create LinkedIn post draft
    draft_post = post_manager.create_draft_post(
        author_urn="urn:li:organization:123456789",
        text=content_item.content,
        visibility="PUBLIC",
        hashtags=content_item.hashtags
    )

    # Publish the post
    published_post = post_manager.publish_approved_post(draft_post)
    print(f"Published post ID: {published_post.external_id}")
```

### Using Content Templates
```python
# Create a template for weekly updates
weekly_template = content_manager.create_content_template(
    name="Weekly Company Update",
    description="Template for weekly company updates",
    content_structure={
        "sections": ["headline", "highlights", "quote", "call_to_action"],
        "required_fields": ["week_number", "highlights", "quote"]
    },
    category=ContentCategory.NEWS,
    created_by="admin"
)

# Create content from template
weekly_update = content_manager.create_content_from_template(
    template_id=weekly_template.id,
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

### Content Moderation
```python
# The system automatically moderates content
moderation_result = content_manager.moderation_engine.evaluate_content(content_item)

if moderation_result.is_approved:
    print("Content passed moderation")
    # Submit for approval
    workflow_engine.create_approval_request(
        post_id=content_item.id,
        requested_by=content_item.author,
        required_levels=[ApprovalLevel.EDITORIAL]
    )
else:
    print("Content did not pass moderation")
    for violation in moderation_result.violations:
        print(f"  - {violation}")
```

## Configuration

### Default Configuration
The skill includes a default configuration with sensible defaults for most use cases. You can create a default configuration file:

```python
from linkedin_posting_automation.scripts.config_manager import create_default_config

create_default_config("./linkedin_config.json")
```

### Production Configuration
For production use, create a more restrictive configuration:

```python
from linkedin_posting_automation.scripts.config_manager import create_production_config

create_production_config("./production_linkedin_config.json")
```

## Security Considerations
- Secure OAuth 2.0 implementation with proper token management
- Encrypted credential storage (implement with environment variables)
- Role-based access controls for different approval levels
- Audit logging for all actions and content changes

## Performance Considerations
- Efficient API usage respecting LinkedIn's rate limits
- Caching for frequently accessed data
- Asynchronous processing for heavy operations
- Optimized database queries for content management

## Integration

### With Claude Code
- Integrate with existing workflows for automated content creation
- Use Claude for content generation and optimization
- Implement automated posting schedules

### With External Systems
- CMS integration for content import
- Analytics platform integration for performance tracking
- Notification systems for approval workflows

## Testing

The skill includes a comprehensive test suite that validates:
- Module imports and basic functionality
- Content management capabilities
- Approval workflow processes
- Configuration management
- Error handling

Run the tests with:
```bash
python test_linkedin_posting_automation.py
```

## Examples

For comprehensive examples of usage scenarios, see:
- `references/usage_examples.md` - Detailed usage examples
- Various content templates and approval workflows
- Integration examples with external systems
- Advanced customization scenarios