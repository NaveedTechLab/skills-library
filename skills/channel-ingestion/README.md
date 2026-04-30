# Channel Ingestion Skill

This skill provides guidance and tools for implementing multi-channel message ingestion with FastAPI endpoints and webhook handlers for Gmail API, Twilio WhatsApp, and Web Support Form integration.

## Overview

The channel ingestion system handles incoming messages from multiple sources:
- Gmail API webhooks for email messages
- Twilio webhooks for WhatsApp messages
- Web Support Form submissions for customer inquiries

All messages are normalized to a common format before being ingested into the system.

## Components

### SKILL.md
Main skill file containing overview, key components, and implementation guidelines.

### Reference Files
- `GMAIL_INTEGRATION.md` - Gmail API webhook specifics
- `TWILIO_WHATSAPP.md` - Twilio WhatsApp integration details
- `WEB_FORM_HANDLING.md` - Web form processing patterns
- `NORMALIZATION_SCHEMA.md` - Message normalization schema
- `SECURITY_PATTERNS.md` - Security implementation patterns

### Scripts
- `channel_ingestion_service.py` - Complete FastAPI implementation example

### Dependencies
- `requirements.txt` - Required Python packages

## Usage

When implementing channel ingestion functionality:

1. Review the main `SKILL.md` for architectural guidance
2. Consult the relevant reference files for specific channel implementations:
   - For Gmail: `GMAIL_INTEGRATION.md`
   - For WhatsApp: `TWILIO_WHATSAPP.md`
   - For Web Forms: `WEB_FORM_HANDLING.md`
3. Use the normalization schema in `NORMALIZATION_SCHEMA.md` to ensure consistent message formats
4. Follow security patterns from `SECURITY_PATTERNS.md`
5. Use the example service in `scripts/channel_ingestion_service.py` as a starting point

## Implementation Steps

1. Set up FastAPI endpoints for each channel
2. Implement webhook handlers with proper authentication
3. Create message normalization functions
4. Add security measures (validation, rate limiting, etc.)
5. Test with actual channel providers

## Security Considerations

- Always validate webhook signatures/authenticity
- Sanitize all input data
- Implement rate limiting
- Use environment variables for secrets
- Log security events without exposing sensitive data