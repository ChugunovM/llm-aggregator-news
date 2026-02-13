%%{init: {"theme": "default"}}%%
graph TD
    A[Web Chat UI\n(React / Streamlit)] --> B[Orchestrator\n(FastAPI + Celery)]
    
    B --> C[Source Adapters]
    C --> C1[Reddit Scraper\n(praw + rate limiting)]
    C --> C2[Telegram Monitor\n(Telethon, public channels)]
    C --> C3[YouTube Analyzer\n(Google API + Whisper.cpp)]
    C --> C4[Forum Parser\n(Scrapy / Playwright)]
    C --> C5[RSS/HTML Fetcher\n(feedparser + BeautifulSoup)]

    B --> D[Content Processor\n(LLM Pipeline)]
    D --> D1[Text Summarizer\n(Phi-3 / Mistral-7B-Q4)]
    D --> D2[Tone & Event Classifier\n(fine-tuned small model or prompt-based)]
    D --> D3[Multimodal Handler\n(Whisper.cpp for audio,\nTesseract+LLaVA for images*)]

    C1 --> E[(Storage\nPostgreSQL + Redis)]
    C2 --> E
    C3 --> E
    C4 --> E
    C5 --> E
    D --> E

    E --> F[Deduplication & Aggregation\n(embedding similarity / URL hash)]
    F --> G[Unified News Feed]
    G --> A

    style A fill:#e1f5fe,stroke:#01579b
    style D fill:#f3e5f5,stroke:#4a148c
    style C fill:#e8f5e9,stroke:#2e7d32
    style E fill:#fff8e1,stroke:#ff8f00
