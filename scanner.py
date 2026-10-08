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

# ==========================================
# КОНФИГУРАЦИЯ ТРЕБОВАНИЙ (ThinkPad P15 Gen 2)
# ==========================================

DEFAULT_MAX_PRICE = 150  # Строго до 150 евро
BROWSER_PROFILE_DIR = "browser_profile"  # Постоянный профиль для сохранения куки и сессий
CSV_DATABASE_PATH = "donor_listings.csv"  # Таблица найденных объявлений
MAX_PAGES = 3           # Максимальное количество страниц результатов на один запрос



# 1. Премиальные флагманские модели (15.6" Slim FHD IPS 30-pin, 100% sRGB / 72% NTSC, >= 300-500 нит)
# 1. Премиальные флагманские модели (15.6" Slim FHD IPS 30-pin, 100% sRGB / 72% NTSC, >= 300-500 нит)
PREMIUM_MODELS = [
    # Группа 1: Fujitsu (Lifebook U-серия и рабочие станции Celsius H-серии)
    "u758", "u759", "u7510", "h7510", "h7511", "celsius",
    # Группа 2: Корпоративный HP тонкие (400 нит Low Power 100% sRGB)
    "elitebook 850", "zbook 15u", "firefly 15",
    # Группа 3: Dell старшая 7000-я серия и XPS (500 нит 100% sRGB)
    "latitude 7500", "latitude 7510", "latitude 7520",
    "9570", "7590", "xps 15",
    # Группа 4: Родня от Lenovo и MSI
    "t15g", "p15", "prestige 15"
]

TARGET_QUERIES = [
    # Группа 1: Fujitsu (Lifebook U-серия и рабочие станции Celsius) — 300 нит, 72% NTSC
    {"name": "Fujitsu Lifebook U758", "query": "fujitsu u758"},
    {"name": "Fujitsu Lifebook U759", "query": "fujitsu u759"},
    {"name": "Fujitsu Lifebook U7510", "query": "fujitsu u7510"},
    {"name": "Fujitsu Celsius H7510", "query": "celsius h7510"},
    {"name": "Fujitsu Celsius H7511", "query": "celsius h7511"},
    # Группа 2: Корпоративный HP тонкие — 400 нит 100% sRGB
    {"name": "HP EliteBook 850 (G5-G8)", "query": "elitebook 850"},
    {"name": "HP ZBook 15u", "query": "zbook 15u"},
    {"name": "HP ZBook Firefly 15", "query": "zbook firefly 15"},
    # Группа 3: Dell 7000-й серии и XPS — 500 нит 100% sRGB
    {"name": "Dell Latitude 7500", "query": "latitude 7500"},
    {"name": "Dell Latitude 7510", "query": "latitude 7510"},
    {"name": "Dell Latitude 7520", "query": "latitude 7520"},
    {"name": "Dell XPS 15 9570", "query": "xps 9570"},
    {"name": "Dell XPS 15 7590", "query": "xps 7590"},
    # Группа 4: Lenovo и MSI — 100% sRGB
    {"name": "ThinkPad T15g", "query": "thinkpad t15g"},
    {"name": "ThinkPad P15", "query": "thinkpad p15"},
    {"name": "MSI Prestige 15", "query": "msi prestige 15"},
    # Группа 5: Хорошая корпоративная IPS (Slim 30-pin, ~45-72% NTSC)
    {"name": "ThinkPad T590", "query": "thinkpad t590"},
    {"name": "ThinkPad P53s", "query": "thinkpad p53s"},
    {"name": "Dell Latitude 5500", "query": "latitude 5500"},
    {"name": "Dell Latitude 5510", "query": "latitude 5510"},
    {"name": "Dell Latitude 5520", "query": "latitude 5520"},
]

