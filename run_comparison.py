import asyncio
import sys
import os
import random
import re
import urllib.parse
import csv
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_MAX_PRICE = 100
BROWSER_PROFILE_DIR = r"c:\work\browser_profile"
OLD_CSV_PATH = r"c:\work\listings_old_variant.csv"
NEW_CSV_PATH = r"c:\work\listings_new_variant.csv"
EXISTING_DB_PATH = r"c:\work\donor_listings.csv"

# ==========================================
# 1. ЗАПРОСЫ ДЛЯ СТАРОГО И НОВОГО ВАРИАНТОВ
# ==========================================

OLD_QUERIES = [
    {"name": "ThinkPad E15", "query": "thinkpad e15"},
    {"name": "ThinkPad L590", "query": "thinkpad l590"},
    {"name": "Lenovo V15", "query": "lenovo v15"},
    {"name": "Medion E15302", "query": "medion e15302"},
    {"name": "HP ProBook 450", "query": "probook 450"},
    {"name": "Dell Latitude 5500", "query": "latitude 5500"},
    {"name": "Fujitsu Lifebook E558", "query": "lifebook e558"},
    {"name": "Fujitsu Lifebook E559", "query": "lifebook e559"},
    {"name": "Fujitsu Lifebook E5510", "query": "lifebook e5510"},
]

NEW_QUERIES = [
    {"name": "Fujitsu Lifebook U758", "query": "fujitsu u758"},
    {"name": "Fujitsu Lifebook U759", "query": "fujitsu u759"},
    {"name": "Fujitsu Lifebook U7510", "query": "fujitsu u7510"},
    {"name": "ThinkPad T590", "query": "thinkpad t590"},
    {"name": "ThinkPad T15", "query": "thinkpad t15"},
    {"name": "ThinkPad P53s", "query": "thinkpad p53s"},
    {"name": "ThinkPad P15s", "query": "thinkpad p15s"},
    {"name": "HP EliteBook 850", "query": "elitebook 850"},
    {"name": "HP ZBook 15", "query": "zbook 15"},
    {"name": "HP ZBook Firefly 15", "query": "zbook firefly 15"},
    {"name": "Dell Latitude 7500", "query": "latitude 7500"},
    {"name": "Dell Latitude 7510", "query": "latitude 7510"},
]

# ==========================================
# 2. ФИЛЬТРЫ И СПИСКИ СОВМЕСТИМОСТИ
# ==========================================

OLD_WHITELIST = [
    r"thinkpad\s*e15",
    r"\be15\b(?:\s*gen\s*[234])?",
    r"thinkpad\s*l590|\bl590\b",
    r"lenovo\s*v15|\bv15\b",
    r"medion\s*(?:akoya\s*)?e15302|\be15302\b",
    r"probook\s*(?:450|455)\s*(?:g[6-9]|g10)\b",
    r"probook.*(?:fhd|full\s*hd)",
    r"latitude\s*(?:5500|5510|5520|3510|3520|55\d\d|35\d\d)",
    r"(?:fujitsu|lifebook).*?\b(?:e\s*558|e\s*559|e\s*5510|e\s*5511)\b",
    r"\b(?:e558|e559|e5510|e5511)\b",
]

NEW_WHITELIST = [
    r"thinkpad\s*t590|\bt590\b",
    r"thinkpad\s*t15|\bt15\b",
    r"thinkpad\s*p53s|\bp53s\b",
    r"thinkpad\s*p15s|\bp15s\b",
    r"elitebook\s*850\b",
    r"zbook\s*(?:firefly\s*)?15\b",
    r"latitude\s*7500\b",
    r"latitude\s*7510\b",
    r"(?:fujitsu|lifebook).*?\b(?:u\s*758|u\s*759|u\s*7510|u\s*7511)\b",
    r"\b(?:u758|u759|u7510|u7511)\b",
]

