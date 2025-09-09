from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime

# These are our database tables - each class becomes a table
# Think of it like a spreadsheet where each class is a different sheet

class Organization(SQLModel, table=True):
    # Like a company - everyone belongs to one
    id: Optional[int] = Field(default=None, primary_key=True)  # Auto-generated ID
    name: str = Field(unique=True)  # Company name (must be unique)
    created_at: datetime = Field(default_factory=datetime.utcnow)  # When created
    
    # Links to other tables (not real columns)
    users: List["User"] = Relationship(back_populates="organization")
    teams: List["Team"] = Relationship(back_populates="organization")
    secrets: List["Secret"] = Relationship(back_populates="organization")

class User(SQLModel, table=True):
    # A person who can login and use the system
    id: Optional[int] = Field(default=None, primary_key=True)  # Auto ID
    email: str = Field(unique=True)  # Their email (must be unique)
    name: str  # Display name
    github_id: str = Field(unique=True)  # GitHub user ID (for login)
    organization_id: Optional[int] = Field(default=None, foreign_key="organization.id")  # Which company they belong to
    is_admin: bool = Field(default=False)  # Can they manage users/teams?
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Join date
    
    # Links to other tables
    organization: Optional[Organization] = Relationship(back_populates="users")
    team_memberships: List["TeamMembership"] = Relationship(back_populates="user")
    created_secrets: List["Secret"] = Relationship(back_populates="creator")

class Team(SQLModel, table=True):
    # A group of users (like "engineering" or "marketing")
    id: Optional[int] = Field(default=None, primary_key=True)  # Auto ID
    name: str  # Team name like "Backend Team"
    organization_id: int = Field(foreign_key="organization.id")  # Which company owns this team
    created_at: datetime = Field(default_factory=datetime.utcnow)  # When created
    
    # Links to other tables
    organization: Organization = Relationship(back_populates="teams")
    members: List["TeamMembership"] = Relationship(back_populates="team")

class TeamMembership(SQLModel, table=True):
    # Links users to teams (many-to-many relationship)
    # One user can be in many teams, one team has many users
    id: Optional[int] = Field(default=None, primary_key=True)  # Auto ID
    team_id: int = Field(foreign_key="team.id")  # Which team
    user_id: int = Field(foreign_key="user.id")  # Which user
    
    # Links to get full team/user objects
    team: Team = Relationship(back_populates="members")
    user: User = Relationship(back_populates="team_memberships")

class Secret(SQLModel, table=True):
    # The main thing we're storing - a key-value pair
    # Like "DATABASE_URL" = "postgres://localhost/mydb"
    id: Optional[int] = Field(default=None, primary_key=True)  # Auto ID
    organization_id: int = Field(foreign_key="organization.id")  # Which company owns this
    key: str  # The name like "API_KEY" or "DATABASE_PASSWORD"
    value: str  # The actual secret value
    created_by_id: int = Field(foreign_key="user.id")  # Who created this
    created_at: datetime = Field(default_factory=datetime.utcnow)  # When created
    updated_at: datetime = Field(default_factory=datetime.utcnow)  # Last modified
    
    # Links to other tables
    organization: Organization = Relationship(back_populates="secrets")
    creator: User = Relationship(back_populates="created_secrets")
    acl_entries: List["ACL"] = Relationship(back_populates="secret")  # Who can access this

class ACL(SQLModel, table=True):
    # Access Control List - who can see/edit each secret
    # Each row is one permission rule
    id: Optional[int] = Field(default=None, primary_key=True)  # Auto ID
    secret_id: int = Field(foreign_key="secret.id")  # Which secret this rule is for
    subject_type: str  # Who gets permission: 'user', 'team', or 'org'
    subject_id: Optional[int] = None  # ID of the user/team (None for whole org)
    can_read: bool = Field(default=True)  # Can they view it?
    can_write: bool = Field(default=False)  # Can they change it?
    
    # Example rows:
    # {secret_id: 1, subject_type: "user", subject_id: 5, can_read: True, can_write: False}
    # Means: User #5 can read secret #1 but not edit it
    #
    # {secret_id: 2, subject_type: "team", subject_id: 3, can_read: True, can_write: True}  
    # Means: Everyone in team #3 can read and edit secret #2
    #
    # {secret_id: 3, subject_type: "org", subject_id: None, can_read: True}
    # Means: Everyone in the organization can read secret #3
    
    secret: Secret = Relationship(back_populates="acl_entries")