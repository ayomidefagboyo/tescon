"""Simple Excel service for loading part metadata."""
import pandas as pd
from typing import Optional, Dict, Any


class ExcelPartsService:
    """Service to load and query part information from Excel."""
    
    def __init__(self):
        self.df = None
        self.parts_dict = {}
    
    def load_excel_file(self, file_path: str, sheet_name: str = "Sheet1") -> bool:
        """Load Excel file and index by symbol number."""
        try:
            self.df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Index by Symbol Number for fast lookup
            if 'Symbol Number' in self.df.columns:
                for _, row in self.df.iterrows():
                    symbol = str(row.get('Symbol Number', '')).strip()
                    if symbol:
                        self.parts_dict[symbol] = row.to_dict()
            
            return True
        except Exception as e:
            print(f"Error loading Excel: {e}")
            return False
    
    def get_part_info(self, symbol_number: str) -> Optional[Dict[str, Any]]:
        """Get part information by symbol number."""
        symbol = str(symbol_number).strip()
        row = self.parts_dict.get(symbol)
        
        if not row:
            return None
        
        # Clean up description fields (remove trailing commas)
        desc1 = str(row.get('Desc1', '')).strip().rstrip(',')
        desc2 = str(row.get('Desc2', '')).strip().rstrip(',')
        long_text = str(row.get('Long Text JDE', '')).strip()
        
        # Use Long Text JDE if available, otherwise fallback
        item_note = long_text if long_text and long_text != 'nan' else None
        
        return {
            'symbol_number': symbol,
            'part_number': str(row.get('Part No', '')).strip(),
            'manufacturer': str(row.get('Manufacturer', '')).strip(),
            'description_1': desc1 if desc1 and desc1 != 'nan' else None,
            'description_2': desc2 if desc2 and desc2 != 'nan' else None,
            'item_note': item_note
        }
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded parts."""
        return {
            'total_parts': len(self.parts_dict)
        }
