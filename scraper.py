"""Playwright-based Google Maps Scraper for Varanasi Local Shops."""

import asyncio
import re
import urllib.parse
from typing import AsyncGenerator, Dict, List, Optional
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from config import DEFAULT_SCROLL_COUNT, DEFAULT_TIMEOUT_MS, PAGE_LOCALE, USER_AGENT


class GoogleMapsScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self) -> None:
        if not self._playwright:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            self._context = await self._browser.new_context(
                user_agent=USER_AGENT,
                locale=PAGE_LOCALE,
                viewport={"width": 1280, "height": 900},
            )

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._playwright = None
        self._browser = None
        self._context = None

    def _extract_rating_and_reviews(self, lines: List[str]) -> tuple[Optional[float], int]:
        """Extract rating (e.g. 4.6) and review count (e.g. 182) from card lines."""
        for line in lines:
            # Matches formats like '4.5(222)', '4.8 (1,240)', or standalone '4.5' followed by '(222)'
            m = re.search(r'([1-5]\.[0-9])\s*\(?([\d,]+)?\)?', line)
            if m:
                rating = float(m.group(1))
                reviews = int(m.group(2).replace(',', '')) if m.group(2) else 0
                return rating, reviews
        return None, 0

    def _extract_category_and_address(self, lines: List[str]) -> tuple[str, str]:
        """Parse category (e.g. 'Toy store') and street address from card lines."""
        category = "Shop"
        address = ""

        for line in lines:
            if " · " in line:
                parts = [p.strip() for p in line.split(" · ")]
                # Category is typically the first part of the ' · ' separated line
                # e.g. "Toy store · D59/79R, 2nd floor, Rajan Shahi Nagar..."
                # or "Pharmacy · Lanka, Lanka Rd..."
                first_part = parts[0]
                # Filter out timing phrases like "Open", "Closed"
                if not any(k in first_part.lower() for k in ["open", "closed", "closes", "opens", "delivery", "dine-in"]):
                    category = first_part
                    if len(parts) > 1:
                        # Clean out icon characters and collect address
                        addr_candidates = [re.sub(r'[\ue000-\uf8ff]', '', p).strip() for p in parts[1:]]
                        address = ", ".join([a for a in addr_candidates if a and not a.startswith("+91") and not re.match(r'^\d', a)])
                    break

        return category, address

    def _extract_phone(self, lines: List[str]) -> Optional[str]:
        """Extract Indian mobile / landline phone number."""
        for line in lines:
            # Matches Indian phone numbers: +91 98391 13763, 098391 13763, 0542-234567, 9839113763
            m = re.search(r'(?:(?:\+?91|0)?[ -]?)?([6-9]\d{4}[ -]?\d{5}|\d{3,4}[ -]?\d{6,7})', line)
            if m:
                clean_phone = re.sub(r'[^\d+]', '', m.group(0))
                # Validate length
                digits = re.sub(r'\D', '', clean_phone)
                if len(digits) >= 10:
                    return clean_phone
        return None

    async def scrape_query(
        self,
        query: str,
        locality: str,
        category_hint: str = "",
        scroll_count: int = DEFAULT_SCROLL_COUNT,
    ) -> AsyncGenerator[Dict, None]:
        """Scrape all shops returned by Google Maps for a given query."""
        if not self._context:
            await self.start()

        page: Page = await self._context.new_page()
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/maps/search/{encoded_query}"

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
            
            # Check if directly redirected to single place detail
            current_url = page.url
            if "/place/" in current_url:
                single_shop = await self._parse_single_place(page, locality, category_hint, query)
                if single_shop:
                    yield single_shop
                return

            # Wait for feed container
            try:
                await page.wait_for_selector('div[role="feed"]', timeout=8000)
            except Exception:
                # No feed found, check if zero results
                return

            feed = await page.query_selector('div[role="feed"]')
            if not feed:
                return

            # Scroll through feed to load more listings
            last_cards_count = 0
            stagnant_count = 0

            for _ in range(scroll_count):
                await page.evaluate('(feed) => feed.scrollBy(0, 3500)', feed)
                await asyncio.sleep(1.8)

                # Check if end of list reached
                end_banner = await page.query_selector('span:has-text("You\'ve reached the end of the list")')
                if end_banner:
                    break

                cards = await page.query_selector_all('div.Nv2PK')
                if len(cards) == last_cards_count:
                    stagnant_count += 1
                    # Extra nudge scroll to bottom
                    await page.evaluate('(feed) => feed.scrollTop = feed.scrollHeight', feed)
                    await asyncio.sleep(1.5)
                    if stagnant_count >= 2:
                        break
                else:
                    stagnant_count = 0
                last_cards_count = len(cards)

            # Extract data from each card
            cards = await page.query_selector_all('div.Nv2PK')
            seen_titles = set()

            for card in cards:
                title_el = await card.query_selector('.qBF1Pd')
                if not title_el:
                    continue
                name = (await title_el.inner_text()).strip()
                if not name or name in seen_titles:
                    continue
                seen_titles.add(name)

                # Website
                web_el = await card.query_selector('a[aria-label*="website" i], a[aria-label*="Website"]')
                website_url = await web_el.get_attribute('href') if web_el else None

                # Maps Link
                link_el = await card.query_selector('a.hfpxzc')
                maps_url = await link_el.get_attribute('href') if link_el else ""

                # Card textual content
                raw_text = await card.inner_text()
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

                rating, reviews_count = self._extract_rating_and_reviews(lines)
                detected_cat, detected_addr = self._extract_category_and_address(lines)
                phone = self._extract_phone(lines)

                final_category = detected_cat if detected_cat != "Shop" else (category_hint or "Shop")
                full_address = f"{detected_addr}, {locality}, Varanasi".strip(", ")

                yield {
                    "name": name,
                    "locality": locality,
                    "category": final_category,
                    "search_query": query,
                    "address": full_address,
                    "phone": phone,
                    "rating": rating,
                    "reviews_count": reviews_count,
                    "website_url": website_url,
                    "maps_url": maps_url,
                }

        finally:
            await page.close()

    async def _parse_single_place(
        self,
        page: Page,
        locality: str,
        category_hint: str,
        query: str
    ) -> Optional[Dict]:
        """Handles cases where Google Maps directly lands on a single store page."""
        try:
            h1 = await page.query_selector('h1')
            name = (await h1.inner_text()).strip() if h1 else ""
            if not name:
                return None

            # Category
            cat_el = await page.query_selector('button[jsaction*="category"]')
            category = (await cat_el.inner_text()).strip() if cat_el else category_hint or "Shop"

            # Website
            web_el = await page.query_selector('a[data-item-id="authority"], a[aria-label*="website" i]')
            website = await web_el.get_attribute('href') if web_el else None

            # Phone
            phone_el = await page.query_selector('button[data-item-id*="phone:"]')
            phone = None
            if phone_el:
                phone_aria = await phone_el.get_attribute('aria-label') or ""
                m = re.search(r'([6-9]\d{4}[ -]?\d{5}|\d{3,4}[ -]?\d{6,7})', phone_aria)
                if m:
                    phone = m.group(0)

            # Address
            addr_el = await page.query_selector('button[data-item-id="address"]')
            address = (await addr_el.inner_text()).strip() if addr_el else f"{locality}, Varanasi"

            # Rating
            star_el = await page.query_selector('div.F7nice span[aria-hidden="true"]')
            rating = float(await star_el.inner_text()) if star_el else None

            rev_el = await page.query_selector('div.F7nice span span[aria-label*="reviews"]')
            reviews = 0
            if rev_el:
                rm = re.search(r'([\d,]+)', await rev_el.get_attribute('aria-label') or "")
                if rm:
                    reviews = int(rm.group(1).replace(',', ''))

            return {
                "name": name,
                "locality": locality,
                "category": category,
                "search_query": query,
                "address": address,
                "phone": phone,
                "rating": rating,
                "reviews_count": reviews,
                "website_url": website,
                "maps_url": page.url,
            }
        except Exception:
            return None

