"""Export Varanasi Shop leads to CSV and styled Excel spreadsheets."""

import csv
import urllib.parse
from typing import Any, Dict, List
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


class LeadExporter:
    @staticmethod
    def _create_whatsapp_link(phone: str, shop_name: str, status: str) -> str:
        """Create a 1-click WhatsApp web chat link with a personalized pre-filled pitch."""
        if not phone:
            return ""
        clean_num = "".join(filter(str.isdigit, phone))
        if len(clean_num) == 10:
            clean_num = "91" + clean_num
        elif clean_num.startswith("0") and len(clean_num) == 11:
            clean_num = "91" + clean_num[1:]

        if status == "NO_WEBSITE":
            msg = f"Namaste {shop_name} ji! Hum Varanasi me local businesses ke liye modern websites & online catalogs banate hain jisse Google search se direct orders aayein. Kya aapke paas website plan discuss karne ke liye 2 min hain?"
        elif status == "GOOGLE_SITE_SHUTDOWN":
            msg = f"Namaste {shop_name} ji! Google ne jo purani free business website band kar di thi, us wajah se aapke customers ko website nahi dikh rahi. Hum aapki brand nayi website 24 ghante me live kar sakte hain."
        elif status == "SOCIAL_ONLY":
            msg = f"Namaste {shop_name} ji! Humne aapka business page dekha. Social media ke sath agar aapki apni official website ho, toh direct WhatsApp orders 3x badh jate hain. Kya hum baat kar sakte hain?"
        elif status == "BROKEN_WEBSITE":
            msg = f"Namaste {shop_name} ji! Humne notice kiya ki aapki shop ki website open nahi ho rahi hai. Hum ise fix ya modernize kar sakte hain."
        else:
            msg = f"Namaste {shop_name} ji! Varanasi me aapke business ki website redesign aur SEO ke regarding reach out kar rahe hain."

        encoded_msg = urllib.parse.quote(msg)
        return f"https://wa.me/{clean_num}?text={encoded_msg}"

    @classmethod
    def export_to_csv(cls, shops: List[Dict[str, Any]], filepath: str = "varanasi_shop_leads.csv") -> None:
        if not shops:
            print("No shops to export.")
            return

        fieldnames = [
            "name",
            "locality",
            "category",
            "phone",
            "rating",
            "reviews_count",
            "website_status",
            "website_url",
            "lead_priority",
            "pitch_hook",
            "address",
            "maps_url",
            "whatsapp_link",
        ]

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for s in shops:
                row = dict(s)
                row["whatsapp_link"] = cls._create_whatsapp_link(
                    s.get("phone", ""), s.get("name", ""), s.get("website_status", "")
                )
                writer.writerow(row)

    @classmethod
    def export_to_excel(cls, shops: List[Dict[str, Any]], filepath: str = "varanasi_shop_leads.xlsx") -> None:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Varanasi Shop Leads"

        headers = [
            ("Shop Name", 28),
            ("Locality", 16),
            ("Category", 18),
            ("Phone", 16),
            ("Rating", 10),
            ("Reviews", 10),
            ("Website Status", 20),
            ("Website URL", 28),
            ("Lead Priority", 14),
            ("Pitch Recommendation", 45),
            ("WhatsApp Outreach Link", 25),
            ("Full Address", 40),
            ("Google Maps URL", 25),
        ]

        # Style definitions
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)

        thin_border = Border(
            left=Side(style="thin", color="E0E0E0"),
            right=Side(style="thin", color="E0E0E0"),
            top=Side(style="thin", color="E0E0E0"),
            bottom=Side(style="thin", color="E0E0E0"),
        )

        # Fills for priority
        fill_high = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")  # soft green
        fill_med = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")   # soft yellow
        fill_low = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")   # soft gray

        # Status fills
        fill_no_web = PatternFill(start_color="FCE8E6", end_color="FCE8E6", fill_type="solid") # soft red/pink
        fill_google_shutdown = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")

        # Write header row
        for col_idx, (header_text, width) in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # Write rows
        for row_idx, s in enumerate(shops, start=2):
            wa_link = cls._create_whatsapp_link(s.get("phone", ""), s.get("name", ""), s.get("website_status", ""))
            status = s.get("website_status", "NO_WEBSITE")
            priority = s.get("lead_priority", "LOW")

            row_values = [
                s.get("name", ""),
                s.get("locality", ""),
                s.get("category", ""),
                s.get("phone", "") or "Not Listed",
                s.get("rating", "") or "N/A",
                s.get("reviews_count", 0),
                status,
                s.get("website_url", "") or "None",
                priority,
                s.get("pitch_hook", ""),
                wa_link,
                s.get("address", ""),
                s.get("maps_url", ""),
            ]

            for col_idx, val in enumerate(row_values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = thin_border
                cell.alignment = left_align

                # Color coding priority
                if col_idx == 9:  # Priority column
                    cell.alignment = center_align
                    if priority == "HIGH":
                        cell.fill = fill_high
                        cell.font = Font(bold=True, color="155724")
                    elif priority == "MEDIUM":
                        cell.fill = fill_med
                        cell.font = Font(bold=True, color="856404")
                    else:
                        cell.fill = fill_low

                # Color coding status
                elif col_idx == 7:  # Website Status column
                    cell.alignment = center_align
                    if status == "NO_WEBSITE":
                        cell.fill = fill_no_web
                        cell.font = Font(bold=True, color="721C24")
                    elif status == "GOOGLE_SITE_SHUTDOWN":
                        cell.fill = fill_google_shutdown
                        cell.font = Font(bold=True, color="721C24")

                # Make WhatsApp & Maps links clickable
                elif col_idx == 11 and wa_link:
                    cell.value = "Chat on WhatsApp"
                    cell.hyperlink = wa_link
                    cell.font = Font(color="0070C0", underline="single")
                    cell.alignment = center_align
                elif col_idx == 13 and val:
                    cell.value = "Open in Maps"
                    cell.hyperlink = val
                    cell.font = Font(color="0070C0", underline="single")
                    cell.alignment = center_align

            ws.row_dimensions[row_idx].height = 24

        wb.save(filepath)

