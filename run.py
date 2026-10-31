#!/usr/bin/env python3
"""Main Entry Point for Varanasi Shop Scraper & Web Agency Lead Generator."""

import argparse
import asyncio
import sys
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from analyzer import LeadAnalyzer
from config import CATEGORIES, DEFAULT_SCROLL_COUNT, VARANASI_LOCALITIES
from database import LeadDatabase
from exporter import LeadExporter
from scraper import GoogleMapsScraper

console = Console()


def print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Varanasi Shop Scraper & Website Lead Generator[/bold cyan]\n"
            "[dim]Scrape local shops across Varanasi localities, identify shop types, and find leads without websites.[/dim]",
            border_style="cyan",
        )
    )


def show_statistics(db: LeadDatabase) -> None:
    stats = db.get_statistics()
    console.print("\n[bold]Current Lead Database Overview:[/bold]")
    table = Table(title="Varanasi Shop Leads Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim", width=30)
    table.add_column("Value", justify="right", style="bold green")

    table.add_row("Total Unique Shops Scraped", str(stats["total_shops"]))
    table.add_row("Shops with Direct Phone", str(stats["with_phone"]))
    table.add_row("🔴 NO WEBSITE (Prime Leads)", f"{stats['no_website']} ({stats['no_website']/max(1, stats['total_shops'])*100:.1f}%)")
    table.add_row("🟠 Discontinued Google Sites", str(stats["google_site_shutdown"]))
    table.add_row("🟡 Social Media Profile Only", str(stats["social_only"]))
    table.add_row("🟡 Directory Listing Only (Justdial)", str(stats["directory_only"]))
    table.add_row("❌ Broken / Inactive Websites", str(stats["broken_website"]))
    table.add_row("🟢 Active Working Websites", str(stats["active_website"]))
    table.add_row("🔥 HIGH PRIORITY Leads", f"[bold red]{stats['high_priority_leads']}[/bold red]")
    table.add_row("⚡ MEDIUM PRIORITY Leads", f"[bold yellow]{stats['medium_priority_leads']}[/bold yellow]")

    console.print(table)

    if stats["locality_breakdown"]:
        loc_table = Table(title="Leads by Locality", show_header=True, header_style="bold blue")
        loc_table.add_column("Locality", style="cyan")
        loc_table.add_column("Total Shops", justify="right")
        loc_table.add_column("Target Prospects (No Web / Broken)", justify="right", style="bold red")

        for row in stats["locality_breakdown"][:10]:
            loc_table.add_row(row["locality"], str(row["count"]), str(row["prospective_leads"]))
        console.print(loc_table)


def interactive_wizard() -> tuple[List[str], List[str], int, bool]:
    console.print("\n[bold yellow]--- Interactive Lead Search Setup ---[/bold yellow]")
    
    # Locality selection
    console.print("\nPopular Localities in Varanasi:")
    for idx, loc in enumerate(VARANASI_LOCALITIES[:12], 1):
        console.print(f" [cyan]{idx}[/cyan]. {loc}", end="  ")
        if idx % 4 == 0:
            console.print()
    console.print("\n")

    locality_input = Prompt.ask(
        "[bold green]Enter localities[/bold green] (comma-separated, e.g. 'Lanka, Sigra, Durgakund' or type 'popular' for top 5)",
        default="Lanka, Sigra, Durgakund",
    )

    if locality_input.strip().lower() == "popular":
        selected_localities = ["Lanka", "Sigra", "Durgakund", "Godowlia", "Bhelupur"]
    else:
        selected_localities = [l.strip() for l in locality_input.split(",") if l.strip()]

    # Category selection
    console.print("\nAvailable Categories:")
    cat_keys = list(CATEGORIES.keys())
    for idx, cat in enumerate(cat_keys, 1):
        console.print(f" [cyan]{idx}[/cyan]. {cat}", end="  ")
        if idx % 3 == 0:
            console.print()
    console.print("\n")

    category_input = Prompt.ask(
        "[bold green]Enter categories[/bold green] (comma-separated, e.g. 'toy, medicine, grocery' or 'all')",
        default="toy, medicine, grocery",
    )

    if category_input.strip().lower() in ["all", "all_shops"]:
        selected_categories = ["all_shops"]
    else:
        selected_categories = [c.strip().lower() for c in category_input.split(",") if c.strip()]

    scrolls_input = Prompt.ask(
        "[bold green]Scroll depth per search[/bold green] (Higher = more shops, 4-15 recommended)",
        default="6",
    )
    scrolls = int(scrolls_input) if scrolls_input.isdigit() else DEFAULT_SCROLL_COUNT

    check_http = Confirm.ask(
        "[bold green]Perform live HTTP health check on existing websites?[/bold green]",
        default=True,
    )

    return selected_localities, selected_categories, scrolls, check_http


