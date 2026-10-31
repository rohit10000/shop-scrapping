"""FastAPI Web Server for Varanasi Shop Scraper & Web Lead Generation UI."""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from analyzer import LeadAnalyzer
from config import CATEGORIES, DEFAULT_SCROLL_COUNT, VARANASI_LOCALITIES
from database import LeadDatabase
from exporter import LeadExporter
from scraper import GoogleMapsScraper

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Varanasi Shop Scraper Dashboard",
    description="Local Business Web Agency Lead Generation Engine",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active Job State Management
class JobState:
    def __init__(self, job_id: str, localities: List[str], exhaustive: bool, scrolls: int, deep_verify: bool):
        self.job_id = job_id
        self.localities = localities
        self.exhaustive = exhaustive
        self.scrolls = scrolls
        self.deep_verify = deep_verify
        self.status = "queued"
        self.total_shops = 0
        self.new_leads = 0
        self.leads: List[Dict[str, Any]] = []
        self.queue: asyncio.Queue = asyncio.Queue()
        self.created_at = datetime.now()
        self.excel_file: Optional[Path] = None


jobs: Dict[str, JobState] = {}


class ScrapeRequest(BaseModel):
    localities: List[str]
    exhaustive: bool = False
    scrolls: int = DEFAULT_SCROLL_COUNT
    deep_verify: bool = True


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> HTMLResponse:
    index_path = BASE_DIR / "templates" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/localities")
async def get_localities() -> Dict[str, List[str]]:
    return {"localities": VARANASI_LOCALITIES}


@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    db = LeadDatabase()
    return db.get_statistics()


async def execute_scrape_task(job: JobState) -> None:
    db = LeadDatabase()
    analyzer = LeadAnalyzer(check_live_http=True)
    scraper = GoogleMapsScraper(headless=True)

    job.status = "running"
    await job.queue.put({
        "type": "log",
        "message": f"🚀 Starting scraper session for {len(job.localities)} localities: {', '.join(job.localities[:5])}..."
    })
    await job.queue.put({
        "type": "status",
        "message": f"Starting browser session for {len(job.localities)} localities..."
    })

    try:
        await scraper.start()
        await job.queue.put({"type": "log", "message": "🌐 Playwright Chromium headless browser launched successfully."})

        # Determine categories to sweep
        if job.exhaustive:
            category_keys = list(CATEGORIES.keys())
        else:
            category_keys = ["all_shops"]

        total_steps = len(job.localities) * len(category_keys)
        current_step = 0

        for loc_idx, locality in enumerate(job.localities):
            await job.queue.put({"type": "log", "message": f"📍 [{loc_idx+1}/{len(job.localities)}] Moving to locality: {locality}"})
            for cat_key in category_keys:
                current_step += 1
                progress_percent = int((current_step / max(1, total_steps)) * 100)

                search_terms = CATEGORIES.get(cat_key, [cat_key])
                for term in search_terms:
                    query = f"{term} in {locality} Varanasi"
                    await job.queue.put({
                        "type": "progress",
                        "percent": min(95, progress_percent),
                        "message": f"Scraping [{loc_idx+1}/{len(job.localities)}] {locality}: '{query}'"
                    })
                    await job.queue.put({"type": "log", "message": f"🔍 Searching Google Maps: '{query}'..."})

                    async for raw_shop in scraper.scrape_query(
                        query=query,
                        locality=locality,
                        category_hint=term,
                        scroll_count=job.scrolls,
                        deep_verify=job.deep_verify,
                    ):
                        analysis = analyzer.analyze(
                            name=raw_shop["name"],
                            website_url=raw_shop["website_url"],
                            phone=raw_shop["phone"],
                            reviews_count=raw_shop["reviews_count"],
                            rating=raw_shop["rating"],
                            category=raw_shop["category"],
                        )

                        full_record = {**raw_shop, **analysis}
                        inserted = db.upsert_shop(full_record)
                        job.total_shops += 1
                        if inserted:
                            job.new_leads += 1
                        job.leads.append(full_record)

                        # Generate pre-filled WhatsApp link for instant UI interaction
                        wa_link = LeadExporter._create_whatsapp_link(
                            full_record.get("phone", ""),
                            full_record.get("name", ""),
                            full_record.get("website_status", "")
                        )
                        full_record["whatsapp_link"] = wa_link

                        # Stream shop event to UI
                        await job.queue.put({
                            "type": "shop_found",
                            "shop": full_record
                        })
                        await job.queue.put({
                            "type": "log",
                            "message": f"  ✓ [{full_record['lead_priority']}] {full_record['name']} | {full_record['website_status']}"
                        })

                    await asyncio.sleep(0.5)

        # Generate custom Excel file for this job
        job_excel_filename = f"varanasi_shop_leads_{job.job_id}.xlsx"
        job_excel_path = DOWNLOADS_DIR / job_excel_filename
        LeadExporter.export_to_excel(job.leads, str(job_excel_path))
        job.excel_file = job_excel_path

        # Also update the master database exports
        all_leads = db.get_all_shops()
        LeadExporter.export_to_csv(all_leads, str(BASE_DIR / "varanasi_shop_leads.csv"))
        LeadExporter.export_to_excel(all_leads, str(BASE_DIR / "varanasi_shop_leads.xlsx"))

        job.status = "completed"
        await job.queue.put({"type": "log", "message": f"🎉 Finished! Total: {job.total_shops} shops. Excel spreadsheet generated."})
        await job.queue.put({
            "type": "complete",
            "total_shops": job.total_shops,
            "new_leads": job.new_leads,
            "download_url": f"/api/download/{job.job_id}"
        })

    except Exception as e:
        job.status = "failed"
        await job.queue.put({
            "type": "error",
            "message": str(e)
        })
    finally:
        await scraper.stop()


@app.post("/api/scrape")
async def start_scrape(req: ScrapeRequest) -> Dict[str, Any]:
    if not req.localities:
        raise HTTPException(status_code=400, detail="No localities provided")

    job_id = str(uuid.uuid4())[:8]
    job = JobState(
        job_id=job_id,
        localities=req.localities,
        exhaustive=req.exhaustive,
        scrolls=req.scrolls,
        deep_verify=req.deep_verify,
    )
    jobs[job_id] = job

    # Launch asynchronous background task
    asyncio.create_task(execute_scrape_task(job))

    return {
        "job_id": job_id,
        "status": "started",
        "localities_count": len(req.localities)
    }


@app.get("/api/jobs/{job_id}/stream")
async def stream_job_events(job_id: str) -> EventSourceResponse:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    async def event_generator():
        while True:
            data = await job.queue.get()
            yield {"data": json.dumps(data)}
            if data.get("type") in ["complete", "error"]:
                break

    return EventSourceResponse(event_generator())


@app.get("/api/download/{job_id}")
async def download_leads(job_id: str) -> FileResponse:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if not job.excel_file or not job.excel_file.exists():
        raise HTTPException(status_code=400, detail="Lead spreadsheet not ready yet")

    return FileResponse(
        path=str(job.excel_file),
        filename=f"varanasi_shop_leads_{job_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

