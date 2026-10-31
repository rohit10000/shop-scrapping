# Varanasi Shop Scraper & Web Agency Lead Generator

A powerful, production-grade web scraping and lead qualification engine tailored for Varanasi city. Built for web design agencies and freelancers selling websites to local shop owners.

---

## 🎯 What it Does

1. **Localities Targeted**: Scrapes shops across any Varanasi locality (`Lanka`, `Sigra`, `Durgakund`, `Godowlia`, `Chowk`, `Bhelupur`, `Mahmoorganj`, `Rathyatra`, `Pandeypur`, etc.).
2. **Shop Type & Category Identification**: Detects whether the business is a toy store, pharmacy/chemist, grocery/kirana, saree/clothing boutique, sweet shop, jewelry store, electronics store, etc.
3. **Website Presence Detection & Qualification**:
   - 🔴 **NO_WEBSITE**: No website listed at all (prime prospect!).
   - 🟠 **GOOGLE_SITE_SHUTDOWN**: Links to `*.business.site` (discontinued by Google in March 2024; urgent fix needed!).
   - 🟡 **SOCIAL_ONLY**: Only has Facebook or Instagram (already values online presence; easy upsell!).
   - 🟡 **DIRECTORY_ONLY**: Only on Justdial / IndiaMart / Sulekha (paying directory listing commissions!).
   - ❌ **BROKEN_WEBSITE**: Custom domain is 404, timed out, or SSL broken.
   - 🟢 **ACTIVE_WEBSITE**: Has a working domain.
4. **Lead Scoring & Sales Pitch Generator**:
   - Calculates **HIGH / MEDIUM / LOW** priority based on footfall, review count, rating, and verified phone number.
   - Generates tailored pitch angles and **1-click WhatsApp outreach links** with personalized Hindi/English messages!
5. **Deduplication & Storage**:
   - Saves into a persistent SQLite database (`varanasi_shops.db`).
   - Exports directly to clean **CSV** and styled **Excel (`.xlsx`)** spreadsheets with color-coded priorities and clickable hyperlinks.

---

## 🚀 Quick Start

### 1. Environment Setup

Activate the virtual environment (already configured):
```bash
source .venv/bin/activate
```

*(If setting up on a new machine):*
```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
playwright install chromium
```

---

## 💻 Usage Commands

### 1. Interactive Selection Wizard
Launch the guided interactive CLI:
```bash
python run.py -i
```
Prompts you to select or type localities, choose shop categories, scroll depth, and health check settings.

### 2. Given Just Localities (Your Core Use Case!)
You can provide one or multiple localities directly without picking categories:
```bash
# Broad sweep across one locality (defaults to all general shops & stores)
python run.py -l "Sigra"

# Broad sweep across multiple localities
python run.py -l "Lanka, Sigra, Durgakund"

# TRULY EXHAUSTIVE CENSUS: Scrapes every single shop category (toys, medicine, grocery, sarees, jewelry, etc.) across the localities
python run.py -l "Lanka, Sigra, Durgakund" --exhaustive
```

### 3. Targeted Category Scraping
```bash
# Toy shops and pharmacies in Lanka and Sigra
python run.py -l "Lanka, Sigra" -c "toy, medicine"

# Groceries, clothing and sweets in Durgakund & Mahmoorganj
python run.py -l "Durgakund, Mahmoorganj" -c "grocery, clothing, sweets_and_bakery"

# All categories in a locality
python run.py -l "Chowk, Godowlia" -c "all_shops"
```

### 3. Deeper Scraping
To scrape more listings (scroll further down the list):
```bash
python run.py -l "Lanka" -c "medicine" -s 12
```

### 4. View Stored Lead Statistics
Check how many leads you have gathered so far:
```bash
python run.py --stats
```

### 5. Re-export to CSV / Excel
Export your database leads anytime without re-scraping:
```bash
python run.py --export-only --csv leads.csv --xlsx leads.xlsx
```

---

## 🏪 Pre-Configured Shop Categories

You can pass any of these keys to the `-c` flag:

| Category Key | Google Search Queries Used |
| :--- | :--- |
| `toy` | Toy shops, kids toys and games |
| `medicine` | Medical stores, pharmacies, chemists |
| `grocery` | Kirana stores, grocery supermarkets, provision stores |
| `clothing` | Saree shops, clothing stores, garment showrooms, boutiques |
| `sweets_and_bakery` | Sweet shops (mithai), bakeries, cake shops |
| `electronics_and_mobile` | Mobile shops, electronics stores, computer/laptop shops |
| `jewelry` | Jewelry stores, jewellers, gold and silver showrooms |
| `footwear` | Shoe stores, footwear shops |
| `hardware_sanitary` | Hardware stores, sanitary ware, electrical stores |
| `books_and_stationery` | Stationery shops, book stores |
| `opticals` | Optical stores, eyewear shops |
| `restaurant_and_cafe` | Restaurants, cafes, fast food |
| `salon_and_beauty` | Beauty parlours, salons |
| `all_shops` | Broad general sweep of all stores |

---

## 📊 Exported Spreadsheets

The script generates `varanasi_shop_leads.xlsx` and `varanasi_shop_leads.csv`:

| Column | Description |
| :--- | :--- |
| **Shop Name** | Business name on Google Maps |
| **Locality** | Target locality in Varanasi (e.g. Lanka, Sigra) |
| **Category** | Exact business category |
| **Phone** | Verified direct mobile/phone number |
| **Rating & Reviews** | Google star rating & total review count |
| **Website Status** | `NO_WEBSITE`, `GOOGLE_SITE_SHUTDOWN`, `SOCIAL_ONLY`, etc. |
| **Lead Priority** | `HIGH` (Green), `MEDIUM` (Yellow), `LOW` |
| **Pitch Recommendation** | Custom reason why they need a website |
| **WhatsApp Outreach Link** | Clickable `wa.me` link with ready-made pitch message |
| **Address** | Street address |
| **Google Maps URL** | Clickable link to inspect photos, reviews, opening hours |

---

## 💼 Sales Playbook for Varanasi Shops

1. **High Review Count + No Website (`HIGH` Priority)**:
   - *Example*: A shop with 300+ reviews in Lanka has high customer trust and active turnover.
   - *Pitch*: "Aapki shop par daily hazaron log visit karte hain aur Google par 300+ reviews hain. Agar aapka ek simple digital catalog ya direct WhatsApp ordering website ho, toh customers direct aapse order kar sakte hain."
2. **Google Business Site Shutdown (`GOOGLE_SITE_SHUTDOWN`)**:
   - *Pitch*: "Google ne March 2024 me free business sites band kar di hain. Aapka pura website link toot chuka hai aur customers blank page dekh rahe hain. Hum 24 ghante me aapki custom website live kar denge."
3. **Only Justdial / IndiaMart (`DIRECTORY_ONLY`)**:
   - *Pitch*: "Justdial/IndiaMart par har inquiry ke paise cut hote hain aur competitors bhi sath me dikhte hain. Apni website par 100% control aapka hoga."

