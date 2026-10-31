"""Lead Analyzer & Sales Intelligence for local Varanasi shops."""

import re
import urllib.parse
from typing import Any, Dict, Optional, Tuple
import requests
import tldextract
from config import SOCIAL_AND_DIRECTORY_DOMAINS


class LeadAnalyzer:
    def __init__(self, check_live_http: bool = True, http_timeout: float = 3.0):
        self.check_live_http = check_live_http
        self.http_timeout = http_timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def extract_domain(self, url: Optional[str]) -> str:
        if not url:
            return ""
        extracted = tldextract.extract(url)
        if extracted.registered_domain:
            return extracted.registered_domain.lower()
        return urllib.parse.urlparse(url).netloc.lower()

    def check_url_health(self, url: str) -> Tuple[bool, Optional[str]]:
        """Quickly check if custom domain website is live or broken."""
        if not self.check_live_http:
            return True, None
        try:
            resp = self._session.get(url, timeout=self.http_timeout, allow_redirects=True, verify=False)
            if resp.status_code >= 400:
                return False, f"HTTP {resp.status_code}"
            return True, None
        except requests.exceptions.SSLError:
            return False, "SSL Certificate Error"
        except requests.exceptions.ConnectionError:
            return False, "Connection Failed / Domain Expired"
        except requests.exceptions.Timeout:
            return False, "Timed Out (>3s)"
        except Exception as e:
            return False, str(e)[:30]

    def analyze(
        self,
        name: str,
        website_url: Optional[str],
        phone: Optional[str],
        reviews_count: int,
        rating: Optional[float],
        category: Optional[str],
    ) -> Dict[str, Any]:
        """Classify website presence and calculate lead priority & pitch angle."""
        phone_valid = bool(phone and len(re.sub(r"\D", "", phone)) >= 10)
        reviews = reviews_count or 0

        # Case 1: No website at all
        if not website_url or not website_url.strip():
            if phone_valid and reviews >= 15:
                priority = "HIGH"
                pitch = f"High-footfall shop ({reviews} reviews, {rating or 'N/A'}★) with NO website. Prime candidate for a full web catalog & WhatsApp commerce."
            elif phone_valid:
                priority = "MEDIUM"
                pitch = "No website found. Direct phone available. Target for budget starter business website."
            else:
                priority = "LOW"
                pitch = "No website and no direct phone. In-person visit required at local shop address."

            return {
                "website_url": None,
                "website_status": "NO_WEBSITE",
                "domain": "",
                "lead_priority": priority,
                "pitch_hook": pitch,
            }

        clean_url = website_url.strip()
        domain = self.extract_domain(clean_url)

        # Case 2: Google Business Site (Discontinued by Google in 2024!)
        if "business.site" in clean_url.lower() or "business.site" in domain:
            priority = "HIGH" if phone_valid else "MEDIUM"
            return {
                "website_url": clean_url,
                "website_status": "GOOGLE_SITE_SHUTDOWN",
                "domain": "business.site",
                "lead_priority": priority,
                "pitch_hook": "CRITICAL: Used Google's free business.site which Google shut down. Their website is DEAD/broken. Pitch immediate custom replacement!",
            }

        # Case 3: Social Media profile only
        if any(s in domain for s in ["facebook.com", "fb.com", "instagram.com", "youtube.com"]):
            priority = "HIGH" if (phone_valid and reviews >= 10) else "MEDIUM"
            return {
                "website_url": clean_url,
                "website_status": "SOCIAL_ONLY",
                "domain": domain,
                "lead_priority": priority,
                "pitch_hook": f"Active on {domain.capitalize()} but lacks an official website. Pitch custom domain to accept direct orders and improve Google SEO ranking.",
            }

        # Case 4: Directory Aggregator link (Justdial, IndiaMart, Sulekha)
        if any(d in domain for d in ["justdial.com", "indiamart.com", "tradeindia.com", "sulekha.com", "zomato.com", "swiggy.com"]):
            priority = "HIGH" if phone_valid else "MEDIUM"
            return {
                "website_url": clean_url,
                "website_status": "DIRECTORY_ONLY",
                "domain": domain,
                "lead_priority": priority,
                "pitch_hook": f"Listed on {domain} aggregator. Paying subscription/lead fees. Pitch direct independent website to own customer relationships directly.",
            }

        # Case 5: Custom Domain Website
        is_live, err_msg = self.check_url_health(clean_url)
        if not is_live:
            return {
                "website_url": clean_url,
                "website_status": "BROKEN_WEBSITE",
                "domain": domain,
                "lead_priority": "HIGH" if phone_valid else "MEDIUM",
                "pitch_hook": f"Existing website is BROKEN ({err_msg}). Pitch website maintenance, redesign, or hosting migration.",
            }

        # Case 6: Active Working Website
        return {
            "website_url": clean_url,
            "website_status": "ACTIVE_WEBSITE",
            "domain": domain,
            "lead_priority": "LOW",
            "pitch_hook": f"Already has active website ({domain}). Secondary target for website redesign, SEO, or e-commerce upgrade.",
        }