# 2. Белый список моделей (Матрица 15.6" Slim 30-pin FHD без ушек)
WHITELIST_MODELS = [
    # Группа 1: Fujitsu Lifebook U-серия 15.6" и Celsius H-серия 15.6" (300 нит, 72% NTSC)
    r"(?:fujitsu|lifebook).*?\b(?:u\s*758|u\s*759|u\s*7510)\b",
    r"\b(?:u758|u759|u7510)\b",
    r"(?:fujitsu|celsius).*?\b(?:h\s*7510|h\s*7511)\b",
    r"\b(?:h7510|h7511)\b",

    # Группа 2: Корпоративный HP тонкие (EliteBook 850 G5-G8, ZBook 15u, ZBook Firefly 15)
    r"elitebook\s*850\s*(?:g[5678]|g\s*[5678])\b",
    r"zbook\s*15u\b",
    r"zbook\s*firefly\s*15\b",
    r"firefly\s*15\b",

    # Группа 3: Dell Latitude 7000-й серии и XPS 15 (500 нит 100% sRGB)
    r"latitude\s*(?:7500|7510|7520)\b",
    r"xps\s*(?:15\s*)?(?:9570|7590)\b",
    r"\b(?:9570|7590)\b",

    # Группа 4: Lenovo ThinkPad P15 / T15g и MSI Prestige 15 (100% sRGB)
    r"thinkpad\s*t15g\b|\bt15g\b",
    r"thinkpad\s*p15\b(?!\s*s\b)",
    r"\bp15\s*gen\s*[123]\b",
    r"msi\s*prestige\s*15\b|prestige\s*15\b",

    # Группа 5: Хорошая корпоративная IPS (~45-72% NTSC, Slim 30-pin, совместимый шлейф)
    r"thinkpad\s*t590\b|\bt590\b",
    r"thinkpad\s*p53s\b|\bp53s\b",
    r"latitude\s*(?:5500|5510|5520)\b",
]

# 3. Черный список (несовместимые матрицы, толстые экраны, заведомо плохие конфигурации)
BLACKLIST_MODELS = [
    r"\bt550\b",
    r"thinkpad\s*t550",
    r"\bt540\b",
    r"\bw540\b",
    r"\bw541\b",
    r"celsius\s*h7[23678]\d\b",                  # Старые тяжелые Celsius H720-H780
    r"elitebook\s*850\s*g[1-4]\b",               # Старые EliteBook 850 G1-G4 (толстые экраны)
    r"zbook\s*15\b(?!\s*u\b)",                  # Толстый ZBook 15 без буквы 'u'
    r"latitude\s*(?:e55\d\d|e65\d\d|35\d\d)\b", # Старые Latitude E-серии и младшие 3000
    r"thinkpad\s*p15s\b|\bp15s\b",              # P15s (250 нит, 45% NTSC в базовых конфигах)
    # Старые процессоры 2-7 поколений (2011-2017 гг)
    r"\b(?:i[357]-?[234567]\d{3}[a-z]?)\b",
    # Другие диагонали
    r"\b(?:u748|u749|u7410|u7411|e548|e549|e5410|e5411)\b",
    r"\b(?:u728|u729|u7210|u7211)\b",
    r"lifebook\s*(?:e75[1-4]|a5\d\d)\b",
    r"xps\s*13\b",
    r"latitude\s*74\d\d\b",
]


# 4. Несовместимое высокое разрешение (4K / UHD / OLED требуют 40-pin шлейф вместо 30-pin)
HIGH_RESOLUTION_KEYWORDS = [
    r"\b4k\b",
    r"\buhd\b",
    r"\bultra\s*hd\b",
    r"\b3840\s*x\s*2160\b",
    r"\b3840x2160\b",
    r"\boled\b"
]

# 3. Дефекты экрана (Стоп-слова)
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

# 4. Низкое разрешение матрицы (HD 1366x768 вместо требуемого FHD 1920x1080)
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

# 5. Стоп-слова статуса объявления (зарезервировано, снято, поиск покупки)
AD_STATUS_STOPWORDS = [
    r"\breserviert\b",
    r"\bgelöscht\b",
    r"\bverkauft\b",
    r"\bgesucht\b",
    r"\bsuche\b",
]

# 6. Отдельные запчасти без матрицы
# 6. Отдельные запчасти без матрицы — два уровня строгости:

