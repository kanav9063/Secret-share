from typing import Optional, List
import time

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
async def create_test_token(session: Session = Depends(get_session)):
    """
    Create a test JWT token with actual database user.
    Phase 3: Updated to create admin user for testing teams.
    """
    try:
        # 1. Get or create test user in database
        test_user = crud.get_or_create_user(
            session,
            email="test@example.com",
            name="Test User",
            github_id="test-12345"
        )
        
        # 2. Make the test user an admin for testing
        test_user.is_admin = True
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        
        # 3. Create JWT token with actual user ID
        token_data = {
            "sub": str(test_user.id),  # Use actual DB user ID
            "email": test_user.email,
            "name": test_user.name,
        }

        # 4. Create token
        token = create_jwt_token(token_data)
    except Exception as e:
        print(f"Error creating test token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        f"&prompt=select_account"
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

    # Create or get user from database to get is_admin status
    try:
        with Session(engine) as session:
            # Ensure email is unique by using GitHub login if email is missing
            user_email = user_data.get("email")
            if not user_email:
                user_email = f"{user_data['login']}@users.noreply.github.com"
            
            # Ensure name is never None - use login as fallback
            user_name = user_data.get("name") or user_data["login"]
            
            db_user = crud.get_or_create_user(
                session=session,
                github_id=str(user_data["id"]),  # Convert to string
                email=user_email,
                name=user_name,
            )
            # Include is_admin in user data for CLI
            user_data["is_admin"] = db_user.is_admin
    except Exception as e:
        print(f"Error creating/getting user: {e}")
        print(f"GitHub user data: {user_data}")
        return HTMLResponse(f"<h1>Error</h1><p>Failed to create user: {str(e)}</p>", 500)
    
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
    List all secrets user can access with detailed sharing information.
    Phase 3 enhancement: Now includes WHO each secret is shared with.
    """
    # 1. Get all secrets user can read (filtered by permissions)
    secrets = crud.list_secrets(session, current_user, query)
    
    # 2. Build enhanced response with sharing details (Phase 3 improvement)
    result = []
    for secret in secrets:
        # 2a. Get all ACL entries to see who has access
        stmt = select(ACL).where(ACL.secret_id == secret.id)
        acl_entries = session.exec(stmt).all()
        
        # 2b. Build human-readable sharing summary
        shared_with = {
            "users": [],
            "teams": [],
            "org_wide": False
        }
        
        # 2c. Convert ACL entries to names (not just IDs)
        for acl in acl_entries:
            if acl.subject_type == "user" and acl.subject_id != secret.created_by_id:
                # Add shared user details
                user = session.get(User, acl.subject_id)
                if user:
                    shared_with["users"].append({
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "can_write": acl.can_write
                    })
            elif acl.subject_type == "team":
                # Add shared team details
                team = session.get(Team, acl.subject_id)
                if team:
                    shared_with["teams"].append({
                        "id": team.id,
                        "name": team.name,
                        "can_write": acl.can_write
                    })
            elif acl.subject_type == "org":
                # Mark organization-wide sharing
                shared_with["org_wide"] = True
                shared_with["org_can_write"] = acl.can_write
        
        # 2d. Get creator's name
        creator = session.get(User, secret.created_by_id)
        creator_name = creator.name if creator else "Unknown"
        
        # 2e. Compile all secret info
        result.append({
            "id": secret.id,
            "key": secret.key,
            "value": secret.value,
            "created_at": secret.created_at.isoformat(),
            "created_by": secret.created_by_id,
            "created_by_name": creator_name,  # New in Phase 3
            "can_write": crud.can_write_secret(session, current_user, secret),
            "is_creator": secret.created_by_id == current_user.id,  # New in Phase 3
            "shared_with": shared_with  # New in Phase 3: Full sharing details
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

# Phase 4C: Enhanced user info endpoint - Get current user with teams and org
@app.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get current user information with organization and teams.
    Shows complete user profile including admin status and team memberships.
    """
    # 1. Get user's teams
    teams = crud.get_user_teams(session, current_user.id)
    
    # 2. Get user's organization
    org = session.get(Organization, current_user.organization_id)
    
    # 3. Return comprehensive user info
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "is_admin": current_user.is_admin
        },
        "organization": {
            "id": org.id,
            "name": org.name
        } if org else None,
        "teams": [
            {"id": t.id, "name": t.name} for t in teams
        ]
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


