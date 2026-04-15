#!/usr/bin/env python3
"""
Agentic Code Review - Examples and Integration Tests

This module demonstrates different ways to use the agentic code review system:
1. Direct programmatic review
2. Webhook-triggered review
3. Custom findings and synthesis
4. Workflow overview

Usage:
    python examples.py                           # Run all examples
    python examples.py direct                    # Run direct review example
    python examples.py webhook                   # Run webhook example
    python examples.py --pr-number 15            # Test against specific PR
"""

import asyncio
import httpx
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
from test_utils import (
    print_header,
    print_success,
    print_error,
    get_github_config,
    GREEN,
    RED,
    YELLOW,
    BLUE,
    RESET,
)

load_dotenv()

# Example PR diff content
EXAMPLE_DIFF = """
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,5 +1,8 @@
 def authenticate(username, password):
     # Check credentials
+    if username == "admin":
+        return password == self.admin_pass
+    return False
     
     def complex_function(self):
         if x > 0:
"""


async def example_direct_review(pr_number: int = 12) -> None:
    """Example: Direct review via /review endpoint."""
    print_header(f"Example 1: Direct PR Review (PR #{pr_number})")
    
    config = get_github_config()
    
    print(f"Testing the /review endpoint...")
    print(f"  Repository: {config['owner']}/{config['repo']}")
    print(f"  PR Number: #{pr_number}\n")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/review",
                json={
                    "pr_number": pr_number,
                    "owner": config['owner'],
                    "repo": config['repo'],
                    "github_token": config['token'],
                },
                timeout=120,
            )
            
            if response.status_code == 200:
                result = response.json()
                print_success("Review completed successfully!")
                print(f"\nResults:")
                print(f"  Total Findings: {result['total_findings']}")
                print(f"  Is Blocked: {result['is_blocked']}")
                print(f"  Status Check: {result.get('status_check_created', False)}")
                print(f"\nView the PR: https://github.com/{config['owner']}/{config['repo']}/pull/{pr_number}")
            else:
                print_error(f"Review failed: {response.text}")
    except httpx.ConnectError:
        print_error("Cannot connect to http://localhost:8000")
        print("Make sure the server is running:")
        print("  python -m uvicorn src.code_reviewer.main:app")
    except Exception as e:
        print_error(f"Error: {e}")


async def example_webhook_trigger() -> None:
    """Example: Webhook trigger demonstration."""
    print_header("Example 2: Webhook-Triggered Review")
    
    print("Webhook flow:")
    print("  1. GitHub sends webhook to /webhook endpoint")
    print("  2. System validates webhook signature")
    print("  3. Server queues background review task")
    print("  4. Agents analyze PR asynchronously")
    print("  5. Results posted as GitHub comment")
    
    print("\nTo test with real webhook:")
    print("  1. Push changes to a branch")
    print("  2. Create a PR on GitHub")
    print("  3. System automatically reviews")
    print("  4. Check PR for comment with findings")


async def example_custom_findings() -> None:
    """Example: Adding custom findings."""
    print_header("Example 3: Understanding Findings")
    
    print("A finding includes:")
    print("  - file_path: Location of the issue")
    print("  - line_number: Line where issue was found")
    print("  - finding_type: Type of issue (e.g., 'Security', 'Performance')")
    print("  - severity: CRITICAL, WARNING, or INFO")
    print("  - description: What the issue is")
    print("  - suggestion: How to fix it")
    print("  - agent_id: Which agent found it")
    
    print("\nFindings flow:")
    print("  1. LogicAgent finds design/pattern issues")
    print("  2. SecurityAgent finds security issues")
    print("  3. SummarizerAgent deduplicates findings")
    print("  4. Results posted to PR as comment")


async def example_workflow_overview() -> None:
    """Example: Explain the multi-phase workflow."""
    print_header("Example 4: Multi-Agent Workflow")
    
    print("""
PHASE A: PARALLEL AGENT ANALYSIS
─────────────────────────────────
Input: PR metadata + diff content
  │
  ├─→ LogicAgent analyzes design patterns, SOLID principles
  │   └─ Returns: List[Finding]
  │
  └─→ SecurityAgent analyzes security issues, secrets, PII
      └─ Returns: List[Finding]
  
Findings merged into shared state

PHASE B: CRITICAL ISSUE CHECK
──────────────────────────────
Evaluate critical findings:
  ├─ If CRITICAL found → is_blocked = True
  └─ Otherwise → is_blocked = False

PHASE C: SYNTHESIS
──────────────────
SummarizerAgent:
  ├─ Deduplicates findings
  ├─ Generates final summary
  └─ Formats GitHub comment

OUTPUT: GitHub Status Check + Comment
""")


async def test_direct_endpoint(pr_number: int) -> None:
    """Run the direct endpoint test."""
    print_header(f"Testing Direct Review Endpoint - PR #{pr_number}")
    
    config = get_github_config()
    payload = {
        "pr_number": pr_number,
        "owner": config['owner'],
        "repo": config['repo'],
        "github_token": config['token'],
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"Calling /review endpoint...")
            response = await client.post(
                "http://localhost:8000/review",
                json=payload,
                timeout=120,
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print_success("Review completed!")
                print(f"\nResults:")
                print(f"  PR Number: {result['pr_number']}")
                print(f"  Total Findings: {result['total_findings']}")
                print(f"  Is Blocked: {result['is_blocked']}")
                
                if result['total_findings'] > 0:
                    print(f"\n{GREEN}Agents found {result['total_findings']} issues!{RESET}")
                else:
                    print(f"\n✅ No critical issues found")
                
                print(f"\nCheck PR: https://github.com/{config['owner']}/{config['repo']}/pull/{pr_number}")
            else:
                print_error(f"Failed with status {response.status_code}")
                print(f"Response: {response.text}")
    except Exception as e:
        print_error(f"Error: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Agentic Review Examples")
    parser.add_argument(
        "example",
        nargs="?",
        choices=["direct", "webhook", "findings", "workflow", "all"],
        default="all",
        help="Which example to run"
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="PR number for direct test"
    )
    
    args = parser.parse_args()
    
    if args.example == "direct" or args.example == "all":
        if args.pr_number:
            await test_direct_endpoint(args.pr_number)
        else:
            print_header("Direct Review")
            print("Usage: python examples.py direct --pr-number 15")
    
    if args.example == "webhook" or args.example == "all":
        await example_webhook_trigger()
    
    if args.example == "findings" or args.example == "all":
        await example_custom_findings()
    
    if args.example == "workflow" or args.example == "all":
        await example_workflow_overview()
    
    if args.example == "all":
        print("\n" + "=" * 70)
        print(f"{BLUE}All examples completed!{RESET}")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Review the source code in src/code_reviewer/")
        print("  2. Check docs/ for detailed documentation")
        print("  3. Run 'python diagnose.py' to verify your setup")
        print("  4. Create a test PR to see the system in action")


if __name__ == "__main__":
    asyncio.run(main())
