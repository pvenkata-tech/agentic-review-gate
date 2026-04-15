#!/usr/bin/env python3
"""
Test Agent Comments End-to-End

This script will:
1. Start the FastAPI server
2. Wait for it to be ready
3. Call the /review endpoint
4. Show you what's happening at each step

Usage:
    python test_agents_e2e.py --pr-number 12
"""

import subprocess
import asyncio
import httpx
import os
import time
import argparse
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

server_process = None


def print_header(title: str):
    print(f"\n{BLUE}{'='*70}")
    print(f"{title}")
    print(f"{'='*70}{RESET}\n")


def print_success(msg: str):
    print(f"{GREEN}✓ {msg}{RESET}")


def print_error(msg: str):
    print(f"{RED}✗ {msg}{RESET}")


def print_warning(msg: str):
    print(f"{YELLOW}⚠ {msg}{RESET}")


def print_info(msg: str):
    print(f"{BLUE}ℹ {msg}{RESET}")


async def wait_for_server(timeout: int = 30):
    """Wait for server to be ready."""
    print_info("Waiting for server to start...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=1)
                if response.status_code == 200:
                    print_success("Server is ready!")
                    return True
        except:
            await asyncio.sleep(1)
    
    print_error(f"Server did not start within {timeout} seconds")
    return False


async def test_review(pr_number: int):
    """Test the review endpoint."""
    print_header(f"Testing Review for PR #{pr_number}")
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print_error("GITHUB_TOKEN not configured")
        return False
    
    payload = {
        "pr_number": pr_number,
        "owner": "pvenkata-tech",
        "repo": "agentic-review-gate",
        "github_token": token,
    }
    
    print_info(f"Sending review request to http://localhost:8000/review")
    print(f"  PR: #{pr_number}")
    print(f"  Token: {token[:20]}...")
    print()
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"{YELLOW}Starting analysis (this may take 10-30 seconds)...{RESET}")
            print()
            
            start = time.time()
            response = await client.post(
                "http://localhost:8000/review",
                json=payload,
                timeout=180
            )
            elapsed = time.time() - start
            
            print(f"{YELLOW}Analysis complete in {elapsed:.1f} seconds{RESET}\n")
            
            if response.status_code == 200:
                result = response.json()
                print_success("Review completed!\n")
                
                print("Results:")
                print(f"  PR Number: {result['pr_number']}")
                print(f"  Total Findings: {result['total_findings']}")
                print(f"  Is Blocked: {result['is_blocked']}")
                
                if result['total_findings'] > 0:
                    print(f"\n{GREEN}✓ Agents found {result['total_findings']} issues!{RESET}")
                    print(f"\n{MAGENTA}Comment should have been posted to:{RESET}")
                    print(f"  https://github.com/pvenkata-tech/agentic-review-gate/pull/{pr_number}")
                    print(f"\n{YELLOW}Waiting 3 seconds for comment posting to complete...{RESET}")
                    await asyncio.sleep(3)
                    print(f"{GREEN}Now check the PR for the comment!{RESET}")
                else:
                    print_warning("No findings detected by agents")
                    print("\nPossible reasons:")
                    print("  1. Code is clean (no issues found)")
                    print("  2. Diff is empty or not parsed correctly")
                    print("  3. Agents couldn't access the code changes")
                
                return True
            else:
                print_error(f"Review failed with status {response.status_code}\n")
                print("Response:")
                print(response.text)
                return False
                
    except httpx.ConnectError:
        print_error("Cannot connect to server")
        return False
    except asyncio.TimeoutError:
        print_warning("Request timed out")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False


def start_server():
    """Start the FastAPI server."""
    print_header("Starting FastAPI Server")
    
    global server_process
    
    try:
        print_info("Launching: python -m uvicorn src.code_reviewer.main:app --reload --host 127.0.0.1 --port 8000")
        print()
        
        server_process = subprocess.Popen(
            [
                "python",
                "-m",
                "uvicorn",
                "src.code_reviewer.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8000"
            ],
            cwd=".",
        )
        
        print_success(f"Server process started (PID: {server_process.pid})")
        return True
    except Exception as e:
        print_error(f"Failed to start server: {str(e)}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test agent comments end-to-end")
    parser.add_argument("--pr-number", type=int, default=12, help="PR number to test")
    parser.add_argument("--no-server", action="store_true", help="Don't start server (assume it's running)")
    
    args = parser.parse_args()
    
    print(f"\n{MAGENTA}Agent Comments End-to-End Test{RESET}")
    print("=" * 70)
    
    # Start server if needed
    if not args.no_server:
        if not start_server():
            return
        
        # Wait for server to be ready
        if not await wait_for_server():
            if server_process:
                server_process.terminate()
            return
    else:
        print_info("Assuming server is already running...")
        if not await wait_for_server():
            return
    
    # Run the test
    print()
    success = await test_review(args.pr_number)
    
    # Summary
    print("\n" + "=" * 70)
    if success:
        print(f"{GREEN}Test completed! ✓{RESET}\n")
        print("What to do next:")
        print("1. Refresh the PR page in your browser")
        print("2. Look for a comment with '🤖 **Automated Code Review**'")
        print("3. If comment not visible, check the server logs above for errors")
        print("4. The server is still running - you can test other PRs")
    else:
        print(f"{RED}Test failed ✗{RESET}\n")
        print("Troubleshooting:")
        print("1. Check the server logs above")
        print("2. Verify GITHUB_TOKEN in .env file")
        print("3. Make sure PR #12 exists in the repository")
    
    print("\n" + "=" * 70)
    
    # Keep server running
    if not args.no_server:
        try:
            print(f"\n{BLUE}Server is running. Press Ctrl+C to stop.{RESET}\n")
            await asyncio.sleep(3600)  # Keep running for 1 hour
        except KeyboardInterrupt:
            print("\n\nShutting down server...")
            if server_process:
                server_process.terminate()
                server_process.wait()
            print("Server stopped.")


if __name__ == "__main__":
    asyncio.run(main())