COMMON_BLACKLIST = [
    r"\bt550\b",
    r"thinkpad\s*t550",
    r"\bt540\b",
    r"\bw540\b",
    r"\bw541\b",
    r"probook\s*(?:450|455)\s*g[1-4]\b",
    r"elitebook\s*850\s*g[1-4]\b",
    r"zbook\s*15\s*g[1-4]\b",
    r"latitude\s*(?:e55\d\d|e65\d\d)\b",
    r"\b(?:u748|u749|u7410|u7411|e548|e549|e5410|e5411)\b",
    r"\b(?:u728|u729|u7210|u7211)\b",
    r"lifebook\s*(?:e75[1-4]|a5\d\d)\b",
]

SCREEN_DEFECT_KEYWORDS = [
    r"displaybruch",
    r"displayschaden",
    r"panelschaden",
    r"bildschirm\s*defekt",
    r"defektes?\s*display",
    r"display\s*defekt",
    r"bildschirmbruch",
    r"glas\s*gebrochen",
    r"\briss(?:e)?\b",
    r"\bgesprungen(?:es)?\b",
    r"\bstreifen\b"
]

LOW_RESOLUTION_KEYWORDS = [
    r"\b1366\s*x\s*768\b",
    r"\b1366x768\b",
    r"\bwxga\b",
    r"\bhd-display\b",
    r"\bhd\s+display\b",
    r"\bhd\s+bildschirm\b",
    r"\bhd\s+auflösung\b",
    r"\bnur\s*hd\b"
]

AD_STATUS_STOPWORDS = [
    r"\breserviert\b",
    r"\bgelöscht\b",
    r"\bverkauft\b",
    r"\bgesucht\b",
    r"\bsuche\b"
]

# Улучшенный фильтр запчастей без матрицы (учитывает немецкие сложные слова)
SPARE_PARTS_WITHOUT_SCREEN = [
    r"\b(?:tastatur|keyboard)\b",
    r"\b(?:mainboard|motherboard)\b",
    r"\b(?:akku|batterie)\b",
    r"\b(?:netzteil|ladekabel|charger|stromkabel)\b",
    r"\b(?:unterer\s*deckel|bodendeckel|unterteil|gehäusedeckel|bottom\s*base)\b",
    r"\b(?:docking[- ]?station|portreplikator|dock)\b",
    r"\b(?:wlan|bluetooth)[- ]?board\b",
    r"\blautsprecher\w*",
    r"\bspeaker\w*",
    r"\b(?:lüfter|kühler|cpu-lüfter|fan)\b",
    r"\b(?:trackpad|touchpad)\b",
    r"\b(?:schrauben\w*|einzeltasten)\b",
    r"\b(?:subboard|daughterboard)\b",
    r"\bscharnier\w*",
    r"\b(?:displayblende|displayrahmen)\b",
]

STORAGE_EXCLUDE_KEYWORDS = [
    r"\bohne\s*ssd\b",
    r"\bssd\s*ausgebaut\b",
    r"\bssd\s*fehlt\b",
    r"\bkeine\s*ssd\b",
    r"\bohne\s*festplatte\b",
    r"\bfestplatte\s*ausgebaut\b",
    r"\b500\s*gb\s*(?:sata\s*)?hdd\b",
    r"\b1\s*tb\s*(?:sata\s*)?hdd\b"
]

STORAGE_PATTERNS = [
    r"512\s*(?:gb\s*)?(?:ssd|nvme|m\.?2)\b",
    r"(?:ssd|nvme|m\.?2)[^\n\.,]{0,20}512\s*gb\b",
    r"512er\s*ssd\b",
    r"0[.,]5\s*tb\s*(?:ssd|nvme)\b"
]

def make_search_url(query: str, max_price: int = DEFAULT_MAX_PRICE) -> str:
    slug = urllib.parse.quote(query.strip().lower().replace(" ", "-"))
    if max_price:
        return f"https://www.kleinanzeigen.de/s-notebooks/preis::{max_price}/{slug}/k0c278"
    return f"https://www.kleinanzeigen.de/s-notebooks/{slug}/k0c278"

