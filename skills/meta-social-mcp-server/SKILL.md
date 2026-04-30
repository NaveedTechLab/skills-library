---
name: meta-social-mcp-server
description: Integrate with Facebook and Instagram APIs via MCP to create, schedule, and manage social posts with human-in-the-loop approval workflows. Use when automating Meta platform social media management.
---

# Meta Social MCP Server

## Description
The Meta Social MCP Server provides Model Context Protocol integration with Facebook and Instagram APIs (Graph API v21), enabling Claude Code to create, schedule, and manage social media posts with HITL (Human-in-the-Loop) approval workflows.

## Purpose
This skill enables Claude Code to manage Facebook Pages and Instagram Business accounts while maintaining strict content approval workflows. All posting operations require human approval before publication.

## Key Features

### Facebook Operations
- List managed pages
- Create page posts (text, image, video)
- Schedule posts for future publication
- Get page insights and engagement metrics
- Manage comments and reactions

### Instagram Operations
- Create feed posts (image, carousel)
- Create Reels
- Get insights and metrics
- Manage comments

### Human-in-the-Loop Controls
| Operation | HITL Required |
|-----------|---------------|
| List pages/accounts | No |
| Get insights | No |
| Create post | Yes |
| Schedule post | Yes |
| Create Reel | Yes |

### Content Approval
- Multi-level approval workflow
- Content preview before posting
- Brand safety checks
- Scheduling validation

## Configuration

### Environment Variables
```bash
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_ACCESS_TOKEN=your_long_lived_token
META_PAGE_ID=your_page_id
META_INSTAGRAM_ACCOUNT_ID=your_ig_account_id
```

### Default Configuration
```json
{
  "meta": {
    "app_id": "",
    "app_secret": "",
    "access_token": "",
    "page_id": "",
    "instagram_account_id": "",
    "api_version": "v21.0",
    "timeout_seconds": 30
  },
  "approval": {
    "require_approval_for_posts": true,
    "require_approval_for_reels": true,
    "approval_timeout_hours": 48,
    "allowed_post_times": ["09:00-21:00"]
  },
  "content": {
    "max_text_length": 63206,
    "max_hashtags": 30,
    "max_images_carousel": 10,
    "supported_image_formats": ["jpg", "jpeg", "png", "gif"],
    "max_video_size_mb": 1024
  }
}
```

## MCP Tools

### facebook_list_pages
List all Facebook pages the user manages.

**HITL:** Not required

### facebook_create_post
Create a post on a Facebook page.

**Parameters:**
- `page_id` (string): Facebook Page ID
- `message` (string): Post text
- `link` (string, optional): URL to share
- `media_urls` (array, optional): Image/video URLs

**HITL:** Required

### facebook_schedule_post
Schedule a post for future publication.

**Parameters:**
- `page_id` (string): Facebook Page ID
- `message` (string): Post text
- `scheduled_time` (string): ISO datetime for publication
- `media_urls` (array, optional): Image/video URLs

**HITL:** Required

### facebook_get_insights
Get engagement metrics for a page or post.

**Parameters:**
- `page_id` (string): Facebook Page ID
- `metrics` (array): Metrics to retrieve
- `date_preset` (string): Time range

**HITL:** Not required

### instagram_create_post
Create a post on Instagram.

**Parameters:**
- `account_id` (string): Instagram Business Account ID
- `caption` (string): Post caption
- `media_url` (string): Image URL
- `location_id` (string, optional): Location tag

**HITL:** Required

### instagram_create_reel
Create an Instagram Reel.

**Parameters:**
- `account_id` (string): Instagram Business Account ID
- `video_url` (string): Video URL
- `caption` (string): Reel caption
- `share_to_feed` (bool): Also share to feed

**HITL:** Required

### instagram_get_insights
Get Instagram account or media insights.

**Parameters:**
- `account_id` (string): Instagram Business Account ID
- `metrics` (array): Metrics to retrieve

**HITL:** Not required

## Usage Scenarios

### Create Facebook Post
```python
# Create post with approval
result = await facebook_create_post(
    page_id="123456789",
    message="Check out our latest product launch!",
    media_urls=["https://example.com/image.jpg"]
)

# Result will include approval_request_id
# Human must approve before posting
```

### Schedule Instagram Post
```python
# Schedule post for tomorrow
result = await instagram_create_post(
    account_id="987654321",
    caption="Morning motivation! #inspired #goodvibes",
    media_url="https://example.com/photo.jpg",
    scheduled_time="2024-01-16T09:00:00Z"
)
```

## Integration Points

### With Vault System
- `/vault/Pending_Approval/meta/` for pending posts
- `/vault/Approved/meta/` for approved content
- `/vault/Rejected/meta/` for rejected content

### With Audit Logger
All operations logged with:
- Platform (Facebook/Instagram)
- Operation type
- Content hash (for tracking)
- Approval status

### With Safety Enforcer
- COMMUNICATION_SEND boundary
- Brand safety content checks

## Database Schema
Reuses LinkedIn pattern:
- `meta_content` table for post drafts
- `meta_approvals` table for approval workflow

## Rate Limits
- Facebook Pages API: 200 calls/hour
- Instagram Graph API: 200 calls/hour
- Content Publishing: 25 posts/day per page

## Security Considerations
- Long-lived access tokens stored securely
- Token refresh handling
- Sensitive data masking in logs
- Content moderation integration

## Dependencies
- `httpx` for async HTTP
- `fastmcp` for MCP server
- `pydantic` for validation
- Integration with phase-3 audit_logger
- Integration with phase-3 safety_enforcer

## When NOT to Use This Skill

- **Personal Facebook profiles** — Meta's Graph API is for Pages and Business accounts; personal profile automation violates Meta's terms of service
- **Emergency or crisis communications** — automated social posting during a crisis can compound damage; always have a human manage communications in real-time during incidents
- **High-frequency posting (more than 3-5 posts/day)** — over-posting on Meta platforms triggers spam detection and reduces organic reach

## Common Mistakes

- Using short-lived user access tokens instead of long-lived page tokens — short-lived tokens expire after 1 hour; generate long-lived tokens (60 days) for automation
- Not testing on a staging page before posting to the main brand page — always validate content and formatting on a test page first
- Posting media without pre-uploading via the resumable upload API — large media files posted inline fail silently on slow connections; use resumable uploads

## Related Skills

- [`twitter-mcp-server`](../twitter-mcp-server/SKILL.md) — Extend automation to X/Twitter alongside Meta
- [`linkedin-posting-automation`](../linkedin-posting-automation/SKILL.md) — Manage LinkedIn alongside Meta platforms
- [`mcp-builder`](../mcp-builder/SKILL.md) — Build the MCP infrastructure this server runs on
