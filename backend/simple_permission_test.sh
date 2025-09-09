#!/bin/bash

echo "======================================"
echo "SIMPLE PERMISSION TEST"
echo "======================================"
echo ""
echo "This script will create test secrets with different permissions"
echo "Then you can check in the CLI to see which ones are visible"
echo ""

# Check if database exists
if [ ! -f "app.db" ]; then
    echo "❌ Error: app.db not found. Are you in the backend directory?"
    exit 1
fi

echo "📝 Setting up test scenarios..."
echo ""

# Test 1: Organization-wide secret
echo "1. Creating ORG_PUBLIC_INFO (everyone in org can see)..."
sqlite3 app.db <<EOF
-- Create a secret that everyone can read
INSERT OR IGNORE INTO secret (id, organization_id, key, value, created_by_id, created_at, updated_at)
VALUES (1000, 1, 'ORG_PUBLIC_INFO', 'This is visible to everyone', 999, datetime('now'), datetime('now'));

-- Give org-wide read permission
INSERT OR IGNORE INTO acl (secret_id, subject_type, subject_id, can_read, can_write)
VALUES (1000, 'org', NULL, 1, 0);
EOF

# Test 2: Private secret you can't see
echo "2. Creating PRIVATE_TO_OTHERS (you should NOT see this)..."
sqlite3 app.db <<EOF
-- Create a secret only user 888 can see
INSERT OR IGNORE INTO secret (id, organization_id, key, value, created_by_id, created_at, updated_at)
VALUES (1001, 1, 'PRIVATE_TO_OTHERS', 'You cannot see this', 888, datetime('now'), datetime('now'));

-- Give permission only to user 888 (who doesn't exist)
INSERT OR IGNORE INTO acl (secret_id, subject_type, subject_id, can_read, can_write)
VALUES (1001, 'user', 888, 1, 1);
EOF

# Test 3: Team secret (with you in the team)
echo "3. Creating TEAM_SECRET (you're in the team, so you can see)..."

# First get your user ID
YOUR_USER_ID=$(sqlite3 app.db "SELECT id FROM user LIMIT 1;")
echo "   Your user ID is: $YOUR_USER_ID"

sqlite3 app.db <<EOF
-- Create a test team
INSERT OR IGNORE INTO team (id, name, organization_id, created_at)
VALUES (100, 'Test Team', 1, datetime('now'));

-- Add you to the team
INSERT OR IGNORE INTO team_membership (team_id, user_id)
VALUES (100, $YOUR_USER_ID);

-- Create a team secret
INSERT OR IGNORE INTO secret (id, organization_id, key, value, created_by_id, created_at, updated_at)
VALUES (1002, 1, 'TEAM_SECRET', 'Only team members see this', 777, datetime('now'), datetime('now'));

-- Give team read permission
INSERT OR IGNORE INTO acl (secret_id, subject_type, subject_id, can_read, can_write)
VALUES (1002, 'team', 100, 1, 0);
EOF

echo ""
echo "======================================"
echo "✅ TEST SETUP COMPLETE!"
echo "======================================"
echo ""
echo "Now go to your CLI and check 'View Secrets'"
echo ""
echo "You SHOULD see:"
echo "  ✅ ORG_PUBLIC_INFO (because of org-wide permission)"
echo "  ✅ TEAM_SECRET (because you're in Test Team)"
echo ""
echo "You should NOT see:"
echo "  ❌ PRIVATE_TO_OTHERS (only user 888 can see it)"
echo ""
echo "======================================"
echo ""
echo "To verify in database, run:"
echo "  sqlite3 app.db \"SELECT key FROM secret;\""
echo "  sqlite3 app.db \"SELECT * FROM acl WHERE subject_type='org';\""
echo "  sqlite3 app.db \"SELECT * FROM acl WHERE subject_type='team';\""