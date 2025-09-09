"""JWT authentication utilities.
Phase 1D: JWT Token Creation and Validation
Phase 1E: GitHub OAuth Flow
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from itsdangerous import URLSafeTimedSerializer
import httpx
from .config import settings

# Phase 1E: Pending tokens for CLI polling (in production, use Redis with TTL)
pending_tokens: Dict[str, Dict[str, Any]] = {}

# Phase 1E: State serializer for CSRF protection
state_serializer = URLSafeTimedSerializer(settings.state_secret)

def create_jwt_token(data: Dict[str, Any]) -> str:
    """
    Part 1D: Create a JWT token with user data
    Used after successful GitHub login
    """
    # 1. Copy the user data
    to_encode = data.copy()
    
    # 2. Add expiration (7 days from now)
    expire = datetime.utcnow() + timedelta(days=settings.jwt_expiry_days)
    to_encode.update({"exp": expire})
    
    # Create the JWT token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret, 
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Part 1D: Check if a JWT token is valid
    Returns user data if valid, None if not
    """
    try:
        # 3. Decode and verify the token signature
        payload = jwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        # Token is invalid (expired, wrong signature, etc.)
        print(f"JWT verification failed: {e}")
        return None

# Part 1E: OAuth State Management (prevents CSRF attacks)
def create_state(cli_token: str) -> str:
    """
    Part 1E: Create signed state for OAuth
    Contains the CLI token so we know which CLI session to give token to
    """
    return state_serializer.dumps({"cli_token": cli_token})

def verify_state(state: str, max_age: int = 600) -> Optional[Dict[str, Any]]:
    """
    Part 1E: Verify the state came from us
    Expires after 10 minutes (600 seconds)
    """
    try:
        return state_serializer.loads(state, max_age=max_age)
    except:
        return None

# Phase 1E: GitHub API Helper
async def get_github_user(access_token: str) -> Optional[Dict[str, Any]]:
    """Get user info from GitHub using access token."""
    async with httpx.AsyncClient() as client:
        # Get user info
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        if resp.status_code != 200:
            return None
        user = resp.json()
        
        # Get primary verified email
        resp = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        if resp.status_code == 200:
            emails = resp.json()
            for email in emails:
                if email.get("primary") and email.get("verified"):
                    user["email"] = email["email"]
                    break
        
        return user
