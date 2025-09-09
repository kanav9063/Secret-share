"""
Comprehensive Unit Tests for Phase 1: Authentication (1A-1H)
Tests all authentication components including:
- 1A: Health check endpoint
- 1B: GitHub OAuth configuration
- 1C: Environment configuration loading
- 1D: JWT token creation and validation
- 1E: OAuth flow (start, callback, exchange)
- 1F: Protected route authentication
- 1G: State management for CSRF protection
- 1H: GitHub user data retrieval
"""

import os
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer

# Set test environment variables before importing app
os.environ.update({
    "GITHUB_CLIENT_ID": "test_client_id",
    "GITHUB_CLIENT_SECRET": "test_client_secret",
    "JWT_SECRET": "test_jwt_secret_key",
    "STATE_SECRET": "test_state_secret_key",
    "BASE_URL": "http://localhost:8001",
    "ADMIN_EMAILS": "admin1@test.com,admin2@test.com"
})

from app.main import app
from app.auth import (
    create_jwt_token,
    verify_jwt_token,
    create_state,
    verify_state,
    get_github_user,
    pending_tokens
)
from app.config import settings

client = TestClient(app)


class TestPhase1A:
    """Test 1A: Health Check Endpoint"""
    
    def test_health_check_returns_200(self):
        """Test that health check endpoint returns 200 OK"""
        response = client.get("/health")
        assert response.status_code == 200
        
    def test_health_check_response_format(self):
        """Test that health check returns correct response format"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "secret-sharing-api"


class TestPhase1B:
    """Test 1B: GitHub OAuth Configuration"""
    
    def test_github_oauth_credentials_loaded(self):
        """Test that GitHub OAuth credentials are properly loaded"""
        assert settings.github_client_id == "test_client_id"
        assert settings.github_client_secret == "test_client_secret"
        
    def test_github_oauth_credentials_not_empty(self):
        """Test that GitHub OAuth credentials are not empty strings"""
        assert len(settings.github_client_id) > 0
        assert len(settings.github_client_secret) > 0


class TestPhase1C:
    """Test 1C: Environment Configuration"""
    
    def test_config_test_endpoint(self):
        """Test that config test endpoint works"""
        response = client.get("/config-test")
        assert response.status_code == 200
        data = response.json()
        assert data["config_loaded"] is True
        
    def test_environment_settings_loaded(self):
        """Test that all environment settings are properly loaded"""
        assert settings.base_url == "http://localhost:8001"
        assert settings.jwt_secret == "test_jwt_secret_key"
        assert settings.state_secret == "test_state_secret_key"
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_expiry_days == 7
        
    def test_admin_emails_parsing(self):
        """Test that admin emails are parsed correctly from comma-separated string"""
        admin_emails = settings.get_admin_emails_list()
        assert len(admin_emails) == 2
        assert "admin1@test.com" in admin_emails
        assert "admin2@test.com" in admin_emails
        
    def test_config_defaults(self):
        """Test that configuration defaults are set properly"""
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_expiry_days == 7


class TestPhase1D:
    """Test 1D: JWT Token Creation and Validation"""
    
    def test_create_jwt_token(self):
        """Test JWT token creation with user data"""
        user_data = {
            "sub": "12345",
            "email": "test@example.com",
            "name": "Test User"
        }
        token = create_jwt_token(user_data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
    def test_jwt_token_contains_expiration(self):
        """Test that JWT token contains expiration claim"""
        user_data = {"sub": "12345", "email": "test@example.com"}
        token = create_jwt_token(user_data)
        
        # Decode without verification to check claims
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert "exp" in decoded
        
    def test_jwt_token_expiry_time(self):
        """Test that JWT token expires in correct number of days"""
        user_data = {"sub": "12345"}
        token = create_jwt_token(user_data)
        
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        exp_timestamp = decoded["exp"]
        exp_date = datetime.fromtimestamp(exp_timestamp)
        
        # Check expiry is approximately 7 days from now
        expected_exp = datetime.utcnow() + timedelta(days=settings.jwt_expiry_days)
        diff = abs((exp_date - expected_exp).total_seconds())
        assert diff < 60  # Within 1 minute tolerance
        
    def test_verify_valid_jwt_token(self):
        """Test verification of a valid JWT token"""
        user_data = {
            "sub": "12345",
            "email": "test@example.com",
            "name": "Test User"
        }
        token = create_jwt_token(user_data)
        verified_data = verify_jwt_token(token)
        
        assert verified_data is not None
        assert verified_data["sub"] == "12345"
        assert verified_data["email"] == "test@example.com"
        assert verified_data["name"] == "Test User"
        
    def test_verify_invalid_jwt_token(self):
        """Test verification of an invalid JWT token"""
        invalid_token = "invalid.token.here"
        verified_data = verify_jwt_token(invalid_token)
        assert verified_data is None
        
    def test_verify_expired_jwt_token(self):
        """Test verification of an expired JWT token"""
        # Create token with past expiration
        user_data = {"sub": "12345"}
        past_time = datetime.utcnow() - timedelta(days=1)
        user_data["exp"] = past_time
        
        expired_token = jwt.encode(
            user_data,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm
        )
        
        verified_data = verify_jwt_token(expired_token)
        assert verified_data is None
        
    def test_test_token_endpoint(self):
        """Test the /test-token endpoint creates valid tokens"""
        response = client.post("/test-token")
        assert response.status_code == 200
        
        data = response.json()
        assert "token" in data
        assert "type" in data
        assert data["type"] == "Bearer"
        assert "expires_in_days" in data
        assert data["expires_in_days"] == 7
        
        # Verify the token is valid
        verified = verify_jwt_token(data["token"])
        assert verified is not None
        assert verified["email"] == "test@example.com"


class TestPhase1E:
    """Test 1E: OAuth Flow (Start, Callback, Exchange)"""
    
    def test_oauth_start_endpoint(self):
        """Test OAuth start endpoint creates proper redirect"""
        cli_token = "test_cli_token_123"
        response = client.get(f"/auth/github/start?cli_token={cli_token}")
        
        assert response.status_code == 307  # Redirect status
        location = response.headers.get("location")
        assert "github.com/login/oauth/authorize" in location
        assert f"client_id={settings.github_client_id}" in location
        assert "state=" in location
        
    def test_oauth_start_requires_cli_token(self):
        """Test OAuth start endpoint requires cli_token parameter"""
        response = client.get("/auth/github/start")
        assert response.status_code == 422  # Validation error
        
    @patch('app.main.get_github_user')
    @patch('httpx.AsyncClient.post')
    def test_oauth_callback_success(self, mock_post, mock_get_user):
        """Test OAuth callback handles successful GitHub authentication"""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "github_token_123"}
        mock_post.return_value = asyncio.coroutine(lambda: mock_response)()
        
        mock_get_user.return_value = asyncio.coroutine(lambda: {
            "id": 123,
            "login": "testuser",
            "email": "test@github.com",
            "name": "Test User"
        })()
        
        # Create valid state
        cli_token = "test_cli_token"
        state = create_state(cli_token)
        
        # Make callback request
        response = client.get(f"/auth/github/callback?code=test_code&state={state}")
        
        assert response.status_code == 200
        assert "Login Successful" in response.text
        
    def test_oauth_callback_invalid_state(self):
        """Test OAuth callback rejects invalid state"""
        response = client.get("/auth/github/callback?code=test_code&state=invalid_state")
        assert response.status_code == 400
        assert "Invalid state" in response.text
        
    def test_cli_exchange_not_ready(self):
        """Test CLI exchange returns 404 when token not ready"""
        response = client.get("/auth/cli-exchange?cli_token=nonexistent_token")
        assert response.status_code == 404
        
    def test_cli_exchange_success(self):
        """Test CLI exchange returns token when ready"""
        # Manually add a pending token
        cli_token = "test_cli_token_exchange"
        test_jwt = create_jwt_token({"sub": "123", "email": "test@example.com"})
        pending_tokens[cli_token] = {
            "token": test_jwt,
            "user": {"id": 123, "login": "testuser"}
        }
        
        response = client.get(f"/auth/cli-exchange?cli_token={cli_token}")
        assert response.status_code == 200
        
        data = response.json()
        assert "token" in data
        assert data["token"] == test_jwt
        assert "user" in data
        
        # Verify token was removed (one-time use)
        assert cli_token not in pending_tokens


class TestPhase1F:
    """Test 1F: Protected Route Authentication"""
    
    def test_protected_route_no_auth_header(self):
        """Test protected route returns 401 without auth header"""
        response = client.get("/test-protected")
        assert response.status_code == 401
        assert "No authorization header" in response.json()["detail"]
        
    def test_protected_route_invalid_format(self):
        """Test protected route rejects invalid auth format"""
        response = client.get(
            "/test-protected",
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401
        assert "Invalid authorization format" in response.json()["detail"]
        
    def test_protected_route_invalid_token(self):
        """Test protected route rejects invalid token"""
        response = client.get(
            "/test-protected",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]
        
    def test_protected_route_valid_token(self):
        """Test protected route accepts valid token"""
        # Create a valid token
        user_data = {
            "sub": "12345",
            "email": "test@example.com",
            "name": "Test User"
        }
        token = create_jwt_token(user_data)
        
        response = client.get(
            "/test-protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Token is valid!"
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"


class TestPhase1G:
    """Test 1G: State Management for CSRF Protection"""
    
    def test_create_state(self):
        """Test state creation with CLI token"""
        cli_token = "test_cli_token"
        state = create_state(cli_token)
        
        assert state is not None
        assert isinstance(state, str)
        assert len(state) > 0
        
    def test_verify_valid_state(self):
        """Test verification of valid state"""
        cli_token = "test_cli_token"
        state = create_state(cli_token)
        
        verified = verify_state(state)
        assert verified is not None
        assert verified["cli_token"] == cli_token
        
    def test_verify_invalid_state(self):
        """Test verification of invalid state"""
        verified = verify_state("invalid_state_string")
        assert verified is None
        
    def test_verify_expired_state(self):
        """Test verification of expired state"""
        cli_token = "test_cli_token"
        state = create_state(cli_token)
        
        # Try to verify with 0 second max age (immediate expiry)
        verified = verify_state(state, max_age=0)
        assert verified is None
        
    def test_state_contains_cli_token(self):
        """Test that state properly embeds CLI token"""
        cli_token = "unique_cli_token_12345"
        state = create_state(cli_token)
        verified = verify_state(state)
        
        assert verified["cli_token"] == cli_token
        
    def test_state_serializer_uses_correct_secret(self):
        """Test that state serializer uses the configured secret"""
        from app.auth import state_serializer
        assert state_serializer.secret_key == settings.state_secret.encode()


class TestPhase1H:
    """Test 1H: GitHub User Data Retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_github_user_success(self):
        """Test successful GitHub user data retrieval"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock user endpoint response
            user_response = Mock()
            user_response.status_code = 200
            user_response.json.return_value = {
                "id": 12345,
                "login": "testuser",
                "name": "Test User"
            }
            
            # Mock emails endpoint response
            emails_response = Mock()
            emails_response.status_code = 200
            emails_response.json.return_value = [
                {"email": "test@github.com", "primary": True, "verified": True},
                {"email": "alt@github.com", "primary": False, "verified": True}
            ]
            
            # Set up side effects for multiple calls
            mock_get.side_effect = [user_response, emails_response]
            
            user_data = await get_github_user("test_access_token")
            
            assert user_data is not None
            assert user_data["id"] == 12345
            assert user_data["login"] == "testuser"
            assert user_data["email"] == "test@github.com"
    
    @pytest.mark.asyncio
    async def test_get_github_user_invalid_token(self):
        """Test GitHub user retrieval with invalid token"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response
            
            user_data = await get_github_user("invalid_token")
            assert user_data is None
    
    @pytest.mark.asyncio
    async def test_get_github_user_no_verified_email(self):
        """Test GitHub user retrieval when no verified email exists"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock user endpoint response
            user_response = Mock()
            user_response.status_code = 200
            user_response.json.return_value = {
                "id": 12345,
                "login": "testuser",
                "name": "Test User"
            }
            
            # Mock emails endpoint response with no verified emails
            emails_response = Mock()
            emails_response.status_code = 200
            emails_response.json.return_value = [
                {"email": "test@github.com", "primary": True, "verified": False}
            ]
            
            mock_get.side_effect = [user_response, emails_response]
            
            user_data = await get_github_user("test_access_token")
            
            assert user_data is not None
            assert user_data["id"] == 12345
            assert "email" not in user_data  # No email added if none verified
    
    @pytest.mark.asyncio
    async def test_get_github_user_handles_api_errors(self):
        """Test GitHub user retrieval handles API errors gracefully"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock user endpoint success but emails endpoint failure
            user_response = Mock()
            user_response.status_code = 200
            user_response.json.return_value = {
                "id": 12345,
                "login": "testuser"
            }
            
            emails_response = Mock()
            emails_response.status_code = 500  # Server error
            
            mock_get.side_effect = [user_response, emails_response]
            
            user_data = await get_github_user("test_access_token")
            
            # Should still return user data even if emails fail
            assert user_data is not None
            assert user_data["id"] == 12345
            assert "email" not in user_data


