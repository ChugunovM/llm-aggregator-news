from app.tasks.telegram_task import is_relevant_to_company

def test_relevance_apple():
    assert is_relevant_to_company("Apple reports record earnings", "Apple")
    assert is_relevant_to_company("iPhone 17 rumours", "Apple")
    assert is_relevant_to_company("NVIDIA launches new GPU", "Apple")