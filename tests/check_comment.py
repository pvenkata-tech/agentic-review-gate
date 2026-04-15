#!/usr/bin/env python3
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def check_comments():
    token = os.getenv('GITHUB_TOKEN')
    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://api.github.com/repos/pvenkata-tech/agentic-review-gate/issues/12/comments',
            headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
        )
        if response.status_code == 200:
            comments = response.json()
            for comment in comments:
                body = comment.get('body', '')
                if 'Automated Code Review' in body or 'agentic' in body.lower():
                    print('✓ Found automated review comment!')
                    print(f'  ID: {comment.get("id")}')
                    print(f'  Posted: {comment.get("created_at")}')
                    print(f'  First 300 chars:')
                    print(body[:300])
                    return True
            print('✗ No automated review comment found')
            print(f'  Total comments: {len(comments)}')
        else:
            print(f'Error: {response.status_code}')

asyncio.run(check_comments())
