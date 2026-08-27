"""
Colruyt product scraper using Playwright (sync API).

Strategy:
  1. Open the categories page and collect all top-level category URLs.
  2. For each category, keep clicking "Meer bekijken" until all products load.
  3. Extract product cards (name, price, unit, promo, image) via JS evaluation.
  4. Upsert every product into PostgreSQL.
"""

import re
import time
import random
import logging
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from sqlalchemy.orm import Session
from .. import crud

logger = logging.getLogger(__name__)

BASE_URL = "https://www.colruyt.be"
CATEGORIES_URL = f"{BASE_URL}/nl/producten/alle-categorieen"

# Realistic browser headers to avoid easy bot detection
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def run_scraper_sync(run_id: int, db: Session) -> None:
    products_scraped = 0
    products_new = 0
    products_updated = 0

    try:
        with sync_playwright() as p:
            logger.info(f"Run #{run_id}: starting browser…")
            browser = p.chromium.launch(
                headless=True,
                # Hides navigator.webdriver — required to pass Colruyt's AntiBot check
                args=["--disable-blink-features=AutomationControlled"],
            )

            context = _new_context(browser)
            page = context.new_page()

            logger.info("Fetching categories from colruyt.be…")
            if not _load_overview(page):
                context, page = _recover_session(browser, context)
                if not _load_overview(page):
                    raise RuntimeError("Overview page persistently blocked by AntiBot")

            categories = _extract_categories(page)
            logger.info(f"Found {len(categories)} top-level categories")

            # The first in-app navigation after consent is consent-gated (load-more
            # stays disabled). Sacrifice one throwaway click+back to warm the SPA.
            _warm_up_spa(page, categories)

            for i, cat in enumerate(categories, start=1):
                try:
                    logger.info(f"[{i}/{len(categories)}] Scraping category '{cat['name']}'…")
                    cat_products, context, page = _scrape_category(browser, context, page, cat)
                    for product_data in cat_products:
                        _, is_new = crud.upsert_product(db, product_data)
                        products_scraped += 1
                        if is_new:
                            products_new += 1
                        else:
                            products_updated += 1

                    crud.update_scraper_run(
                        db,
                        run_id,
                        products_scraped=products_scraped,
                        products_new=products_new,
                        products_updated=products_updated,
                    )

                    # Polite delay between categories to avoid tripping the AntiBot rate limit
                    time.sleep(random.uniform(3.0, 6.0))

                except Exception as e:
                    logger.error(f"Error scraping category '{cat['name']}': {e}")

            browser.close()

        crud.update_scraper_run(
            db,
            run_id,
            status="completed",
            finished_at=datetime.now(timezone.utc),
            products_scraped=products_scraped,
            products_new=products_new,
            products_updated=products_updated,
        )
        logger.info(
            f"Run #{run_id} finished: {products_scraped} products "
            f"({products_new} new, {products_updated} updated)"
        )

    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        crud.update_scraper_run(
            db,
            run_id,
            status="failed",
            finished_at=datetime.now(timezone.utc),
            error_message=str(e),
        )

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dismiss_cookies(page) -> None:
    """Give cookie consent by clicking reject-all.

    A real consent click (not JS removal) is required: the site gates product
    lazy-loading / "Meer bekijken" behind consent. Waits for the banner to
    disappear so it can't intercept later tile clicks.
    """
    for sel in (
        "#onetrust-reject-all-handler",
        'button:has-text("Alle cookies weigeren")',
        "#onetrust-accept-btn-handler",
        'button:has-text("Alle cookies aanvaarden")',
    ):
        try:
            btn = page.locator(sel)
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click(timeout=4000)
                try:
                    page.wait_for_selector("#onetrust-banner-sdk", state="hidden", timeout=6000)
                except PWTimeout:
                    pass
                page.wait_for_timeout(400)
                return
        except Exception:
            pass


def _new_context(browser):
    return browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 900},
        locale="nl-BE",
    )


def _recover_session(browser, old_context, cooldown: float = 20.0):
    """Drop the flagged session and start a fresh one after a cooldown."""
    logger.warning(f"Recreating browser session after AntiBot block (cooldown {cooldown:.0f}s)…")
    try:
        old_context.close()
    except Exception:
        pass
    time.sleep(cooldown)
    context = _new_context(browser)
    return context, context.new_page()


def _is_antibot(page) -> bool:
    try:
        return "antibot" in (page.title() or "").lower()
    except Exception:
        return False


def _load_overview(page, attempts: int = 3) -> bool:
    """Load the categories overview once, retrying with backoff if AntiBot intercepts."""
    for attempt in range(1, attempts + 1):
        try:
            page.goto(CATEGORIES_URL, wait_until="domcontentloaded", timeout=30000)
        except PWTimeout:
            continue
        page.wait_for_timeout(1500)
        _dismiss_cookies(page)
        if not _is_antibot(page):
            return True
        wait = min(6 * attempt, 20)
        logger.warning(f"AntiBot on overview, retrying in {wait}s (attempt {attempt}/{attempts})…")
        time.sleep(wait)
    return False