def parse_price_value(price_str: str) -> float | None:
    if not price_str:
        return None
    if "zu verschenken" in price_str.lower():
        return 0.0
    m = re.search(r"(\d+(?:[.,]\d+)?)", price_str)
    if m:
        val = m.group(1).replace(".", "").replace(",", ".")
        try:
            return float(val)
        except ValueError:
            return None
    return None

def evaluate_item(item: dict, whitelist: list, variant_name: str) -> dict:
    title_lower = item.get("title", "").lower()
    text = f"{title_lower} {item.get('description', '')}".lower()

    num_price = parse_price_value(item.get("price", ""))
    if num_price is not None and num_price > DEFAULT_MAX_PRICE:
        item["status"] = "REJECTED"
        item["reason"] = f"Цена превышает {DEFAULT_MAX_PRICE} €"
        return item

    for sp in AD_STATUS_STOPWORDS:
        if re.search(sp, title_lower):
            item["status"] = "REJECTED"
            item["reason"] = "Объявление снято или поиск покупки"
            return item

    has_fhd = bool(re.search(r"\b(?:fhd|full\s*hd|1920\s*x\s*1080|1920x1080)\b", text))
    if not has_fhd:
        for lr in LOW_RESOLUTION_KEYWORDS:
            if re.search(lr, text):
                item["status"] = "REJECTED"
                item["reason"] = "Низкое разрешение HD (требуется FHD)"
                return item

    for bp in COMMON_BLACKLIST:
        if re.search(bp, text):
            item["status"] = "REJECTED"
            item["reason"] = "В черном списке (старая толстая или несовместимая матрица)"
            return item

    for dp in SCREEN_DEFECT_KEYWORDS:
        if re.search(dp, text):
            item["status"] = "REJECTED"
            item["reason"] = "Дефект экрана"
            return item

    # Проверка запчастей без экрана (если явно не указано display/matrix/bildschirm)
    has_screen_core = bool(re.search(r"\b(?:display|bildschirm|matrix|panel|lcd|screen)\b", title_lower))
    has_laptop_word = bool(re.search(r"\b(?:laptop|notebook|rechner)\b", title_lower))
    
    for sp in SPARE_PARTS_WITHOUT_SCREEN:
        if re.search(sp, title_lower):
            # Если это отдельная деталь и нет матрицы
            if not has_screen_core:
                item["status"] = "REJECTED"
                item["reason"] = "Запчасть/аксессуар без матрицы (динамики, док, петли, плата)"
                return item

    matched_model = False
    for wp in whitelist:
        if re.search(wp, text):
            matched_model = True
            break

    if not matched_model:
        item["status"] = "REJECTED"
        item["reason"] = f"Не входит в белый список ({variant_name})"
        return item

    has_storage_exclude = any(re.search(p, text) for p in STORAGE_EXCLUDE_KEYWORDS)
    has_512 = any(re.search(sp, text) for sp in STORAGE_PATTERNS) and not has_storage_exclude
    item["has_512gb"] = has_512

    if has_512:
        item["status"] = "MATCH"
        item["reason"] = f"Идеально: совместимый донор 15.6\" FHD Slim + SSD 512GB ({variant_name})"
    else:
        item["status"] = "POTENTIAL"
        if has_storage_exclude:
            item["reason"] = "Подходящая матрица 15.6\" FHD Slim (SSD отсутствует или только HDD)"
        else:
            item["reason"] = f"Подходящая матрица 15.6\" FHD Slim (объем SSD требует уточнения) [{variant_name}]"

    return item

