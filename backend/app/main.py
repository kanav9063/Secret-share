from typing import Optional, List

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, SQLModel, create_engine, select
from pydantic import BaseModel

from .auth import create_state  # Phase 1D & 1E
from .auth import (
    create_jwt_token,
    get_github_user,
    pending_tokens,
    verify_jwt_token,
    verify_state,
)
from .config import settings  # Phase 1C
from .models import *  # Phase 2A: Database models
from . import crud  # Phase 2C: Database operations

# Phase 2B: Create database engine
engine = create_engine("sqlite:///app.db", echo=True)

# Create the FastAPI application
app = FastAPI(title="Secret Sharing API")

# Phase 2B: Create tables on startup
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

# Phase 2B: Dependency to get database session
def get_session():
    with Session(engine) as session:
        yield session

# Phase 2D: Pydantic models for API requests/responses
class ACLEntry(BaseModel):
    """Defines who can access a secret"""
    subject_type: str  # 'user', 'team', 'org'
    subject_id: Optional[int] = None
    can_read: bool = True
    can_write: bool = False

class SecretCreate(BaseModel):
    """Request body for creating a secret"""
    key: str
    value: str
    acl_entries: Optional[List[ACLEntry]] = None

class SecretUpdate(BaseModel):
    """Request body for updating a secret"""
    value: Optional[str] = None
    acl_entries: Optional[List[ACLEntry]] = None

# Phase 2D: Dependency to get current user from JWT
async def get_current_user(
    authorization: Optional[str] = Header(None),
    session: Session = Depends(get_session)
) -> User:
    """
    Extract and validate user from JWT token.
    This runs before every protected endpoint.
    """
    # 1. Check authorization header exists
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    
    # 2. Check it's a Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    # 3. Extract and verify the token
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # 4. Get or create user in database
    user = crud.get_or_create_user(
        session,
        email=payload.get("email"),
        name=payload.get("name"),
        github_id=payload.get("sub")
    )
    
    return user


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


# Phase 2D: Secret Management Endpoints

@app.get("/secrets")
async def list_secrets(
    query: Optional[str] = Query(None, description="Search filter for secret keys"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    List all secrets user can access.
    This is the main endpoint for displaying secrets in the CLI.
    """
    # 1. Get all secrets user can read (filtered by permissions)
    secrets = crud.list_secrets(session, current_user, query)
    
    # 2. Add metadata for each secret (can user write to it?)
    result = []
    for secret in secrets:
        result.append({
            "id": secret.id,
            "key": secret.key,
            "value": secret.value,
            "created_by_id": secret.created_by_id,
            "created_at": secret.created_at,
            "can_write": crud.can_write_secret(session, current_user, secret)
        })
    
    return result

@app.post("/secrets", status_code=201)
async def create_secret(
    body: SecretCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new secret.
    User provides key and value, optionally can share with teams/users.
    """
    # 1. Convert ACL entries to dict format for crud function
    acl_dicts = None
    if body.acl_entries:
        acl_dicts = [entry.dict() for entry in body.acl_entries]
    
    # 2. Create the secret in database
    secret = crud.create_secret(
        session,
        current_user,
        body.key,
        body.value,
        acl_dicts
    )
    
    # 3. Return created secret with metadata
    return {
        "id": secret.id,
        "key": secret.key,
        "value": secret.value,
        "created_by_id": secret.created_by_id,
        "created_at": secret.created_at,
        "message": "Secret created successfully"
    }

# Phase 2D: Helper endpoint for testing - Get current user info
@app.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information from JWT token.
    Useful for testing authentication.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "organization_id": current_user.organization_id,
        "is_admin": current_user.is_admin
    }

@app.get("/secrets/{secret_id}")
async def get_secret(
    secret_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific secret by ID.
    Returns 404 if not found, 403 if no permission.
    """
    # 1. Try to get the secret
    secret = crud.get_secret(session, secret_id, current_user)
    
    # 2. Handle not found or no permission
    if not secret:
        # Check if secret exists but user can't access it
        secret_exists = session.get(Secret, secret_id)
        if secret_exists and secret_exists.organization_id == current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=404, detail="Secret not found")
    
    # 3. Return secret with metadata
    return {
        "id": secret.id,
        "key": secret.key,
        "value": secret.value,
        "created_by_id": secret.created_by_id,
        "created_at": secret.created_at,
        "can_write": crud.can_write_secret(session, current_user, secret)
    }

@app.put("/secrets/{secret_id}")
async def update_secret(
    secret_id: int,
    body: SecretUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a secret's value or permissions.
    Only users with write permission can update.
    """
    # 1. Convert ACL entries if provided
    acl_dicts = None
    if body.acl_entries is not None:
        acl_dicts = [entry.dict() for entry in body.acl_entries]
    
    # 2. Try to update the secret
    secret = crud.update_secret(
        session,
        secret_id,
        current_user,
        body.value,
        acl_dicts
    )
    
    # 3. Handle errors
    if not secret:
        # Check why update failed
        secret_exists = session.get(Secret, secret_id)
        if not secret_exists:
            raise HTTPException(status_code=404, detail="Secret not found")
        elif not crud.can_write_secret(session, current_user, secret_exists):
            raise HTTPException(status_code=403, detail="No write permission")
        else:
            raise HTTPException(status_code=400, detail="Update failed")
    
    # 4. Return updated secret
    return {
        "id": secret.id,
        "key": secret.key,
        "value": secret.value,
        "updated_at": secret.updated_at,
        "message": "Secret updated successfully"
    }
