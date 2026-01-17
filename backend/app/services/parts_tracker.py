"""Parts processing tracker service."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class PartsTracker:
    """Track progress of parts processing for image cataloging."""

    def __init__(self, tracker_file: str = "parts_tracker.json"):
        self.tracker_file = Path(tracker_file)
        self.processed_parts: Set[str] = set()
        self.failed_parts: Dict[str, str] = {}  # part_number -> error_reason
        self.part_stats: Dict[str, Dict] = {}   # part_number -> stats
        self.total_parts = 0
        self.load_tracker()

    def load_tracker(self):
        """Load tracker data from file."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    data = json.load(f)
                    self.processed_parts = set(data.get('processed_parts', []))
                    self.failed_parts = data.get('failed_parts', {})
                    self.part_stats = data.get('part_stats', {})
                    self.total_parts = data.get('total_parts', 0)
                    logger.info(f"Loaded tracker: {len(self.processed_parts)} processed, {len(self.failed_parts)} failed")
            except Exception as e:
                logger.error(f"Failed to load tracker file: {e}")

    def save_tracker(self):
        """Save tracker data to file."""
        try:
            data = {
                'processed_parts': list(self.processed_parts),
                'failed_parts': self.failed_parts,
                'part_stats': self.part_stats,
                'total_parts': self.total_parts,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.tracker_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tracker file: {e}")

    def set_total_parts(self, total: int):
        """Set the total number of parts to process."""
        self.total_parts = total
        self.save_tracker()

    def mark_part_processed(self, part_number: str, image_count: int, processing_time: float = None):
        """
        Mark a part as successfully processed.

        Args:
            part_number: The part number
            image_count: Number of images processed for this part
            processing_time: Processing time in seconds
        """
        self.processed_parts.add(part_number)

        # Remove from failed if it was there
        if part_number in self.failed_parts:
            del self.failed_parts[part_number]

        # Update stats
        self.part_stats[part_number] = {
            'status': 'completed',
            'image_count': image_count,
            'processing_time': processing_time,
            'completed_at': datetime.now().isoformat()
        }

        self.save_tracker()
        logger.info(f"Part {part_number} marked as processed with {image_count} images")

    def mark_part_failed(self, part_number: str, error_reason: str):
        """
        Mark a part as failed processing.

        Args:
            part_number: The part number
            error_reason: Reason for failure
        """
        self.failed_parts[part_number] = error_reason

        # Remove from processed if it was there
        self.processed_parts.discard(part_number)

        # Update stats
        self.part_stats[part_number] = {
            'status': 'failed',
            'error_reason': error_reason,
            'failed_at': datetime.now().isoformat()
        }

        self.save_tracker()
        logger.warning(f"Part {part_number} marked as failed: {error_reason}")

    def is_part_processed(self, part_number: str) -> bool:
        """Check if a part has been processed."""
        return part_number in self.processed_parts

    def is_part_failed(self, part_number: str) -> bool:
        """Check if a part has failed processing."""
        return part_number in self.failed_parts

    def get_progress_stats(self) -> Dict:
        """Get overall progress statistics."""
        processed_count = len(self.processed_parts)
        failed_count = len(self.failed_parts)
        remaining_count = max(0, self.total_parts - processed_count - failed_count)

        progress_percentage = 0
        if self.total_parts > 0:
            progress_percentage = (processed_count / self.total_parts) * 100

        return {
            'total_parts': self.total_parts,
            'processed_count': processed_count,
            'failed_count': failed_count,
            'remaining_count': remaining_count,
            'progress_percentage': round(progress_percentage, 2),
            'success_rate': round((processed_count / max(1, processed_count + failed_count)) * 100, 2)
        }

    def get_processed_parts(self) -> List[str]:
        """Get list of processed part numbers."""
        return list(self.processed_parts)

    def get_failed_parts(self) -> Dict[str, str]:
        """Get dictionary of failed parts and their error reasons."""
        return self.failed_parts.copy()

    def get_remaining_parts(self, all_parts: List[str]) -> List[str]:
        """
        Get list of parts that haven't been processed yet.

        Args:
            all_parts: List of all part numbers

        Returns:
            List of unprocessed part numbers
        """
        all_parts_set = set(all_parts)
        processed_and_failed = self.processed_parts.union(set(self.failed_parts.keys()))
        return list(all_parts_set - processed_and_failed)

    def get_part_status(self, part_number: str) -> Optional[Dict]:
        """
        Get detailed status of a specific part.

        Args:
            part_number: The part number to check

        Returns:
            Dict with part status or None if not found
        """
        return self.part_stats.get(part_number)

    def reset_part(self, part_number: str):
        """
        Reset a part's status (remove from processed/failed).

        Args:
            part_number: The part number to reset
        """
        self.processed_parts.discard(part_number)
        if part_number in self.failed_parts:
            del self.failed_parts[part_number]
        if part_number in self.part_stats:
            del self.part_stats[part_number]

        self.save_tracker()
        logger.info(f"Reset status for part {part_number}")

    def reset_all(self):
        """Reset all tracking data."""
        self.processed_parts.clear()
        self.failed_parts.clear()
        self.part_stats.clear()
        self.total_parts = 0
        self.save_tracker()
        logger.info("Reset all tracking data")

    def export_report(self, output_file: str = None) -> str:
        """
        Export a detailed progress report.

        Args:
            output_file: Optional output file path

        Returns:
            Report content as string
        """
        stats = self.get_progress_stats()

        report_lines = [
            "PARTS PROCESSING REPORT",
            "=" * 40,
            f"Total Parts: {stats['total_parts']}",
            f"Processed: {stats['processed_count']} ({stats['progress_percentage']}%)",
            f"Failed: {stats['failed_count']}",
            f"Remaining: {stats['remaining_count']}",
            f"Success Rate: {stats['success_rate']}%",
            "",
            "FAILED PARTS:",
            "-" * 20
        ]

        for part_number, error in self.failed_parts.items():
            report_lines.append(f"{part_number}: {error}")

        report_content = "\n".join(report_lines)

        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report_content)
                logger.info(f"Report exported to {output_file}")
            except Exception as e:
                logger.error(f"Failed to export report: {e}")

        return report_content


# Global tracker instance
parts_tracker = PartsTracker()

def get_parts_tracker() -> PartsTracker:
    """Get the global parts tracker instance."""
    return parts_tracker