# 6а. СТРОГИЕ стоп-слова: никогда не упоминаются как «аксессуар в комплекте» у целого ноутбука.
#     Отклоняем если есть в заголовке (кроме случаев наличия экрана в заголовке).
SPARE_PARTS_STRICT = [
    r"tastatur\w*",
    r"keyboard\w*",
    r"\b(?:mainboard|motherboard)\b",
    r"\b(?:unterer\s*deckel|bodendeckel|bodenplatte|unterteil|unterseite|gehäusedeckel|bottom\s*base|backplate)\b",
    r"\b(?:wlan|bluetooth)[- ]?board\b",
    r"lautsprecher\w*",
    r"speaker\w*",
    r"\b(?:lüfter|kühler|cpu-lüfter|fan)\b",
    r"\b(?:trackpad|touchpad)\b",
    r"\b(?:schrauben\w*|einzeltasten)\b",
    r"\b(?:subboard|daughterboard|platine)\b",
    r"scharnier\w*",
    r"\b(?:displayblende|displayrahmen)\b",
    r"\bersatzteile\b",    # «Ersatzteile» — запчасти
    r"\bteile\b",          # «Teile» — части/запчасти
]

# 6б. КОНТЕКСТНЫЕ стоп-слова: могут означать «входит в комплект» ("mit Akku", "mit Dockingstation").
#     Используем позиционную проверку: отклоняем только если название ноутбука
#     НЕ стоит до стоп-слова в заголовке.
SPARE_PARTS_CONTEXT = [
    r"\b(?:akku|batterie)\b",
    r"\b(?:netzteil|ladekabel|charger|stromkabel)\b",
    r"\b(?:docking[- ]?station|portreplikator|dock)\b",
    r"\bpalmrest\b",       # Подставка для ладони
]

# 7. Исключение накопителей без SSD или только HDD
STORAGE_EXCLUDE_KEYWORDS = [
    r"\bohne\s*ssd\b",
    r"\bssd\s*ausgebaut\b",
    r"\bssd\s*fehlt\b",
    r"\bkeine\s*ssd\b",
    r"\bohne\s*festplatte\b",
    r"\bfestplatte\s*ausgebaut\b",
    r"\b500\s*gb\s*(?:sata\s*)?hdd\b",
    r"\bsata\s*hdd\b"
]

# 8. Строгая проверка накопителя на 512 ГБ SSD
STORAGE_PATTERNS = [
    r"512\s*(?:gb\s*)?(?:ssd|nvme|m\.?2)\b",
    r"(?:ssd|nvme|m\.?2)[^\n\.,]{0,20}512\s*gb\b",
    r"512er\s*ssd\b",
    r"0[.,]5\s*tb\s*(?:ssd|nvme)\b"
]



def make_search_url(query: str, max_price: int = DEFAULT_MAX_PRICE, page: int = 1) -> str:
    """Генерирует правильный URL поиска Kleinanzeigen с ключевым словом, лимитом цены и номером страницы."""
    slug = urllib.parse.quote(query.strip().lower().replace(" ", "-"))
    base = (
        f"https://www.kleinanzeigen.de/s-notebooks/preis::{max_price}/{slug}/k0c278"
        if max_price else
        f"https://www.kleinanzeigen.de/s-notebooks/{slug}/k0c278"
    )
    if page > 1:
        return f"{base}?pageNum={page}"
    return base


def parse_price_value(price_str: str) -> float | None:
    """Извлекает числовое значение цены из строки."""
    if not price_str:
        return None
    if "zu verschenken" in price_str.lower():
        return 0.0
    # Ищем число вида 100, 99, 1.200 или 120,50
    m = re.search(r"(\d+(?:[.,]\d+)?)", price_str)
    if m:
        val = m.group(1).replace(".", "").replace(",", ".")
        try:
            return float(val)
        except ValueError:
            return None
    return None

