"""
FastAPI Entrypoint: Main service for the code reviewer system.

Provides REST endpoints for:
- Triggering PR reviews
- Receiving GitHub webhook events
- Status and health checks
- Review statistics
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import asyncio

from code_reviewer.core.state import ReviewState, PRMetadata
from code_reviewer.core.coordinator import ReviewCoordinator
from code_reviewer.utils.logger import get_logger
from code_reviewer.utils.github_client import GitHubClient, GitHubConfig


# Initialize
app = FastAPI(
    title="Code Reviewer",
    description="Production-grade multi-agent PR review system",
    version="0.1.0",
)

logger = get_logger()
coordinator = ReviewCoordinator()


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
    2. Initiates review with the coordinator
    3. Posts findings as a GitHub comment
    4. Returns summary statistics
    
    Args:
        request: ReviewRequest with PR details
        background_tasks: FastAPI background tasks
        
    Returns:
        ReviewResponse with findings summary
        
    Raises:
        HTTPException: If PR not found or review fails
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
        
        # Create initial state
        initial_state = ReviewState(pr_metadata=pr_metadata)
        
        # Run review (in background to avoid timeout)
        review_state = await coordinator.review_pr(initial_state)
        
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
async def github_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Handle GitHub webhook events.
    
    This endpoint receives webhooks for:
    - pull_request events (opened, synchronize)
    - issue comments
    
    Args:
        payload: GitHub webhook payload
        background_tasks: FastAPI background tasks
        
    Returns:
        JSON response acknowledging receipt
    """
    event_type = payload.get("action")
    pr = payload.get("pull_request")
    
    if not pr:
        return JSONResponse({"status": "ignored", "reason": "not a PR event"})
    
    # Only trigger on new PR or new commits
    if event_type not in ("opened", "synchronize"):
        return JSONResponse({"status": "ignored", "reason": f"action: {event_type}"})
    
    pr_number = pr["number"]
    
    # Trigger review in background
    review_request = ReviewRequest(
        pr_number=pr_number,
        owner=payload["repository"]["owner"]["login"],
        repo=payload["repository"]["name"],
        github_token="",  # Would be fetched from secure storage in production
    )
    
    background_tasks.add_task(
        _run_review_background,
        review_request,
    )
    
    return JSONResponse({
        "status": "accepted",
        "pr_number": pr_number,
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
    
    Args:
        request: Review request
    """
    try:
        # Create a temporary endpoint call to run review
        # In production, would share the coordinator instance
        await review_pr(request, BackgroundTasks())
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
