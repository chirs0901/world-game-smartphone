"""Social media service — Xiaohongshu (小红书) post capture for brand monitoring.

Uses opencli CLI to search Xiaohongshu for brand-related posts.
Caches results for 2 hours. Falls back to cached data when live search is unavailable.
Cover images are fetched from XHS note pages (opencli search doesn't return images).
"""

import hashlib
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import httpx

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

    def _fetch_note_cover(self, post_url: str) -> tuple[str, bool]:
        """Fetch a XHS note page and extract the cover image URL.

        XHS note pages contain __INITIAL_STATE__ with full note data
        including imageList (cover images) and video info.

        Returns:
            (cover_url, is_video)
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.xiaohongshu.com/",
            }
            resp = httpx.get(post_url, headers=headers, follow_redirects=True, timeout=12.0)
            html = resp.text

            # Parse __INITIAL_STATE__
            state_match = re.search(
                r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*</script>",
                html,
                re.DOTALL,
            )
            if not state_match:
                return ("", False)

            raw = state_match.group(1).replace("undefined", "null")
            state = json.loads(raw)
            note_map = state.get("note", {}).get("noteDetailMap", {})

            for _nid, ndata in note_map.items():
                note_info = ndata.get("note", {})
                is_video = bool(note_info.get("video"))
                img_list = note_info.get("imageList", [])
                if img_list and isinstance(img_list, list):
                    first_img = img_list[0]
                    if isinstance(first_img, dict):
                        cover_url = first_img.get("urlDefault", first_img.get("url", ""))
                        if cover_url:
                            # Upgrade http to https for security
                            if cover_url.startswith("http://"):
                                cover_url = "https://" + cover_url[7:]
                            return (cover_url, is_video)

            return ("", False)

        except Exception as e:
            logger.debug("Note cover fetch failed", url=post_url[:60], error=str(e)[:80])
            return ("", False)

    def _fetch_covers_batch(self, posts: list[dict], max_count: int = 10) -> None:
        """Fetch cover images for top posts in parallel.

        Modifies posts in-place by setting 'cover' and 'type' fields.
        Only fetches covers for posts that don't already have one.
        """
        # Select posts that need cover fetching (top N by likes)
        candidates = []
        for p in posts[:max_count]:
            if not p.get("cover"):
                url = p.get("url", "")
                if url and "xiaohongshu.com" in url:
                    candidates.append(p)

        if not candidates:
            return

        logger.info("Fetching XHS note covers", count=len(candidates))

        def _worker(post: dict) -> tuple[dict, str, bool]:
            cover_url, is_video = self._fetch_note_cover(post["url"])
            return (post, cover_url, is_video)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_worker, p): p for p in candidates}
            for future in as_completed(futures, timeout=30):
                try:
                    post, cover_url, is_video = future.result(timeout=15)
                    if cover_url:
                        post["cover"] = cover_url
                        if is_video:
                            post["type"] = "video"
                        else:
                            if not post.get("type"):
                                post["type"] = "note"
                except Exception:
                    pass  # Leave cover empty

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

        # Normalize fields and sort by likes descending
        if posts:
            for i, p in enumerate(posts):
                # Ensure unique id
                if not p.get("id"):
                    p["id"] = hashlib.md5(
                        (p.get("title", "") + p.get("url", "") + str(i)).encode()
                    ).hexdigest()[:12]
                # Normalize likes field (opencli returns string likes like "5.7万")
                if "likes" not in p and "like_count" in p:
                    p["likes"] = p["like_count"]
                if "likes" not in p:
                    p["likes"] = 0
                # Parse string likes like "5.7万" into numeric
                if isinstance(p["likes"], str):
                    p["likes"] = self._parse_likes(p["likes"])
                # Ensure cover field exists
                if "cover" not in p:
                    # Try alternative field names from opencli
                    for alt in ("image", "thumb", "cover_url", "cover_image"):
                        if alt in p:
                            p["cover"] = p[alt]
                            break
                    else:
                        p["cover"] = ""

            # Sort by likes (highest first) then take top N
            posts.sort(key=lambda p: p.get("likes", 0), reverse=True)
            posts = posts[:limit]

            # Fetch cover images for top posts (opencli search doesn't return covers)
            self._fetch_covers_batch(posts, max_count=10)

            # Generate proxy URLs for covers
            for p in posts:
                if p.get("cover") and p["cover"].startswith("http"):
                    p["cover_proxy"] = f"/api/social/image-proxy?url={quote(p['cover'], safe='')}"
                else:
                    p["cover_proxy"] = ""
                # Determine type if not already set by cover fetcher
                if not p.get("type"):
                    p["type"] = "note"

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

    @staticmethod
    def _parse_likes(raw: str) -> int:
        """Parse XHS likes string like '952', '5.7万', '1.2万' into int."""
        s = raw.strip()
        try:
            if '万' in s:
                return int(float(s.replace('万', '')) * 10000)
            if '亿' in s:
                return int(float(s.replace('亿', '')) * 100000000)
            return int(s.replace(',', '').replace('+', ''))
        except (ValueError, AttributeError):
            return 0

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
