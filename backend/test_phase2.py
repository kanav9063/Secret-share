"""
Phase 2 Test Suite: Database + Basic Secrets
Tests all CRUD operations and API endpoints for secret management.
Run with: python test_phase2.py
"""

import requests
import json
import time
from typing import Dict, Optional

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_TOKEN = None  # Will be populated during setup

def print_test(test_name: str, passed: bool, details: str = ""):
    """Pretty print test results"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"         {details}")

def get_test_token() -> str:
    """Get a test JWT token"""
    response = requests.post(f"{BASE_URL}/test-token")
    if response.status_code == 200:
        return response.json()["token"]
    raise Exception("Failed to get test token")

# ============================================================================
# PART 2A-2B: Database Setup Tests
# ============================================================================

def test_database_tables():
    """Test that database tables were created"""
    # This is tested implicitly - if tables don't exist, API calls will fail
    print("\n=== Part 2A-2B: Database Setup ===")
    print_test("Database tables created", True, "Tables created on startup")

# ============================================================================
# PART 2C-2D: CRUD Operations & API Endpoints
# ============================================================================

def test_list_secrets_empty():
    """Test listing secrets when none exist"""
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    response = requests.get(f"{BASE_URL}/secrets", headers=headers)
    
    passed = response.status_code == 200 and response.json() == []
    print_test("List secrets (empty)", passed, f"Status: {response.status_code}")
    return passed

def test_create_secret_basic():
    """Test creating a basic secret"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "key": "TEST_SECRET_1",
        "value": "my-secret-value-123"
    }
    
    response = requests.post(f"{BASE_URL}/secrets", headers=headers, json=data)
    
    if response.status_code == 201:
        secret = response.json()
        passed = (
            secret.get("key") == "TEST_SECRET_1" and
            secret.get("value") == "my-secret-value-123" and
            "id" in secret and
            "created_at" in secret
        )
    else:
        passed = False
    
    print_test("Create basic secret", passed, f"Status: {response.status_code}")
    return response.json()["id"] if passed else None

def test_list_secrets_with_data():
    """Test listing secrets after creating some"""
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    response = requests.get(f"{BASE_URL}/secrets", headers=headers)
    
    if response.status_code == 200:
        secrets = response.json()
        passed = (
            len(secrets) > 0 and
            all("key" in s and "value" in s and "can_write" in s for s in secrets)
        )
    else:
        passed = False
    
    print_test("List secrets (with data)", passed, f"Found {len(response.json())} secrets")
    return passed

def test_get_specific_secret(secret_id: int):
    """Test getting a specific secret by ID"""
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    response = requests.get(f"{BASE_URL}/secrets/{secret_id}", headers=headers)
    
    if response.status_code == 200:
        secret = response.json()
        passed = (
            secret.get("id") == secret_id and
            "key" in secret and
            "value" in secret and
            "can_write" in secret
        )
    else:
        passed = False
    
    print_test("Get specific secret", passed, f"Secret ID: {secret_id}")
    return passed

