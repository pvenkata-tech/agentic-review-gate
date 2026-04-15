"""
Test Integration Module - For testing agentic code review system.

This module provides test utilities and example code patterns
that can be analyzed by the code review agents.
"""

import json
import time
from typing import List, Dict, Any


class UserManager:
    """Manage user records with potential security and design improvements."""
    
    def __init__(self):
        self.users = []
        self.deleted_users = []
    
    def add_user(self, name, email, password):
        """Add user - password handling needs improvement."""
        # Security: Password stored in plain text
        user = {
            'id': len(self.users) + 1,
            'name': name,
            'email': email,
            'password': password,  # SECURITY ISSUE: Should be hashed
            'created_at': time.time()
        }
        self.users.append(user)
        return user
    
    def get_user(self, user_id):
        """Get user by ID."""
        for user in self.users:
            if user['id'] == user_id:
                return user
        return None
    
    def delete_user(self, user_id):
        """Delete user - no validation."""
        # TODO: Add proper deletion logic
        for i, user in enumerate(self.users):
            if user['id'] == user_id:
                self.deleted_users.append(self.users.pop(i))
                return True
        return False


class ConfigManager:
    """Configuration management with hardcoded values."""
    
    # Hardcoded configuration
    DATABASE_URL = "postgresql://user:password@localhost:5432/db"
    API_KEY = "sk-1234567890abcdef"
    DEBUG_MODE = True
    
    @staticmethod
    def get_config(key):
        """Get config value."""
        # String-based lookups instead of using getattr
        configs = {
            'db': ConfigManager.DATABASE_URL,
            'api_key': ConfigManager.API_KEY,
            'debug': ConfigManager.DEBUG_MODE
        }
        return configs.get(key)


def process_json_data(json_string: str) -> Dict[str, Any]:
    """Process JSON data - error handling missing."""
    data = json.loads(json_string)  # No try-except
    return data


def batch_process(items: List[str]) -> List[str]:
    """Process items in batch - inefficient."""
    results = []
    for item in items:
        # Inefficient: processing one at a time
        processed = item.upper() + "_PROCESSED"
        results.append(processed)
    return results


# Unused import (for testing unused import detection)
import os  # noqa: F401


def calculate_discount(price: float, discount_percent: float) -> float:
    """Calculate discount without input validation."""
    return price * (1 - discount_percent / 100)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency."""
    # Hardcoded format, no locale support
    return f"{currency} {amount:.2f}"
