"""
FastAPI Entrypoint: Main service for the code reviewer system.

Provides REST endpoints:
- Triggering PR reviews
- Receiving GitHub webhook events
- Status and health checks
- Review statistics
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from code_reviewer.core.state import ReviewState, PRMetadata
from code_reviewer.core.coordinator import ReviewCoordinator
from code_reviewer.utils.logger import get_logger
from code_reviewer.utils.github_client import GitHubClient, GitHubConfig
from code_reviewer.utils.diff_parser import DiffParser, DiffAnalyzer
from code_reviewer.utils.webhooks import WebhookHandler, WebhookValidationError
from code_reviewer.prompts import get_prompt_for_agent
from code_reviewer.utils.cache import get_cache_backend


# Initialize
app = FastAPI(
    title="Code Reviewer",
    description="Production-grade multi-agent PR review system",
    version="0.1.0",
)

logger = get_logger()

# Initialize webhook handler with GitHub secret
github_webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
webhook_handler = WebhookHandler(secret=github_webhook_secret)
if github_webhook_secret:
    logger.info("Webhook handler initialized with signature validation enabled")
else:
    logger.warning("Webhook handler: signature validation disabled (GITHUB_WEBHOOK_SECRET not set)")

# Initialize cache backend for persistent state
cache_backend = get_cache_backend()
logger.info(f"Initialized cache backend: {type(cache_backend).__name__}")

# Initialize coordinator with cache backend for finding deduplication
coordinator = ReviewCoordinator(cache_backend=cache_backend)




# Pydantic models for API
class ReviewRequest(BaseModel):
    """Request to review a PR."""
    pr_number: int
    owner: str
    repo: str
    github_token: str


class ReviewResponse(BaseModel):
    """Response from review."""
    pr_number: int
    total_findings: int
    is_blocked: bool
    summary_url: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "0.1.0"


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy")


@app.post("/review", response_model=ReviewResponse)
async def review_pr(request: ReviewRequest, background_tasks: BackgroundTasks):
    """
    Trigger a PR review.
    
    This endpoint:
    1. Fetches PR metadata from GitHub
    2. Loads previous findings (for deduplication)
    3. Initiates review with the coordinator
    4. Saves findings to cache for next review
    5. Posts findings as a GitHub comment
    6. Returns summary statistics
    
    Args:
        request: ReviewRequest with PR details
        background_tasks: FastAPI background tasks
        
    Returns:
        ReviewResponse with findings summary
        
    Raises:
        HTTPException: If PR not found or review fails
    """
    return await _execute_review(request, background_tasks)


async def _execute_review(request: ReviewRequest, background_tasks: BackgroundTasks) -> ReviewResponse:
    """
    Execute the actual PR review logic.
    
    This is extracted into a separate function so it can be called from both
    the REST endpoint and the background task triggered by webhooks.
    
    Args:
        request: ReviewRequest with PR details
        background_tasks: FastAPI background tasks for posting comments
        
    Returns:
        ReviewResponse with findings summary
    """
    try:
        logger.log_pr_review_start(request.pr_number, "unknown")
        
        # Initialize GitHub client
        github_config = GitHubConfig(
            token=request.github_token,
            owner=request.owner,
            repo=request.repo,
        )
        github_client = GitHubClient(github_config)
        
        # Fetch PR metadata
        pr_info = await github_client.get_pr_info(request.pr_number)
        pr_diff = await github_client.get_pr_diff(request.pr_number)
        
        # Extract data for ReviewState
        pr_metadata = PRMetadata(
            pr_number=request.pr_number,
            title=pr_info["title"],
            author=pr_info["user"]["login"],
            branch=pr_info["head"]["ref"],
            base_branch=pr_info["base"]["ref"],
            diff_content=pr_diff,
            files_changed=[f["filename"] for f in pr_info.get("files", [])],
            additions=pr_info.get("additions", 0),
            deletions=pr_info.get("deletions", 0),
        )
        
        # Load previous findings from cache for deduplication
        cache_key = f"pr:{request.pr_number}:findings"
        previous_finding_ids = cache_backend.get(cache_key)
        if previous_finding_ids:
            logger.info(
                f"Loaded {len(previous_finding_ids)} previous findings from cache",
                pr_number=request.pr_number
            )
        
        # Create initial state
        initial_state = ReviewState(pr_metadata=pr_metadata)
        
        # Run review with deduplication support
        review_state = await coordinator.review_pr(
            initial_state,
            previous_finding_ids=previous_finding_ids
        )
        
        # Cache the new findings for next review
        new_finding_ids = review_state.get_finding_ids()
        if new_finding_ids:
            cache_backend.set(cache_key, new_finding_ids, ex=86400*30)  # 30 days
            logger.info(
                f"Cached {len(new_finding_ids)} finding IDs for next review",
                pr_number=request.pr_number
            )
        
        # Get stats
        stats = coordinator.get_review_stats(review_state)
        
        # Post comment to GitHub (background task)
        if review_state.final_summary:
            background_tasks.add_task(
                _post_review_comment,
                github_client,
                request.pr_number,
                review_state.final_summary,
            )
        
        logger.log_pr_review_complete(
            request.pr_number,
            stats["total_findings"],
            review_state.is_blocked,
            sum(m.execution_time_ms for m in review_state.metadata),
        )
        
        return ReviewResponse(
            pr_number=request.pr_number,
            total_findings=stats["total_findings"],
            is_blocked=review_state.is_blocked,
        )
    
    except Exception as e:
        logger.error(f"Review failed for PR {request.pr_number}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Review failed: {str(e)}",
        )


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle GitHub webhook events with full validation.
    
    This endpoint:
    1. Validates X-Hub-Signature-256 HMAC-SHA256 signature
    2. Filters for pull_request events only
    3. Only processes open/synchronize/reopen actions
    4. Extracts PR metadata and triggers async review
    
    Security Features:
    - Constant-time HMAC signature comparison (prevents timing attacks)
    - Validates webhook secret (GITHUB_WEBHOOK_SECRET)
    - Filters event types to prevent abuse
    - Validates payload structure
    
    Returns:
        JSON response with status and details
        
    Raises:
        HTTPException: 403 if signature invalid, 400 if payload invalid
    """
    # Get raw body for signature validation (must be before any parsing)
    raw_body = await request.body()
    
    # Extract required headers
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    
    logger.debug(
        f"Webhook received",
        event_type=event_type,
        signature_present=bool(signature_header)
    )
    
    # Process and validate webhook
    should_process, payload, error_message = webhook_handler.process_webhook(
        raw_body=raw_body,
        signature_header=signature_header,
        event_type=event_type
    )
    
    # Handle validation errors
    if error_message:
        if "signature validation failed" in error_message:
            logger.error(f"Webhook validation failed: {error_message}")
            raise HTTPException(
                status_code=403,
                detail="Webhook signature validation failed"
            )
        else:
            # Non-critical errors (event type not supported, etc)
            logger.debug(f"Webhook ignored: {error_message}")
            return JSONResponse(webhook_handler.get_ignored_response(error_message))
    
    # If we shouldn't process this webhook, return ignored
    if not should_process:
        logger.debug(f"Webhook ignored: {error_message or 'event does not trigger review'}")
        if payload:
            return JSONResponse(webhook_handler.get_ignored_response(error_message or "Event does not trigger review"))
        else:
            return JSONResponse(webhook_handler.get_ignored_response(error_message or "Invalid payload"))
    
    # Got a valid trigger event
    logger.info(
        f"GitHub webhook accepted for PR review",
        pr_number=payload.pr_number,
        repo=payload.full_repo,
        action=payload.action,
        files_changed=payload.changed_files,
    )
    
    # Get GitHub token
    github_token = os.getenv("GITHUB_TOKEN", "")
    if not github_token:
        logger.error("GITHUB_TOKEN not configured - cannot process webhook")
        return JSONResponse(
            webhook_handler.get_error_response(
                "GITHUB_TOKEN not configured on server"
            )
        )
    
    # Trigger review in background
    review_request = ReviewRequest(
        pr_number=payload.pr_number,
        owner=payload.owner,
        repo=payload.repo,
        github_token=github_token,
    )
    
    background_tasks.add_task(
        _run_review_background,
        review_request,
    )
    
    return JSONResponse({
        "status": "accepted",
        "pr_number": payload.pr_number,
        "action": payload.action,
    })


