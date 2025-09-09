from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth import create_state  # Phase 1D & 1E
from .auth import (
    create_jwt_token,
    get_github_user,
    pending_tokens,
    verify_jwt_token,
    verify_state,
)
from .config import settings  # Phase 1C

# Create the FastAPI application
app = FastAPI(title="Secret Sharing API")


# Part 1A: Basic health check to verify server is running
@app.get("/health")
async def health():
    """
    Simple endpoint to check if server is up.
    Test with: curl http://localhost:8001/health
    """
    return {"status": "healthy", "service": "secret-sharing-api"}


# Phase 1C: Test that environment variables are loading correctly
@app.get("/config-test")
async def config_test():
    """
    Test endpoint to verify configuration is loaded.
    NEVER include this in production!
    """
    return {
        "config_loaded": True,
        "base_url": settings.base_url,
        "github_client_id": settings.github_client_id[:10] + "...",
        "jwt_algorithm": settings.jwt_algorithm,
        "admin_emails_count": len(settings.get_admin_emails_list()),
    }


# JWT Test Endpoints (for development only)
# Phase 1D: Create a JWT token (simulating what happens after login)
@app.post("/test-token")
async def create_test_token():
    """
    Create a test JWT token.
    In real app, this would happen after login.
    """
    # Sample user data
    test_user = {
        "sub": "12345",  # User ID
        "email": "test@example.com",
        "name": "Test User",
    }

    # Create token
    token = create_jwt_token(test_user)

    return {
        "token": token,
        "type": "Bearer",
        "expires_in_days": settings.jwt_expiry_days,
    }


# Phase 1D: Test endpoint that requires a valid JWT token
@app.get("/test-protected")
async def protected_route(authorization: Optional[str] = Header(None)):
    """
    Test endpoint that requires a valid JWT token.
    Send token in Authorization header as: Bearer <token>
    """
    # Check if authorization header exists
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")

    # Check if it's a Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    # Extract the token
    token = authorization.replace("Bearer ", "")

    # Verify the token
    payload = verify_jwt_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Token is valid! Return the user data
    return {"message": "Token is valid!", "user": payload}


# GitHub OAuth Flow Endpoints

# Part 1E: OAuth Endpoint 1 - Start the flow
@app.get("/auth/github/start")
async def github_login_start(cli_token: str = Query(...)):
    """
    Part 1E: Where CLI sends user to login
    CLI opens browser to this URL with their unique token
    """
    # 1. Create signed state with CLI token inside
    state = create_state(cli_token)

    # 2. Redirect to GitHub login page
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.base_url}/auth/github/callback"
        f"&scope=user:email"
        f"&state={state}"
    )
    return RedirectResponse(url=github_auth_url)


# Part 1E: OAuth Endpoint 2 - GitHub sends user back here
@app.get("/auth/github/callback")
async def github_callback(code: str = Query(...), state: str = Query(...)):
    """
    Part 1E: GitHub redirects here after login
    We get a code to exchange for access token
    """
    # 1. Verify state to prevent CSRF attacks
    state_data = verify_state(state)
    if not state_data:
        return HTMLResponse("<h1>Error</h1><p>Invalid state</p>", 400)

    cli_token = state_data["cli_token"]

    # 2. Exchange GitHub's code for an access token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )

        if resp.status_code != 200:
            return HTMLResponse("<h1>Error</h1><p>Failed to get token</p>", 400)

        token_data = resp.json()
        access_token = token_data.get("access_token")

    # Get user info from GitHub
    user_data = await get_github_user(access_token)
    if not user_data:
        return HTMLResponse("<h1>Error</h1><p>Failed to get user info</p>", 400)

    # Create JWT for our app
    jwt_token = create_jwt_token(
        {
            "sub": str(user_data["id"]),
            "email": user_data.get(
                "email", f"{user_data['login']}@users.noreply.github.com"
            ),
            "name": user_data.get("name", user_data["login"]),
            "login": user_data["login"],
        }
    )

    # Store for CLI polling
    pending_tokens[cli_token] = {"token": jwt_token, "user": user_data}

    # Return success page
    return HTMLResponse(
        f"""
        <html>
        <body style="font-family: sans-serif; text-align: center; padding: 40px;">
            <h1>Login Successful :)</h1>
            <p>You can return to the CLI now.</p>
            <script>setTimeout(() => window.close(), 2000);</script>
        </body>
        </html>
    """
    )


# Part 1E: OAuth Endpoint 3 - CLI gets the token
@app.get("/auth/cli-exchange")
async def cli_exchange(cli_token: str = Query(...)):
    """
    Part 1E: CLI polls this to get the JWT token
    Returns 404 until login is complete
    """
    # 1. Check if login is done
    if cli_token not in pending_tokens:
        raise HTTPException(status_code=404, detail="Token not ready")

    # 2. Return token and remove it (one-time use)
    data = pending_tokens.pop(cli_token)
    return {"token": data["token"], "user": data["user"]}
