#!/usr/bin/env python3
"""
Test Data Setup Script
Creates dummy users, teams, and secrets with various permissions
Run this after starting the backend to populate test data
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"

# First, you need to login and get your token
print("=" * 60)
print("TEST DATA SETUP SCRIPT")
print("=" * 60)
print("\nIMPORTANT: You must be logged in first!")
print("1. Run the CLI and login with GitHub")
print("2. Copy your token from: ~/.config/secret-cli/config.json")
print("3. Paste it below")
print("=" * 60)

TOKEN = input("\nPaste your JWT token here: ").strip()

if not TOKEN:
    print("❌ No token provided. Exiting.")
    exit(1)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Test connection
try:
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    if response.status_code != 200:
        print(f"❌ Invalid token or backend not running: {response.status_code}")
        exit(1)
    current_user = response.json()
    print(f"\n✅ Authenticated as: {current_user['name']} ({current_user['email']})")
    print(f"   Organization ID: {current_user['organization_id']}")
    print(f"   User ID: {current_user['id']}")
except Exception as e:
    print(f"❌ Cannot connect to backend: {e}")
    exit(1)

print("\n" + "=" * 60)
print("CREATING TEST DATA")
print("=" * 60)

# Track what we create
created_data = {
    "users": [],
    "teams": [],
    "secrets": [],
    "shared_secrets": []
}

# ============================================================
# STEP 1: Create dummy users (simulated - we'll note them)
# ============================================================
print("\n📝 Simulated Users (imagine these exist):")
print("-" * 40)

simulated_users = [
    {"id": 100, "name": "Alice Developer", "email": "alice@example.com", "is_admin": False},
    {"id": 101, "name": "Bob Manager", "email": "bob@example.com", "is_admin": True},
    {"id": 102, "name": "Charlie Intern", "email": "charlie@example.com", "is_admin": False},
    {"id": 103, "name": "Diana DevOps", "email": "diana@example.com", "is_admin": False},
]

for user in simulated_users:
    print(f"  User #{user['id']}: {user['name']} ({user['email']}) {'[ADMIN]' if user['is_admin'] else ''}")

# ============================================================
# STEP 2: Create Teams (we can't actually create these yet without admin endpoints)
# But let's create secrets that WOULD be shared with teams
# ============================================================
print("\n📝 Simulated Teams:")
print("-" * 40)

simulated_teams = [
    {"id": 10, "name": "Backend Team", "members": [100, 103]},  # Alice, Diana
    {"id": 11, "name": "Frontend Team", "members": [102]},      # Charlie
    {"id": 12, "name": "DevOps Team", "members": [103]},        # Diana
    {"id": 13, "name": "Management", "members": [101]},         # Bob
]

for team in simulated_teams:
    members = ", ".join([f"User #{m}" for m in team['members']])
    print(f"  Team #{team['id']}: {team['name']} - Members: {members}")

# ============================================================
# STEP 3: Create Various Secrets with Different Permissions
# ============================================================
print("\n📝 Creating Secrets with Various Permissions:")
print("-" * 40)

test_secrets = [
    {
        "name": "PUBLIC_API_ENDPOINT",
        "key": "PUBLIC_API_ENDPOINT",
        "value": "https://api.example.com/v1",
        "description": "Organization-wide readable",
        "acl_entries": [
            {"subject_type": "org", "subject_id": None, "can_read": True, "can_write": False}
        ]
    },
    {
        "name": "DATABASE_PASSWORD",
        "key": "DATABASE_PASSWORD",
        "value": "postgres://user:pass@localhost/db",
        "description": "Backend team only (simulated team #10)",
        "acl_entries": [
            {"subject_type": "team", "subject_id": 10, "can_read": True, "can_write": False}
        ]
    },
    {
        "name": "ADMIN_SECRET",
        "key": "ADMIN_SECRET",
        "value": "only-admins-can-see-this",
        "description": "Admin only (simulated user #101 - Bob)",
        "acl_entries": [
            {"subject_type": "user", "subject_id": 101, "can_read": True, "can_write": True}
        ]
    },
    {
        "name": "DEPLOYMENT_KEY",
        "key": "DEPLOYMENT_KEY",
        "value": "ssh-rsa AAAAB3NzaC1yc2EA...",
        "description": "DevOps team can read and write (simulated team #12)",
        "acl_entries": [
            {"subject_type": "team", "subject_id": 12, "can_read": True, "can_write": True}
        ]
    },
    {
        "name": "SHARED_WITH_ALICE",
        "key": "SHARED_WITH_ALICE",
        "value": "alice-specific-secret",
        "description": "Shared with specific user (simulated user #100 - Alice)",
        "acl_entries": [
            {"subject_type": "user", "subject_id": 100, "can_read": True, "can_write": False}
        ]
    },
    {
        "name": "MY_PRIVATE_SECRET",
        "key": "MY_PRIVATE_SECRET",
        "value": "only-i-can-see-this",
        "description": "Private to creator (you)",
        "acl_entries": []  # Only creator can access
    },
    {
        "name": "FRONTEND_CONFIG",
        "key": "FRONTEND_CONFIG",
        "value": '{"theme": "dark", "api": "v2"}',
        "description": "Frontend team read-only (simulated team #11)",
        "acl_entries": [
            {"subject_type": "team", "subject_id": 11, "can_read": True, "can_write": False}
        ]
    },
    {
        "name": "WRITABLE_BY_BACKEND",
        "key": "WRITABLE_BY_BACKEND",
        "value": "backend-team-can-edit",
        "description": "Backend team can edit (simulated team #10)",
        "acl_entries": [
            {"subject_type": "team", "subject_id": 10, "can_read": True, "can_write": True}
        ]
    }
]

for secret_data in test_secrets:
    try:
        # Create the secret
        response = requests.post(
            f"{BASE_URL}/secrets",
            headers=headers,
            json={
                "key": secret_data["key"],
                "value": secret_data["value"],
                "acl_entries": secret_data["acl_entries"]
            }
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"  ✅ Created: {secret_data['name']}")
            print(f"     → {secret_data['description']}")
            created_data["secrets"].append(result)
        else:
            print(f"  ⚠️  {secret_data['name']}: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Failed to create {secret_data['name']}: {e}")

# ============================================================
# STEP 4: Show what was created
# ============================================================
print("\n" + "=" * 60)
print("TESTING PERMISSIONS")
print("=" * 60)

# Get all secrets to see what you have access to
try:
    response = requests.get(f"{BASE_URL}/secrets", headers=headers)
    if response.status_code == 200:
        secrets = response.json()
        print(f"\n✅ You can see {len(secrets)} secrets:")
        print("-" * 40)
        
        for secret in secrets:
            write_access = "✓ Can Edit" if secret.get("can_write") else "✗ Read Only"
            print(f"  • {secret['key'][:30].ljust(30)} - {write_access}")
            
        # Show what you CAN'T see (simulated)
        print("\n❌ Secrets you CANNOT see (if other users existed):")
        print("-" * 40)
        print("  • ADMIN_SECRET - Only Bob (admin) can see")
        print("  • SHARED_WITH_ALICE - Only Alice can see")
        print("  • Team secrets - Only team members can see")
        
except Exception as e:
    print(f"❌ Failed to list secrets: {e}")

# ============================================================
# STEP 5: Database Verification Queries
# ============================================================
print("\n" + "=" * 60)
print("DATABASE VERIFICATION")
print("=" * 60)
print("\nRun these SQL queries to verify the data:")
print("-" * 40)

verification_queries = """
-- Check all secrets
SELECT id, key, created_by_id FROM secret;

