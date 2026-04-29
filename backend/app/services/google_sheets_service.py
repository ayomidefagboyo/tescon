"""Google Sheets service for exporting tracker + catalog data as a live sheet."""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)

# Column order matching the user's desired layout
SHEET_COLUMNS = [
    "None",  # row number placeholder
    "Symbol#",
    "Unit",
    "Location",
    "Whs",
    "Short#",
    "Year",
    "Desc1",
    "Desc2",
    "Item Note",
    "Criticality",
    "MfgName",
    "PartNo",
    "ModelNo",
    "UOM",
    "Status",
    "CatGroup",
    "NGNUnitCost",
    "NGNAmount",
    "USDUnitCost",
    "USDAmount",
    "CreatedDate",
    "LastIssuedDate",
    "Move Date",
    "Key",
    "Min",
    "Max",
    "Min / Max Review",
    "Recommended Min / Max",
    "Shelf Condition",
    "BOH",
    "COUNT",
    "STOCKING OPTIONS",
    "Qty to KEEP",
    "Qty to RFD",
    "QTY to DSE)",
    "KEEP Amount",
    "RFD Amount",
    "DSE Amount",
    "ADDITIONAL PRESERVATION REQUIRED (YES/NO)",
    "Parts Description",
    "Recommended Desc",
    "Remarks",
    "MonthEntry",
    "MonthCode",
    "CreatedBy",
    # --- Tracker / photo capture columns ---
    "Photo Status",
    "Image Count",
    "Photo Completed At",
    "Photo Queued At",
    "Photo Failed At",
    "Photo Error",
]

# Mapping from Excel "Photo Data" sheet columns → our output columns
_EXCEL_COL_MAP = {
    "Symbol Number": "Symbol#",
    "Location": "Location",
    "Whs": "Whs",
    "Desc1": "Desc1",
    "Desc2": "Desc2",
    "Long Text Desc": "Item Note",
    "Criticality": "Criticality",
    "Mfg Name": "MfgName",
    "Part No": "PartNo",
    "Model No": "ModelNo",
    "UOM": "UOM",
    "Grp Desc": "CatGroup",
    "Unit Cost(N)": "NGNUnitCost",
    "Unit Cost ($)": "USDUnitCost",
    "Created Date": "CreatedDate",
    "Last issue date": "LastIssuedDate",
    "Min": "Min",
    "Max": "Max",
    "BOH": "BOH",
    "Shelf Life": "Shelf Condition",
    "Comm Code": "Short#",
    "Grp": "Year",
}


def _get_credentials():
    """Load Google service account credentials."""
    try:
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        # Check for credentials path in env, then default locations
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            # Try well-known locations
            candidates = [
                Path(__file__).resolve().parents[2] / "tescon-484514-5ec0add0b2b7.json",
                Path.cwd() / "tescon-484514-5ec0add0b2b7.json",
            ]
            for c in candidates:
                if c.exists():
                    creds_path = str(c)
                    break

        if not creds_path or not Path(creds_path).exists():
            raise FileNotFoundError(
                "Google service account JSON not found. "
                "Set GOOGLE_APPLICATION_CREDENTIALS env var or place the JSON in the backend directory."
            )

        return Credentials.from_service_account_file(creds_path, scopes=scopes)
    except ImportError:
        raise ImportError("gspread and google-auth are required. Run: pip install gspread google-auth")


