"""SQLite Database manager for Varanasi Shop leads with deduplication and reporting."""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class LeadDatabase:
    def __init__(self, db_path: str = "varanasi_shops.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    locality TEXT NOT NULL,
                    category TEXT,
                    search_query TEXT,
                    address TEXT,
                    phone TEXT,
                    rating REAL,
                    reviews_count INTEGER DEFAULT 0,
                    website_url TEXT,
                    website_status TEXT NOT NULL,
                    domain TEXT,
                    lead_priority TEXT NOT NULL,
                    pitch_hook TEXT,
                    maps_url TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, locality, phone)
                )
                """
            )
            # Create helpful indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_locality ON shops(locality)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON shops(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_website_status ON shops(website_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON shops(lead_priority)")
            conn.commit()

    def upsert_shop(self, shop: Dict[str, Any]) -> bool:
        """Insert or update a shop. Returns True if inserted, False if updated/skipped."""
        query = """
            INSERT INTO shops (
                name, locality, category, search_query, address, phone,
                rating, reviews_count, website_url, website_status,
                domain, lead_priority, pitch_hook, maps_url, scraped_at
            ) VALUES (
                :name, :locality, :category, :search_query, :address, :phone,
                :rating, :reviews_count, :website_url, :website_status,
                :domain, :lead_priority, :pitch_hook, :maps_url, :scraped_at
            )
            ON CONFLICT(name, locality, phone) DO UPDATE SET
                category = coalesce(excluded.category, shops.category),
                rating = coalesce(excluded.rating, shops.rating),
                reviews_count = max(shops.reviews_count, excluded.reviews_count),
                website_url = coalesce(excluded.website_url, shops.website_url),
                website_status = excluded.website_status,
                domain = coalesce(excluded.domain, shops.domain),
                lead_priority = excluded.lead_priority,
                pitch_hook = excluded.pitch_hook,
                maps_url = coalesce(excluded.maps_url, shops.maps_url),
                scraped_at = excluded.scraped_at
        """
        shop_data = dict(shop)
        shop_data.setdefault("scraped_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        with self._get_connection() as conn:
            cursor = conn.execute(query, shop_data)
            conn.commit()
            return cursor.rowcount > 0

    def get_all_shops(
        self,
        locality: Optional[str] = None,
        category: Optional[str] = None,
        website_status: Optional[str] = None,
        min_priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch filtered shops from the database."""
        conditions = []
        params = []
        if locality:
            conditions.append("locality = ?")
            params.append(locality)
        if category:
            conditions.append("category LIKE ?")
            params.append(f"%{category}%")
        if website_status:
            conditions.append("website_status = ?")
            params.append(website_status)
        if min_priority:
            if min_priority == "HIGH":
                conditions.append("lead_priority = 'HIGH'")
            elif min_priority == "MEDIUM":
                conditions.append("lead_priority IN ('HIGH', 'MEDIUM')")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM shops
            {where_clause}
            ORDER BY
                CASE lead_priority
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'LOW' THEN 3
                    ELSE 4
                END,
                reviews_count DESC
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Compute high level stats for marketing / sales overview."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
            no_website = conn.execute("SELECT COUNT(*) FROM shops WHERE website_status = 'NO_WEBSITE'").fetchone()[0]
            social_only = conn.execute("SELECT COUNT(*) FROM shops WHERE website_status = 'SOCIAL_ONLY'").fetchone()[0]
            directory_only = conn.execute("SELECT COUNT(*) FROM shops WHERE website_status = 'DIRECTORY_ONLY'").fetchone()[0]
            google_site = conn.execute("SELECT COUNT(*) FROM shops WHERE website_status = 'GOOGLE_SITE_SHUTDOWN'").fetchone()[0]
            broken_website = conn.execute("SELECT COUNT(*) FROM shops WHERE website_status = 'BROKEN_WEBSITE'").fetchone()[0]
            active_website = conn.execute("SELECT COUNT(*) FROM shops WHERE website_status = 'ACTIVE_WEBSITE'").fetchone()[0]
            with_phone = conn.execute("SELECT COUNT(*) FROM shops WHERE phone IS NOT NULL AND phone != ''").fetchone()[0]
            high_priority = conn.execute("SELECT COUNT(*) FROM shops WHERE lead_priority = 'HIGH'").fetchone()[0]
            medium_priority = conn.execute("SELECT COUNT(*) FROM shops WHERE lead_priority = 'MEDIUM'").fetchone()[0]

            # Group by locality
            localities_cursor = conn.execute(
                """
                SELECT locality, COUNT(*) as count,
                       SUM(CASE WHEN website_status IN ('NO_WEBSITE', 'SOCIAL_ONLY', 'DIRECTORY_ONLY', 'GOOGLE_SITE_SHUTDOWN', 'BROKEN_WEBSITE') THEN 1 ELSE 0 END) as prospective_leads
                FROM shops
                GROUP BY locality
                ORDER BY prospective_leads DESC
                """
            )
            locality_stats = [dict(r) for r in localities_cursor.fetchall()]

            # Group by category
            categories_cursor = conn.execute(
                """
                SELECT category, COUNT(*) as count,
                       SUM(CASE WHEN website_status = 'NO_WEBSITE' THEN 1 ELSE 0 END) as no_web
                FROM shops
                GROUP BY category
                ORDER BY count DESC
                LIMIT 10
                """
            )
            category_stats = [dict(r) for r in categories_cursor.fetchall()]

        return {
            "total_shops": total,
            "no_website": no_website,
            "social_only": social_only,
            "directory_only": directory_only,
            "google_site_shutdown": google_site,
            "broken_website": broken_website,
            "active_website": active_website,
            "with_phone": with_phone,
            "high_priority_leads": high_priority,
            "medium_priority_leads": medium_priority,
            "locality_breakdown": locality_stats,
            "category_breakdown": category_stats,
        }

