from datetime import datetime
from app.utils.date_utils import extract_data_from_html

def test_extract_date_from_apple_newsroom():
    html = """
    <html>
    <body>
        <p class="date">February 2, 2026</p>
        <h1>Apple announces new product</h1>
    </body>
    </html>
    """
    result = extract_data_from_html(html, "https://example.com")
    assert result == datetime(2026, 2, 2)

def test_extract_date_from_text():
    html = "<html><body>Press Release<br>January 29, 2026</body></html>"
    result = extract_data_from_html(html, "https://example.com")
    assert result == datetime(2026, 1, 29)