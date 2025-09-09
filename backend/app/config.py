"""
Part 1C: Environment Configuration
Loads settings from .env file automatically
"""

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Part 1B: GitHub OAuth credentials from our registered app
    github_client_id: str
    github_client_secret: str
    
    # Server config
    base_url: str = "http://localhost:8001"
    
    # Part 1D: Secrets for signing JWT tokens
    jwt_secret: str = "dev-jwt-secret-change-in-production"
    state_secret: str = "dev-state-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 7
    
    # Admin emails (will be parsed from comma-separated string)
    admin_emails: str = ""
    
    class Config:
        # Load from .env file
        env_file = ".env"
        env_file_encoding = 'utf-8'
    
    def get_admin_emails_list(self) -> List[str]:
        """Parse admin emails from comma-separated string."""
        if self.admin_emails:
            return [email.strip() for email in self.admin_emails.split(",")]
        return []

# Create a single instance to use throughout the app
settings = Settings()