# Phase 3B: Team Management Endpoints

@app.get("/teams")
async def list_teams(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    List all teams in the organization.
    Any user can see all teams in their org.
    """
    # 1. Get all teams in user's organization
    teams = crud.get_org_teams(session, current_user.organization_id)
    
    # 2. Return teams list
    return {"teams": teams}

@app.get("/teams/mine")
async def my_teams(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    List teams the current user belongs to.
    Shows which teams the user is a member of.
    """
    # 1. Get teams user is a member of
    teams = crud.get_user_teams(session, current_user.id)
    
    # 2. Return user's teams
    return {"teams": teams}

@app.post("/teams")
async def create_team_endpoint(
    name: str = Query(..., description="Team name"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Create a new team (admin only).
    Admin users can create teams in their organization.
    """
    # 1. Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # 2. Validate team name is not empty
    if not name or not name.strip():
        raise HTTPException(status_code=422, detail="Team name cannot be empty")
    
    # 3. Create the team with cleaned name
    team = crud.create_team(session, name.strip(), current_user.organization_id)
    
    # 4. Add creator as first member
    crud.add_team_member(session, team.id, current_user.id)
    
    # 5. Return created team as dict
    return {
        "team": {
            "id": team.id,
            "name": team.name,
            "organization_id": team.organization_id,
            "created_at": team.created_at.isoformat() if team.created_at else None
        }
    }

@app.post("/teams/{team_id}/members")
async def add_member(
    team_id: int,
    user_id: int = Query(..., description="User ID to add"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Add a member to a team (admin only).
    Admins can add any user in their org to any team.
    """
    # 1. Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # 2. Verify team exists and belongs to user's org
    teams = crud.get_org_teams(session, current_user.organization_id)
    team = next((t for t in teams if t.id == team_id), None)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in your organization")
    
    # 3. Verify user exists and belongs to same org
    user_to_add = session.get(User, user_id)
    if not user_to_add or user_to_add.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found in your organization")
    
    # 4. Add user to team
    membership = crud.add_team_member(session, team_id, user_id)
    
    # 5. Return membership info
    return {"membership": membership, "message": f"User {user_to_add.name} added to team {team.name}"}

@app.get("/teams/{team_id}/members")
async def list_team_members(
    team_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    List members of a team.
    Any user in the org can see team membership.
    """
    # 1. Verify team exists and belongs to user's org
    teams = crud.get_org_teams(session, current_user.organization_id)
    team = next((t for t in teams if t.id == team_id), None)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in your organization")
    
    # 2. Get team members
    members = crud.get_team_members(session, team_id)
    
    # 3. Return members list
    return {"team": team, "members": members}

@app.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    List all users in the organization.
    Used for adding users to teams.
    """
    # 1. Get all users in the organization
    stmt = select(User).where(User.organization_id == current_user.organization_id)
    users = session.exec(stmt).all()
    
    # 2. Return users list
    return {"users": users}


# PHASE 4A: Admin User Management Endpoints

@app.post("/admin/users")
async def create_user(
    email: str = Query(..., description="User email"),
    name: str = Query(..., description="User full name"),
    is_admin: bool = Query(False, description="Grant admin privileges"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Create a new user (admin only).
    This allows admins to onboard users without GitHub login.
    """
    # 1. Check if current user is admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # 2. Check if email already exists
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # 3. Create new user with manual prefix (no GitHub ID yet)
    new_user = User(
        email=email,
        name=name,
        github_id=f"manual-{email}-{int(time.time())}",  # Unique ID for manual users
        organization_id=current_user.organization_id,
        is_admin=is_admin,
        created_at=datetime.utcnow()
    )
    
    # 4. Save to database
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # 5. Return created user
    return {
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "is_admin": new_user.is_admin
        },
        "message": f"User {new_user.name} created successfully"
    }

@app.put("/admin/users/{user_id}/promote")
async def promote_to_admin(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Promote user to admin (admin only).
    Grants admin privileges to a regular user.
    """
    # 1. Check if current user is admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # 2. Find the user to promote
    user = session.get(User, user_id)
    if not user or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found in your organization")
    
    # 3. Check if already admin
    if user.is_admin:
        return {"message": f"User {user.name} is already an admin"}
    
    # 4. Promote to admin
    user.is_admin = True
    session.commit()
    
    # 5. Return success message
    return {"message": f"User {user.name} promoted to admin"}

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete a user (admin only).
    Removes user and all their team memberships.
    """
    # 1. Check if current user is admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # 2. Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # 3. Find the user to delete
    user = session.get(User, user_id)
    if not user or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="User not found in your organization")
    
    # 4. Delete user (cascade will handle memberships and ACLs)
    session.delete(user)
    session.commit()
    
    # 5. Return success message
    return {"message": f"User {user.name} deleted successfully"}

@app.delete("/admin/teams/{team_id}")
async def delete_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete a team (admin only).
    Removes team and all memberships.
    """
    # 1. Check if current user is admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # 2. Find the team to delete
    team = session.get(Team, team_id)
    if not team or team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Team not found in your organization")
    
    # 3. Delete related records first (memberships and ACL entries)
    # Delete all team memberships
    stmt = select(TeamMembership).where(TeamMembership.team_id == team_id)
    memberships = session.exec(stmt).all()
    for membership in memberships:
        session.delete(membership)
    
    # Delete all ACL entries for this team
    stmt = select(ACL).where(ACL.subject_type == "team", ACL.subject_id == team_id)
    acl_entries = session.exec(stmt).all()
    for acl in acl_entries:
        session.delete(acl)
    
    # 4. Now delete the team
    session.delete(team)
    session.commit()
    
    # 5. Return success message
    return {"message": f"Team {team.name} deleted successfully"}

@app.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Remove user from team (admin only).
    Removes a team membership.
    """
    # 1. Check if current user is admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # 2. Find the membership to remove
    stmt = select(TeamMembership).where(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id == user_id
    )
    membership = session.exec(stmt).first()
    
    # 3. Check if membership exists
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this team")
    
    # 4. Verify team is in user's org
    team = session.get(Team, team_id)
    if not team or team.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Team not found in your organization")
    
    # 5. Remove membership
    session.delete(membership)
    session.commit()
    
    # 6. Return success message
    user = session.get(User, user_id)
    return {"message": f"User {user.name if user else 'unknown'} removed from team {team.name}"}


# PHASE 4B: Secret Management Endpoints (Delete)

@app.delete("/secrets/{secret_id}")
async def delete_secret(
    secret_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete a secret (creator or admin only).
    Only the creator or an admin can delete secrets.
    """
    # 1. Find the secret
    secret = session.get(Secret, secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # 2. Check if secret is in user's organization
    if secret.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # 3. Check permission: only creator or admin can delete
    if secret.created_by_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only creator or admin can delete this secret")
    
    # 4. Delete all ACL entries for this secret first
    stmt = select(ACL).where(ACL.secret_id == secret_id)
    acl_entries = session.exec(stmt).all()
    for acl in acl_entries:
        session.delete(acl)
    
    # 5. Now delete the secret
    session.delete(secret)
    session.commit()
    
    # 6. Return success message
    return {"message": f"Secret '{secret.key}' deleted successfully"}
