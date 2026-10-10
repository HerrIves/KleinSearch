"""Entry point.

  python src/main.py              open the dashboard window (settings, Start scan, progress)
  python src/main.py --no-ui      scan all enabled profiles in the console
  python src/main.py --clean-db   re-check stored listings against current profiles
"""
import asyncio
import random
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import config
import notifier
import scraper
import storage
from evaluator import evaluate_listing
from generate_dashboard import generate_dashboard
from logger import logger
from models import STATUS_MATCH, STATUS_PARTIAL, STATUS_REJECTED

ProgressFn = Callable[[int, str], Awaitable[None]]

BROWSER_ARGS = ["--start-maximized", "--disable-blink-features=AutomationControlled", "--disable-infobars"]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


async def _no_progress(percent: int, text: str) -> None:
    return None


_STATUS_RANK = {STATUS_MATCH: 0, STATUS_PARTIAL: 1, STATUS_REJECTED: 2}


def _rank(result: Dict[str, Any]):
    return _STATUS_RANK.get(result["status"], 3), len(result.get("missing") or [])


async def run_scan(page, settings: Dict[str, Any], progress: ProgressFn = _no_progress) -> Dict[str, int]:
    """Scans every enabled profile, evaluates results and stores them. Returns counters."""
    # First, clean up the database to remove listings that no longer match the current settings
    updated, removed = storage.reevaluate(settings)
    if removed:
        logger.info(f"Cleaned up {removed} listings that no longer match current settings.")

    profiles = [p for p in settings.get("profiles", []) if p.get("enabled") and p.get("queries")]
    global_exclude = settings.get("global_exclude", [])
    jobs = [(p, q) for p in profiles for q in p["queries"]]
    summary = {"match": 0, "partial": 0, "rejected": 0, "added": 0, "total": 0}
    if not jobs:
        logger.info("No enabled profile with queries. Nothing to scan.")
        await progress(100, "Nothing to scan: enable a profile and add queries")
        return summary

    found: Dict[str, Dict[str, Any]] = {}
    for index, (profile, query) in enumerate(jobs):
        logger.info(f"\n[{profile['name']}] query: {query}")

        async def on_page(page_num: int, pages: int, _i=index, _q=query, _p=profile) -> None:
            done = (_i + (page_num - 1) / pages) / len(jobs)
            await progress(5 + int(done * 85), f"{_p['name']}: \"{_q}\" (page {page_num}/{pages})")

        raw = await scraper.scan_query(
            page,
            query,
            pages=profile["pages"],
            price_min=profile.get("price_min"),
            price_max=profile.get("price_max"),
            category=profile.get("category", ""),
            on_page=on_page,
        )
        for item in raw:
            result = evaluate_listing(item, profile, global_exclude)
            key = str(result.get("id") or result.get("link"))
            previous = found.get(key)
            # the same ad can appear for several queries/profiles: keep the best evaluation
            if previous is None or _rank(result) < _rank(previous):
                found[key] = result
        if index < len(jobs) - 1:
            await page.wait_for_timeout(int(random.uniform(1.5, 3.0) * 1000))

    results = list(found.values())
    summary["match"] = sum(r["status"] == STATUS_MATCH for r in results)
    summary["partial"] = sum(r["status"] == STATUS_PARTIAL for r in results)
    summary["rejected"] = sum(r["status"] == STATUS_REJECTED for r in results)

    await progress(95, "Saving results...")
    summary["added"], summary["total"], new_items = storage.upsert_listings_detailed(results)
    notified_count = notifier.notify_listings(new_items, settings)
    if notified_count:
        logger.info(f"Telegram alerts sent: {notified_count}")
    logger.info("\n" + "=" * 60)
    logger.info(
        f"MATCH: {summary['match']} | PARTIAL: {summary['partial']} | rejected: {summary['rejected']} | "
        f"new: {summary['added']} | total stored: {summary['total']}"
    )
    logger.info("=" * 60)
    for r in sorted(results, key=lambda r: len(r["missing"])):
        if r["status"] != STATUS_REJECTED:
            logger.info(f"  [{r['status']}] {r['title']} | {r['price']} | {r['link']}")
    return summary


