"""RSS feed aggregation service for industry intelligence."""

import asyncio
import hashlib
import json
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

# OPML file path relative to project root
OPML_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mobile_industry_intelligence.opml")

# RSSHub custom sources (sites without official RSS)
RSSHUB_SOURCES = [
    {
        "name": "中国信通院 手机出货量报告",
        "category": "手机厂商动态",
        "url": "https://rsshub.app/generic/webpage?url=https%3A%2F%2Fwww.caict.ac.cn%2Fkxyj%2Fqwfb%2Fbps%2F&title_selector=.list li a&link_selector=.list li a&description_selector=.list li span&link_prefix=https%3A%2F%2Fwww.caict.ac.cn%2Fkxyj%2Fqwfb%2Fbps%2F",
    },
    {
        "name": "赛诺市场 手机销量月报",
        "category": "手机厂商动态",
        "url": "https://rsshub.app/generic/webpage?url=https%3A%2F%2Fwww.sinoresearch.com%2Fnews&title_selector=.news-list .item h3 a&link_selector=.news-list .item h3 a&description_selector=.news-list .item p&link_prefix=https%3A%2F%2Fwww.sinoresearch.com%2F",
    },
    {
        "name": "洛图科技 屏幕面板报告",
        "category": "屏幕显示",
        "url": "https://rsshub.app/generic/webpage?url=https%3A%2F%2Fwww.runto.com.cn%2Freport&title_selector=.report-list .item h3 a&link_selector=.report-list .item h3 a&description_selector=.report-list .item .desc&link_prefix=https%3A%2F%2Fwww.runto.com.cn%2F",
    },
]


@dataclass
class RSSFeed:
    """An RSS feed source."""
    name: str
    category: str
    xml_url: str
    html_url: str = ""


@dataclass
class RSSItem:
    """A single RSS item/article."""
    id: str
    title: str
    description: str
    link: str
    source_name: str
    source_category: str
    published: str = ""
    fetched_at: float = field(default_factory=time.time)