-- Check all ACL entries
SELECT 
    s.key,
    a.subject_type,
    a.subject_id,
    a.can_read,
    a.can_write
FROM acl a
JOIN secret s ON a.secret_id = s.id
ORDER BY s.key, a.subject_type;

-- Count permissions by type
SELECT 
    subject_type,
    COUNT(*) as count
FROM acl
GROUP BY subject_type;

-- Secrets with org-wide access
SELECT s.key
FROM secret s
JOIN acl a ON s.id = a.secret_id
WHERE a.subject_type = 'org';

-- Secrets with team access (simulated)
SELECT s.key, a.subject_id as team_id
FROM secret s
JOIN acl a ON s.id = a.secret_id
WHERE a.subject_type = 'team';
"""

print(verification_queries)

print("\n" + "=" * 60)
print("TEST SCENARIOS")
print("=" * 60)
print("""
1. ORG-WIDE ACCESS TEST:
   - "PUBLIC_API_ENDPOINT" should be visible to everyone
   - Any user in the org can read it
   
2. TEAM ACCESS TEST (Simulated):
   - "DATABASE_PASSWORD" is for Backend Team (#10)
   - If Alice (user #100) existed, she could see it
   - If Charlie (user #102) existed, he couldn't
   
3. USER-SPECIFIC ACCESS TEST (Simulated):
   - "SHARED_WITH_ALICE" is only for Alice (#100)
   - Only she could see it (if she existed)
   
4. WRITE PERMISSION TEST:
   - "DEPLOYMENT_KEY" - DevOps team can edit
   - "WRITABLE_BY_BACKEND" - Backend team can edit
   
5. PRIVATE SECRET TEST:
   - "MY_PRIVATE_SECRET" - Only you can see
   - No ACL entries except creator

6. ADMIN TEST (Simulated):
   - "ADMIN_SECRET" - Only Bob (admin) can see
   - Admins bypass all permissions in their org
""")

print("\n" + "=" * 60)
print("✅ TEST DATA SETUP COMPLETE!")
print("=" * 60)
print("\nNext steps:")
print("1. Check the CLI to see which secrets are visible")
print("2. Run the SQL queries above to verify ACL entries")
print("3. Test updating secrets you have write access to")
print("4. Try accessing secrets with different permission levels")