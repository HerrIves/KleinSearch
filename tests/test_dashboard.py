"""
Tests for generate_dashboard.py — Python-emulation of JS functions getMatrixBadge() and parseNumericPrice().
Run: pytest tests/ -v
"""
import re


# ─────────────────────────────────────────────────────────────────────────────
# Python-port of getMatrixBadge() from generate_dashboard.py
# Must match the JS implementation exactly.
# ─────────────────────────────────────────────────────────────────────────────

def get_matrix_badge(title: str) -> str:
    """Python-emulation of JS function getMatrixBadge() from the dashboard."""
    t = (title or "").lower()

    ips_models = [
        re.compile(r"thinkpad\s*t590\b"),
        re.compile(r"\bt590\b"),
        re.compile(r"thinkpad\s*p53s\b"),
        re.compile(r"\bp53s\b"),
        re.compile(r"latitude\s*5[45]\d\d\b"),        # 5400-5499, 5500-5599
        re.compile(r"latitude\s*55\d\d\b"),            # fallback 5500-series
        re.compile(r"elitebook\s*850\s*g5\b"),
        re.compile(r"zbook\s*15\s*g[3456]\b"),         # ZBook 15 G3-G6 without 'u'
        re.compile(r"zbook\s*15\b(?!\s*u\b)"),         # ZBook 15 without 'u'
    ]
    for pattern in ips_models:
        if pattern.search(t):
            return "IPS"

    premium_models = [
        re.compile(r"\b(?:u758|u759|u7510)\b"),
        re.compile(r"\b(?:h7510|h7511)\b"),
        re.compile(r"elitebook\s*850\s*g[678]\b"),
        re.compile(r"elitebook\s*850\b"),              # EliteBook 850 without generation
        re.compile(r"zbook\s*15u\b"),
        re.compile(r"zbook\s*firefly\s*15\b"),
        re.compile(r"firefly\s*15\b"),
        re.compile(r"latitude\s*(?:7500|7510|7520)\b"),
        re.compile(r"xps\s*(?:15\s*)?(?:9570|7590)\b"),
        re.compile(r"\b(?:9570|7590)\b"),
        re.compile(r"thinkpad\s*t15g\b"),
        re.compile(r"thinkpad\s*p15\b(?!\s*s)"),
        re.compile(r"msi\s*prestige\s*15\b"),
    ]
    for pattern in premium_models:
        if pattern.search(t):
            return "PREMIUM"

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Python-port of parseNumericPrice() from generate_dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