class RSSService:
    """Fetches, aggregates, and caches RSS feeds for the intel center."""

    def __init__(self):
        self._cache: dict[str, RSSItem] = {}
        self._feeds: list[RSSFeed] = []
        self._last_fetch: dict[str, float] = {}
        self._load_opml()

    def _load_opml(self):
        """Parse OPML file to get feed sources."""
        try:
            tree = ET.parse(OPML_PATH)
            root = tree.getroot()
            body = root.find("body")
            if body is None:
                return
            for category_elem in body.findall("outline"):
                category_name = category_elem.get("text", "未分类")
                for feed_elem in category_elem.findall("outline"):
                    if feed_elem.get("type") == "rss":
                        self._feeds.append(RSSFeed(
                            name=feed_elem.get("text", feed_elem.get("title", "")),
                            category=category_name,
                            xml_url=feed_elem.get("xmlUrl", ""),
                            html_url=feed_elem.get("htmlUrl", ""),
                        ))
        except Exception as e:
            print(f"[RSS] Failed to load OPML: {e}")

    async def fetch_all(self, max_per_source: int = 5) -> list[RSSItem]:
        """Fetch all feeds concurrently."""
        items: list[RSSItem] = []
        semaphore = asyncio.Semaphore(5)

        async def fetch_one(feed: RSSFeed):
            async with semaphore:
                return await self._fetch_feed(feed, max_per_source)

        # Fetch official RSS feeds
        tasks = [fetch_one(f) for f in self._feeds]
        # Also fetch RSSHub custom sources
        for src in RSSHUB_SOURCES:
            tasks.append(self._fetch_rsshub(src["name"], src["category"], src["url"], max_per_source))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                items.extend(result)

        # Deduplicate by title hash
        seen = set()
        unique: list[RSSItem] = []
        for item in sorted(items, key=lambda x: x.published or "", reverse=True):
            h = hashlib.md5(item.title.encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(item)

        # Update cache
        for item in unique:
            self._cache[item.id] = item

        return unique[:50]  # Limit to 50 items

    async def _fetch_feed(self, feed: RSSFeed, max_items: int) -> list[RSSItem]:
        """Fetch a single RSS feed."""
        items: list[RSSItem] = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(feed.xml_url, headers={
                    "User-Agent": "WorldGame-IntelPlatform/1.0 (Industry Intelligence Aggregator)"
                })
                if resp.status_code != 200:
                    return items

                root = ET.fromstring(resp.text)
                # Handle both RSS 2.0 and Atom formats
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                channel = root.find("channel")
                if channel is not None:
                    # RSS 2.0
                    for item_elem in channel.findall("item")[:max_items]:
                        item = self._parse_rss_item(item_elem, feed)
                        if item:
                            items.append(item)
                else:
                    # Try Atom
                    for entry in root.findall("atom:entry", ns)[:max_items]:
                        item = self._parse_atom_entry(entry, feed, ns)
                        if item:
                            items.append(item)
        except Exception as e:
            print(f"[RSS] Failed to fetch {feed.name}: {e}")
        return items

    def _parse_rss_item(self, elem: ET.Element, feed: RSSFeed) -> Optional[RSSItem]:
        """Parse RSS 2.0 item element."""
        title = (elem.findtext("title") or "").strip()
        if not title:
            return None
        desc = (elem.findtext("description") or "").strip()
        # Strip HTML tags from description
        desc = BeautifulSoup(desc, "html.parser").get_text()[:300]
        link = (elem.findtext("link") or "").strip()
        pub_date = (elem.findtext("pubDate") or "")
        item_id = hashlib.md5((title + link).encode()).hexdigest()[:12]
        return RSSItem(
            id=item_id,
            title=title,
            description=desc,
            link=link,
            source_name=feed.name,
            source_category=feed.category,
            published=pub_date,
        )

    def _parse_atom_entry(self, elem: ET.Element, feed: RSSFeed, ns: dict) -> Optional[RSSItem]:
        """Parse Atom entry element."""
        title = (elem.findtext("atom:title", namespaces=ns) or "").strip()
        if not title:
            return None
        summary = (elem.findtext("atom:summary", namespaces=ns) or "").strip()
        desc = BeautifulSoup(summary, "html.parser").get_text()[:300]
        link_elem = elem.find("atom:link", ns)
        link = link_elem.get("href", "") if link_elem is not None else ""
        updated = (elem.findtext("atom:updated", namespaces=ns) or "")
        item_id = hashlib.md5((title + link).encode()).hexdigest()[:12]
        return RSSItem(
            id=item_id,
            title=title,
            description=desc,
            link=link,
            source_name=feed.name,
            source_category=feed.category,
            published=updated,
        )

    async def _fetch_rsshub(self, name: str, category: str, url: str, max_items: int) -> list[RSSItem]:
        """Fetch from RSSHub-generated feed."""
        items: list[RSSItem] = []
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "WorldGame-IntelPlatform/1.0"
                })
                if resp.status_code != 200:
                    return items
                root = ET.fromstring(resp.text)
                channel = root.find("channel")
                if channel is not None:
                    for item_elem in channel.findall("item")[:max_items]:
                        title = (item_elem.findtext("title") or "").strip()
                        if not title:
                            continue
                        desc = (item_elem.findtext("description") or "").strip()
                        desc = BeautifulSoup(desc, "html.parser").get_text()[:300]
                        link = (item_elem.findtext("link") or "").strip()
                        item_id = hashlib.md5((title + link).encode()).hexdigest()[:12]
                        items.append(RSSItem(
                            id=item_id,
                            title=title,
                            description=desc,
                            link=link,
                            source_name=name,
                            source_category=category,
                            published=item_elem.findtext("pubDate") or "",
                        ))
        except Exception as e:
            print(f"[RSSHub] Failed to fetch {name}: {e}")
        return items

    def get_cached(self) -> list[RSSItem]:
        """Return cached items."""
        return sorted(self._cache.values(), key=lambda x: x.fetched_at, reverse=True)[:50]

    def get_feeds(self) -> list[RSSFeed]:
        """Return all feed sources."""
        return self._feeds

    def get_categories(self) -> list[str]:
        """Return unique categories."""
        return list(dict.fromkeys(f.category for f in self._feeds))
