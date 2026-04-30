# Gmail API Setup Guide

Step-by-step instructions to configure Google Cloud for Gmail Watcher.

## Table of Contents

1. [Create Google Cloud Project](#create-google-cloud-project)
2. [Enable Gmail API](#enable-gmail-api)
3. [Configure OAuth Consent Screen](#configure-oauth-consent-screen)
4. [Create OAuth Credentials](#create-oauth-credentials)
5. [Download Credentials](#download-credentials)
6. [First-Time Authentication](#first-time-authentication)
7. [Troubleshooting](#troubleshooting)

---

## Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** dropdown (top bar)
3. Click **New Project**
4. Enter project name: `Gmail Watcher` (or your preference)
5. Click **Create**
6. Wait for project creation, then select it

## Enable Gmail API

1. In Cloud Console, go to **APIs & Services** > **Library**
2. Search for `Gmail API`
3. Click **Gmail API** in results
4. Click **Enable**
5. Wait for API to be enabled

## Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** user type (unless you have Google Workspace)
3. Click **Create**

### App Information

Fill in required fields:

| Field | Value |
|-------|-------|
| App name | Gmail Watcher |
| User support email | Your email |
| Developer contact | Your email |

4. Click **Save and Continue**

### Scopes

1. Click **Add or Remove Scopes**
2. Search for `gmail.readonly`
3. Check `https://www.googleapis.com/auth/gmail.readonly`
4. Click **Update**
5. Click **Save and Continue**

### Test Users

1. Click **Add Users**
2. Enter your Gmail address
3. Click **Add**
4. Click **Save and Continue**

### Summary

1. Review settings
2. Click **Back to Dashboard**

## Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `Gmail Watcher Desktop`
5. Click **Create**

## Download Credentials

1. In the popup, click **Download JSON**
2. Save as `credentials.json` in your project directory
3. Click **OK**

**Security Note**: Keep `credentials.json` secure. Never commit to git.

Add to `.gitignore`:
```
credentials.json
token.json
```

## First-Time Authentication

Run the authentication command:

```bash
python scripts/cli.py auth --credentials ./credentials.json
```

This will:
1. Open browser for Google sign-in
2. Request permission for Gmail read access
3. Save token to `token.json`

### Expected Browser Flow

1. Select your Google account
2. See warning "Google hasn't verified this app"
3. Click **Advanced** > **Go to Gmail Watcher (unsafe)**
4. Review permissions: "View your email messages and settings"
5. Click **Allow**
6. See "Authentication successful" in terminal

## Troubleshooting

### "Access Denied" Error

**Cause**: User not in test users list

**Fix**:
1. Go to OAuth consent screen
2. Add your email to Test Users
3. Try authentication again

### "Invalid Client" Error

**Cause**: Corrupted credentials.json

**Fix**:
1. Delete `credentials.json`
2. Download fresh copy from Cloud Console
3. Try again

### "Token Expired" Error

**Cause**: Old token needs refresh

**Fix**:
1. Delete `token.json`
2. Run auth command again

### "API Not Enabled" Error

**Cause**: Gmail API not enabled for project

**Fix**:
1. Go to APIs & Services > Library
2. Search and enable Gmail API

### Browser Doesn't Open

**Cause**: Running in headless environment

**Fix**: Use manual auth flow:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)

# Get URL for manual auth
auth_url, _ = flow.authorization_url(prompt='consent')
print(f"Visit: {auth_url}")

# After visiting URL, paste the code
code = input("Enter authorization code: ")
flow.fetch_token(code=code)

# Save token
with open('token.json', 'w') as f:
    f.write(flow.credentials.to_json())
```

### Rate Limiting

Gmail API has quotas:
- 1 billion quota units/day
- `messages.list`: 5 units
- `messages.get`: 5 units

For typical usage (polling every 60s), you won't hit limits.

## Security Best Practices

1. **Never share credentials.json** - Contains client secret
2. **Store token.json securely** - Contains access token
3. **Use minimum scopes** - Only `gmail.readonly` needed
4. **Rotate credentials periodically** - Delete and recreate in Cloud Console
5. **Monitor usage** - Check Cloud Console for unusual activity

## Moving to Production

For production use:

1. Complete OAuth consent screen verification
2. Submit app for Google review
3. After approval, remove "Test app" limitations

Verification requirements:
- Privacy policy URL
- Terms of service URL
- App homepage
- Demo video (for sensitive scopes)