def parse_articles(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article", class_="aditem")
    if not articles:
        articles = soup.find_all("article")

    raw_items = []
    for art in articles:
        ad_id = art.get("data-adid")
        heading = art.find(["h2", "h3", "h4"])
        title_tag = art.find("a", class_="ellipsis") or (heading.find("a") if heading else None)
        
        title = heading.get_text(strip=True) if heading else (title_tag.get_text(strip=True) if title_tag else "")
        if not title:
            continue

        href = art.get("data-href")
        if not href and heading:
            a_tag = heading.find("a")
            if a_tag and a_tag.get("href"):
                href = a_tag.get("href")
            else:
                span = heading.find(attrs={"data-url": True})
                if span:
                    href = span.get("data-url")
        if not href and title_tag and title_tag.get("href"):
            href = title_tag.get("href")
        if not href:
            continue

        link = "https://www.kleinanzeigen.de" + href if href.startswith("/") else href
        desc_el = art.find("p", class_="aditem-main--middle--description")
        description = desc_el.get_text(separator=" ", strip=True) if desc_el else ""

        price_box = art.find(class_=re.compile(r"price", re.I))
        price = "Не указана"
        if price_box:
            m_price = re.search(r"(\d+[\d\.,]*\s*€(?:\s*VB)?)", price_box.get_text(separator=" ", strip=True))
            price = m_price.group(1).strip() if m_price else price_box.get_text(strip=True)

        location = "Не указано"
        loc_box = art.find(class_=re.compile(r"location", re.I))
        if loc_box:
            txt = loc_box.get_text(separator=" ", strip=True)
            txt = re.sub(r"\s+", " ", txt).strip()
            if txt:
                location = txt

        shipping = "Только самовывоз"
        for badge in art.find_all(class_=re.compile(r"(shipping|delivery|badge|tag|bubble)", re.I)):
            txt = badge.get_text(separator=" ", strip=True).lower()
            if "versand möglich" in txt or "+ versand" in txt or "direkt kaufen" in txt:
                shipping = "Доставка возможна"
                break
        if shipping == "Только самовывоз":
            old_ship = art.find(class_="aditem-main--middle--price-shipping--shipping")
            if old_ship and "versand" in old_ship.get_text(strip=True).lower():
                shipping = "Доставка возможна"

        raw_items.append({
            "id": ad_id or link,
            "title": title,
            "description": description,
            "price": price,
            "location": location,
            "shipping": shipping,
            "link": link
        })
    return raw_items

def load_user_notes(db_path: str) -> dict:
    notes = {}
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                for r in reader:
                    rid = str(r.get("ID") or r.get("Ссылка") or "").strip()
                    comm = (r.get("Комментарий") or r.get("Примечание") or "").strip()
                    # Сохраняем только реальные пользовательские правки
                    if comm and not comm.startswith("Идеально:") and not comm.startswith("Подходящая матрица") and not comm.startswith("Подходящая модель") and not comm.startswith("Флагманский"):
                        notes[rid] = comm
        except Exception as e:
            print(f"Загрузка заметок: {e}")
    return notes

def save_variant_csv(listings: list, output_path: str, user_notes: dict):
    fieldnames = [
        "Дата добавления",
        "Статус",
        "Модель / Заголовок",
        "Цена",
        "SSD 512GB",
        "Местоположение",
        "Доставка",
        "Комментарий",
        "Ссылка",
        "ID"
    ]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    seen = set()

    for item in listings:
        status = item.get("status")
        if status not in ["MATCH", "POTENTIAL"]:
            continue
        rid = str(item.get("id") or item.get("link")).strip()
        if rid in seen:
            continue
        seen.add(rid)

        # Подставляем сохраненную пользовательскую заметку, если есть
        comment = user_notes.get(rid, item.get("reason", ""))

        rows.append({
            "Дата добавления": now_str,
            "Статус": status,
            "Модель / Заголовок": item.get("title", ""),
            "Цена": item.get("price", ""),
            "SSD 512GB": "Да" if item.get("has_512gb") else "Уточнить",
            "Местоположение": item.get("location", "Не указано"),
            "Доставка": item.get("shipping", "Уточнить"),
            "Комментарий": comment,
            "Ссылка": item.get("link", ""),
            "ID": rid
        })

    rows.sort(key=lambda r: (1 if r["Статус"] == "MATCH" else 0, r["Цена"]), reverse=True)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)