def _warm_up_spa(page, categories: list[dict]) -> None:
    """Consume the consent-gated first in-app navigation with a throwaway click+back."""
    if not categories:
        return
    try:
        page.locator(f'a[href="{categories[0]["href"]}"]').first.click(timeout=10000)
        page.wait_for_timeout(3000)
        page.go_back(wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1500)
    except Exception:
        pass


def _extract_categories(page) -> list[dict]:
    """Read top-level category links from the already-loaded overview page."""
    links = page.eval_on_selector_all(
        'a[href*="/nl/producten/alle-categorieen/"]',
        """els => els.map(el => ({
            href: el.getAttribute("href") || "",
            text: el.innerText.trim()
        }))""",
    )

    categories = []
    seen = set()
    for link in links:
        href = link.get("href", "")
        # Top-level path has exactly 4 segments: nl/producten/alle-categorieen/<slug>
        parts = [p for p in href.strip("/").split("/") if p]
        if len(parts) == 4 and href not in seen:
            seen.add(href)
            full_url = BASE_URL + href if not href.startswith("http") else href
            # Name is often duplicated ("Groenten en fruit Groenten en fruit") — take first half
            raw = link.get("text", "").strip()
            name = _deduplicate_text(raw.split("\n")[0])
            categories.append({"url": full_url, "href": href, "name": name})

    return categories


def _ensure_overview(browser, context, page):
    """Guarantee the page sits on a healthy (non-AntiBot) overview, recovering if needed.

    Returns (context, page) since recovery may replace both.
    """
    link_sel = 'a[href*="/nl/producten/alle-categorieen/"]'
    if not _is_antibot(page) and page.locator(link_sel).count() > 0:
        return context, page
    if _load_overview(page):
        return context, page
    context, page = _recover_session(browser, context)
    _load_overview(page)
    return context, page


def _scrape_category(browser, context, page, category: dict, attempts: int = 3):
    """Open a category by clicking its tile, load every product, return to the overview.

    Navigating via clicks + history (instead of direct goto of listing pages, which
    return HTTP 456) keeps us under the AntiBot radar. Returns (products, context, page).
    """
    for attempt in range(1, attempts + 1):
        context, page = _ensure_overview(browser, context, page)

        try:
            page.wait_for_selector(f'a[href="{category["href"]}"]', state="attached", timeout=15000)
        except PWTimeout:
            logger.warning(f"'{category['name']}': category link not found, skipped")
            return [], context, page

        link = page.locator(f'a[href="{category["href"]}"]').first
        try:
            link.click(timeout=10000)
        except PWTimeout:
            # A lingering cookie banner intercepted the click — re-consent and retry
            _dismiss_cookies(page)
            link.click(timeout=10000)
        page.wait_for_timeout(3500)

        if not _is_antibot(page):
            break

        cooldown = min(10 * attempt, 30)
        logger.warning(
            f"'{category['name']}': blocked by AntiBot, "
            f"recovering (attempt {attempt}/{attempts})…"
        )
        context, page = _recover_session(browser, context, cooldown=cooldown)
    else:
        logger.warning(f"'{category['name']}': still blocked after {attempts} attempts, skipped")
        return [], context, page

    _load_all_products(page, category["name"])
    products = _extract_products_from_page(page, category["name"], category["url"])
    logger.info(f"'{category['name']}': found {len(products)} products")

    # Return to the overview via history (bfcache) instead of a fresh, guarded navigation
    try:
        page.go_back(wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1000)
    except PWTimeout:
        pass

    return products, context, page


def _load_all_products(page, name: str) -> None:
    """Scroll and click "Meer bekijken" until the full product list is loaded."""
    clicks = 0
    idle_rounds = 0
    for _ in range(300):
        page.mouse.wheel(0, 20000)
        page.wait_for_timeout(700)

        # The load-more control is an <a class="load-more__btn">, not a <button>
        btn = page.locator('a.load-more__btn, button:has-text("Meer bekijken")')
        clicked = False
        if btn.count() > 0:
            try:
                if btn.first.is_visible():
                    btn.first.click(timeout=5000)
                    page.wait_for_timeout(1200)
                    clicks += 1
                    clicked = True
            except PWTimeout:
                pass

        if clicked:
            idle_rounds = 0
            if clicks % 10 == 0:
                logger.info(f"'{name}': loading more products… ({clicks}x)")
        else:
            idle_rounds += 1
            if idle_rounds >= 4:
                break


