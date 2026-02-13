import praw
from app.config import settings

def get_reddit_client():
    # if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
    #     raise ValueError("Reddit credentials missing in environment variables")
    if not settings.REDDIT_USERNAME or not settings.REDDIT_PASSWORD:
         raise ValueError("Reddit credentials missing in environment variables")
    
    return praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        username=settings.REDDIT_PASSWORD,
        password=settings.REDDIT_PASSWORD,
        user_agent=settings.REDDIT_USER_AGENT,
    )