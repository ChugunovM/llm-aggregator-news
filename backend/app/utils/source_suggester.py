import re

def suggest_source(company: str) -> tuple[list[str], list[str]]:
    """
    Предлагает источники новостей по названию компании.
    Возвращает (urls, telegram_channels)
    """
    company_clean = re.sub(r'[^a-zA-Z0-9]', '', company).lower()
    company_upper = company_clean.upper()

    # 1. Официальные URL
    official_urls = [
        f"https://www.{company_clean}.com/newsroom/",
        f"https://www.{company_clean}.com/press/",
        f"https://www.{company_clean}.com/blog/",
        f"https://www.{company_clean}.com/news/",
    ]

    # 2. Google News
    google_rss = f"https://news.google.com/rss/search?q={company}&hl=en-US&gl=US&ceid=US:en"

    # 3. Seeking Alpha
    seeking_alpha = f"https://seekingalpha.com/symbol/{company_upper}/feed"

    urls = official_urls + [google_rss, seeking_alpha]

    # 4. Telegram
    tg_base = ["@cnbc", "@reuters", "@businessinsider"]
    tg_company = f"@{company_clean}" or f"@media_{company_clean}"

    # Отраслевые эвристики
    tech_companies = {"apple", "microsoft", "google", "nvidia", "tesla", "meta", "amazon"}
    if company_clean in tech_companies:
        tg_base.append("@techcrunch")
        tg_base.append("@verge")
    
    telegram_channels = [tg_company] + tg_base
    print("DEBUG: official_urls =", official_urls)
    print("DEBUG: urls =", urls)

    print("URLs:", urls)
    print("Types:", [type(u) for u in urls])

    return urls, telegram_channels