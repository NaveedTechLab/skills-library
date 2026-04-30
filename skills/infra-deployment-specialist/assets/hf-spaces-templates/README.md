---
title: Marketing AI Agent
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# Marketing AI Agent

AI-powered marketing automation platform with multi-agent reasoning.

## Features

- Multi-agent content generation
- Social media integration (Twitter, LinkedIn)
- Automated scheduling and posting
- Analytics and insights

## Configuration

Set the following secrets in your Space settings:

- `DATABASE_URL` - Neon PostgreSQL connection string
- `SECRET_KEY` - Application secret key
- `TWITTER_CLIENT_ID` - Twitter OAuth client ID
- `TWITTER_CLIENT_SECRET` - Twitter OAuth client secret
- `LINKEDIN_CLIENT_ID` - LinkedIn OAuth client ID
- `LINKEDIN_CLIENT_SECRET` - LinkedIn OAuth client secret

## Local Development

```bash
docker build -t marketing-agent .
docker run -p 7860:7860 --env-file .env marketing-agent
```
