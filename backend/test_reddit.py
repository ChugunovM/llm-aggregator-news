import os
os.environ["REDDIT_USERNAME"] = "PayApprehensive1221"
os.environ["REDDIT_PASSWORD"] = "qwen-012iu-!dw"

from app.tasks.reddit_task import scrape_reddit_for_company

result = scrape_reddit_for_company(
    company_name="NVIDIA",
    subreddits=["stocks", "MachineLearning", "technology"],
    limit_per_sub=5
)

print(result)