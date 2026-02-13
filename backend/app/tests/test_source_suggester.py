from app.utils.source_suggester import suggest_source

def test_suggest_sources_apple():
    urls, tg = suggest_source("Apple")
    assert "https://www.apple.com/newsroom" in urls
    assert "@apple" in tg
    assert "@techcrunch" in tg