"""
Agri-Only Curated News Router.
Strictly filtered agricultural news covering 9 foundational topics with Kannada/English labels.
"""
from typing import Optional, List
import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
import models

router = APIRouter(prefix="/api/news", tags=["news"])

STRICT_NEWS_CATEGORIES = [
    {
        "id": 1,
        "name": "Commodity Rates & Market Trends",
        "kannada": "ಕೃಷಿ ದರ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ಪ್ರವೃತ್ತಿಗಳು",
        "icon": "TrendingUp",
        "badge_color": "emerald",
    },
    {
        "id": 2,
        "name": "Govt Subsidized Agricultural Tools",
        "kannada": "ಸರ್ಕಾರದ ಸಬ್ಸಿಡಿ ಕೃಷಿ ಯಂತ್ರೋಪಕರಣಗಳು",
        "icon": "Tractor",
        "badge_color": "blue",
    },
    {
        "id": 3,
        "name": "Upcoming Weather & Monsoon Alerts",
        "kannada": "ಹವಾಮಾನ ಮತ್ತು ಮುಂಗಾರು ಮುನ್ಸೂಚನೆ",
        "icon": "CloudRain",
        "badge_color": "sky",
    },
    {
        "id": 4,
        "name": "Price Drops in Agri Tools & Vehicles",
        "kannada": "ಕೃಷಿ ಸಲಕರಣೆಗಳ ದರ ಇಳಿಕೆ ಮತ್ತು ಕೊಡುಗೆಗಳು",
        "icon": "Tag",
        "badge_color": "rose",
    },
    {
        "id": 5,
        "name": "Government Support Schemes for Farmers",
        "kannada": "ರೈತ ಬೆಂಬಲ ಮತ್ತು ಕಲ್ಯಾಣ ಯೋಜನೆಗಳು",
        "icon": "Landmark",
        "badge_color": "purple",
    },
    {
        "id": 6,
        "name": "Crop Insurance Schemes",
        "kannada": "ಬೆಳೆ ವಿಮೆ ಯೋಜನೆಗಳು (PMFBY)",
        "icon": "ShieldCheck",
        "badge_color": "amber",
    },
    {
        "id": 7,
        "name": "Budget-Friendly Pumpsets",
        "kannada": "ಕಡಿಮೆ ವೆಚ್ಚದ ನೀರಾವರಿ ಪಂಪ್‌ಸೆಟ್‌ಗಳು",
        "icon": "Gauge",
        "badge_color": "teal",
    },
    {
        "id": 8,
        "name": "Quality Reviews of Agri Products",
        "kannada": "ಕೃಷಿ ಉತ್ಪನ್ನಗಳ ಗುಣಮಟ್ಟ ವಿಮರ್ಶೆ (ಬೀಜ/ಗೊಬ್ಬರ)",
        "icon": "Sparkles",
        "badge_color": "indigo",
    },
    {
        "id": 9,
        "name": "Solar Energy Utilization & Govt Subsidy Schemes",
        "kannada": "ಸೌರಶಕ್ತಿ ಕೃಷಿ ಮತ್ತು ಕುಸುಮ್ ಸಬ್ಸಿಡಿ ಯೋಜನೆ",
        "icon": "SunMedium",
        "badge_color": "yellow",
    },
]


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """Return strictly the 9 curated agricultural news topics with counts."""
    categories_with_counts = []
    for cat in STRICT_NEWS_CATEGORIES:
        cnt = db.query(models.NewsArticle).filter(models.NewsArticle.category_id == cat["id"]).count()
        categories_with_counts.append({
            **cat,
            "article_count": cnt,
        })
    return categories_with_counts


@router.get("")
@router.get("/")
def get_articles(
    category_id: Optional[int] = Query(None, description="Category ID 1 to 9"),
    search: Optional[str] = Query(None, description="Keyword search query"),
    db: Session = Depends(get_db),
):
    """
    Fetch agricultural news articles strictly filtered across the 9 topics.
    Supports optional category ID filtering and keyword search.
    """
    q = db.query(models.NewsArticle)

    if category_id:
        q = q.filter(models.NewsArticle.category_id == category_id)

    if search:
        search_term = f"%{search.strip()}%"
        q = q.filter(
            (models.NewsArticle.title.ilike(search_term)) |
            (models.NewsArticle.title_kannada.ilike(search_term)) |
            (models.NewsArticle.summary.ilike(search_term)) |
            (models.NewsArticle.category_name.ilike(search_term))
        )

    articles = q.order_by(models.NewsArticle.id.desc()).all()

    res = []
    for a in articles:
        takeaways = []
        if a.key_takeaways:
            try:
                takeaways = json.loads(a.key_takeaways)
            except Exception:
                takeaways = [a.key_takeaways]

        cat_meta = next((c for c in STRICT_NEWS_CATEGORIES if c["id"] == a.category_id), STRICT_NEWS_CATEGORIES[0])

        res.append({
            "id": a.id,
            "category_id": a.category_id,
            "category_name": a.category_name,
            "category_kannada": a.category_kannada,
            "badge_color": cat_meta.get("badge_color", "emerald"),
            "icon": cat_meta.get("icon", "Newspaper"),
            "title": a.title,
            "title_kannada": a.title_kannada,
            "summary": a.summary,
            "summary_kannada": a.summary_kannada,
            "content": a.content,
            "source": a.source,
            "read_time": a.read_time,
            "published_date": a.published_date,
            "image_url": a.image_url,
            "key_takeaways": takeaways,
            "action_url": a.action_url,
            "voice_query_prompt": a.voice_query_prompt,
        })

    return {
        "total": len(res),
        "selected_category_id": category_id,
        "categories": STRICT_NEWS_CATEGORIES,
        "articles": res,
    }


@router.get("/{article_id}")
def get_article_detail(article_id: int, db: Session = Depends(get_db)):
    """Fetch complete detail for a specific agricultural news article."""
    a = db.query(models.NewsArticle).filter(models.NewsArticle.id == article_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Article not found")

    takeaways = []
    if a.key_takeaways:
        try:
            takeaways = json.loads(a.key_takeaways)
        except Exception:
            takeaways = [a.key_takeaways]

    cat_meta = next((c for c in STRICT_NEWS_CATEGORIES if c["id"] == a.category_id), STRICT_NEWS_CATEGORIES[0])

    return {
        "id": a.id,
        "category_id": a.category_id,
        "category_name": a.category_name,
        "category_kannada": a.category_kannada,
        "badge_color": cat_meta.get("badge_color", "emerald"),
        "icon": cat_meta.get("icon", "Newspaper"),
        "title": a.title,
        "title_kannada": a.title_kannada,
        "summary": a.summary,
        "summary_kannada": a.summary_kannada,
        "content": a.content,
        "source": a.source,
        "read_time": a.read_time,
        "published_date": a.published_date,
        "image_url": a.image_url,
        "key_takeaways": takeaways,
        "action_url": a.action_url,
        "voice_query_prompt": a.voice_query_prompt,
    }