class AppController:
    """Handlers exposed to the dashboard page. Kept free of Playwright so they are unit-testable."""

    def __init__(self, config_path: str = config.CONFIG_PATH, csv_path: str = config.CSV_DATABASE_PATH):
        self.config_path = config_path
        self.csv_path = csv_path
        self.scan_requested = asyncio.Event()
        self.scanning = False

    def get_settings(self) -> Dict[str, Any]:
        return config.load_settings(self.config_path)

    def save_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        saved = config.save_settings(settings, self.config_path)
        logger.info(f"Settings saved ({len(saved['profiles'])} profiles)")
        return saved

    def request_scan(self) -> bool:
        if self.scanning:
            return False
        self.scan_requested.set()
        return True

    def save_note(self, item_id: str, note: str) -> bool:
        return storage.save_note(str(item_id), note, self.csv_path)

    def test_telegram(self, bot_token: str, chat_id: str) -> Dict[str, Any]:
        ok, message = notifier.test_telegram_connection(bot_token, chat_id)
        return {"ok": ok, "message": message}


async def run_ui() -> None:
    from playwright.async_api import async_playwright

    controller = AppController()
    generate_dashboard(settings=controller.get_settings())

    async with async_playwright() as p:
        ui_browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        ui_context = await ui_browser.new_context(no_viewport=True)
        ui_page = await ui_context.new_page()
        closed = asyncio.Event()
        ui_page.on("close", lambda _: closed.set())
        ui_browser.on("disconnected", lambda _: closed.set())

        await ui_page.expose_binding("ka_save_settings", lambda _src, s: controller.save_settings(s))
        await ui_page.expose_binding("ka_start_scan", lambda _src: controller.request_scan())
        await ui_page.expose_binding("ka_save_note", lambda _src, i, n: controller.save_note(i, n))
        await ui_page.expose_binding("ka_test_telegram", lambda _src, t, c: controller.test_telegram(t, c))
        await ui_page.goto(Path(config.HTML_DASHBOARD_PATH).as_uri())
        logger.info("Dashboard opened. Use Settings / Start scan in the browser window. Close it to exit.")

        async def progress(percent: int, text: str) -> None:
            if closed.is_set():
                return
            try:
                await ui_page.evaluate("([p, t]) => window.updateProgress && window.updateProgress(p, t)", [percent, text])
            except Exception:
                pass

        while not closed.is_set():
            waiter = asyncio.create_task(controller.scan_requested.wait())
            closer = asyncio.create_task(closed.wait())
            await asyncio.wait({waiter, closer}, return_when=asyncio.FIRST_COMPLETED)
            waiter.cancel()
            closer.cancel()
            if closed.is_set():
                break

            controller.scanning = True
            try:
                settings = controller.get_settings()
                await progress(2, "Opening search browser...")
                await _scan_with_browser(p, settings, progress)
                generate_dashboard(settings=settings)
                await progress(100, "Done. Reloading...")
                if not closed.is_set():
                    await ui_page.wait_for_timeout(800)
                    await ui_page.reload()
            except Exception as e:
                logger.error(f"Scan failed: {e}")
                await progress(100, f"Scan failed: {e}")
            finally:
                controller.scanning = False
                controller.scan_requested.clear()

        try:
            await ui_browser.close()
        except Exception:
            pass
    logger.info("Dashboard closed.")


async def _scan_with_browser(p, settings: Dict[str, Any], progress: ProgressFn = _no_progress) -> Dict[str, int]:
    context = await p.chromium.launch_persistent_context(
        user_data_dir=config.BROWSER_PROFILE_DIR,
        headless=True,
        slow_mo=250,
        no_viewport=True,
        args=BROWSER_ARGS,
        ignore_default_args=["--enable-automation"],
        user_agent=USER_AGENT,
        locale="de-DE",
    )
    try:
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        page = context.pages[0] if context.pages else await context.new_page()
        return await run_scan(page, settings, progress)
    finally:
        await context.close()


async def run_console() -> None:
    from playwright.async_api import async_playwright

    settings = config.load_settings()
    async with async_playwright() as p:
        await _scan_with_browser(p, settings)
    generate_dashboard(settings=settings)
    logger.info(f"Dashboard updated: {config.HTML_DASHBOARD_PATH}")


def main(argv: Optional[List[str]] = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    storage.migrate_legacy_csv()
    if "--clean-db" in args:
        updated, removed = storage.reevaluate(config.load_settings())
        logger.info(f"clean-db: {updated} updated, {removed} removed")
        generate_dashboard(settings=config.load_settings())
    elif "--no-ui" in args:
        asyncio.run(run_console())
    else:
        asyncio.run(run_ui())


if __name__ == "__main__":
    main()
