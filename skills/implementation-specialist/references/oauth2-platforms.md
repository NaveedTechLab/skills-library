# OAuth2 Platform Integration Guide

## Twitter/X OAuth2

### Configuration
```python
# .env
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
TWITTER_REDIRECT_URI=http://localhost:3000/api/auth/callback/twitter
```

### FastAPI Implementation
```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import secrets

router = APIRouter(prefix="/auth/twitter", tags=["auth"])

# Store state tokens (use Redis in production)
state_store = {}

@router.get("/login")
async def twitter_login():
    state = secrets.token_urlsafe(32)
    state_store[state] = True

    auth_url = (
        "https://twitter.com/i/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={TWITTER_CLIENT_ID}"
        f"&redirect_uri={TWITTER_REDIRECT_URI}"
        f"&scope=tweet.read tweet.write users.read offline.access"
        f"&state={state}"
        f"&code_challenge=challenge"
        f"&code_challenge_method=plain"
    )
    return RedirectResponse(auth_url)

@router.get("/callback")
async def twitter_callback(code: str, state: str):
    if state not in state_store:
        raise HTTPException(status_code=400, detail="Invalid state")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": TWITTER_CLIENT_ID,
                "redirect_uri": TWITTER_REDIRECT_URI,
                "code_verifier": "challenge",
            },
            auth=(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET),
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Token exchange failed")

        tokens = token_response.json()
        return {"access_token": tokens["access_token"], "refresh_token": tokens.get("refresh_token")}
```

### Next.js Client
```typescript
// app/api/auth/twitter/route.ts
export async function GET() {
  const response = await fetch('http://localhost:8000/auth/twitter/login');
  const data = await response.json();
  return Response.redirect(data.auth_url);
}
```

## LinkedIn OAuth2

### Configuration
```python
# .env
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:3000/api/auth/callback/linkedin
```

### FastAPI Implementation
```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import secrets

router = APIRouter(prefix="/auth/linkedin", tags=["auth"])

state_store = {}

@router.get("/login")
async def linkedin_login():
    state = secrets.token_urlsafe(32)
    state_store[state] = True

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
        f"&scope=openid profile email w_member_social"
        f"&state={state}"
    )
    return RedirectResponse(auth_url)

@router.get("/callback")
async def linkedin_callback(code: str, state: str):
    if state not in state_store:
        raise HTTPException(status_code=400, detail="Invalid state")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Token exchange failed")

        tokens = token_response.json()
        return {"access_token": tokens["access_token"]}
```

## Security Best Practices

1. **State Parameter**: Always validate state to prevent CSRF attacks
2. **PKCE**: Use PKCE (Proof Key for Code Exchange) for public clients
3. **Token Storage**: Store tokens securely (encrypted database, not localStorage)
4. **Scope Minimization**: Request only necessary scopes
5. **Token Refresh**: Implement refresh token rotation
6. **HTTPS Only**: Never use OAuth2 over HTTP in production
