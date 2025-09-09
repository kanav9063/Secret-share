"""
Phase 4 Test Suite: Complete System
Tests admin operations, secret deletion, and user profiles.
Run with: python test_phase4.py
"""

import requests
import json
import time
from typing import Dict, Optional, List

# Test configuration
BASE_URL = "http://localhost:8001"
ADMIN_TOKEN = None  # Admin user token
USER_TOKEN = None   # Regular user token
CREATED_USER_ID = None  # ID of user created during test
CREATED_TEAM_ID = None  # ID of team created during test
SECRET_ID = None    # Test secret ID

def print_test(test_name: str, passed: bool, details: str = ""):
    """Pretty print test results"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"         {details}")

def get_admin_token() -> str:
    """Get a test JWT token for admin user"""
    try:
        response = requests.post(f"{BASE_URL}/test-token")
        if response.status_code == 200:
            return response.json()["token"]
        else:
            raise Exception(f"Failed to get admin token: {response.status_code}")
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to backend. Is it running on port 8001?")

# ============================================================================
# PART 4A: Admin User Management Tests
# ============================================================================

def test_admin_user_management():
    """Test admin user CRUD operations"""
    print("\n=== Part 4A: Admin User Management ===")
    global CREATED_USER_ID
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    # 1. Create a new user
    response = requests.post(
        f"{BASE_URL}/admin/users",
        params={
            "email": f"testuser-{int(time.time())}@example.com",
            "name": "Test User",
            "is_admin": False
        },
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        if "user" in data:
            CREATED_USER_ID = data["user"]["id"]
            print_test("Create user via admin", True, f"User ID: {CREATED_USER_ID}")
        else:
            print_test("Create user via admin", False, "No user in response")
    else:
        print_test("Create user via admin", False, f"Status: {response.status_code}")
    
    # 2. Promote user to admin
    if CREATED_USER_ID:
        response = requests.put(
            f"{BASE_URL}/admin/users/{CREATED_USER_ID}/promote",
            headers=headers
        )
        passed = response.status_code == 200
        print_test("Promote user to admin", passed, f"Status: {response.status_code}")
    
    # 3. Try to delete self (should fail)
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    if response.status_code == 200:
        my_id = response.json()["user"]["id"]
        response = requests.delete(
            f"{BASE_URL}/admin/users/{my_id}",
            headers=headers
        )
        passed = response.status_code == 400  # Should fail
        print_test("Prevent self-deletion", passed, f"Status: {response.status_code}")
    
    # 4. Delete created user
    if CREATED_USER_ID:
        response = requests.delete(
            f"{BASE_URL}/admin/users/{CREATED_USER_ID}",
            headers=headers
        )
        passed = response.status_code == 200
        print_test("Delete user", passed, f"Status: {response.status_code}")
        if passed:
            CREATED_USER_ID = None  # Clear since deleted

# ============================================================================
# PART 4B: Admin Team Management Tests
# ============================================================================

def test_admin_team_management():
    """Test admin team operations"""
    print("\n=== Part 4B: Admin Team Management ===")
    global CREATED_TEAM_ID
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    # 1. Create a team (already tested in Phase 3, but verify)
    response = requests.post(
        f"{BASE_URL}/teams?name=TestTeam-{int(time.time())}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        if "team" in data and data["team"]:
            CREATED_TEAM_ID = data["team"]["id"]
            print_test("Create team", True, f"Team ID: {CREATED_TEAM_ID}")
        else:
            print_test("Create team", False, "No team in response")
    else:
        print_test("Create team", False, f"Status: {response.status_code}")
    
    # 2. Add member to team
    if CREATED_TEAM_ID:
        # Get a user to add
        response = requests.get(f"{BASE_URL}/users", headers=headers)
        if response.status_code == 200:
            users = response.json()["users"]
            if len(users) > 1:
                # Add first non-self user
                for user in users:
                    response_me = requests.get(f"{BASE_URL}/me", headers=headers)
                    my_id = response_me.json()["user"]["id"]
                    if user["id"] != my_id:
                        response = requests.post(
                            f"{BASE_URL}/teams/{CREATED_TEAM_ID}/members?user_id={user['id']}",
                            headers=headers
                        )
                        passed = response.status_code == 200
                        print_test("Add team member", passed, f"Added user {user['id']}")
                        
                        # Remove member
                        if passed:
                            response = requests.delete(
                                f"{BASE_URL}/teams/{CREATED_TEAM_ID}/members/{user['id']}",
                                headers=headers
                            )
                            passed = response.status_code == 200
                            print_test("Remove team member", passed, f"Status: {response.status_code}")
                        break
    
    # 3. Delete team
    if CREATED_TEAM_ID:
        response = requests.delete(
            f"{BASE_URL}/admin/teams/{CREATED_TEAM_ID}",
            headers=headers
        )
        passed = response.status_code == 200
        print_test("Delete team", passed, f"Status: {response.status_code}")
        if passed:
            CREATED_TEAM_ID = None

# ============================================================================
# PART 4C: Secret Deletion Tests
# ============================================================================

def test_secret_deletion():
    """Test secret deletion functionality"""
    print("\n=== Part 4C: Secret Deletion ===")
    global SECRET_ID
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    # 1. Create a secret to delete
    secret_data = {
        "key": f"delete-test-{int(time.time())}",
        "value": "will-be-deleted",
        "acl_entries": []
    }
    
    response = requests.post(
        f"{BASE_URL}/secrets",
        headers=headers,
        json=secret_data
    )
    
    if response.status_code == 201:
        SECRET_ID = response.json()["id"]
        print_test("Create secret for deletion", True, f"Secret ID: {SECRET_ID}")
    else:
        print_test("Create secret for deletion", False, f"Status: {response.status_code}")
        return
    
    # 2. Verify secret exists
    response = requests.get(f"{BASE_URL}/secrets", headers=headers)
    if response.status_code == 200:
        secrets = response.json()
        found = any(s["id"] == SECRET_ID for s in secrets)
        print_test("Secret exists before deletion", found, f"Found: {found}")
    
    # 3. Delete the secret
    response = requests.delete(
        f"{BASE_URL}/secrets/{SECRET_ID}",
        headers=headers
    )
    passed = response.status_code == 200
    print_test("Delete secret", passed, f"Status: {response.status_code}")
    
    # 4. Verify secret is gone
    if passed:
        response = requests.get(f"{BASE_URL}/secrets", headers=headers)
        if response.status_code == 200:
            secrets = response.json()
            not_found = not any(s["id"] == SECRET_ID for s in secrets)
            print_test("Secret removed after deletion", not_found, f"Still exists: {not not_found}")
    
    # 5. Try to delete non-existent secret
    response = requests.delete(
        f"{BASE_URL}/secrets/999999",
        headers=headers
    )
    passed = response.status_code == 404
    print_test("Delete non-existent secret returns 404", passed, f"Status: {response.status_code}")

# ============================================================================
# PART 4D: User Profile Tests
# ============================================================================

def test_user_profile():
    """Test enhanced /me endpoint"""
    print("\n=== Part 4D: User Profile ===")
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    # 1. Get current user profile
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # Check for required fields
        has_user = "user" in data
        has_org = "organization" in data
        has_teams = "teams" in data
        
        if has_user:
            user = data["user"]
            has_user_fields = all(field in user for field in ["id", "email", "name", "is_admin"])
            print_test("Profile has user info", has_user_fields, 
                      f"User: {user.get('name', 'Unknown')}")
        else:
            print_test("Profile has user info", False, "Missing user field")
        
        if has_org and data["organization"]:
            org = data["organization"]
            has_org_fields = all(field in org for field in ["id", "name"])
            print_test("Profile has organization", has_org_fields, 
                      f"Org: {org.get('name', 'Unknown')}")
        else:
            print_test("Profile has organization", False, "Missing or null organization")
        
        if has_teams:
            teams = data["teams"]
            print_test("Profile has teams list", True, f"Member of {len(teams)} teams")
            
            # Check team structure if any teams exist
            if teams:
                team = teams[0]
                has_team_fields = all(field in team for field in ["id", "name"])
                print_test("Team data structure", has_team_fields, 
                          f"Sample team: {team.get('name', 'Unknown')}")
        else:
            print_test("Profile has teams list", False, "Missing teams field")
    else:
        print_test("Get user profile", False, f"Status: {response.status_code}")

# ============================================================================
# PART 4E: Authorization Tests
# ============================================================================

def test_authorization():
    """Test that non-admins cannot use admin endpoints"""
    print("\n=== Part 4E: Authorization ===")
    
    # This would require a non-admin token to test properly
    # For now, test with admin token and verify it works
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    # 1. Verify admin can access admin endpoints
    response = requests.post(
        f"{BASE_URL}/admin/users",
        params={
            "email": f"auth-test-{int(time.time())}@example.com",
            "name": "Auth Test",
            "is_admin": False
        },
        headers=headers
    )
    
    if response.status_code == 200:
        user_id = response.json()["user"]["id"]
        print_test("Admin can create users", True, f"Created user {user_id}")
        
        # Clean up
        requests.delete(f"{BASE_URL}/admin/users/{user_id}", headers=headers)
    else:
        print_test("Admin can create users", False, f"Status: {response.status_code}")
    
    # 2. Test without auth (should fail)
    response = requests.post(
        f"{BASE_URL}/admin/users",
        params={
            "email": "noauth@example.com",
            "name": "No Auth",
            "is_admin": False
        }
    )
    passed = response.status_code == 401
    print_test("Admin endpoints require auth", passed, f"Status: {response.status_code}")

# ============================================================================
# Integration Tests
# ============================================================================

def test_integration():
    """Test full admin workflow"""
    print("\n=== Integration Tests ===")
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    # Full workflow: Create user, create team, add user to team, create secret, share with team
    workflow_success = True
    created_items = {}
    
    try:
        # 1. Create user
        response = requests.post(
            f"{BASE_URL}/admin/users",
            params={
                "email": f"integration-{int(time.time())}@example.com",
                "name": "Integration User",
                "is_admin": False
            },
            headers=headers
        )
        if response.status_code == 200:
            created_items["user_id"] = response.json()["user"]["id"]
        else:
            workflow_success = False
        
        # 2. Create team
        response = requests.post(
            f"{BASE_URL}/teams?name=IntegrationTeam-{int(time.time())}",
            headers=headers
        )
        if response.status_code == 200:
            created_items["team_id"] = response.json()["team"]["id"]
        else:
            workflow_success = False
        
        # 3. Add user to team
        if "user_id" in created_items and "team_id" in created_items:
            response = requests.post(
                f"{BASE_URL}/teams/{created_items['team_id']}/members?user_id={created_items['user_id']}",
                headers=headers
            )
            workflow_success = workflow_success and response.status_code == 200
        
        # 4. Create secret shared with team
        if "team_id" in created_items:
            secret_data = {
                "key": f"integration-secret-{int(time.time())}",
                "value": "shared-with-team",
                "acl_entries": [{
                    "subject_type": "team",
                    "subject_id": created_items["team_id"],
                    "can_read": True,
                    "can_write": False
                }]
            }
            response = requests.post(
                f"{BASE_URL}/secrets",
                headers=headers,
                json=secret_data
            )
            if response.status_code == 201:
                created_items["secret_id"] = response.json()["id"]
            else:
                workflow_success = False
        
        print_test("Full admin workflow", workflow_success, 
                  f"Created: user={created_items.get('user_id')}, "
                  f"team={created_items.get('team_id')}, "
                  f"secret={created_items.get('secret_id')}")
        
        # Cleanup
        if "secret_id" in created_items:
            requests.delete(f"{BASE_URL}/secrets/{created_items['secret_id']}", headers=headers)
        if "team_id" in created_items:
            requests.delete(f"{BASE_URL}/admin/teams/{created_items['team_id']}", headers=headers)
        if "user_id" in created_items:
            requests.delete(f"{BASE_URL}/admin/users/{created_items['user_id']}", headers=headers)
            
    except Exception as e:
        print_test("Full admin workflow", False, str(e))

# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    """Run all Phase 4 tests"""
    print("=" * 60)
    print("PHASE 4 TEST SUITE: Complete System")
    print("=" * 60)
    
    # Setup
    print("\n=== Setup ===")
    global ADMIN_TOKEN
    try:
        ADMIN_TOKEN = get_admin_token()
        print_test("Get admin token", True, "Token acquired")
    except Exception as e:
        print_test("Get admin token", False, str(e))
        print("\n❌ Cannot continue without token")
        return
    
    # Run all test suites
    test_admin_user_management()
    test_admin_team_management()
    test_secret_deletion()
    test_user_profile()
    test_authorization()
    test_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("Phase 4 Testing Complete!")
    print("=" * 60)
    print("\nKey Features Tested:")
    print("✓ Admin user management (create, promote, delete)")
    print("✓ Admin team management (create, add/remove members, delete)")
    print("✓ Secret deletion")
    print("✓ Enhanced user profile (/me endpoint)")
    print("✓ Authorization checks")
    print("✓ Full integration workflow")
    
    print("\n⚠️  Note: Some tests require multiple user accounts")
    print("    for complete permission testing")

if __name__ == "__main__":
    main()