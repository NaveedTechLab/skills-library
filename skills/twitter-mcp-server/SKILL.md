---
name: twitter-mcp-server
description: Integrate with the X (Twitter) API v2 via MCP to create tweets, post threads, and manage media with HITL approval workflows. Use when automating Twitter/X account management from Claude Code.
---

# Twitter (X) MCP Server

## Description
The Twitter MCP Server provides Model Context Protocol integration with the X API v2 (formerly Twitter API), enabling Claude Code to create tweets, post threads, and manage media with HITL (Human-in-the-Loop) approval workflows.

## Purpose
This skill enables Claude Code to manage Twitter/X accounts while maintaining strict approval workflows for all tweet operations. It handles OAuth 2.0 authentication, rate limiting, and provides comprehensive audit logging.

## Key Features

### Tweet Operations
- Create single tweets
- Post tweet threads
- Upload media (images, videos, GIFs)
- Delete tweets
- Get tweet details and metrics

### Rate Limiting
Built-in rate limit handling with automatic tracking:
- Tweet creation: 200/15min window
- Media upload: 615/15min window
- Rate limit headers parsing

### Human-in-the-Loop Controls
| Operation | HITL Required |
|-----------|---------------|
| Get tweet | No |
| Get rate limits | No |
| Upload media | No |
| Create tweet | Yes |
| Create thread | Yes |
| Delete tweet | Yes |

### OAuth 2.0 with PKCE
Secure authentication flow:
- OAuth 2.0 Authorization Code Flow with PKCE
- Token refresh handling
- Secure token storage

## Configuration

### Environment Variables
```bash
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

### Default Configuration
```json
{
  "twitter": {
    "client_id": "",
    "client_secret": "",
    "access_token": "",
    "access_token_secret": "",
    "bearer_token": "",
    "api_version": "2",
    "timeout_seconds": 30
  },
  "approval": {
    "require_approval_for_tweets": true,
    "require_approval_for_threads": true,
    "require_approval_for_delete": true,
    "approval_timeout_hours": 24
  },
  "rate_limiting": {
    "enable_tracking": true,
    "warn_at_percentage": 80,
    "block_at_percentage": 95
  }
}
```

## MCP Tools

### twitter_create_tweet
Create a single tweet.

**Parameters:**
- `text` (string): Tweet text (max 280 chars)
- `reply_to` (string, optional): Tweet ID to reply to
- `quote_tweet_id` (string, optional): Tweet ID to quote
- `media_ids` (array, optional): Media IDs to attach

**HITL:** Required

### twitter_create_thread
Post a thread of connected tweets.

**Parameters:**
- `tweets` (array): Array of tweet texts
- `media_ids_per_tweet` (array, optional): Media IDs for each tweet

**HITL:** Required

### twitter_upload_media
Upload media for use in tweets.

**Parameters:**
- `media_url` (string): URL to media file
- `media_type` (string): image, video, or gif
- `alt_text` (string, optional): Accessibility text

**HITL:** Not required

### twitter_delete_tweet
Delete a tweet.

**Parameters:**
- `tweet_id` (string): ID of tweet to delete

**HITL:** Required

### twitter_get_tweet
Get tweet details and metrics.

**Parameters:**
- `tweet_id` (string): Tweet ID
- `expansions` (array, optional): Data expansions

**HITL:** Not required

### twitter_get_rate_limits
Check current API rate limit status.

**HITL:** Not required

## Usage Scenarios

### Create Simple Tweet
```python
result = await twitter_create_tweet(
    text="Hello Twitter! This is my first automated tweet."
)
# Returns approval_request_id - human must approve
```

### Create Thread
```python
result = await twitter_create_thread(
    tweets=[
        "1/5 Here's an important thread about AI safety...",
        "2/5 First, let's discuss the key principles...",
        "3/5 Second, implementation considerations...",
        "4/5 Third, monitoring and oversight...",
        "5/5 In conclusion, safety requires constant vigilance."
    ]
)
```

### Tweet with Media
```python
# First upload media
media_result = await twitter_upload_media(
    media_url="https://example.com/image.jpg",
    media_type="image",
    alt_text="A beautiful sunset"
)

# Then create tweet with media
tweet_result = await twitter_create_tweet(
    text="Check out this amazing view!",
    media_ids=[media_result["media_id"]]
)
```

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /2/tweets | 200 | 15 min |
| POST /2/media/upload | 615 | 15 min |
| GET /2/tweets/:id | 300 | 15 min |
| DELETE /2/tweets/:id | 50 | 15 min |

The server tracks rate limits automatically and:
- Warns when approaching limits (80%)
- Blocks requests when near limit (95%)
- Returns time until reset

## Integration Points

### With Vault System
- `/vault/Pending_Approval/twitter/` for pending tweets
- `/vault/Approved/twitter/` after approval
- `/vault/Rejected/twitter/` if rejected

### With Audit Logger
All operations logged with:
- Tweet content hash
- Character count
- Media attachments
- Rate limit status

### With Safety Enforcer
- COMMUNICATION_SEND boundary
- Content moderation checks

## Security Considerations
- OAuth tokens encrypted at rest
- No plaintext credential logging
- Rate limit protection
- Content length validation

## Dependencies
- `httpx` for async HTTP
- `fastmcp` for MCP server
- `pydantic` for validation
- `tweepy` (optional, for advanced features)
- Integration with phase-3 audit_logger

## When NOT to Use This Skill

- **Personal Twitter accounts** — the X API v2 Basic tier is expensive and requires Elevated access for meaningful functionality; personal posting is faster done manually
- **During Twitter/X API rate limit blackout periods** — X API rate limits are strict; automated posting during high-traffic events can exhaust your quota for hours
- **Crisis or sensitive topics** — never automate responses to breaking news, controversy, or sensitive topics; real-time human judgment is required

## Common Mistakes

- Using read-write OAuth 1.0a tokens for a read-only application — always request minimum necessary OAuth scopes; excessive permissions increase the blast radius of a token compromise
- Not handling the `duplicate_content` error — X rejects identical tweets; always vary content or include timestamps when posting programmatically
- Posting threads without tracking the parent tweet ID correctly — broken thread chains where replies aren't attached to the right parent create confusing, disjointed threads

## Related Skills

- [`meta-social-mcp-server`](../meta-social-mcp-server/SKILL.md) — Extend social automation to Facebook and Instagram alongside X
- [`linkedin-posting-automation`](../linkedin-posting-automation/SKILL.md) — Manage LinkedIn alongside X/Twitter
- [`mcp-builder`](../mcp-builder/SKILL.md) — Build the MCP infrastructure this server runs on
