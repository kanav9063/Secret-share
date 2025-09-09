---
noteId: "30c099a08d6411f08b2675fee6e4b94e"
tags: []

---

# SecretShare

Product Engineer Take Home Assignment implementation: A secret sharing system with CLI and backend web server.

## Assignment Requirements

Secret sharing system with:
- Command line utility using Ink
- Backend web server 
- Key/value secret storage with authorization
- User, team, organization, and admin support
- OAuth2 authentication via GitHub
- Session persistence across CLI restarts

## Implementation Overview

**CLI**: React Ink-based terminal interface with TypeScript
**Backend**: FastAPI with Python, SQLite database
**Authentication**: GitHub OAuth2 with browser-based login
**Authorization**: ACL-based permissions for users, teams, and organizations

## Architecture

### Authentication Flow Diagram
Shows the complete OAuth2 flow from CLI to GitHub and back. This diagram illustrates how we achieve seamless browser-based authentication without requiring users to copy/paste tokens, fulfilling the assignment's requirement for frictionless social login. The CLI generates a unique token, opens the browser, and polls for the JWT after GitHub authorization completes.

[Diagram 1 - Authentication Flow]

### Database Entity Relationship Diagram  
Displays the complete database schema with all six tables and their relationships. This ERD demonstrates how we implement the hierarchical organization structure (users belong to one organization, can belong to multiple teams) and the ACL-based permission system that controls secret access at user, team, and organization levels.

[Diagram 2 - Database ERD]

### API Request Flow
Illustrates the JWT verification pipeline for authenticated requests. Every API call passes through the authentication layer where the JWT is extracted from headers, verified, and used to fetch the current user from the database. This ensures all operations are properly authorized and scoped to the user's organization.

[Diagram 3 - API Request Flow]

### System Overview
High-level component architecture showing the interactions between CLI, FastAPI backend, SQLite database, and GitHub OAuth. This diagram provides a quick understanding of the system's main components and how they communicate, useful for understanding the overall architecture before diving into specific flows.

[Diagram 4 - System Overview]

## Tech Stack

### CLI (TypeScript)
- **Framework**: Ink 6.x
- **Components**: ink-text-input, ink-select-input, ink-spinner
- **HTTP Client**: node-fetch
- **Config**: conf (persistent token storage)
- **Browser**: open (cross-platform browser launching)

### Backend (Python)
- **Framework**: FastAPI (async web framework)
- **Database**: SQLite with SQLModel (SQLAlchemy wrapper)
- **Authentication**: python-jose (JWT), authlib (GitHub OAuth)
- **HTTP Client**: httpx (GitHub API calls)

## Installation

1. **Clone and setup backend**
   ```bash
   git clone <repo-url>
   cd ChipAgents-SecretShare/backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your GitHub OAuth credentials
   ```

3. **Start backend server**
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

4. **Setup CLI (new terminal)**
   ```bash
   cd ../cli
   npm install
   npm run dev
   ```

## GitHub OAuth Setup

1. Go to GitHub Settings > Developer Settings > OAuth Apps
2. Create OAuth App:
   - Application name: `SecretShare`
   - Homepage URL: `http://localhost:8001`
   - Authorization callback URL: `http://localhost:8001/auth/github/callback`
3. Copy Client ID and Client Secret to `.env` file

## Operations Implemented

### Authentication
- **Login**: Browser-based GitHub OAuth with automatic token exchange
- **Logout**: Session termination with local storage cleanup
- **Session Persistence**: JWT tokens stored in `~/.config/secret-cli/`

### Secret Management
- **List secrets**: View all authorized key/value pairs with sharing details
- **Create secrets**: Add new secrets with granular permissions
- **Update secrets**: Modify values and authorization settings
- **Delete secrets**: Remove secrets (creator/admin only)

### Authorization Levels
- **Private**: Creator only
- **User-specific**: Individual user permissions
- **Team-based**: All team members
- **Organization-wide**: All organization users
- **Advanced**: Custom user/team combinations with read/write controls

### Administration (Admin Users)
- **Create users**: Add users to organization
- **Create teams**: Establish team structures
- **Manage memberships**: Add/remove team members
- **User management**: Promote users to admin, delete users
- **Team management**: Delete teams and memberships

### Organization Structure
- Users belong to one organization
- Users can belong to multiple teams
- Admins scoped to their organization
- Complete data isolation between organizations

## Permission System

### Access Control Lists (ACL)
Each secret has ACL entries defining:
- **Subject Type**: user, team, or org
- **Subject ID**: Specific user/team ID
- **Permissions**: can_read, can_write flags

### Permission Resolution
1. Organization admins have full access
2. Secret creators retain full control
3. Explicit user permissions via ACL
4. Team membership inheritance
5. Organization-wide permissions

## Database Schema

```
organizations: id, name, created_at
users: id, email, name, github_id, organization_id, is_admin, created_at  
teams: id, name, organization_id, created_at
secrets: id, organization_id, key, value, created_by_id, created_at, updated_at
acl: id, secret_id, subject_type, subject_id, can_read, can_write
team_memberships: id, team_id, user_id
```

## API Endpoints

### Authentication
```
GET  /auth/github/start        - Initiate OAuth
GET  /auth/github/callback     - OAuth callback  
GET  /auth/cli-exchange        - Token exchange
```

### Secrets
```
GET    /secrets                - List authorized secrets
POST   /secrets                - Create secret with ACL
GET    /secrets/{id}           - Get specific secret
PUT    /secrets/{id}           - Update secret/permissions
DELETE /secrets/{id}           - Delete secret
```

### Teams & Users
```
GET  /teams                    - List org teams
POST /teams                    - Create team (admin)
GET  /users                    - List org users
GET  /teams/{id}/members       - List team members
POST /teams/{id}/members       - Add member (admin)
```

### Administration
```
POST   /admin/users            - Create user (admin)
DELETE /admin/users/{id}       - Delete user (admin)  
PUT    /admin/users/{id}/promote - Promote to admin
DELETE /admin/teams/{id}       - Delete team (admin)
```

## Security Features
- CSRF protection via cryptographically signed state
- JWT tokens with configurable expiration
- One-time token exchange (CLI tokens single-use)
- Organization-level data isolation
- Permission validation on every operation

## Development

### Project Structure
```
backend/app/
├── main.py          # FastAPI app and endpoints
├── auth.py          # JWT and OAuth utilities  
├── crud.py          # Database operations
├── models.py        # SQLModel schema
└── config.py        # Environment config

cli/src/
├── app.tsx          # Main Ink application
├── config.ts        # Token persistence
└── screens/         # UI components
```

### Database Operations
- **Create**: Users auto-assigned to organization, secrets get creator ACL
- **Read**: Permission filtering applied to all list operations  
- **Update**: Write permission validation, ACL replacement
- **Delete**: Cascade deletes for related records

### CLI Interface
- Arrow key navigation, Enter/Escape controls
- Real-time secret creation with sharing wizard
- Team and user selection interfaces
- Admin panel for user/team management
- Status indicators and error handling

## Assignment Completion

✅ **CLI with Ink**: React-based terminal interface  
✅ **Backend**: FastAPI web server with REST API  
✅ **Secret Storage**: Key/value pairs with authorization  
✅ **OAuth2 Login**: GitHub authentication with browser flow  
✅ **Session Persistence**: JWT storage across CLI restarts  
✅ **User/Team/Org Model**: Complete hierarchical structure  
✅ **Admin Operations**: User/team creation and management  
✅ **Authorization**: Granular read/write permissions  
✅ **All Required Operations**: Login, logout, list, create, admin functions