class TestIntegrationPhase1:
    """Integration tests for complete Phase 1 flow"""
    
    def test_complete_auth_flow_simulation(self):
        """Test simulated complete authentication flow"""
        # Step 1: Health check
        response = client.get("/health")
        assert response.status_code == 200
        
        # Step 2: Start OAuth flow
        cli_token = "integration_test_token"
        response = client.get(f"/auth/github/start?cli_token={cli_token}")
        assert response.status_code == 307
        
        # Step 3: Simulate successful callback (would normally go through GitHub)
        # We'll manually add to pending tokens to simulate
        test_jwt = create_jwt_token({
            "sub": "123",
            "email": "integration@test.com",
            "name": "Integration Test"
        })
        pending_tokens[cli_token] = {
            "token": test_jwt,
            "user": {"id": 123, "login": "integrationtest"}
        }
        
        # Step 4: CLI exchanges token
        response = client.get(f"/auth/cli-exchange?cli_token={cli_token}")
        assert response.status_code == 200
        data = response.json()
        received_token = data["token"]
        
        # Step 5: Use token to access protected route
        response = client.get(
            "/test-protected",
            headers={"Authorization": f"Bearer {received_token}"}
        )
        assert response.status_code == 200
        assert response.json()["user"]["email"] == "integration@test.com"
    
    def test_all_phase1_endpoints_exist(self):
        """Test that all Phase 1 endpoints are accessible"""
        endpoints = [
            ("/health", "GET", 200),
            ("/config-test", "GET", 200),
            ("/test-token", "POST", 200),
            ("/test-protected", "GET", 401),  # 401 without auth
            ("/auth/github/start", "GET", 422),  # 422 without params
            ("/auth/github/callback", "GET", 422),  # 422 without params
            ("/auth/cli-exchange", "GET", 422),  # 422 without params
        ]
        
        for path, method, expected_status in endpoints:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path)
            
            # Check that endpoint exists (not 404)
            assert response.status_code != 404, f"Endpoint {path} not found"
            # For parameterized endpoints, 422 is expected without params
            if expected_status in [200, 401, 422]:
                assert response.status_code == expected_status, f"Unexpected status for {path}"


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])