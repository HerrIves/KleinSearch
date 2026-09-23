"""
Тесты для scanner.py — проверка evaluate_listing() и parse_price_value().
Запуск: pytest tests/ -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scanner import evaluate_listing, parse_price_value, make_search_url


# ─────────────────────────────────────────────────────────────────────────────
# parse_price_value()
# ─────────────────────────────────────────────────────────────────────────────

class TestParsePriceValue:
    def test_simple_euro(self):
        assert parse_price_value("100 €") == 100.0

    def test_with_vb(self):
        assert parse_price_value("120 € VB") == 120.0

    def test_german_thousands(self):
        # 1.200 € — немецкий формат: точка — разделитель тысяч
        result = parse_price_value("1.200 €")
        assert result == 1200.0

    def test_zu_verschenken(self):
        assert parse_price_value("Zu verschenken") == 0.0

    def test_none_for_no_price(self):
        assert parse_price_value("Цена не указана") is None

    def test_one_euro(self):
        assert parse_price_value("1 € VB") == 1.0

    def test_empty_string(self):
        assert parse_price_value("") is None

    def test_none_input(self):
        assert parse_price_value(None) is None


# ─────────────────────────────────────────────────────────────────────────────
# make_search_url()
# ─────────────────────────────────────────────────────────────────────────────

class TestMakeSearchUrl:
    def test_page_1_no_param(self):
        url = make_search_url("fujitsu u759", 125, page=1)
        assert "pageNum" not in url
        assert "fujitsu-u759" in url
        assert "preis::125" in url

    def test_page_2_has_param(self):
        url = make_search_url("fujitsu u759", 125, page=2)
        assert "pageNum=2" in url

    def test_page_3_has_param(self):
        url = make_search_url("latitude 5520", 125, page=3)
        assert "pageNum=3" in url

    def test_no_price(self):
        url = make_search_url("thinkpad t590", 0)
        assert "preis::" not in url


# ─────────────────────────────────────────────────────────────────────────────
# evaluate_listing() — вспомогательная фабрика
# ─────────────────────────────────────────────────────────────────────────────

def make_item(title: str, price: str = "100 €", description: str = "") -> dict:
    """Создаёт минимальный словарь объявления для evaluate_listing()."""
    return {
        "id": "test-id",
        "title": title,
        "description": description,
        "price": price,
        "location": "Berlin",
        "shipping": "Versand möglich",
        "link": "https://www.kleinanzeigen.de/s-anzeige/test/12345678-278-1",
    }


class TestEvaluateListing:

    # ── MATCH кейсы ──────────────────────────────────────────────────────────

    def test_match_fujitsu_u759_with_512(self):
        item = make_item("Fujitsu Lifebook U759 i5-8365U 16 GB 512GB SSD")
        result = evaluate_listing(item)
        assert result["status"] == "MATCH"
        assert result["has_512gb"] is True

    def test_match_elitebook_g7_fhd_512(self):
        item = make_item("HP EliteBook 850 G7 15.6 FHD 512 GB SSD Laptop")
        result = evaluate_listing(item)
        assert result["status"] == "MATCH"

    def test_match_latitude_7510_nvme(self):
        item = make_item("Dell Latitude 7510 FHD 512GB NVMe")
        result = evaluate_listing(item)
        assert result["status"] == "MATCH"

    # ── POTENTIAL кейсы ───────────────────────────────────────────────────────

    def test_potential_fujitsu_u759_no_ssd_info(self):
        item = make_item("Fujitsu Lifebook U759 i5 16GB Laptop")
        result = evaluate_listing(item)
        assert result["status"] == "POTENTIAL"
        assert result["has_512gb"] is False

    def test_potential_latitude_5520_fhd_256gb(self):
        item = make_item("DELL Latitude 5520 FHD 256GB SSD Laptop")
        result = evaluate_listing(item)
        assert result["status"] == "POTENTIAL"

    def test_potential_latitude_5500_no_ssd(self):
        item = make_item("DELL Latitude 5500 Laptop ohne SSD")
        result = evaluate_listing(item)
        # ohne SSD → STORAGE_EXCLUDE → POTENTIAL без SSD, не MATCH
        assert result["status"] == "POTENTIAL"
        assert result["has_512gb"] is False

    # ── REJECTED кейсы ───────────────────────────────────────────────────────

    def test_rejected_blacklist_t550(self):
        item = make_item("Lenovo ThinkPad T550 i5 8GB")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_blacklist_zbook15_no_u(self):
        """ZBook 15 без 'u' — несовместимая толстая матрица."""
        item = make_item("HP ZBook 15 G5 ohne SSD")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_screen_defect_displaybruch(self):
        item = make_item("Fujitsu Lifebook U759 Displaybruch defekt")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_spare_keyboard(self):
        item = make_item("ThinkPad T590 Tastatur Deutsch QWERTZ")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_uhd_incompatible_connector(self):
        """4K/UHD требует 40-pin шлейф — несовместим."""
        item = make_item("Dell Latitude 7500 4K UHD Display Laptop")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_not_in_whitelist(self):
        """ProBook 450 отсутствует в белом списке доноров."""
        item = make_item("HP ProBook 450 G8 FHD 512GB SSD")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_price_over_limit(self):
        item = make_item("Fujitsu Lifebook U759 512GB", price="200 €")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_low_resolution_hd(self):
        item = make_item("Fujitsu Lifebook U759 HD Display 1366x768")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_p15s_blacklisted(self):
        """ThinkPad P15s — в чёрном списке (слабая матрица 250 нит)."""
        item = make_item("Lenovo ThinkPad P15s Gen 2 FHD 512GB")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"

    def test_rejected_verkauft(self):
        """Объявление помечено как 'verkauft' (продано)."""
        item = make_item("Fujitsu U759 512GB SSD verkauft")
        result = evaluate_listing(item)
        assert result["status"] == "REJECTED"
