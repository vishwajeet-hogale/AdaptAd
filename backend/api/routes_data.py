"""
Data routes: users, ads, content library.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from ..data.generate import generate_users
from ..data.content_library import generate_content_library
from ..data.ad_inventory import generate_ad_inventory
from ..state import UserProfile, AdCandidate, ContentItem
from ..config import config

router = APIRouter(prefix="/api", tags=["data"])

# Module-level singletons so data is generated once per process.
_users: Optional[list[UserProfile]] = None
_ads: Optional[list[AdCandidate]] = None
_content: Optional[list[ContentItem]] = None


def get_users() -> list[UserProfile]:
    global _users
    if _users is None:
        _users = generate_users(count=config.simulation.num_users, seed=42)
    return _users


def get_ads() -> list[AdCandidate]:
    global _ads
    if _ads is None:
        _ads = generate_ad_inventory(count=config.simulation.num_ads, seed=42)
    return _ads


def get_content() -> list[ContentItem]:
    global _content
    if _content is None:
        _content = generate_content_library(count=config.simulation.num_content_items, seed=42)
    return _content


@router.get("/users")
def list_users(limit: int = 1000, offset: int = 0):
    users = get_users()
    return {"users": [u.model_dump() for u in users[offset: offset + limit]], "total": len(users)}


@router.get("/users/{user_id}")
def get_user(user_id: int):
    users = get_users()
    user = next((u for u in users if u.id == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    return user.model_dump()


@router.get("/ads")
def list_ads(category: Optional[str] = None, limit: int = 200, offset: int = 0):
    ads = get_ads()
    if category:
        ads = [a for a in ads if a.category == category]
    return {"ads": [a.model_dump() for a in ads[offset: offset + limit]], "total": len(ads)}


@router.get("/content")
def list_content(genre: Optional[str] = None, limit: int = 300, offset: int = 0):
    items = get_content()
    if genre:
        items = [c for c in items if c.genre.lower() == genre.lower()]
    return {"content": [c.model_dump() for c in items[offset: offset + limit]], "total": len(items)}


@router.get("/health")
def health():
    return {
        "status": "ok",
        "users": len(get_users()),
        "ads": len(get_ads()),
        "content": len(get_content()),
    }