def evaluate_listing(item: dict) -> dict:
    """Оценивает объявление по всем критериям для ThinkPad P15 Gen 2."""
    title_lower = item.get("title", "").lower()
    text = f"{title_lower} {item.get('description', '')}".lower()

    # 0. Проверка максимальной цены (строго до DEFAULT_MAX_PRICE евро)
    num_price = parse_price_value(item.get("price", ""))
    if num_price is not None and num_price > DEFAULT_MAX_PRICE:
        item["status"] = "REJECTED"
        item["reason"] = f"Цена превышает {DEFAULT_MAX_PRICE} € ({item.get('price')})"
        return item

    # 1. Проверка статуса объявления (зарезервировано, снято, поиск покупки)
    for sp in AD_STATUS_STOPWORDS:
        if re.search(sp, title_lower):
            item["status"] = "REJECTED"
            item["reason"] = "Объявление снято, зарезервировано или поиск покупки"
            return item

    # 2. Проверка несовместимого разрешения (4K / UHD / OLED - шлейф 40-pin вместо 30-pin)
    for hr in HIGH_RESOLUTION_KEYWORDS:
        if re.search(hr, text):
            item["status"] = "REJECTED"
            item["reason"] = "Несовместимое разрешение 4K/UHD/OLED (шлейф 40-pin, требуется 30-pin FHD)"
            return item

    # 3. Проверка низкого разрешения матрицы (HD 1366x768 вместо FHD 1920x1080)
    has_fhd = bool(re.search(r"\b(?:fhd|full\s*hd|1920\s*x\s*1080|1920x1080)\b", text))
    if not has_fhd:
        for lr in LOW_RESOLUTION_KEYWORDS:
            if re.search(lr, text):
                item["status"] = "REJECTED"
                item["reason"] = "Низкое разрешение экрана (HD 1366x768 вместо FHD)"
                return item

    # 4. Проверка черного списка
    for bp in BLACKLIST_MODELS:
        if re.search(bp, text):
            item["status"] = "REJECTED"
            item["reason"] = "В черном списке (несовместимая или старая толстая матрица)"
            return item

    # 5. Проверка дефектов экрана
    for dp in SCREEN_DEFECT_KEYWORDS:
        if re.search(dp, text):
            match_word = re.search(dp, text).group(0)
            item["status"] = "REJECTED"
            item["reason"] = f"Дефект экрана ({match_word})"
            return item

    # 6. Отсеивание отдельных мелких запчастей без матрицы (клавиатура, кулер, плата и т.п.)
    # Если в заголовке упоминается экран — это явно не "только запчасть"
    has_screen_core = bool(re.search(r"\b(?:display|bildschirm|matrix|panel|lcd|screen)\b", title_lower))

    # 6а. СТРОГИЕ — клавиатура, вентилятор, материнка и т.п. никогда не бывают «в комплекте»
    if not has_screen_core:
        for sp in SPARE_PARTS_STRICT:
            if re.search(sp, title_lower):
                item["status"] = "REJECTED"
                item["reason"] = "Запчасть/аксессуар без матрицы (динамики, клавиатура, плата и т.п.)"
                return item

    # 6б. КОНТЕКСТНЫЕ — Akku/Netzteil/Dock могут означать «входит в комплект».
    #     Отклоняем только если слово-запчасть стоит ДО названия ноутбука в заголовке.
    _laptop_brand_re = re.compile(
        r"\b(?:lifebook|elitebook|zbook|thinkpad|latitude|xps|prestige|precision|probook"
        r"|notebook|laptop)\b"
    )
    if not has_screen_core:
        for sp in SPARE_PARTS_CONTEXT:
            sp_match = re.search(sp, title_lower)
            if not sp_match:
                continue
            spare_pos = sp_match.start()
            laptop_before_spare = _laptop_brand_re.search(title_lower[:spare_pos])
            if not laptop_before_spare:
                item["status"] = "REJECTED"
                item["reason"] = "Запчасть/аксессуар без матрицы (аккумулятор, зарядка, dok)"
                return item

    # 7. Проверка белого списка моделей
    matched_model = False
    for wp in WHITELIST_MODELS:
        if re.search(wp, text):
            matched_model = True
            break

    if not matched_model:
        item["status"] = "REJECTED"
        item["reason"] = "Модель не входит в выверенный белый список доноров 100% sRGB"
        return item

    # Проверка на премиальную модель
    is_premium = any(re.search(rf"\b{re.escape(m)}\b", text) for m in PREMIUM_MODELS)
    item["is_premium"] = is_premium

    # 8. Проверка накопителя на 512 ГБ SSD (с исключением HDD и удаленных SSD)
    has_storage_exclude = any(re.search(p, text) for p in STORAGE_EXCLUDE_KEYWORDS)
    has_512 = any(re.search(sp, text) for sp in STORAGE_PATTERNS) and not has_storage_exclude
    item["has_512gb"] = has_512

    if has_512:
        item["status"] = "MATCH"
        item["reason"] = "Идеально: донор 100% sRGB / 72% NTSC (15.6\" FHD Slim 30-pin + SSD 512GB)"
    else:
        item["status"] = "POTENTIAL"
        if has_storage_exclude:
            item["reason"] = "Матрица 100% sRGB / 72% NTSC (15.6\" FHD Slim, без SSD или только HDD)"
        elif is_premium:
            item["reason"] = "Выверенный премиум-донор 100% sRGB / 72% NTSC (SSD требует уточнения)"
        else:
            item["reason"] = "Подходящая матрица 15.6\" FHD Slim (объем SSD требует уточнения)"

    return item

