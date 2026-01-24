"""Excel file processing service for parts catalog."""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ExcelPartsService:
    """Service for processing Excel parts catalog files."""

    def __init__(self):
        self.parts_data: Optional[pd.DataFrame] = None
        self.unique_parts: Optional[pd.DataFrame] = None
        self.total_parts = 0

    def load_excel_file(self, file_path: str, sheet_name: str = "Data") -> bool:
        """
        Load Excel file and process parts data.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to read (default: "Data")

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read Excel file
            self.parts_data = pd.read_excel(file_path, sheet_name=sheet_name)
            logger.info(f"Loaded Excel file: {len(self.parts_data)} total rows")

            # Process and deduplicate parts
            self._process_parts_data()
            return True

        except Exception as e:
            logger.error(f"Failed to load Excel file: {e}")
            return False

    def _process_parts_data(self):
        """Process parts data to remove duplicates and clean data."""
        if self.parts_data is None:
            return

        # Remove rows with null symbol numbers
        cleaned_data = self.parts_data.dropna(subset=['Symbol Number'])

        # Deduplicate by Symbol Number, keeping first occurrence
        self.unique_parts = cleaned_data.drop_duplicates(subset=['Symbol Number'], keep='first')

        # Clean and prepare the data
        self.unique_parts = self.unique_parts.copy()
        self.unique_parts['Symbol Number'] = self.unique_parts['Symbol Number'].astype(str)

        # Fill null descriptions with empty strings
        self.unique_parts['Desc1'] = self.unique_parts['Desc1'].fillna('')
        self.unique_parts['Desc2'] = self.unique_parts['Desc2'].fillna('')
        self.unique_parts['Long Text Desc'] = self.unique_parts['Long Text Desc'].fillna('')

        # Create combined description for better text embedding
        self.unique_parts['Combined_Description'] = self.unique_parts.apply(
            lambda row: self._combine_descriptions(row['Desc1'], row['Desc2'], row['Long Text Desc']),
            axis=1
        )

        self.total_parts = len(self.unique_parts)

        logger.info(f"Processed {self.total_parts} unique parts after deduplication")

    def _combine_descriptions(self, desc1: str, desc2: str, long_desc: str) -> str:
        """
        Combine multiple description fields into a comprehensive description.

        Args:
            desc1: Primary description
            desc2: Secondary description
            long_desc: Long text description

        Returns:
            Combined description string
        """
        parts = []
        seen = set()

        # Helper to add unique descriptions
        def add_if_unique(text):
            if text and text.strip() and text.strip().lower() not in seen:
                clean_text = text.strip()
                parts.append(clean_text)
                seen.add(clean_text.lower())

        # Add descriptions in order of priority
        add_if_unique(desc1)
        add_if_unique(desc2)
        add_if_unique(long_desc)

        # Join with ", " separator for better readability
        return ", ".join(parts) if parts else ""

    def _safe_get_column(self, row, column_name: str, default='') -> Optional[str]:
        """
        Safely get a column value from a row, handling missing columns.
        
        Args:
            row: DataFrame row (Series)
            column_name: Name of the column to retrieve
            default: Default value if column doesn't exist
            
        Returns:
            Column value as string or None if empty/invalid
        """
        # Check if column exists in the DataFrame
        if self.unique_parts is not None and column_name not in self.unique_parts.columns:
            return None
            
        # Get value using .get() to handle missing keys
        value = row.get(column_name, default)
        
        # Check if value is valid (not NaN, not empty string, not 'nan' string)
        if pd.notna(value) and str(value).lower() not in ['', 'nan']:
            return str(value)
        return None

    def _get_long_description_with_fallback(self, row) -> str:
        """
        Get long description using Desc1 + Desc2.

        Always uses Desc1 + Desc2 joined together with " | " separator.

        Args:
            row: DataFrame row with part data

        Returns:
            Long description string (never empty)
        """
        # Always use Desc1 + Desc2
        desc1 = str(row.get('Desc1', '')) if pd.notna(row.get('Desc1')) else ''
        desc2 = str(row.get('Desc2', '')) if pd.notna(row.get('Desc2')) else ''

        # Join with " | " separator for clarity
        fallback_parts = []
        if desc1.strip():
            fallback_parts.append(desc1.strip())
        if desc2.strip():
            fallback_parts.append(desc2.strip())

        result = " | ".join(fallback_parts) if fallback_parts else 'No description available'
        return result

    def get_part_info(self, symbol_number: str) -> Optional[Dict]:
        """
        Get part information by symbol number.

        Args:
            symbol_number: The symbol number to search for

        Returns:
            Dict with part info or None if not found
        """
        if self.unique_parts is None:
            return None

        # Search for the part
        part_row = self.unique_parts[
            self.unique_parts['Symbol Number'].astype(str) == str(symbol_number)
        ]

        if part_row.empty:
            return None

        row = part_row.iloc[0]

        # Get Long Text JDE for item_note
        long_text_jde = self._safe_get_column(row, 'Long Text JDE')
        
        # Get long description with fallback (Desc1 + Desc2)
        long_desc = self._get_long_description_with_fallback(row)

        return {
            'symbol_number': str(row['Symbol Number']),
            # Keep backward-compatible fields
            'description': str(row['Desc1']) if pd.notna(row['Desc1']) else '',
            'item_note': long_text_jde or long_desc or 'No description available',  # Ensure never None
            # Expose source fields explicitly for richer labeling
            'description_1': str(row['Desc1']) if pd.notna(row['Desc1']) else '',
            'description_2': str(row['Desc2']) if pd.notna(row['Desc2']) else '',
            'long_description': long_desc,
            'combined_description': str(row['Combined_Description']),
            # Location: use Excel Location column only (no warehouse prefix)
            'location': str(row['Location']) if pd.notna(row['Location']) else '',
            # JDE columns (Part No and Mfg Name) - use helper for safe access
            'part_number': self._safe_get_column(row, 'Part No'),
            'manufacturer': self._safe_get_column(row, 'Mfg Name')
        }

    def search_parts(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search parts by symbol number or description.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching parts
        """
        if self.unique_parts is None:
            return []

        query_lower = query.lower()

        # Search in symbol number and description
        mask = (
            self.unique_parts['Symbol Number'].astype(str).str.lower().str.contains(query_lower, na=False) |
            self.unique_parts['Combined_Description'].astype(str).str.lower().str.contains(query_lower, na=False)
        )

        matching_parts = self.unique_parts[mask].head(limit)

        results = []
        for _, row in matching_parts.iterrows():
            # Get Long Text JDE for item_note
            long_text_jde = self._safe_get_column(row, 'Long Text JDE')
            
            # Get long description with fallback (Desc1 + Desc2)
            long_desc = self._get_long_description_with_fallback(row)

            results.append({
                'symbol_number': str(row['Symbol Number']),
                'description': str(row['Desc1']) if pd.notna(row['Desc1']) else '',
                'item_note': long_text_jde or long_desc or 'No description available',  # Ensure never None
                'description_1': str(row['Desc1']) if pd.notna(row['Desc1']) else '',
                'description_2': str(row['Desc2']) if pd.notna(row['Desc2']) else '',
                'long_description': long_desc,
                'combined_description': str(row['Combined_Description']),
                'location': str(row['Location']) if pd.notna(row['Location']) else '',
                'part_number': self._safe_get_column(row, 'Part No'),
                'manufacturer': self._safe_get_column(row, 'Mfg Name')
            })

        return results

    def get_all_parts(self, offset: int = 0, limit: int = 100) -> Tuple[List[Dict], int]:
        """
        Get paginated list of all parts.

        Args:
            offset: Starting offset
            limit: Number of parts to return

        Returns:
            Tuple of (parts_list, total_count)
        """
        if self.unique_parts is None:
            return [], 0

        total_count = len(self.unique_parts)
        parts_subset = self.unique_parts.iloc[offset:offset+limit]

        results = []
        for _, row in parts_subset.iterrows():
            # Get Long Text JDE for item_note
            long_text_jde = self._safe_get_column(row, 'Long Text JDE')
            
            # Get long description with fallback (Desc1 + Desc2)
            long_desc = self._get_long_description_with_fallback(row)

            results.append({
                'symbol_number': str(row['Symbol Number']),
                'description': str(row['Desc1']) if pd.notna(row['Desc1']) else '',
                'item_note': long_text_jde or long_desc or 'No description available',  # Ensure never None
                'description_1': str(row['Desc1']) if pd.notna(row['Desc1']) else '',
                'description_2': str(row['Desc2']) if pd.notna(row['Desc2']) else '',
                'long_description': long_desc,
                'combined_description': str(row['Combined_Description']),
                'location': str(row['Location']) if pd.notna(row['Location']) else '',
                'part_number': self._safe_get_column(row, 'Part No'),
                'manufacturer': self._safe_get_column(row, 'Mfg Name')
            })

        return results, total_count

    def get_stats(self) -> Dict:
        """Get statistics about the loaded parts data."""
        if self.unique_parts is None:
            return {'total_parts': 0, 'loaded': False}

        return {
            'total_parts': self.total_parts,
            'loaded': True,
            'has_descriptions': (self.unique_parts['Desc1'] != '').sum(),
            'has_long_descriptions': (self.unique_parts['Desc1'].notna() | self.unique_parts['Desc2'].notna()).sum(),
            'unique_warehouses': self.unique_parts['Whs'].nunique() if 'Whs' in self.unique_parts.columns else 0
        }


# Global instance
excel_parts_service = ExcelPartsService()

def get_excel_parts_service() -> ExcelPartsService:
    """Get the global Excel parts service instance."""
    return excel_parts_service