@app.get("/review/{pr_number}/stats")
async def get_review_stats(pr_number: int):
    """
    Get statistics for a previously reviewed PR.
    
    In production, this would query a persistent store of review results.
    For now, returns 404.
    
    Args:
        pr_number: GitHub PR number
        
    Returns:
        Statistics about the review
    """
    raise HTTPException(
        status_code=501,
        detail="Review history storage not yet implemented. Use /review endpoint.",
    )


async def _post_review_comment(
    github_client: GitHubClient,
    pr_number: int,
    comment_body: str,
) -> None:
    """
    Post review comment to GitHub (background task).
    
    Args:
        github_client: GitHub client instance
        pr_number: PR number
        comment_body: Comment body (Markdown)
    """
    try:
        # Check if bot already commented
        existing_comment_id = await github_client.find_review_comment(pr_number)
        
        if existing_comment_id:
            # Update existing comment
            await github_client.update_review_comment(existing_comment_id, comment_body)
            logger.info(
                f"Updated review comment on PR #{pr_number}",
                pr_number=pr_number,
                comment_id=existing_comment_id,
            )
        else:
            # Post new comment
            result = await github_client.post_review_comment(pr_number, comment_body)
            logger.info(
                f"Posted review comment on PR #{pr_number}",
                pr_number=pr_number,
                comment_id=result.get("id"),
            )
    except Exception as e:
        logger.error(f"Failed to post review comment: {str(e)}", pr_number=pr_number)