async def run_scan_set(page, queries: list, whitelist: list, variant_name: str) -> list:
    print(f"\n" + "=" * 60)
    print(f" ▶ ЗАПУСК СКАНИРОВАНИЯ: {variant_name.upper()} ({len(queries)} запросов)")
    print("=" * 60)
    valid_items = []
    seen_ids = set()

    for q in queries:
        url = make_search_url(q["query"], DEFAULT_MAX_PRICE)
        print(f"[{variant_name}] Сканируем '{q['name']}': {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded")
            try:
                btn = page.get_by_role("button", name="Akzeptieren")
                if await btn.is_visible(timeout=1500):
                    await btn.click()
            except Exception:
                pass

            for _ in range(2):
                await page.mouse.wheel(0, random.randint(300, 500))
                await page.wait_for_timeout(random.randint(200, 400))

            html = await page.content()
            raw = parse_articles(html)
            for r in raw:
                if r["id"] in seen_ids:
                    continue
                seen_ids.add(r["id"])
                evaluated = evaluate_item(r, whitelist, variant_name)
                if evaluated["status"] in ["MATCH", "POTENTIAL"]:
                    valid_items.append(evaluated)

            await page.wait_for_timeout(random.randint(1500, 2500))
        except Exception as e:
            print(f"Ошибка при запросе {q['name']}: {e}")

    return valid_items

async def main():
    print("======================================================================")
    print(" СРАВНИТЕЛЬНОЕ СКАНИРОВАНИЕ ДВУХ ВАРИАНТОВ ДОНОРОВ ThinkPad P15 Gen 2")
    print(" 1. Старый вариант: Базовый корпоративный (E15, L590, V15, Medion, ProBook, Lat 5500, E558-E5510)")
    print(" 2. Новый вариант: Премиум & Workstation (T590, T15, P53s, P15s, EliteBook, ZBook, Lat 7500, U758-U7510)")
    print("======================================================================")

    user_notes = load_user_notes(EXISTING_DB_PATH)
    print(f"Загружено сохраненных пользовательских заметок: {len(user_notes)}")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_PROFILE_DIR,
            headless=False,
            slow_mo=200,
            no_viewport=True,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="de-DE"
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # 1. Сканирование старого варианта
        old_items = await run_scan_set(page, OLD_QUERIES, OLD_WHITELIST, "Старый: Базовый корпоративный")
        old_count = save_variant_csv(old_items, OLD_CSV_PATH, user_notes)
        print(f"✔ Старый вариант сохранен: {OLD_CSV_PATH} ({old_count} записей)")

        # 2. Сканирование нового варианта
        new_items = await run_scan_set(page, NEW_QUERIES, NEW_WHITELIST, "Новый: Премиум & Workstation")
        new_count = save_variant_csv(new_items, NEW_CSV_PATH, user_notes)
        print(f"✔ Новый вариант сохранен: {NEW_CSV_PATH} ({new_count} записей)")

        await context.close()

    # 3. Комплексный сравнительный анализ
    print("\n" + "=" * 70)
    print(" 📊 РЕЗУЛЬТАТЫ СРАВНЕНИЯ ДВУХ ВАРИАНТОВ")
    print("=" * 70)
    print(f"• Старый вариант (базовый/массовый): {old_count} объявлений")
    print(f"• Новый вариант (премиум/workstation): {new_count} объявлений")

    old_ids = {str(x['id']): x for x in old_items}
    new_ids = {str(x['id']): x for x in new_items}
    common_ids = set(old_ids.keys()) & set(new_ids.keys())
    print(f"• Общих объявлений между списками: {len(common_ids)}")

    print("\n--- ТОП ИЗ СТАРОГО ВАРИАНТА (Базовый) ---")
    for idx, item in enumerate(old_items[:5], 1):
        print(f"{idx}. {item['title']} | {item['price']} | {item['location']}")
        print(f"   {item['link']}")

    print("\n--- ТОП ИЗ НОВОГО ВАРИАНТА (Премиум) ---")
    for idx, item in enumerate(new_items[:5], 1):
        print(f"{idx}. {item['title']} | {item['price']} | {item['location']}")
        print(f"   {item['link']}")

if __name__ == "__main__":
    asyncio.run(main())