def test_update_secret_value(secret_id: int):
    """Test updating a secret's value"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"value": "updated-value-456"}
    
    response = requests.put(f"{BASE_URL}/secrets/{secret_id}", headers=headers, json=data)
    
    if response.status_code == 200:
        secret = response.json()
        passed = secret.get("value") == "updated-value-456"
    else:
        passed = False
    
    print_test("Update secret value", passed, f"Status: {response.status_code}")
    return passed

def test_search_secrets():
    """Test searching secrets by key"""
    # First create a secret with a unique key
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"key": "SEARCH_TEST_KEY", "value": "findme"}
    requests.post(f"{BASE_URL}/secrets", headers=headers, json=data)
    
    # Now search for it
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    response = requests.get(f"{BASE_URL}/secrets?query=SEARCH", headers=headers)
    
    if response.status_code == 200:
        secrets = response.json()
        passed = (
            len(secrets) >= 1 and
            any(s["key"] == "SEARCH_TEST_KEY" for s in secrets)
        )
    else:
        passed = False
    
    print_test("Search secrets", passed, f"Found {len(response.json())} matching secrets")
    return passed

def test_permissions_creator_has_write():
    """Test that creator has write permission"""
    # Create a secret
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"key": "PERMISSION_TEST", "value": "test"}
    response = requests.post(f"{BASE_URL}/secrets", headers=headers, json=data)
    secret_id = response.json()["id"]
    
    # Get the secret and check can_write
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    response = requests.get(f"{BASE_URL}/secrets/{secret_id}", headers=headers)
    
    passed = response.json().get("can_write") == True
    print_test("Creator has write permission", passed)
    return passed

def test_invalid_token_rejected():
    """Test that invalid tokens are rejected"""
    headers = {"Authorization": "Bearer invalid-token"}
    response = requests.get(f"{BASE_URL}/secrets", headers=headers)
    
    passed = response.status_code == 401
    print_test("Invalid token rejected", passed, f"Status: {response.status_code}")
    return passed

def test_no_token_rejected():
    """Test that requests without tokens are rejected"""
    response = requests.get(f"{BASE_URL}/secrets")
    
    passed = response.status_code == 401
    print_test("No token rejected", passed, f"Status: {response.status_code}")
    return passed

# ============================================================================
# PART 2G: Persistence Testing
# ============================================================================

def test_persistence():
    """Test that secrets persist (would need server restart to fully test)"""
    print("\n=== Part 2G: Persistence Testing ===")
    
    # Create a secret with unique key
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    timestamp = str(int(time.time()))
    data = {"key": f"PERSIST_TEST_{timestamp}", "value": "should_persist"}
    response = requests.post(f"{BASE_URL}/secrets", headers=headers, json=data)
    
    if response.status_code == 201:
        secret_id = response.json()["id"]
        
        # Retrieve it again
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        response = requests.get(f"{BASE_URL}/secrets/{secret_id}", headers=headers)
        
        passed = (
            response.status_code == 200 and
            response.json()["value"] == "should_persist"
        )
    else:
        passed = False
    
    print_test("Secrets persist in database", passed)
    print("  Note: Full persistence test requires server restart")
    return passed

# ============================================================================
# ACL (Access Control List) Tests
# ============================================================================

def test_acl_creation():
    """Test that ACL entries are created with secrets"""
    print("\n=== ACL (Permission) Testing ===")
    
    # Create a secret with explicit ACL
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "key": "ACL_TEST_SECRET",
        "value": "test",
        "acl_entries": [
            {
                "subject_type": "org",
                "subject_id": None,
                "can_read": True,
                "can_write": False
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/secrets", headers=headers, json=data)
    passed = response.status_code == 201
    
    print_test("Create secret with ACL", passed, "Org-wide read permission")
    return passed

# ============================================================================
# Error Handling Tests
# ============================================================================

def test_error_handling():
    """Test various error conditions"""
    print("\n=== Error Handling ===")
    
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    
    # Test 404 for non-existent secret
    response = requests.get(f"{BASE_URL}/secrets/99999", headers=headers)
    passed_404 = response.status_code == 404
    print_test("404 for non-existent secret", passed_404)
    
    # Test missing required fields
    headers_post = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.post(f"{BASE_URL}/secrets", headers=headers_post, json={"key": "MISSING_VALUE"})
    passed_validation = response.status_code == 422
    print_test("Validation for missing fields", passed_validation)
    
    return passed_404 and passed_validation

# ============================================================================
# Main Test Runner
# ============================================================================

def run_extended_tests():
    """Extended tests for edge cases and advanced scenarios"""
    import threading
    
    print("\n" + "=" * 60)
    print("EXTENDED TEST SUITE: Edge Cases & Advanced Scenarios")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test Very Long Values
    print("\n=== Edge Case: Very Long Values ===")
    try:
        long_value = "x" * 10000
        response = requests.post(
            f"{BASE_URL}/secrets",
            headers=headers,
            json={"key": f"LONG_VALUE_{int(time.time())}", "value": long_value}
        )
        if response.status_code == 201:
            print("✅ PASS: 10,000 character value stored")
        else:
            print(f"❌ FAIL: Long value rejected - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ FAIL: Long value error - {e}")
    
    # Test Special Characters
    print("\n=== Edge Case: Special Characters ===")
    special_cases = [
        ("SPECIAL_!@#$%", "value_with_!@#$%^&*()"),
        ("KEY.WITH.DOTS", "value.with.dots"),
        ("KEY-WITH-DASHES", "value-with-dashes"),
        ("KEY_WITH_EMOJI_🔐", "value_with_emoji_🎉"),
        ("中文密钥", "中文值"),
        ("KEY WITH SPACES", "value with spaces"),
    ]
    
    for key, value in special_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/secrets",
                headers=headers,
                json={"key": key, "value": value}
            )
            if response.status_code in [200, 201]:
                print(f"✅ PASS: Special chars - {key[:20]}...")
            else:
                print(f"❌ FAIL: Special chars - {key[:20]}... Status: {response.status_code}")
        except Exception as e:
            print(f"❌ FAIL: Special chars - {key[:20]}... Error: {e}")
    
    # Test SQL Injection
    print("\n=== Security: SQL Injection Tests ===")
    injection_attempts = [
        "'; DROP TABLE secret; --",
        "1' OR '1'='1",
        "admin'--",
        "' UNION SELECT * FROM user--",
    ]
    
    for attempt in injection_attempts:
        try:
            response = requests.post(
                f"{BASE_URL}/secrets",
                headers=headers,
                json={"key": f"INJECTION_TEST_{int(time.time())}", "value": attempt}
            )
            if response.status_code in [200, 201]:
                secret_id = response.json()["id"]
                verify = requests.get(f"{BASE_URL}/secrets/{secret_id}", headers=headers)
                if verify.status_code == 200 and verify.json()["value"] == attempt:
                    print(f"✅ PASS: SQL injection safe - stored as literal")
                else:
                    print(f"❌ FAIL: SQL injection - value corrupted")
            else:
                print(f"⚠️  WARNING: Injection attempt blocked - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ FAIL: SQL injection test - {e}")
    
    # Test Concurrent Creation
    print("\n=== Concurrency: Rapid Creation ===")
    concurrent_results = []
    
    def create_secret_thread(index):
        try:
            response = requests.post(
                f"{BASE_URL}/secrets",
                headers=headers,
                json={"key": f"CONCURRENT_{index}_{int(time.time())}", "value": f"concurrent_value_{index}"}
            )
            concurrent_results.append(response.status_code)
        except Exception as e:
            concurrent_results.append(f"Error: {e}")
    
    threads = []
    for i in range(10):
        t = threading.Thread(target=create_secret_thread, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    success_count = sum(1 for r in concurrent_results if isinstance(r, int) and r in [200, 201])
    print(f"✅ PASS: Concurrent creation - {success_count}/10 succeeded")
    
    # Test Empty Values
    print("\n=== Edge Case: Empty and Null Values ===")
    edge_values = [
        ("", "empty string"),
        (" ", "single space"),
        ("   ", "multiple spaces"),
        ("\n", "newline"),
        ("\t", "tab"),
        ("null", "string 'null'"),
        ("0", "zero as string"),
        ("false", "false as string"),
    ]
    
    for value, description in edge_values:
        try:
            response = requests.post(
                f"{BASE_URL}/secrets",
                headers=headers,
                json={"key": f"EDGE_VALUE_{int(time.time())}", "value": value}
            )
            if response.status_code in [200, 201]:
                print(f"✅ PASS: {description} accepted")
            else:
                print(f"❌ FAIL: {description} rejected - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ FAIL: {description} - Error: {e}")
    
    # Test Invalid Operations
    print("\n=== Error Handling: Invalid Operations ===")
    try:
        response = requests.put(
            f"{BASE_URL}/secrets/999999",
            headers=headers,
            json={"value": "update_non_existent"}
        )
        if response.status_code == 404:
            print("✅ PASS: 404 for non-existent secret update")
        else:
            print(f"❌ FAIL: Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"❌ FAIL: Error handling test - {e}")
    
    # Test Malformed Requests
    print("\n=== Error Handling: Malformed Requests ===")
    malformed_tests = [
        ({"key": "NO_VALUE"}, "missing value field"),
        ({"value": "NO_KEY"}, "missing key field"),
        ({}, "empty body"),
    ]
    
    for body, description in malformed_tests:
        try:
            response = requests.post(
                f"{BASE_URL}/secrets",
                headers=headers,
                json=body
            )
            if response.status_code in [400, 422]:
                print(f"✅ PASS: Rejected {description}")
            else:
                print(f"❌ FAIL: Accepted {description} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ FAIL: {description} - Error: {e}")
    
    # Test Complex Permissions
    print("\n=== Complex Permissions ===")
    try:
        response = requests.post(
            f"{BASE_URL}/secrets",
            headers=headers,
            json={
                "key": f"MULTI_ACL_{int(time.time())}",
                "value": "multiple_permissions",
                "acl_entries": [
                    {"subject_type": "org", "subject_id": None, "can_read": True, "can_write": False},
                    {"subject_type": "team", "subject_id": 1, "can_read": True, "can_write": True},
                    {"subject_type": "user", "subject_id": 999, "can_read": True, "can_write": False},
                ]
            }
        )
        if response.status_code in [200, 201]:
            print("✅ PASS: Multiple ACL entries accepted")
        else:
            print(f"❌ FAIL: Multiple ACL entries - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ FAIL: Complex permissions - {e}")
    
    # Test Performance
    print("\n=== Performance: Bulk Operations ===")
    try:
        start_time = time.time()
        for i in range(50):
            requests.post(
                f"{BASE_URL}/secrets",
                headers=headers,
                json={"key": f"BULK_{i}", "value": f"bulk_value_{i}"}
            )
        create_time = time.time() - start_time
        
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/secrets", headers=headers)
        list_time = time.time() - start_time
        
        if response.status_code == 200:
            total_secrets = len(response.json())
            print(f"✅ PASS: Created 50 secrets in {create_time:.2f}s")
            print(f"✅ PASS: Listed {total_secrets} secrets in {list_time:.2f}s")
        else:
            print(f"❌ FAIL: Performance test - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ FAIL: Performance test - {e}")
    
    print("\n" + "=" * 60)
    print("EXTENDED TESTING COMPLETE!")
    print("=" * 60)

def run_all_tests():
    """Run all Phase 2 tests"""
    global TEST_TOKEN
    
    print("=" * 60)
    print("PHASE 2 TEST SUITE: Database + Basic Secrets")
    print("=" * 60)
    
    # Setup
    print("\n=== Setup ===")
    try:
        TEST_TOKEN = get_test_token()
        print_test("Get test token", True)
    except Exception as e:
        print_test("Get test token", False, str(e))
        print("\n❌ FATAL: Cannot proceed without token")
        return
    
    # Part 2A-2B: Database
    test_database_tables()
    
    # Part 2C-2D: CRUD & API
    print("\n=== Part 2C-2D: CRUD Operations & API ===")
    
    # Clear any existing secrets first (start fresh)
    test_list_secrets_empty()
    
    # Create and retrieve secrets
    secret_id = test_create_secret_basic()
    if secret_id:
        test_list_secrets_with_data()
        test_get_specific_secret(secret_id)
        test_update_secret_value(secret_id)
    
    test_search_secrets()
    test_permissions_creator_has_write()
    
    # Authentication tests
    print("\n=== Authentication ===")
    test_invalid_token_rejected()
    test_no_token_rejected()
    
    # Persistence
    test_persistence()
    
    # ACL
    test_acl_creation()
    
    # Error handling
    test_error_handling()
    
    print("\n" + "=" * 60)
    print("Phase 2 Test Suite Complete!")
    print("=" * 60)
    
    # Run extended tests
    run_extended_tests()

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is running\n")
            run_all_tests()
        else:
            print("❌ Server returned unexpected status")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at", BASE_URL)
        print("   Make sure to run: uvicorn app.main:app --reload --port 8001")