#!/usr/bin/env python3
"""
Manual Testing Script for Permissions
Run this to set up test scenarios you can verify in the CLI
"""

import sqlite3
import sys
from datetime import datetime

print("=" * 60)
print("PERMISSIONS TESTING SETUP")
print("=" * 60)

# Connect to database
try:
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    print("✅ Connected to database")
except Exception as e:
    print(f"❌ Cannot connect to database: {e}")
    print("Make sure you're in the backend directory!")
    sys.exit(1)

# Get your user info
cursor.execute("SELECT id, name, email, organization_id FROM user LIMIT 1")
user = cursor.fetchone()
if not user:
    print("❌ No users found. Please login first via CLI")
    sys.exit(1)

YOUR_USER_ID = user[0]
YOUR_NAME = user[1]
YOUR_ORG_ID = user[3]

print(f"\n📝 Your Info:")
print(f"   User ID: {YOUR_USER_ID}")
print(f"   Name: {YOUR_NAME}")
print(f"   Org ID: {YOUR_ORG_ID}")

print("\n" + "=" * 60)
print("CREATING TEST SCENARIOS")
print("=" * 60)

# Scenario 1: Organization-wide readable secret
print("\n1️⃣ Creating ORG-WIDE secret (everyone can read)...")
try:
    # Create secret as if another user created it
    cursor.execute("""
        INSERT INTO secret (organization_id, key, value, created_by_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (YOUR_ORG_ID, 'ORG_WIFI_PASSWORD', 'CompanyWifi2024!', 9999))
    
    secret_id = cursor.lastrowid
    
    # Add org-wide read permission
    cursor.execute("""
        INSERT INTO acl (secret_id, subject_type, subject_id, can_read, can_write)
        VALUES (?, 'org', NULL, 1, 0)
    """, (secret_id,))
    
    print(f"   ✅ Created: ORG_WIFI_PASSWORD (ID: {secret_id})")
    print(f"   → You should see this even though user 9999 created it")
except sqlite3.IntegrityError:
    print("   ⚠️  Already exists")

# Scenario 2: Team-only secret
print("\n2️⃣ Creating TEAM-ONLY secret...")
try:
    # First create a team
    cursor.execute("""
        INSERT INTO team (name, organization_id, created_at)
        VALUES (?, ?, datetime('now'))
    """, ('Backend Team', YOUR_ORG_ID))
    team_id = cursor.lastrowid
    
    # Add you to the team
    cursor.execute("""
        INSERT INTO team_membership (team_id, user_id)
        VALUES (?, ?)
    """, (team_id, YOUR_USER_ID))
    
    # Create a secret
    cursor.execute("""
        INSERT INTO secret (organization_id, key, value, created_by_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (YOUR_ORG_ID, 'BACKEND_DATABASE_URL', 'postgres://team-secret', 8888))
    secret_id = cursor.lastrowid
    
    # Give team read permission
    cursor.execute("""
        INSERT INTO acl (secret_id, subject_type, subject_id, can_read, can_write)
        VALUES (?, 'team', ?, 1, 0)
    """, (secret_id, team_id))
    
    print(f"   ✅ Created: BACKEND_DATABASE_URL (ID: {secret_id})")
    print(f"   ✅ Created: Backend Team (ID: {team_id})")
    print(f"   ✅ Added you to Backend Team")
    print(f"   → You should see this because you're in the team")
except sqlite3.IntegrityError:
    print("   ⚠️  Already exists")

# Scenario 3: Secret you DON'T have access to
print("\n3️⃣ Creating RESTRICTED secret (you can't see)...")
try:
    # Create secret with no permissions for you
    cursor.execute("""
        INSERT INTO secret (organization_id, key, value, created_by_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (YOUR_ORG_ID, 'CEO_PRIVATE_KEY', 'top-secret-ceo-only', 7777))
    secret_id = cursor.lastrowid
    
    # Give permission to a different user (not you)
    cursor.execute("""
        INSERT INTO acl (secret_id, subject_type, subject_id, can_read, can_write)
        VALUES (?, 'user', ?, 1, 1)
    """, (secret_id, 5555))  # User 5555 doesn't exist
    
    print(f"   ✅ Created: CEO_PRIVATE_KEY (ID: {secret_id})")
    print(f"   → You should NOT see this (only user 5555 can)")
except sqlite3.IntegrityError:
    print("   ⚠️  Already exists")

# Scenario 4: Secret with WRITE permission for your team
print("\n4️⃣ Creating EDITABLE team secret...")
try:
    # Get the Backend Team ID we created
    cursor.execute("SELECT id FROM team WHERE name = 'Backend Team' AND organization_id = ?", (YOUR_ORG_ID,))
    team = cursor.fetchone()
    if team:
        team_id = team[0]
        
        # Create a secret
        cursor.execute("""
            INSERT INTO secret (organization_id, key, value, created_by_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (YOUR_ORG_ID, 'TEAM_EDITABLE_CONFIG', 'team-can-edit-this', 6666))
        secret_id = cursor.lastrowid
        
        # Give team write permission
        cursor.execute("""
            INSERT INTO acl (secret_id, subject_type, subject_id, can_read, can_write)
            VALUES (?, 'team', ?, 1, 1)
        """, (secret_id, team_id))
        
        print(f"   ✅ Created: TEAM_EDITABLE_CONFIG (ID: {secret_id})")
        print(f"   → You should see ✓ (can edit) because your team has write access")
except sqlite3.IntegrityError:
    print("   ⚠️  Already exists")

# Scenario 5: Your own secret (always have full access)
print("\n5️⃣ Creating YOUR secret...")
try:
    cursor.execute("""
        INSERT INTO secret (organization_id, key, value, created_by_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (YOUR_ORG_ID, 'MY_PERSONAL_TOKEN', 'only-i-control-this', YOUR_USER_ID))
    secret_id = cursor.lastrowid
    
    # Creator always gets full access
    cursor.execute("""
        INSERT INTO acl (secret_id, subject_type, subject_id, can_read, can_write)
        VALUES (?, 'user', ?, 1, 1)
    """, (secret_id, YOUR_USER_ID))
    
    print(f"   ✅ Created: MY_PERSONAL_TOKEN (ID: {secret_id})")
    print(f"   → You should see ✓ (can edit) because you created it")
except sqlite3.IntegrityError:
    print("   ⚠️  Already exists")

# Commit all changes
conn.commit()

print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

# Show what should be visible
cursor.execute("""
    SELECT DISTINCT s.key, s.created_by_id,
           CASE 
               WHEN s.created_by_id = ? THEN 'You created'
               ELSE 'Other user created'
           END as creator,
           a.subject_type,
           CASE
               WHEN a.subject_type = 'org' THEN 'Org-wide'
               WHEN a.subject_type = 'team' THEN 'Via team'
               WHEN a.subject_type = 'user' AND a.subject_id = ? THEN 'Direct to you'
               ELSE 'Other'
           END as access_reason,
           a.can_write
    FROM secret s
    LEFT JOIN acl a ON s.id = a.secret_id
    WHERE s.organization_id = ?
    ORDER BY s.key
""", (YOUR_USER_ID, YOUR_USER_ID, YOUR_ORG_ID))

results = cursor.fetchall()

print("\n📋 Secrets in your organization:")
print("-" * 60)
for row in results:
    key, created_by, creator, subject_type, reason, can_write = row
    write = "✓ Can Edit" if can_write else "✗ Read Only"
    print(f"{key:30} | {creator:20} | {reason:15} | {write}")

print("\n" + "=" * 60)
print("TEST IN CLI")
print("=" * 60)
print("""
1. Go to your CLI and select "View Secrets"
2. You SHOULD see:
   ✅ ORG_WIFI_PASSWORD (org-wide permission)
   ✅ BACKEND_DATABASE_URL (you're in Backend Team)
   ✅ TEAM_EDITABLE_CONFIG (with ✓ for write)
   ✅ MY_PERSONAL_TOKEN (you created it)
   
3. You should NOT see:
   ❌ CEO_PRIVATE_KEY (no permission)

4. Test write permissions:
   - Try updating TEAM_EDITABLE_CONFIG (should work)
   - Try updating ORG_WIFI_PASSWORD (should update if no one else created it)

5. Check the database after testing:
   sqlite3 app.db
   SELECT * FROM secret WHERE key LIKE '%TEAM%';
   SELECT * FROM acl WHERE subject_type = 'team';
""")

conn.close()
print("\n✅ Test setup complete!")