async def run_pipeline(
    localities: List[str],
    categories: List[str],
    scroll_count: int = DEFAULT_SCROLL_COUNT,
    check_http: bool = True,
    headless: bool = True,
    csv_file: str = "varanasi_shop_leads.csv",
    xlsx_file: str = "varanasi_shop_leads.xlsx",
) -> None:
    db = LeadDatabase()
    analyzer = LeadAnalyzer(check_live_http=check_http)
    scraper = GoogleMapsScraper(headless=headless)

    console.print(f"\n[bold green]Starting Scraper for {len(localities)} localities and {len(categories)} categories...[/bold green]")
    await scraper.start()

    total_scraped = 0
    new_inserted = 0

    try:
        for locality in localities:
            for cat_name in categories:
                # Find search terms for category
                search_terms = CATEGORIES.get(cat_name, [cat_name])

                for term in search_terms:
                    query = f"{term} in {locality} Varanasi"
                    console.print(f"\n🔍 [bold blue]Searching:[/bold blue] [white]'{query}'[/white]")

                    count_query = 0
                    async for raw_shop in scraper.scrape_query(
                        query=query,
                        locality=locality,
                        category_hint=term,
                        scroll_count=scroll_count,
                    ):
                        # Analyze website & lead priority
                        analysis = analyzer.analyze(
                            name=raw_shop["name"],
                            website_url=raw_shop["website_url"],
                            phone=raw_shop["phone"],
                            reviews_count=raw_shop["reviews_count"],
                            rating=raw_shop["rating"],
                            category=raw_shop["category"],
                        )

                        # Merge
                        full_record = {**raw_shop, **analysis}
                        inserted = db.upsert_shop(full_record)
                        total_scraped += 1
                        if inserted:
                            new_inserted += 1
                        count_query += 1

                        # Terminal display badge
                        status_color = {
                            "NO_WEBSITE": "red",
                            "GOOGLE_SITE_SHUTDOWN": "bold red",
                            "SOCIAL_ONLY": "yellow",
                            "DIRECTORY_ONLY": "yellow",
                            "BROKEN_WEBSITE": "bold magenta",
                            "ACTIVE_WEBSITE": "dim green",
                        }.get(full_record["website_status"], "white")

                        phone_display = full_record["phone"] or "No Phone"
                        priority_display = full_record["lead_priority"]
                        priority_color = "green" if priority_display == "HIGH" else ("yellow" if priority_display == "MEDIUM" else "dim")

                        console.print(
                            f"  • [{priority_color}][{priority_display}][/{priority_color}] "
                            f"[bold]{full_record['name'][:30]}[/bold] | "
                            f"[cyan]{full_record['category']}[/cyan] | "
                            f"📞 {phone_display} | "
                            f"[{status_color}]{full_record['website_status']}[/{status_color}]"
                        )

                    console.print(f"  └── Found [bold]{count_query}[/bold] shops for '{query}'")
                    await asyncio.sleep(1)

    finally:
        await scraper.stop()

    console.print(f"\n[bold green]✓ Scraping Complete![/bold green] Total processed: {total_scraped} | New leads saved: {new_inserted}")

    # Export
    all_leads = db.get_all_shops()
    LeadExporter.export_to_csv(all_leads, csv_file)
    LeadExporter.export_to_excel(all_leads, xls_file := xlsx_file)
    console.print(f"📁 [bold]Exported Leads:[/bold]\n  - [green]{csv_file}[/green]\n  - [green]{xlsx_file}[/green] (with 1-click WhatsApp outreach links!)")

    # Show Final Stats
    show_statistics(db)


def main() -> None:
    parser = argparse.ArgumentParser(description="Varanasi Shop Scraper & Web Agency Lead Generator")
    parser.add_argument("-l", "--localities", help="Comma-separated localities (e.g. Lanka,Sigra,Durgakund)")
    parser.add_argument("-c", "--categories", help="Comma-separated categories (e.g. toy,medicine,grocery). Defaults to 'all_shops' if omitted.")
    parser.add_argument("--exhaustive", action="store_true", help="Scrape ALL pre-configured shop categories across the localities for a complete census")
    parser.add_argument("-s", "--scrolls", type=int, default=DEFAULT_SCROLL_COUNT, help="Scroll depth per search")
    parser.add_argument("--no-http", action="store_true", help="Skip live HTTP checking for existing websites")
    parser.add_argument("--headful", action="store_true", help="Run browser in visible mode (not headless)")
    parser.add_argument("--stats", action="store_true", help="Show current lead database statistics and exit")
    parser.add_argument("--export-only", action="store_true", help="Export existing database to CSV & Excel without scraping")
    parser.add_argument("--csv", default="varanasi_shop_leads.csv", help="CSV export filename")
    parser.add_argument("--xlsx", default="varanasi_shop_leads.xlsx", help="Excel export filename")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive selection wizard")

    args = parser.parse_args()
    print_banner()

    db = LeadDatabase()

    if args.stats:
        show_statistics(db)
        return

    if args.export_only:
        all_leads = db.get_all_shops()
        LeadExporter.export_to_csv(all_leads, args.csv)
        LeadExporter.export_to_excel(all_leads, args.xlsx)
        console.print(f"Exported {len(all_leads)} leads to {args.csv} and {args.xlsx}")
        return

    # If no parameters passed or --interactive flag given, run wizard
    if args.interactive or (not args.localities and not args.categories and not args.exhaustive):
        localities, categories, scrolls, check_http = interactive_wizard()
    else:
        if not args.localities:
            console.print("[bold red]Error:[/bold red] Please provide at least one locality using -l (e.g. -l 'Lanka, Sigra')")
            return
        localities = [l.strip() for l in args.localities.split(",") if l.strip()]

        if args.exhaustive:
            categories = list(CATEGORIES.keys())
        elif args.categories:
            categories = [c.strip().lower() for c in args.categories.split(",") if c.strip()]
        else:
            categories = ["all_shops"]

        scrolls = args.scrolls
        check_http = not args.no_http

    asyncio.run(
        run_pipeline(
            localities=localities,
            categories=categories,
            scroll_count=scrolls,
            check_http=check_http,
            headless=not args.headful,
            csv_file=args.csv,
            xlsx_file=args.xlsx,
        )
    )


if __name__ == "__main__":
    main()

