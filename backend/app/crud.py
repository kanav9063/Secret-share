from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime

from .models import User, Secret, ACL, Organization, Team, TeamMembership

def create_secret(
    session: Session,
    user: User, 
    key: str,
    value: str,
    acl_entries: Optional[List[dict]] = None
) -> Secret:
    """
    Create a new secret with default ACL for creator.
    This is how users store their secrets in the database.
    """
    # 1. Create the secret object with user's organization
    secret = Secret(
        organization_id=user.organization_id,
        key=key,
        value=value,
        created_by_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # 2. Save secret to database
    session.add(secret)
    session.commit()
    session.refresh(secret)  # Get the generated ID
    
    # 3. Give creator full access (read + write)
    creator_acl = ACL(
        secret_id=secret.id,
        subject_type="user",
        subject_id=user.id,
        can_read=True,
        can_write=True
    )
    session.add(creator_acl)
    
    # 4. Add any additional permissions (sharing with teams/users)
    if acl_entries:
        for entry in acl_entries:
            acl = ACL(
                secret_id=secret.id,
                subject_type=entry.get("subject_type"),  # 'user', 'team', or 'org'
                subject_id=entry.get("subject_id"),      # ID of user/team
                can_read=entry.get("can_read", True),
                can_write=entry.get("can_write", False)
            )
            session.add(acl)
    
    # 5. Save all ACL entries
    session.commit()
    return secret

def list_secrets(
    session: Session,
    user: User,
    query: Optional[str] = None
) -> List[Secret]:
    """
    List all secrets the user can read.
    This is what shows up in the CLI secrets list.
    """
    # 1. Get all secrets in the user's organization
    stmt = select(Secret).where(Secret.organization_id == user.organization_id)
    
    # 2. Apply search filter if user is searching
    if query:
        stmt = stmt.where(Secret.key.contains(query))
    
    # 3. Execute the database query
    secrets = session.exec(stmt).all()
    
    # 4. Filter to only secrets user has permission to read
    readable_secrets = []
    for secret in secrets:
        if can_read_secret(session, user, secret):
            readable_secrets.append(secret)
    
    return readable_secrets

def get_secret(
    session: Session,
    secret_id: int,
    user: User
) -> Optional[Secret]:
    """
    Get a specific secret if user can read it.
    Returns None if secret doesn't exist or user can't access it.
    """
    # 1. Try to get the secret from database
    secret = session.get(Secret, secret_id)
    
    # 2. Check if secret exists
    if not secret:
        return None
    
    # 3. Check if secret is in user's organization
    if secret.organization_id != user.organization_id:
        return None
    
    # 4. Check if user has read permission
    if not can_read_secret(session, user, secret):
        return None
    
    return secret

def update_secret(
    session: Session,
    secret_id: int,
    user: User,
    value: Optional[str] = None,
    acl_entries: Optional[List[dict]] = None
) -> Optional[Secret]:
    """
    Update a secret's value or permissions if user can write.
    Used when user wants to change secret value or share it.
    """
    # 1. Get the secret from database
    secret = session.get(Secret, secret_id)
    
    if not secret:
        return None
    
    # 2. Check if user has write permission
    if not can_write_secret(session, user, secret):
        return None
    
    # 3. Update the secret value if provided
    if value is not None:
        secret.value = value
        secret.updated_at = datetime.utcnow()
    
    # 4. Update permissions if provided
    if acl_entries is not None:
        # 4a. Delete existing ACL except creator's (creator always keeps access)
        stmt = select(ACL).where(
            ACL.secret_id == secret_id,
            ACL.subject_type != "user" or ACL.subject_id != secret.created_by_id
        )
        existing_acls = session.exec(stmt).all()
        for acl in existing_acls:
            session.delete(acl)
        
        # 4b. Add new ACL entries
        for entry in acl_entries:
            acl = ACL(
                secret_id=secret.id,
                subject_type=entry.get("subject_type"),
                subject_id=entry.get("subject_id"),
                can_read=entry.get("can_read", True),
                can_write=entry.get("can_write", False)
            )
            session.add(acl)
    
    # 5. Save changes to database
    session.commit()
    session.refresh(secret)
    return secret

def can_read_secret(
    session: Session,
    user: User,
    secret: Secret
) -> bool:
    """
    Check if user can read a secret.
    This is our permission system - determines who sees what.
    """
    # 1. Admins can read everything in their org
    if user.is_admin and user.organization_id == secret.organization_id:
        return True
    
    # 2. Creator can always read their own secrets
    if secret.created_by_id == user.id:
        return True
    
    # 3. Check ACL (Access Control List) entries
    stmt = select(ACL).where(ACL.secret_id == secret.id)
    acl_entries = session.exec(stmt).all()
    
    for acl in acl_entries:
        # 3a. Check if user has direct read permission
        if acl.subject_type == "user" and acl.subject_id == user.id and acl.can_read:
            return True
        
        # 3b. Check if entire org has read permission
        if acl.subject_type == "org" and acl.can_read:
            return True
        
        # 3c. Check if user's team has read permission
        if acl.subject_type == "team":
            # Check if user is member of this team
            stmt = select(TeamMembership).where(
                TeamMembership.team_id == acl.subject_id,
                TeamMembership.user_id == user.id
            )
            membership = session.exec(stmt).first()
            if membership and acl.can_read:
                return True
    
    # 4. No permission found
    return False

def can_write_secret(
    session: Session,
    user: User,
    secret: Secret
) -> bool:
    """
    Check if user can write to a secret.
    Similar to can_read but for write permissions.
    """
    # 1. Creator can always write to their own secrets
    if secret.created_by_id == user.id:
        return True
    
    # 2. Admins can write everything in their org
    if user.is_admin and user.organization_id == secret.organization_id:
        return True
    
    # 3. Check ACL entries for write permission
    stmt = select(ACL).where(ACL.secret_id == secret.id)
    acl_entries = session.exec(stmt).all()
    
    for acl in acl_entries:
        # 3a. Check if user has direct write permission
        if acl.subject_type == "user" and acl.subject_id == user.id and acl.can_write:
            return True
        
        # 3b. Check if entire org has write permission
        if acl.subject_type == "org" and acl.can_write:
            return True
        
        # 3c. Check if user's team has write permission
        if acl.subject_type == "team":
            stmt = select(TeamMembership).where(
                TeamMembership.team_id == acl.subject_id,
                TeamMembership.user_id == user.id
            )
            membership = session.exec(stmt).first()
            if membership and acl.can_write:
                return True
    
    # 4. No write permission found
    return False

def get_or_create_user(
    session: Session,
    email: str,
    name: str,
    github_id: str
) -> User:
    """
    Get existing user or create new one.
    Used during login to ensure user exists in our database.
    """
    # 1. Check if user already exists (by GitHub ID or email for testing)
    stmt = select(User).where(
        (User.github_id == github_id) | (User.email == email)
    )
    user = session.exec(stmt).first()
    
    if user:
        # Update GitHub ID if needed (for test users)
        if user.github_id != github_id:
            user.github_id = github_id
            session.add(user)
            session.commit()
        return user
    
    # 2. Create default organization if this is the first user
    stmt = select(Organization)
    org = session.exec(stmt).first()
    if not org:
        org = Organization(name="Default Organization")
        session.add(org)
        session.commit()
        session.refresh(org)
    
    # 3. Create new user in the organization
    user = User(
        email=email,
        name=name,
        github_id=github_id,
        organization_id=org.id,
        is_admin=False,  # Set to True for first user in production
        created_at=datetime.utcnow()
    )
    
    # 4. Save user to database
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user

def create_team(
    session: Session,
    name: str,
    org_id: int
) -> Team:
    """
    Create a new team in the organization.
    Teams are groups of users that can share secrets.
    """
    # 1. Create the team object with the organization ID
    team = Team(
        name=name,
        organization_id=org_id,
        created_at=datetime.utcnow()
    )
    
    # 2. Save team to database
    session.add(team)
    session.commit()
    session.refresh(team)  # Get the generated ID
    
    return team

def get_org_teams(session: Session, org_id: int) -> List[Team]:
    """
    Get all teams in an organization.
    Used to display available teams in the UI.
    """
    # 1. Query all teams that belong to this organization
    stmt = select(Team).where(Team.organization_id == org_id)
    
    # 2. Execute query and return all teams
    return session.exec(stmt).all()

def add_team_member(
    session: Session,
    team_id: int,
    user_id: int
) -> TeamMembership:
    """
    Add a user to a team.
    Prevents duplicate memberships - if user is already in team, returns existing.
    """
    # 1. Check if user is already a member of this team
    stmt = select(TeamMembership).where(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id == user_id
    )
    existing = session.exec(stmt).first()
    
    # 2. If already a member, return existing membership
    if existing:
        return existing
    
    # 3. Create new membership linking user to team
    membership = TeamMembership(
        team_id=team_id,
        user_id=user_id
    )
    
    # 4. Save membership to database
    session.add(membership)
    session.commit()
    session.refresh(membership)
    
    return membership

def get_user_teams(session: Session, user_id: int) -> List[Team]:
    """
    Get all teams a user belongs to.
    Used to show which teams the current user is a member of.
    """
    # 1. Join Team and TeamMembership tables to find user's teams
    stmt = select(Team).join(TeamMembership).where(
        TeamMembership.user_id == user_id
    )
    
    # 2. Execute query and return all teams user belongs to
    return session.exec(stmt).all()

def get_team_members(session: Session, team_id: int) -> List[User]:
    """
    Get all members of a team.
    Used to display team roster in the UI.
    """
    # 1. Join User and TeamMembership tables to find team members
    stmt = select(User).join(TeamMembership).where(
        TeamMembership.team_id == team_id
    )
    
    # 2. Execute query and return all users in the team
    return session.exec(stmt).all()