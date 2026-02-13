import requests
import streamlit as st
from sqlalchemy.orm import Session
from database import SessionLocal
from app.models.news_item import NewsItem
from app.tasks.main_workflow import trigger_company_monitoring
from app.utils.source_suggester import suggest_source
from app.tasks.rss_task import flatten_list

# Показ списка подписок
st.subheader("🔔 Мои подписки")
subs = requests.get("http://backend:8000/subscriptions").json()
for sub in subs:
    with st.expander(f"{sub['company']} (каждые {sub['interval_hours']} ч)"):
        st.write(f"Последнее обновление: {sub['last_run_at'] or 'никогда'}")
        st.write(f"URLs: {', '.join(sub['urls'][:2])}...")
        st.write(f"Telegram: {', '.join(sub['telegram_channels'])}")
        if st.button("🗑️ Удалить", key=f"del_{sub['id']}"):
            requests.delete(f"http://backend:8000/subscribe/{sub['id']}")
            st.rerun()  

# Поле ввода
company = st.text_input("Название компании", placeholder="Например: Apple, NVIDIA")

# Кастомные источники
with st.expander("⚙️ Расширенные настройки (необязательно)"):
    custom_rss = st.text_area("RSS / URL сайтов (по одному на строку)", height=80)
    custom_tg = st.text_input("Telegram-каналы (через запятую)", placeholder="@cnbc, @techcrunch")

col1, col2 = st.columns([1, 5])
if col1.button("🔍 Собрать новости и подписаться"):
    if not company:
        st.error("Введите название компании")
    else:
        # Кастомные источники
        # custom_urls = [u.strip() for u in custom_rss.split("\n") if u.strip()]
        custom_urls = []
        if custom_rss:
            for line in custom_rss.splitlines():
                cleaned = line.strip()
                if cleaned and cleaned != "":
                    custom_urls.append(cleaned)
                    
        custom_tg = [ch.strip() for ch in custom_tg.split(",") if ch.strip()]

        # Автоисточники (если кастомные не заданы)
        if not custom_urls and not custom_tg: 
            auto_urls, auto_tg = suggest_source(company)
            all_urls = auto_urls
            all_tg = auto_tg
            st.info(f"Автоопределены источники: {len(all_urls)} URL, {len(all_tg)} Telegram-каналов")
        else:
            all_urls = custom_urls,
            all_tg = custom_tg

        all_urls = flatten_list(all_urls)
        # Запуск Celery
        task = trigger_company_monitoring.delay(
            company_name=company,
            sources=["rss", "telegram"],
            urls=all_urls,
            telegram_channels=all_tg
        )
        st.success(f"Задача запущена! ID: {task.id[:8]}")
        st.info("Обновите страницу через 10-20 секунд")
        
        st.write("Отправляем:", {
            "company": company,
            "urls": all_urls,
            "telegram_channels": all_tg,
            "interval_hours": 2
        })

        resp = requests.post("http://backend:8000/subscribe", json={
            "company": company,
            "urls": all_urls,
            "telegram_channels": all_tg,
            "interval_hours": 2
        })
        st.success("Подписка создана!")

# Показ новостей из БД
st.subheader(f"📰 Новости по: {company or 'все компании'}")
db: Session = SessionLocal()
try:
    query = db.query(NewsItem)
    if company:
        query = query.filter(NewsItem.company.ilike(f"%{company}%"))
    items = query.order_by(NewsItem.published_at.desc()).limit(20).all()

    for item in items:
        with st.container():
            source_badge = f"`{item.source}`"
            sentiment_color = {
                "позитивная": "green",
                "негативная": "red",
                "нейтральная": "gray"
            }.get(item.sentiment, "gray")

            st.markdown(f"""
            **{item.title}**
            *{item.published_at.strftime('%Y-%m-%d %H:%M') if item.published_at else 'без даты'}*
            Источник: {source_badge} | Тональность: `:{sentiment_color}[●]` {item.sentiment}                        
            """)
            st.write(item.summary or item.raw_text[:300] + "...")
            st.markdown(f"[Читать оригинал]({item.url})")
            st.divider()
finally:
    db.close


            