async def _run_review_background(request: ReviewRequest) -> None:
    """
    Run review in background (triggered by webhook).
    
    This executes the review logic asynchronously without blocking the webhook response.
    
    Args:
        request: Review request with PR details
    """
    try:
        # Initialize GitHub client for comment posting
        github_config = GitHubConfig(
            token=request.github_token,
            owner=request.owner,
            repo=request.repo,
        )
        github_client = GitHubClient(github_config)
        
        # Fetch PR metadata
        pr_info = await github_client.get_pr_info(request.pr_number)
        pr_diff = await github_client.get_pr_diff(request.pr_number)
        
        # Extract data for ReviewState
        pr_metadata = PRMetadata(
            pr_number=request.pr_number,
            title=pr_info["title"],
            author=pr_info["user"]["login"],
            branch=pr_info["head"]["ref"],
            base_branch=pr_info["base"]["ref"],
            diff_content=pr_diff,
            files_changed=[f["filename"] for f in pr_info.get("files", [])],
            additions=pr_info.get("additions", 0),
            deletions=pr_info.get("deletions", 0),
        )
        
        # Load previous findings from cache for deduplication
        cache_key = f"pr:{request.pr_number}:findings"
        previous_finding_ids = cache_backend.get(cache_key)
        
        # Create initial state
        initial_state = ReviewState(pr_metadata=pr_metadata)
        
        # Run review with deduplication support
        review_state = await coordinator.review_pr(
            initial_state,
            previous_finding_ids=previous_finding_ids
        )
        
        # Cache the new findings for next review
        new_finding_ids = review_state.get_finding_ids()
        if new_finding_ids:
            cache_backend.set(cache_key, new_finding_ids, ex=86400*30)  # 30 days
        
        # Post comment to GitHub synchronously (not in background task)
        if review_state.final_summary:
            await _post_review_comment(
                github_client,
                request.pr_number,
                review_state.final_summary,
            )
        
        logger.info(
            f"Completed PR review #%d with webhook processing",
            request.pr_number
        )
    except Exception as e:
        logger.error(f"Background review failed: {str(e)}", pr_number=request.pr_number)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,  # Use our custom logging
    )