def parse_listings_from_html(html: str) -> list:
    """Извлекает объявления и описание из HTML страницы."""
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article", class_="aditem")
    if not articles:
        articles = soup.find_all("article")

    results = []

    for art in articles:
        # ID объявления
        ad_id = art.get("data-adid")

        # Заголовок
        heading = art.find(["h2", "h3", "h4"])
        title_tag = art.find("a", class_="ellipsis") or (heading.find("a") if heading else None)
        
        if heading:
            title = heading.get_text(strip=True)
        elif title_tag:
            title = title_tag.get_text(strip=True)
        else:
            continue

        if not title:
            continue

        # Ссылка
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
            a_any = art.find("a", href=True)
            if a_any:
                href = a_any["href"]

        if href and not href.startswith("http"):
            link = "https://www.kleinanzeigen.de" + href
        else:
            link = href or ""

        # Описание из сниппета или JSON-LD
        description = ""
        json_ld = art.find("script", type="application/ld+json")
        if json_ld and json_ld.string:
            import json
            try:
                data = json.loads(json_ld.string)
                description = data.get("description", "")
            except Exception:
                pass

        if not description:
            p_desc = art.find("p", class_=re.compile(r"description|text-bodyRegular"))
            if p_desc:
                description = p_desc.get_text(strip=True)

        # Цена
        price = None
        price_tag = art.find("p", class_="aditem-main--middle--price-shipping--price")
        if not price_tag:
            price_tag = art.find(class_=re.compile(r"price", re.I))

        if price_tag:
            price = price_tag.get_text(strip=True)
        else:
            for p in art.find_all(["p", "span"]):
                t = p.get_text(strip=True)
                # Ищем короткий текст, похожий на цену (до 30 символов)
                if len(t) <= 30 and ("€" in t or "VB" in t or "zu verschenken" in t.lower()):
                    price = t
                    break

        if not price:
            price = "Цена не указана"
        else:
            # Очистка от переносов строк и защита от длинного рекламного текста
            price = " ".join(price.split()).strip()
            if len(price) > 35:
                m = re.search(r"(\d+(?:[.,]\d+)?\s*€(?:\s*VB)?)", price, re.I)
                if m:
                    price = m.group(1).strip()
                else:
                    price = price[:32] + "..."

        # Местоположение
        location = "Не указано"
        loc_svg = art.find("svg", attrs={"data-title": "locationOutline"})
        if loc_svg and loc_svg.parent:
            loc_span = loc_svg.parent.find("span")
            if loc_span:
                location = loc_span.get_text(strip=True)
        if location == "Не указано":
            old_loc = art.find(class_="aditem-main--top--left")
            if old_loc:
                location = old_loc.get_text(strip=True)

        # Доставка
        shipping = "Только самовывоз"
        for tag in art.find_all(["span", "p"]):
            txt = tag.get_text(strip=True)
            if "versand möglich" in txt.lower() or "+ versand" in txt.lower() or "direkt kaufen" in txt.lower():
                shipping = "Доставка возможна"
                break
            elif "nur abholung" in txt.lower():
                shipping = "Только самовывоз"
                break
        if shipping == "Только самовывоз":
            old_ship = art.find(class_="aditem-main--middle--price-shipping--shipping")
            if old_ship and "versand" in old_ship.get_text(strip=True).lower():
                shipping = "Доставка возможна"

        item = {
            "id": ad_id or link,
            "title": title,
            "description": description,
            "price": price,
            "location": location,
            "shipping": shipping,
            "link": link
        }

        evaluated = evaluate_listing(item)
        results.append(evaluated)

    return results

