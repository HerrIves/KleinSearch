"""Fetching and parsing Kleinanzeigen search result pages (no per-listing page visits)."""
import json
import random
import re
from typing import Awaitable, Callable, Dict, List, Optional

from bs4 import BeautifulSoup

from evaluator import BASE_URL, make_search_url
from logger import logger
from models import NO_PRICE, SHIPPING_NO, SHIPPING_YES, UNKNOWN_LOCATION

_PRICE_IN_TEXT = re.compile(r"(\d[\d.,]*\s*€(?:\s*VB)?)", re.I)


def _text(tag) -> str:
    return tag.get_text(" ", strip=True) if tag else ""


def _icon_text(article, icon_name: str) -> str:
    """Text next to an svg icon, e.g. locationOutline / calendarOutline."""
    svg = article.find("svg", attrs={"data-title": icon_name})
    if svg and svg.parent:
        return _text(svg.parent.find("span"))
    return ""


def _parse_price(article) -> str:
    tag = article.find("p", class_="aditem-main--middle--price-shipping--price") or article.find(
        "p", class_=re.compile(r"text-title3")
    )
    candidates = [_text(tag)] if tag else []
    candidates += [_text(t) for t in article.find_all(["p", "span"])]
    for text in candidates:
        if not text or len(text) > 40:
            continue
        if "verschenken" in text.lower():
            return "Zu verschenken"
        m = _PRICE_IN_TEXT.search(text)
        if m:
            return " ".join(m.group(1).split())
        if text.strip().upper() == "VB":
            return "VB"
    return NO_PRICE


def _parse_shipping(article) -> str:
    for tag in article.find_all(["span", "p"]):
        txt = _text(tag).lower()
        if "versand möglich" in txt or "+ versand" in txt or "direkt kaufen" in txt:
            return SHIPPING_YES
    return SHIPPING_NO


def parse_listings_from_html(html: str) -> List[Dict[str, str]]:
    """Extracts raw listings (title, snippet description, price, ...) from a search result page."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for art in soup.find_all("article"):
        heading = art.find(["h2", "h3", "h4"])
        title = _text(heading)
        if not title:
            continue

        href = art.get("data-href") or ""
        if not href and heading and heading.find("a", href=True):
            href = heading.find("a", href=True)["href"]
        link = href if href.startswith("http") else (BASE_URL + href if href else "")

        description = ""
        ld = art.find("script", type="application/ld+json")
        if ld and ld.string:
            try:
                description = json.loads(ld.string).get("description", "") or ""
            except ValueError:
                pass
        if not description:
            p_desc = art.find("p", class_=re.compile(r"description|text-bodyRegular"))
            description = p_desc.get_text(" ", strip=True) if p_desc else ""

        old_location = art.find(class_="aditem-main--top--left")
        location = _icon_text(art, "locationOutline") or _text(old_location) or UNKNOWN_LOCATION

        results.append(
            {
                "id": art.get("data-adid") or link,
                "title": title,
                "description": " ".join(description.split()),
                "price": _parse_price(art),
                "location": location,
                "shipping": _parse_shipping(art),
                "posted": _icon_text(art, "calendarOutline"),
                "link": link,
            }
        )
    return results


async def scan_url(page, url: str) -> List[Dict[str, str]]:
    """Loads one search page in the browser with light human-like behaviour."""
    logger.info(f"  Loading: {url}")
    await page.goto(url, wait_until="domcontentloaded")
    for label in ("Alle akzeptieren", "Akzeptieren"):
        try:
            button = page.get_by_role("button", name=label)
            if await button.first.is_visible(timeout=1500):
                await button.first.click()
                logger.info("  Cookies accepted")
                break
        except Exception:
            pass
    for _ in range(random.randint(2, 3)):
        await page.mouse.wheel(0, random.randint(350, 600))
        await page.wait_for_timeout(random.randint(400, 800))
    return parse_listings_from_html(await page.content())


async def scan_query(
    page,
    query: str,
    pages: int = 1,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    category: str = "",
    on_page: Optional[Callable[[int, int], Awaitable[None]]] = None,
) -> List[Dict[str, str]]:
    """Scans up to `pages` result pages for one query. Stops early on an empty page."""
    all_results: List[Dict[str, str]] = []
    seen = set()
    for page_num in range(1, pages + 1):
        if on_page:
            await on_page(page_num, pages)
        url = make_search_url(query, price_min, price_max, category, page=page_num)
        try:
            results = await scan_url(page, url)
        except Exception as e:
            logger.warning(f"  Error on page {page_num}: {e}")
            break
        new = [r for r in results if r["id"] not in seen]
        seen.update(r["id"] for r in new)
        all_results.extend(new)
        logger.info(f"  Page {page_num}: {len(new)} new listings (total {len(all_results)})")
        if not new:
            break
        if page_num < pages:
            await page.wait_for_timeout(int(random.uniform(2.0, 4.0) * 1000))
    return all_results