def parse_numeric_price(s: str) -> float:
    """Python-emulation of JS function parseNumericPrice() from the dashboard."""
    if not s:
        return 0.0
    if "zu verschenken" in s.lower():
        return 0.0
    # German format: 1.200 € or 1.200,50 €
    m = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)", s)
    if not m:
        return 9999.0
    raw = m.group(1).replace(".", "").replace(",", ".")
    return float(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for getMatrixBadge
# ─────────────────────────────────────────────────────────────────────────────

class TestGetMatrixBadge:

    # ── PREMIUM (100% sRGB) ───────────────────────────────────────────────────

    def test_fujitsu_u758(self):
        assert get_matrix_badge("Fujitsu Lifebook U758 i5 8GB 256GB") == "PREMIUM"

    def test_fujitsu_u759(self):
        assert get_matrix_badge("Fujitsu Lifebook U759 i5-8365U 16 GB 512GB") == "PREMIUM"

    def test_celsius_h7510(self):
        assert get_matrix_badge("Fujitsu Celsius H7510 Workstation") == "PREMIUM"

    def test_zbook_15u_premium(self):
        assert get_matrix_badge("HP ZBook 15u G6 DEFEKT i7") == "PREMIUM"

    def test_zbook_firefly_15(self):
        assert get_matrix_badge("HP ZBook Firefly 15 G8 i7 512GB") == "PREMIUM"

    def test_elitebook_850_g7(self):
        assert get_matrix_badge("HP EliteBook 850 G7 FHD 512GB") == "PREMIUM"

    def test_elitebook_850_g8(self):
        assert get_matrix_badge("HP EliteBook 850 G8 Laptop") == "PREMIUM"

    def test_elitebook_850_no_gen(self):
        """EliteBook 850 without generation specified — treated as premium."""
        assert get_matrix_badge("HP EliteBook 850 Laptop FHD") == "PREMIUM"

    def test_latitude_7510(self):
        assert get_matrix_badge("Dell Latitude 7510 FHD 512GB NVMe") == "PREMIUM"

    def test_xps_9570(self):
        assert get_matrix_badge("Dell XPS 15 9570 4K i7") == "PREMIUM"

    def test_thinkpad_p15(self):
        assert get_matrix_badge("Lenovo ThinkPad P15 Gen 2 i7") == "PREMIUM"

    def test_msi_prestige_15(self):
        assert get_matrix_badge("MSI Prestige 15 A10SC i7") == "PREMIUM"

    # ── IPS (~45-72% NTSC) ───────────────────────────────────────────────────

    def test_thinkpad_t590(self):
        assert get_matrix_badge("Notebook Lenovo ThinkPad T590 Intel core i7") == "IPS"

    def test_thinkpad_t590_typo(self):
        """Typo in title 'lenevo' with T590."""
        assert get_matrix_badge("Lenevo thinkpad T590 oder bessere") == "IPS"

    def test_thinkpad_p53s(self):
        assert get_matrix_badge("Lenovo ThinkPad P53s 15.6 FHD i5") == "IPS"

    def test_latitude_5500(self):
        assert get_matrix_badge("DELL Latitude 5500 Laptop") == "IPS"

    def test_latitude_5510(self):
        assert get_matrix_badge("Laptop Dell Latitude 5510") == "IPS"

    def test_latitude_5520(self):
        assert get_matrix_badge("DELL Latitude 5520 DEFEKT") == "IPS"

    def test_elitebook_850_g5(self):
        assert get_matrix_badge("HP EliteBook 850 G5 i5 Laptop") == "IPS"

    def test_zbook_15_g5_no_u(self):
        """ZBook 15 G5 without 'u' — IPS, not premium."""
        assert get_matrix_badge("HP ZBook 15 G5 Rückdeckel Matrix LCD") == "IPS"

    # ── NO BADGE ──────────────────────────────────────────────────────────────

    def test_no_badge_probook(self):
        assert get_matrix_badge("HP ProBook 450 G8 G9 Display komplett") == ""

    def test_no_badge_medion(self):
        assert get_matrix_badge("Medion Display MD 63630 E15302 Laptop Bildschirm") == ""

    def test_no_badge_p15s(self):
        """P15s — in scanner blocklist, no badge needed."""
        assert get_matrix_badge("Lenovo ThinkPad P15s Gen 2") == ""

    def test_no_badge_empty(self):
        assert get_matrix_badge("") == ""


# ─────────────────────────────────────────────────────────────────────────────
# Tests for parseNumericPrice
# ─────────────────────────────────────────────────────────────────────────────

class TestParseNumericPrice:

    def test_simple(self):
        assert parse_numeric_price("100 €") == 100.0

    def test_with_vb(self):
        assert parse_numeric_price("120 € VB") == 120.0

    def test_german_thousands(self):
        assert parse_numeric_price("1.200 €") == 1200.0

    def test_german_thousands_vb(self):
        assert parse_numeric_price("1.500 € VB") == 1500.0

    def test_zu_verschenken(self):
        assert parse_numeric_price("Zu verschenken") == 0.0

    def test_one_euro(self):
        assert parse_numeric_price("1 € VB") == 1.0

    def test_empty(self):
        assert parse_numeric_price("") == 0.0

    def test_no_price_string(self):
        assert parse_numeric_price("Price not specified") == 9999.0


def test_render_dashboard_sanitizes_telegram_token():
    from generate_dashboard import render_dashboard
    settings = {
        "profiles": [],
        "telegram": {
            "enabled": True,
            "bot_token": "SUPER_SECRET_TOKEN_12345",
            "chat_id": "1175147457",
        },
    }
    html = render_dashboard([], settings)
    assert "SUPER_SECRET_TOKEN_12345" not in html
    assert '"bot_token": ""' in html


def test_render_dashboard_includes_profile_tabs_and_notify_controls():
    from generate_dashboard import render_dashboard
    html = render_dashboard([], {"profiles": [{"name": "ThinkPad", "enabled": True}]})
    assert 'id="profileTabs"' in html
    assert 'id="tgNotifyMatch"' in html
    assert 'id="tgNotifyPartial"' in html
    assert 'data-f="location"' in html
    assert 'data-f="radius"' in html