def save_listings_to_csv(listings: list, csv_path: str = CSV_DATABASE_PATH) -> tuple[int, int]:
    """
    Сохраняет найденные объявления в CSV-файл (Excel-совместимый UTF-8 с BOM).
    Добавляет только новые объявления, предотвращая дубликаты.
    Возвращает (количество_добавленных, всего_в_таблице).
    """
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
    existing_ids = set()
    rows = []
    rows_by_id = {}

    if os.path.exists(csv_path):
        try:
            with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                for r in reader:
                    # Поддержка старых строк без новых полей
                    if "Местоположение" not in r:
                        r["Местоположение"] = "Не указано"
                    if "Доставка" not in r:
                        r["Доставка"] = "Уточнить"
                    rows.append(r)
                    rid = str(r.get("ID") or r.get("Ссылка", ""))
                    if rid:
                        existing_ids.add(rid)
                        rows_by_id[rid] = r
        except Exception as e:
            print(f"Предупреждение: ошибка чтения существующей таблицы: {e}")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    added_count = 0

    for item in listings:
        status = item.get("status")
        if status not in ["MATCH", "POTENTIAL"]:
            continue

        item_id = str(item.get("id") or item.get("link"))
        has_512 = "Да" if item.get("has_512gb") else "Уточнить"

        if item_id in rows_by_id:
            # Обновляем существующую запись новыми данными (локация, доставка, цена)
            existing_row = rows_by_id[item_id]
            if item.get("location") and item.get("location") != "Не указано":
                existing_row["Местоположение"] = item.get("location")
            if item.get("shipping"):
                existing_row["Доставка"] = item.get("shipping")
            if item.get("price"):
                existing_row["Цена"] = item.get("price")
            existing_row["Статус"] = status
            existing_row["SSD 512GB"] = has_512
            # Сохраняем пользовательские примечания и не перезаписываем их дефолтными фразами
            curr_comment = existing_row.get("Комментарий", "")
            is_auto_reason = (
                not curr_comment or
                "Идеально: совместимый донор" in curr_comment or
                "Подходящая модель" in curr_comment or
                "Подходящая матрица" in curr_comment
            )
            if is_auto_reason and item.get("reason"):
                existing_row["Комментарий"] = item.get("reason")
            continue

        existing_ids.add(item_id)

        new_row = {
            "Дата добавления": now_str,
            "Статус": status,
            "Модель / Заголовок": item.get("title", ""),
            "Цена": item.get("price", ""),
            "SSD 512GB": has_512,
            "Местоположение": item.get("location", "Не указано"),
            "Доставка": item.get("shipping", "Только самовывоз"),
            "Комментарий": item.get("reason", ""),
            "Ссылка": item.get("link", ""),
            "ID": item_id
        }
        rows.append(new_row)
        rows_by_id[item_id] = new_row
        added_count += 1

    # Сортировка: самые свежие объявления всегда вверху таблицы (по дате добавления),
    # а среди записей с одинаковым временем сначала идут полные совпадения (MATCH)
    rows.sort(
        key=lambda r: (
            r.get("Дата добавления", ""),
            1 if r.get("Статус") == "MATCH" else 0
        ),
        reverse=True
    )

    try:
        with open(csv_path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        print(f"Ошибка сохранения таблицы в {csv_path}: {e}")

    return added_count, len(rows)

async def scan_url(page, url: str) -> list:
    """Загружает страницу через Playwright и извлекает объявления с имитацией поведения человека."""
    print(f"\nЗагружаем: {url}")
    await page.goto(url, wait_until="domcontentloaded")

    # Принятие куки при первом посещении
    try:
        accept_btn = page.get_by_role("button", name="Akzeptieren")
        if await accept_btn.is_visible(timeout=2000):
            await accept_btn.click()
            print("Куки приняты и сохранены в постоянный профиль!")
    except Exception:
        pass

    # Имитация человеческого скролла со случайной амплитудой
    scroll_steps = random.randint(2, 3)
    for _ in range(scroll_steps):
        scroll_delta = random.randint(350, 600)
        await page.mouse.wheel(0, scroll_delta)
        await page.wait_for_timeout(random.randint(400, 800))

    html = await page.content()
    return parse_listings_from_html(html)


async def scan_query(page, query: str, max_pages: int = MAX_PAGES) -> list:
    """Сканирует несколько страниц результатов по одному поисковому запросу."""
    all_results = []
    for page_num in range(1, max_pages + 1):
        url = make_search_url(query, DEFAULT_MAX_PRICE, page=page_num)
        try:
            results = await scan_url(page, url)
        except Exception as e:
            print(f"  ⚠ Ошибка на странице {page_num}: {e}")
            break

        if not results:
            # Пустая страница — дальше листать нет смысла
            print(f"  ↩ Стр. {page_num}: объявлений не найдено, прекращаем пагинацию")
            break

        all_results.extend(results)
        print(f"  ✓ Стр. {page_num}: найдено {len(results)} объявлений (всего: {len(all_results)})")

        # Если страница содержала меньше 10 объявлений — скорее всего последняя
        if len(results) < 10:
            print(f"  ↩ Стр. {page_num}: мало объявлений ({len(results)} < 10), пагинация завершена")
            break

        if page_num < max_pages:
            jitter = random.uniform(2.0, 4.0)
            await page.wait_for_timeout(int(jitter * 1000))

    return all_results



def clean_db(csv_path: str = CSV_DATABASE_PATH) -> None:
    """Ретроспективно проверяет все записи в базе через evaluate_listing().
    Записи, которые не прошли бы текущие фильтры, помечаются статусом REJECTED.
    Пользовательские примечания и вся история сохраняются."""
    if not os.path.exists(csv_path):
        print("Файл базы не найден.")
        return

    fieldnames = [
        "Дата добавления", "Статус", "Модель / Заголовок", "Цена",
        "SSD 512GB", "Местоположение", "Доставка", "Комментарий", "Ссылка", "ID"
    ]

    rows = []
    with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            rows.append(r)

    changed = 0
    for row in rows:
        if row.get("Статус") == "REJECTED":
            continue
        dummy = {
            "id": row.get("ID", ""),
            "title": row.get("Модель / Заголовок", ""),
            "description": "",
            "price": row.get("Цена", ""),
            "location": row.get("Местоположение", ""),
            "shipping": row.get("Доставка", ""),
            "link": row.get("Ссылка", ""),
        }
        result = evaluate_listing(dummy)
        if result["status"] == "REJECTED":
            old_status = row["Статус"]
            row["Статус"] = "REJECTED"
            row["Комментарий"] = f"[clean-db] Отклонено текущими фильтрами: {result['reason']}"
            print(f"  ⚠ REJECTED: «{row['Модель / Заголовок']}» (было: {old_status}) — {result['reason']}")
            changed += 1

    with open(csv_path, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ clean-db завершён: помечено REJECTED — {changed} записей (всего в базе: {len(rows)})")


async def main():
    args = sys.argv[1:]

    # Режим аудита базы (без браузера)
    if args and args[0].lower() == "--clean-db":
        print("=" * 70)
        print(" АУДИТ БАЗЫ: проверка записей через текущие фильтры")
        print("=" * 70)
        clean_db()
        try:
            from generate_dashboard import generate_dashboard
            generate_dashboard()
            print("🌐 HTML-страница обновлена: index.html")
        except Exception as e:
            print(f"Предупреждение: {e}")
        return

    targets = TARGET_QUERIES
    if args:
        arg = " ".join(args).strip()
        if arg.lower() not in ["all", "--all"]:
            targets = [{"name": arg, "query": arg}]

    print("=" * 70)
    print(" СКАНЕР ДОНОРОВ ДЛЯ ThinkPad P15 Gen 2 (15.6\" FHD Slim + 512GB SSD)")
    print("=" * 70)
    print(f"Макс. цена: {DEFAULT_MAX_PRICE} €  |  Страниц на запрос: {MAX_PAGES}")
    print(f"Целевые запросы ({len(targets)}): {', '.join(q['name'] for q in targets)}")
    print(f"Профиль браузера: {BROWSER_PROFILE_DIR} (сессии/куки сохраняются)")
    print("-" * 70)

    all_matches = []
    all_potentials = []
    rejected_count = 0
    seen_ids = set()

    async with async_playwright() as p:
        # Запускаем постоянный контекст с маскировкой под обычного пользователя
        context = await p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_PROFILE_DIR,
            headless=False,
            slow_mo=350,
            no_viewport=True,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ],
            ignore_default_args=["--enable-automation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="de-DE"
        )

        # Скрываем флаг автоматизации navigator.webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = context.pages[0] if context.pages else await context.new_page()

        for target in targets:
            print(f"\n📋 Запрос: {target['name']}")
            try:
                listings = await scan_query(page, target["query"])
            except Exception as e:
                print(f"Ошибка при сканировании {target['name']}: {e}")
                continue

            for item in listings:
                if item["id"] in seen_ids:
                    continue
                seen_ids.add(item["id"])

                if item["status"] == "MATCH":
                    all_matches.append(item)
                elif item["status"] == "POTENTIAL":
                    all_potentials.append(item)
                else:
                    rejected_count += 1

            # Задержка между поисковыми запросами (уже включена внутри scan_query между страницами,
            # но здесь добавляем дополнительную паузу перед следующим ключевым словом)
            if target != targets[-1]:
                jitter = random.uniform(1.5, 3.0)
                await page.wait_for_timeout(int(jitter * 1000))

        print("\n" + "=" * 70)
        print(" РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ")
        print("=" * 70)

        # 1. Полные совпадения
        if all_matches:
            print(f"\n🎯 НАЙДЕНО ПОЛНЫХ СОВПАДЕНИЙ (MATCH): {len(all_matches)}")
            print("-" * 70)
            for idx, item in enumerate(all_matches, 1):
                print(f"{idx}. {item['title']} | {item['price']}")
                print(f"   Статус: {item['reason']}")
                print(f"   Ссылка: {item['link']}")
                print("-" * 70)
        else:
            print("\n🎯 Полных совпадений (модель + 512GB SSD) пока не найдено.")

        # 2. Потенциальные доноры (модель подходит, SSD требует уточнения)
        if all_potentials:
            print(f"\n⚠️ ПОТЕНЦИАЛЬНЫЕ ДОНОРЫ (Подходящая матрица, объем SSD требует уточнения): {len(all_potentials)}")
            print("-" * 70)
            for idx, item in enumerate(all_potentials[:15], 1):
                print(f"{idx}. {item['title']} | {item['price']}")
                print(f"   Ссылка: {item['link']}")
                print("-" * 70)
            if len(all_potentials) > 15:
                print(f"... и еще {len(all_potentials) - 15} объявлений.")

        print(f"\nОтфильтровано нерелевантных объявлений (дефекты экрана / T550 / другие модели): {rejected_count}")
        print("=" * 70)

        # Сохранение и обновление базы данных в CSV
        added_count, total_count = save_listings_to_csv(all_matches + all_potentials)
        print(f"\n📊 ТАБЛИЦА ОБНОВЛЕНА: добавлено {added_count} новых объявлений (всего в базе: {total_count})")
        print(f"Путь к файлу: {CSV_DATABASE_PATH}")

        # Автоматическое обновление интерактивной HTML-страницы
        try:
            from generate_dashboard import generate_dashboard
            generate_dashboard()
            print("🌐 HTML-страница обновлена: index.html")
        except Exception as e:
            print(f"Предупреждение: ошибка обновления HTML-витрины: {e}")
        print("=" * 70)

        if sys.stdin and sys.stdin.isatty():
            input("\nБраузер завершил поиск. Нажмите Enter, чтобы закрыть окно...")
        else:
            print("\nОставляем окно открытым на 5 секунд...")
            await page.wait_for_timeout(5000)

        await context.close()

if __name__ == "__main__":
    asyncio.run(main())