def _extract_products_from_page(page, category_name: str, category_url: str) -> list[dict]:
    """Extract structured product data via a single JS eval over the DOM."""
    raw_items = page.eval_on_selector_all(
        'a[href*="/nl/producten/"]',
        r"""els => els
            .filter(el => /\/nl\/producten\/\d+$/.test(el.getAttribute("href") || ""))
            .map(el => {
                const href = el.getAttribute("href");
                const match = href.match(/\/nl\/producten\/(\d+)$/);
                const img = el.querySelector("img");
                return {
                    id: match ? match[1] : null,
                    href: href,
                    text: (el.innerText || "").trim(),
                    imgAlt: img ? (img.getAttribute("alt") || "").trim() : null,
                    imgSrc: img ? (img.getAttribute("src") || img.getAttribute("data-src")) : null
                };
            })
            .filter(p => p.id)
        """,
    )

    products = []
    seen_ids: set[str] = set()

    for item in raw_items:
        colruyt_id = item.get("id")
        if not colruyt_id or colruyt_id in seen_ids:
            continue
        seen_ids.add(colruyt_id)

        name, price, unit, quantity, is_promo, promo_price = _parse_card_text(item.get("text", ""))
        # The image alt is the exact product name; card text often starts with the weight
        if item.get("imgAlt"):
            name = item["imgAlt"]
        if not name:
            continue

        products.append(
            {
                "colruyt_id": colruyt_id,
                "name": name,
                "brand": _extract_brand(name),
                "price": price,
                "unit": unit,
                "quantity": quantity,
                "category": category_name,
                "url": BASE_URL + item["href"],
                "image_url": item.get("imgSrc"),
                "is_in_promo": is_promo,
                "promo_price": promo_price,
            }
        )

    return products


def _parse_card_text(text: str):
    """
    Parse a product card's raw innerText into
    (name, price, unit, quantity, is_promo, promo_price).

    Card lines look like:
        ["komkommer", "0", "89", "/st", "0,89/st"]
        ["BONI bananen", "±1kg", "1", "49", "/kg", "1,49/kg"]
        ["trostomaten", "1", "70", "/kg", "1,70/kg", "Reactie promo concurrent", ...]
    """
    if not text:
        return None, None, None, None, False, None

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Match combined price lines like "1,49/kg" or "0,89/st"
    price_re = re.compile(
        r"(\d+)[,\s](\d{2})\s*/\s*(st|kg|l|ml|g|cl|stuk|100g|100ml)",
        re.IGNORECASE,
    )
    # Quantity/packaging lines ("±1kg", "500g", "12x25cl", "1L") and price fragments ("1", "49", "/kg")
    qty_re = re.compile(r"^[±~]?[\d.,/x×\s]*(g|kg|cl|ml|l|st|stuks?)?\.?$", re.IGNORECASE)
    # A real packaging line must contain both a digit and a unit (excludes bare "1", "49")
    real_qty_re = re.compile(r"^[±~]?\d[\d.,x×\s]*\s*(g|kg|cl|ml|l|st|stuks?)$", re.IGNORECASE)

    prices: list[float] = []
    unit: str | None = None
    quantity: str | None = None
    name_candidates: list[str] = []

    for line in lines:
        m = price_re.search(line)
        if m:
            p = float(f"{m.group(1)}.{m.group(2)}")
            prices.append(p)
            if unit is None:
                unit = m.group(3).lower()
        elif qty_re.match(line):
            if quantity is None and real_qty_re.match(line):
                quantity = line
            continue
        elif not any(kw in line.lower() for kw in ("actie", "promo", "xtra", "vanaf", "reactie", "concurrent")):
            name_candidates.append(line)

    name = name_candidates[0] if name_candidates else None
    if name:
        name = _deduplicate_text(name)

    price = prices[0] if prices else None
    promo_price = prices[1] if len(prices) > 1 else None
    is_promo = promo_price is not None

    return name, price, unit, quantity, is_promo, promo_price


def _extract_brand(name: str) -> str | None:
    """
    Colruyt prefixes the brand in capitals: "BONI bananen" -> "BONI",
    "CÔTE D'OR bar melk" -> "CÔTE D'OR". Returns None when no capitalised prefix.
    """
    tokens = name.split()
    brand_tokens: list[str] = []
    for tok in tokens:
        letters = [c for c in tok if c.isalpha()]
        # Keep leading tokens that are all-caps and at least 2 letters long
        if len(letters) >= 2 and all(c.isupper() for c in letters):
            brand_tokens.append(tok)
        else:
            break
    if not brand_tokens or len(brand_tokens) == len(tokens):
        return None
    return " ".join(brand_tokens)


def _deduplicate_text(text: str) -> str:
    """
    "komkommer komkommer" -> "komkommer"
    "BONI bananen BONI bananen" -> "BONI bananen"
    """
    words = text.split()
    n = len(words)
    for half in range(1, n // 2 + 1):
        if words[:half] == words[half : half * 2]:
            return " ".join(words[:half])
    return text
