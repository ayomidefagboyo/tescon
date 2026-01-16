"""Google Sheets service for part lookup."""
import os
import json
import base64
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import re


class GoogleSheetsService:
    """Manages part information from Google Sheets."""
    
    def __init__(
        self,
        sheet_id: Optional[str] = None,
        tab_name: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Google Sheets service.
        
        Args:
            sheet_id: Google Sheet ID (from URL)
            tab_name: Tab/worksheet name (defaults to first tab)
            credentials_path: Path to service account JSON file
        """
        self.sheet_id = sheet_id or os.getenv("GOOGLE_SHEETS_ID")
        self.tab_name = tab_name or os.getenv("GOOGLE_SHEETS_TAB_NAME")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        
        # Column name mappings (with flexible matching)
        self.part_number_col = os.getenv("GOOGLE_SHEETS_PART_NUMBER_COL", None)
        self.description_col = os.getenv("GOOGLE_SHEETS_DESCRIPTION_COL", None)
        self.location_col = os.getenv("GOOGLE_SHEETS_LOCATION_COL", None)
        self.item_note_col = os.getenv("GOOGLE_SHEETS_ITEM_NOTE_COL", None)
        
        # Cache settings
        self.cache_ttl_seconds = 120  # 2 minutes
        self.parts_cache: Dict[str, Dict] = {}
        self.cache_timestamp: Optional[datetime] = None
        self.column_mapping: Dict[str, str] = {}
        
        # Initialize connection
        self.client: Optional[gspread.Client] = None
        self.worksheet: Optional[gspread.Worksheet] = None
        
        if self.sheet_id and self.credentials_path:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Sheets client with credentials."""
        try:
            # Load credentials
            creds = self._load_credentials()
            if not creds:
                print("⚠ Warning: Google Sheets credentials not found. Part lookup will be unavailable.")
                return
            
            # Create client
            self.client = gspread.authorize(creds)
            
            # Open sheet
            sheet = self.client.open_by_key(self.sheet_id)
            
            # Get worksheet
            if self.tab_name:
                try:
                    self.worksheet = sheet.worksheet(self.tab_name)
                except gspread.WorksheetNotFound:
                    print(f"⚠ Warning: Tab '{self.tab_name}' not found. Using first tab.")
                    self.worksheet = sheet.sheet1
            else:
                self.worksheet = sheet.sheet1
            
            # Detect column mapping
            self._detect_columns()
            
            print(f"✓ Google Sheets API configured successfully (Sheet: {self.sheet_id})")
            
        except Exception as e:
            print(f"⚠ Warning: Failed to initialize Google Sheets: {e}")
            print("Part lookup will be unavailable. Check GOOGLE_CLOUD_SETUP.md for setup instructions.")
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from file or environment variable."""
        try:
            # Try loading from file path
            if self.credentials_path and os.path.exists(self.credentials_path):
                return Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets.readonly',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
            
            # Try loading from base64 encoded environment variable (for Render)
            creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
            if creds_json:
                try:
                    # Decode base64
                    creds_data = base64.b64decode(creds_json)
                    creds_dict = json.loads(creds_data)
                    return Credentials.from_service_account_info(
                        creds_dict,
                        scopes=[
                            'https://www.googleapis.com/auth/spreadsheets.readonly',
                            'https://www.googleapis.com/auth/drive'
                        ]
                    )
                except Exception as e:
                    print(f"Error decoding credentials from env: {e}")
            
            return None
            
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def _detect_columns(self):
        """Auto-detect column names from sheet header."""
        if not self.worksheet:
            return
        
        try:
            # Get first row (headers)
            headers = self.worksheet.row_values(1)
            
            # Normalize headers (lowercase, strip whitespace)
            normalized_headers = {h.lower().strip(): h for h in headers if h}
            
            # Find columns with flexible matching
            def find_column(keywords: List[str], override: Optional[str] = None) -> Optional[str]:
                if override:
                    # Use explicit override
                    for h in headers:
                        if h.lower().strip() == override.lower().strip():
                            return h
                    return None
                
                # Auto-detect by keywords
                for keyword in keywords:
                    for norm_key, orig_key in normalized_headers.items():
                        if keyword in norm_key:
                            return orig_key
                return None
            
            # Detect part number column
            part_col = find_column(
                ["part", "number", "partnumber", "part_num", "item", "sku"],
                self.part_number_col
            )
            
            # Detect description column
            desc_col = find_column(
                ["description", "desc", "name", "title", "item_name"],
                self.description_col
            )
            
            # Detect location column
            loc_col = find_column(
                ["location", "loc", "warehouse", "site", "place"],
                self.location_col
            )
            
            # Detect item note column
            note_col = find_column(
                ["note", "notes", "item_note", "comment", "remarks"],
                self.item_note_col
            )
            
            self.column_mapping = {
                "part_number": part_col,
                "description": desc_col,
                "location": loc_col,
                "item_note": note_col
            }
            
            # Validate we found at least part number
            if not part_col:
                print("⚠ Warning: Could not detect 'Part Number' column in Google Sheet")
                print(f"Available columns: {headers}")
            else:
                print(f"✓ Detected columns: Part={part_col}, Desc={desc_col}, Loc={loc_col}, Note={note_col}")
                
        except Exception as e:
            print(f"Error detecting columns: {e}")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.cache_timestamp:
            return False
        
        age = datetime.now() - self.cache_timestamp
        return age.total_seconds() < self.cache_ttl_seconds
    
    def _load_all_parts(self):
        """Load all parts from sheet into cache."""
        if not self.worksheet:
            return
        
        if self._is_cache_valid():
            return  # Cache is still valid
        
        try:
            # Get all values
            all_values = self.worksheet.get_all_values()
            
            if not all_values:
                return
            
            # Get header row
            headers = all_values[0]
            part_col_idx = headers.index(self.column_mapping["part_number"]) if self.column_mapping.get("part_number") in headers else None
            
            if part_col_idx is None:
                print("⚠ Warning: Part number column not found in sheet")
                return
            
            # Get indices for other columns
            desc_col_idx = headers.index(self.column_mapping["description"]) if self.column_mapping.get("description") in headers else None
            loc_col_idx = headers.index(self.column_mapping["location"]) if self.column_mapping.get("location") in headers else None
            note_col_idx = headers.index(self.column_mapping["item_note"]) if self.column_mapping.get("item_note") in headers else None
            
            # Clear cache
            self.parts_cache.clear()
            
            # Process each row (skip header)
            for row in all_values[1:]:
                if len(row) <= part_col_idx:
                    continue
                
                part_number = str(row[part_col_idx]).strip()
                if not part_number or part_number.lower() in ['', 'nan', 'none']:
                    continue
                
                description = str(row[desc_col_idx]).strip() if desc_col_idx and len(row) > desc_col_idx else ""
                location = str(row[loc_col_idx]).strip() if loc_col_idx and len(row) > loc_col_idx else ""
                item_note = str(row[note_col_idx]).strip() if note_col_idx and len(row) > note_col_idx else ""
                
                # Clean up values
                if description.lower() in ['nan', 'none', '']:
                    description = ""
                if location.lower() in ['nan', 'none', '']:
                    location = ""
                if item_note.lower() in ['nan', 'none', '']:
                    item_note = ""
                
                self.parts_cache[part_number] = {
                    "part_number": part_number,
                    "description": description,
                    "location": location,
                    "item_note": item_note
                }
            
            self.cache_timestamp = datetime.now()
            print(f"✓ Loaded {len(self.parts_cache)} parts from Google Sheet (cached for {self.cache_ttl_seconds}s)")
            
        except Exception as e:
            print(f"Error loading parts from sheet: {e}")
    
    def get_part_info(self, part_number: str) -> Optional[Dict]:
        """
        Get part information by part number.
        
        Args:
            part_number: Part number to lookup
            
        Returns:
            Dictionary with part information or None if not found
        """
        if not self.worksheet:
            return None
        
        part_number = str(part_number).strip()
        
        # Load parts if cache is invalid
        self._load_all_parts()
        
        # Check cache
        return self.parts_cache.get(part_number)
    
    def search_parts(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search parts by part number (for autocomplete).
        
        Args:
            query: Search query (partial part number)
            limit: Maximum results to return
            
        Returns:
            List of matching parts
        """
        if not self.worksheet:
            return []
        
        query = str(query).strip().lower()
        if not query:
            return []
        
        # Load parts if cache is invalid
        self._load_all_parts()
        
        # Search in cache
        matches = []
        for part_num, part_info in self.parts_cache.items():
            if query in part_num.lower():
                matches.append(part_info)
                if len(matches) >= limit:
                    break
        
        return matches
    
    def reload_cache(self):
        """Force reload parts from sheet (bypass cache)."""
        self.cache_timestamp = None
        self._load_all_parts()


# Global instance
_sheets_service: Optional[GoogleSheetsService] = None


def get_sheets_service() -> Optional[GoogleSheetsService]:
    """Get or create global Google Sheets service instance."""
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = GoogleSheetsService()
    return _sheets_service
