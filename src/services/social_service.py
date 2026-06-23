"""Social media service — Xiaohongshu (小红书) post capture for brand monitoring.

Uses opencli CLI to search Xiaohongshu for brand-related posts.
Caches results for 2 hours. Falls back to cached data when live search is unavailable.
"""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from src.utils.config import load_yaml
from src.utils.logging import logger

# Cache directory
_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "social_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 2-hour cache TTL
_CACHE_TTL = 7200

# Brand ID → XHS search keyword mapping (use real brand names for better results)
BRAND_SEARCH_KEYWORDS: dict[str, str] = {
    "apply": "iPhone 16 Apple",
    "samsun": "三星Galaxy S25",
    "huawey": "华为Mate 70",
    "oyeah": "OPPO Find X8",
    "viva": "vivo X200",
    "xiaomee": "小米15",
    "honorx": "荣耀Magic7",
    "nothingx": "Nothing Phone",
}


class SocialService:
    """Social media monitoring service for brand-related posts."""

    def __init__(self):
        self._brand_map = self._load_brand_map()

    def _load_brand_map(self) -> dict[str, str]:
        """Load brand names from companies config."""
        try:
            companies_config = load_yaml("companies.yaml")
            brand_map: dict[str, str] = {}
            for c in companies_config.get("companies", []):
                brand_id = c.get("id", "")
                if brand_id:
                    # Prefer explicit search keywords, fall back to brand name
                    brand_map[brand_id] = BRAND_SEARCH_KEYWORDS.get(
                        brand_id, c.get("name", brand_id)
                    )
            return brand_map
        except Exception:
            return BRAND_SEARCH_KEYWORDS

    def get_search_keyword(self, brand_id: str) -> str:
        """Get the real brand search keyword for XHS search."""
        return self._brand_map.get(brand_id, brand_id)

    def _cache_path(self, brand_id: str) -> Path:
        """Get cache file path for a brand."""
        key = hashlib.md5(brand_id.encode()).hexdigest()[:12]
        return _CACHE_DIR / f"xhs_{key}.json"

    def _load_cache(self, brand_id: str) -> Optional[dict]:
        """Load cached results if not expired."""
        cache_file = self._cache_path(brand_id)
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            age = time.time() - data.get("cached_at", 0)
            if age < _CACHE_TTL:
                return data
        except Exception:
            pass
        return None

    def _save_cache(self, brand_id: str, data: dict) -> None:
        """Save results to cache."""
        cache_file = self._cache_path(brand_id)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to save social cache", error=str(e))

    def search_xhs_posts(
        self, brand_id: str, limit: int = 20, force_refresh: bool = False
    ) -> dict:
        """Search Xiaohongshu for brand-related posts.

        Args:
            brand_id: Company ID (e.g. "apply", "samsun")
            limit: Max number of posts to return
            force_refresh: If True, bypass cache

        Returns:
            {
                "brand_id": str,
                "search_keyword": str,
                "posts": [...],
                "total_found": int,
                "cached_at": float,
                "from_cache": bool,
                "error": str | None,
            }
        """
        # Check cache first
        if not force_refresh:
            cached = self._load_cache(brand_id)
            if cached:
                cached["from_cache"] = True
                return cached

        keyword = self.get_search_keyword(brand_id)

        # Try to search via opencli
        posts: list[dict] = []
        error: Optional[str] = None

        try:
            cmd = [
                "opencli", "xiaohongshu", "search",
                keyword, "--limit", str(max(limit * 2, 30)), "-f", "json",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "HOME": os.environ.get("HOME", "")},
            )

            if result.returncode == 0 and result.stdout.strip():
                try:
                    raw_data = json.loads(result.stdout)
                    # Handle various response formats
                    if isinstance(raw_data, list):
                        posts = raw_data
                    elif isinstance(raw_data, dict):
                        posts = raw_data.get("items", raw_data.get("data", raw_data.get("posts", [])))
                        if not posts and "ok" in raw_data:
                            if raw_data.get("ok"):
                                posts = raw_data.get("data", raw_data.get("result", []))
                            else:
                                error = raw_data.get("error", {}).get("message", "opencli search failed")
                except json.JSONDecodeError:
                    error = f"Failed to parse opencli output"

            if result.returncode != 0:
                stderr = result.stderr.strip()
                if "BROWSER_CONNECT" in stderr or "Browser Bridge" in stderr:
                    error = "需要Chrome浏览器扩展（opencli Browser Bridge）"
                else:
                    error = stderr[:200] if stderr else f"opencli exit code {result.returncode}"

        except subprocess.TimeoutExpired:
            error = "XHS搜索超时（60s）"
        except FileNotFoundError:
            error = "opencli 未安装或不在 PATH 中"
        except Exception as e:
            error = str(e)[:200]
            logger.warning("XHS search error", brand=brand_id, error=error)

        # Sort by likes descending, take top N
        if posts:
            for i, p in enumerate(posts):
                # Ensure unique id
                if not p.get("id"):
                    p["id"] = hashlib.md5(
                        (p.get("title", "") + p.get("url", "") + str(i)).encode()
                    ).hexdigest()[:12]
                # Normalize likes field
                if "likes" not in p and "like_count" in p:
                    p["likes"] = p["like_count"]
                if "likes" not in p:
                    p["likes"] = 0
                # Normalize cover image - use proxy URL
                if "cover" not in p and "images" in p:
                    imgs = p["images"]
                    p["cover"] = imgs[0] if isinstance(imgs, list) and imgs else ""
                if "cover" not in p:
                    p["cover"] = ""
                # Convert cover to proxy URL if it's an external URL
                if p["cover"] and p["cover"].startswith("http"):
                    p["cover_proxy"] = f"/api/social/image-proxy?url={quote(p['cover'], safe='')}"
                else:
                    p["cover_proxy"] = p["cover"]
                # Detect if it's a video (no cover + has video flag)
                if not p["cover"] and p.get("type") == "video":
                    p["cover_proxy"] = ""  # Will show placeholder
                    p["type"] = "video"

            posts.sort(key=lambda p: p.get("likes", 0), reverse=True)
            posts = posts[:limit]

        # Build result
        cached_at = time.time()
        result_data = {
            "brand_id": brand_id,
            "search_keyword": keyword,
            "posts": posts,
            "total_found": len(posts),
            "cached_at": cached_at,
            "from_cache": False,
            "error": error,
        }

        # Always cache what we have (even if empty/error) to avoid hammering
        cache_data = {**result_data, "cached_at": cached_at}
        self._save_cache(brand_id, cache_data)

        # If live search failed, try to return stale cache
        if error and not posts:
            stale = self._load_cache_stale(brand_id)
            if stale:
                stale["error"] = error
                stale["from_cache"] = True
                return stale

        return result_data

    def _load_cache_stale(self, brand_id: str) -> Optional[dict]:
        """Load cache regardless of age (stale fallback)."""
        cache_file = self._cache_path(brand_id)
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
