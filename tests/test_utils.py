#!/usr/bin/env python3
"""
Shared test utilities and helpers.

This module contains reusable functions for all tests.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{BLUE}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{RESET}\n")


def print_success(msg: str) -> None:
    """Print a success message."""
    print(f"{GREEN}✓ {msg}{RESET}")


def print_error(msg: str) -> None:
    """Print an error message."""
    print(f"{RED}✗ {msg}{RESET}")


def print_warning(msg: str) -> None:
    """Print a warning message."""
    print(f"{YELLOW}⚠ {msg}{RESET}")


def print_info(msg: str) -> None:
    """Print an info message."""
    print(f"{BLUE}ℹ {msg}{RESET}")


def get_github_token() -> str:
    """Get GitHub token from environment. Exits if not found."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print_error("GITHUB_TOKEN not set in environment")
        sys.exit(1)
    return token


def get_github_config() -> dict:
    """Get standard GitHub configuration."""
    return {
        "owner": os.getenv("GITHUB_OWNER", "pvenkata-tech"),
        "repo": os.getenv("GITHUB_REPO", "agentic-review-gate"),
        "token": get_github_token(),
    }