def _build_rows(
    excel_path: str,
    sheet_name: str,
    tracker_part_stats: Dict[str, Dict],
    date_filter: Optional[str] = None,
) -> List[List[Any]]:
    """
    Read the full Excel catalog and merge with tracker data.

    Returns a list of rows (each row is a list of cell values) with
    the header as the first row.
    """
    # Read ALL columns from the Excel catalog
    df = pd.read_excel(excel_path, sheet_name=sheet_name, engine="openpyxl")

    # Build output rows
    rows: List[List[Any]] = []
    rows.append(SHEET_COLUMNS)  # Header row

    for idx, (_, excel_row) in enumerate(df.iterrows(), start=1):
        symbol = str(excel_row.get("Symbol Number", "")).strip()
        if not symbol or symbol.lower() == "nan":
            continue

        # Get tracker info for this symbol
        tracker = tracker_part_stats.get(symbol, {})
        tracker_status = tracker.get("status", "")

        # Apply date filter if set
        if date_filter:
            ts = (
                tracker.get("completed_at")
                or tracker.get("queued_at")
                or tracker.get("failed_at")
                or ""
            )
            if ts and not ts.startswith(date_filter):
                continue

        def _val(excel_col: str, default=""):
            v = excel_row.get(excel_col)
            if pd.isna(v):
                return default
            return str(v)

        # Build the row matching SHEET_COLUMNS order
        row = [
            idx,  # None / row number
            symbol,  # Symbol#
            _val("Coy", "EGTL"),  # Unit
            _val("Location"),  # Location
            _val("Whs"),  # Whs
            _val("Comm Code"),  # Short#
            _val("Grp"),  # Year
            _val("Desc1"),  # Desc1
            _val("Desc2"),  # Desc2
            _val("Long Text Desc"),  # Item Note
            _val("Criticality"),  # Criticality
            _val("Mfg Name"),  # MfgName
            _val("Part No"),  # PartNo
            _val("Model No"),  # ModelNo
            _val("UOM"),  # UOM
            "",  # Status (computed below)
            _val("Grp Desc"),  # CatGroup
            _val("Unit Cost(N)"),  # NGNUnitCost
            "",  # NGNAmount (UnitCost * BOH)
            _val("Unit Cost ($)"),  # USDUnitCost
            "",  # USDAmount (UnitCost * BOH)
            _val("Created Date"),  # CreatedDate
            _val("Last issue date"),  # LastIssuedDate
            "",  # Move Date
            f"{_val('Whs')}{symbol}",  # Key (Whs + Symbol#)
            _val("Min"),  # Min
            _val("Max"),  # Max
            f"{_val('Min')}/ {_val('Max')}",  # Min / Max Review
            "",  # Recommended Min / Max
            _val("Shelf Life"),  # Shelf Condition
            _val("BOH"),  # BOH
            "",  # COUNT
            "",  # STOCKING OPTIONS
            "",  # Qty to KEEP
            "",  # Qty to RFD
            "",  # QTY to DSE
            "",  # KEEP Amount
            "",  # RFD Amount
            "",  # DSE Amount
            "",  # ADDITIONAL PRESERVATION REQUIRED
            f"{_val('Desc1')} {_val('Desc2')}".strip(),  # Parts Description
            "",  # Recommended Desc
            "",  # Remarks
            "",  # MonthEntry
            "",  # MonthCode
            "",  # CreatedBy
            # --- Tracker columns ---
            tracker_status.capitalize() if tracker_status else "Not Started",
            tracker.get("image_count", 0) or 0,
            tracker.get("completed_at", ""),
            tracker.get("queued_at", ""),
            tracker.get("failed_at", ""),
            tracker.get("error_reason", ""),
        ]

        rows.append(row)

    return rows


def export_to_google_sheets(
    excel_path: str,
    sheet_name: str,
    tracker_part_stats: Dict[str, Dict],
    date_filter: Optional[str] = None,
    spreadsheet_title: Optional[str] = None,
    share_with_email: Optional[str] = None,
) -> Dict[str, str]:
    """
    Export full catalog + tracker data to a Google Sheets spreadsheet.

    Args:
        excel_path: Path to the Excel catalog file.
        sheet_name: Sheet name in the Excel file (e.g. "Photo Data").
        tracker_part_stats: Dict of {symbol_number: stats} from PartsTracker.
        date_filter: Optional YYYY-MM-DD date filter.
        spreadsheet_title: Title for the Google Sheet.
        share_with_email: Email address to share the sheet with (editor access).

    Returns:
        Dict with 'url' and 'spreadsheet_id'.
    """
    import gspread

    creds = _get_credentials()
    gc = gspread.authorize(creds)

    # Build data rows
    rows = _build_rows(excel_path, sheet_name, tracker_part_stats, date_filter)

    if not spreadsheet_title:
        date_str = date_filter or datetime.now().date().isoformat()
        spreadsheet_title = f"TESCON Full Report - {date_str}"

    # Create spreadsheet
    logger.info(f"Creating Google Sheet: {spreadsheet_title}")
    sh = gc.create(spreadsheet_title)

    # Write data to the first worksheet
    worksheet = sh.sheet1
    worksheet.update_title("Full Data")

    # Resize to fit data
    num_rows = len(rows)
    num_cols = len(SHEET_COLUMNS)
    worksheet.resize(rows=max(num_rows, 1), cols=num_cols)

    # Write all data in one batch
    worksheet.update(
        range_name=f"A1",
        values=rows,
        value_input_option="USER_ENTERED",
    )

    # Format header row (bold, frozen)
    worksheet.format("1:1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.7},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
    })
    worksheet.freeze(rows=1)

    # Auto-resize columns (gspread doesn't have auto-fit, set reasonable widths)
    # Set column widths for key columns
    requests = []
    col_widths = {0: 50, 1: 100, 2: 60, 3: 100, 4: 100, 7: 200, 8: 200, 9: 250, 11: 120, 12: 120}
    for col_idx, width in col_widths.items():
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": worksheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": col_idx,
                    "endIndex": col_idx + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        })

    if requests:
        sh.batch_update({"requests": requests})

    # Share with the user's email if provided
    if share_with_email:
        sh.share(share_with_email, perm_type="user", role="writer")
        logger.info(f"Shared with {share_with_email}")

    # Also make it accessible to anyone with the link
    sh.share("", perm_type="anyone", role="reader")

    url = sh.url
    spreadsheet_id = sh.id

    logger.info(f"Google Sheet created: {url}")

    return {
        "url": url,
        "spreadsheet_id": spreadsheet_id,
        "title": spreadsheet_title,
        "total_rows": num_rows - 1,  # exclude header
    }
