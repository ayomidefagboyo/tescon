"""Parts processing tracker service."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class PartsTracker:
    """Track progress of parts processing for image cataloging."""

    def __init__(self, tracker_file: Optional[str] = None):
        backend_root = Path(__file__).resolve().parents[2]
        default_tracker_path = backend_root / "parts_tracker.json"
        legacy_cwd_tracker_path = Path.cwd() / "parts_tracker.json"
        self.db_path = backend_root / "parts_tracker.db"

        if tracker_file:
            self.tracker_file = Path(tracker_file)
        else:
            candidate_paths = [default_tracker_path, legacy_cwd_tracker_path]
            existing_candidates = [path for path in candidate_paths if path.exists()]
            if not existing_candidates:
                self.tracker_file = default_tracker_path
            elif len(existing_candidates) == 1:
                self.tracker_file = existing_candidates[0]
            else:
                # Prefer the file with richer tracker data, then newer mtime.
                self.tracker_file = max(existing_candidates, key=self._tracker_file_score)

        self.processed_parts: Set[str] = set()
        self.failed_parts: Dict[str, str] = {}  # symbol_number -> error_reason
        self.queued_parts: Set[str] = set()     # Parts uploaded and queued for processing
        self.part_stats: Dict[str, Dict] = {}   # symbol_number -> stats
        self.total_parts = 0
        self._init_db()
        self.load_tracker()
        self._load_state_from_db()

    def _tracker_file_score(self, file_path: Path):
        """Score tracker files so we can pick the most complete state."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            processed = len(data.get('processed_parts', []))
            failed = len(data.get('failed_parts', {}))
            queued = len(data.get('queued_parts', []))
            total = int(data.get('total_parts', 0) or 0)
            return (processed + failed + queued, total, file_path.stat().st_mtime)
        except Exception:
            return (-1, -1, -1)

    def _connect_db(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize SQLite tables for tracker state."""
        conn = self._connect_db()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tracker_status (
                    symbol_number TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    image_count INTEGER,
                    error_reason TEXT,
                    queued_at TEXT,
                    completed_at TEXT,
                    failed_at TEXT,
                    processing_time REAL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tracker_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _get_meta_int(self, key: str, default: int = 0) -> int:
        conn = self._connect_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT value FROM tracker_meta WHERE key = ?", (key,))
            row = cur.fetchone()
            if not row:
                return default
            try:
                return int(row[0])
            except (TypeError, ValueError):
                return default
        finally:
            conn.close()

    def _set_meta(self, key: str, value: str):
        conn = self._connect_db()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO tracker_meta (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value)
            )
            conn.commit()
        finally:
            conn.close()

    def _load_state_from_db(self):
        """
        Load in-memory tracker state from SQLite.
        If DB is empty and file has data, bootstrap DB from file.
        """
        conn = self._connect_db()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT symbol_number, status, image_count, error_reason, queued_at, completed_at, failed_at, processing_time
                FROM tracker_status
                """
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        if rows:
            self.processed_parts.clear()
            self.failed_parts.clear()
            self.queued_parts.clear()
            self.part_stats.clear()

            for row in rows:
                symbol_number, status, image_count, error_reason, queued_at, completed_at, failed_at, processing_time = row
                if status == "completed":
                    self.processed_parts.add(symbol_number)
                elif status == "queued":
                    self.queued_parts.add(symbol_number)
                elif status == "failed":
                    self.failed_parts[symbol_number] = error_reason or ""

                stats = {
                    "status": status,
                    "image_count": image_count
                }
                if error_reason:
                    stats["error_reason"] = error_reason
                if queued_at:
                    stats["queued_at"] = queued_at
                if completed_at:
                    stats["completed_at"] = completed_at
                if failed_at:
                    stats["failed_at"] = failed_at
                if processing_time is not None:
                    stats["processing_time"] = processing_time
                self.part_stats[symbol_number] = stats

            self.total_parts = self._get_meta_int("total_parts", self.total_parts)
            return

        # Bootstrap DB from existing file-based state for backward compatibility.
        if self.processed_parts or self.queued_parts or self.failed_parts:
            self._rewrite_db_from_memory()
        self.total_parts = self._get_meta_int("total_parts", self.total_parts)

    def refresh_from_db(self):
        """Public helper to refresh in-memory state from SQLite."""
        self._load_state_from_db()

    def _upsert_status_row(self, symbol_number: str, stats: Dict):
        conn = self._connect_db()
        try:
            cur = conn.cursor()
            now_iso = datetime.now().isoformat()
            cur.execute(
                """
                INSERT INTO tracker_status (
                    symbol_number, status, image_count, error_reason, queued_at, completed_at, failed_at, processing_time, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol_number) DO UPDATE SET
                    status = excluded.status,
                    image_count = excluded.image_count,
                    error_reason = excluded.error_reason,
                    queued_at = excluded.queued_at,
                    completed_at = excluded.completed_at,
                    failed_at = excluded.failed_at,
                    processing_time = excluded.processing_time,
                    updated_at = excluded.updated_at
                """,
                (
                    symbol_number,
                    stats.get("status"),
                    stats.get("image_count"),
                    stats.get("error_reason"),
                    stats.get("queued_at"),
                    stats.get("completed_at"),
                    stats.get("failed_at"),
                    stats.get("processing_time"),
                    now_iso
                )
            )
            conn.commit()
        finally:
            conn.close()

    def _delete_status_row(self, symbol_number: str):
        conn = self._connect_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tracker_status WHERE symbol_number = ?", (symbol_number,))
            conn.commit()
        finally:
            conn.close()

    def _rewrite_db_from_memory(self):
        """Replace DB tracker rows with current in-memory state."""
        conn = self._connect_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tracker_status")
            now_iso = datetime.now().isoformat()
            rows = []
            for symbol_number, stats in self.part_stats.items():
                rows.append((
                    symbol_number,
                    stats.get("status"),
                    stats.get("image_count"),
                    stats.get("error_reason"),
                    stats.get("queued_at"),
                    stats.get("completed_at"),
                    stats.get("failed_at"),
                    stats.get("processing_time"),
                    now_iso
                ))

            if rows:
                cur.executemany(
                    """
                    INSERT INTO tracker_status (
                        symbol_number, status, image_count, error_reason, queued_at, completed_at, failed_at, processing_time, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows
                )

            cur.execute(
                """
                INSERT INTO tracker_meta (key, value)
                VALUES ('total_parts', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(self.total_parts),)
            )
            conn.commit()
        finally:
            conn.close()

    def load_tracker(self):
        """Load tracker data from file."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    data = json.load(f)
                    self.processed_parts = set(data.get('processed_parts', []))
                    self.failed_parts = data.get('failed_parts', {})
                    self.queued_parts = set(data.get('queued_parts', []))
                    self.part_stats = data.get('part_stats', {})
                    self.total_parts = data.get('total_parts', 0)
                    logger.info(f"Loaded tracker: {len(self.processed_parts)} processed, {len(self.failed_parts)} failed, {len(self.queued_parts)} queued")
            except Exception as e:
                logger.error(f"Failed to load tracker file: {e}")

    def save_tracker(self):
        """Save tracker data to file."""
        try:
            data = {
                'processed_parts': list(self.processed_parts),
                'failed_parts': self.failed_parts,
                'queued_parts': list(self.queued_parts),
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
        self._set_meta("total_parts", str(total))
        self.save_tracker()

    def mark_part_queued(self, symbol_number: str, image_count: int):
        """
        Mark a part as queued for processing.

        Args:
            symbol_number: The part number
            image_count: Number of images uploaded
        """
        # Clear any previous status when re-queuing (important for retries)
        self.processed_parts.discard(symbol_number)
        if symbol_number in self.failed_parts:
            del self.failed_parts[symbol_number]

        self.queued_parts.add(symbol_number)

        # Update stats
        self.part_stats[symbol_number] = {
            'status': 'queued',
            'image_count': image_count,
            'queued_at': datetime.now().isoformat()
        }

        self._upsert_status_row(symbol_number, self.part_stats[symbol_number])
        self.save_tracker()
        logger.info(f"Part {symbol_number} marked as queued with {image_count} images")

    def mark_part_processed(self, symbol_number: str, image_count: int, processing_time: float = None):
        """
        Mark a part as successfully processed.

        Args:
            symbol_number: The part number
            image_count: Number of images processed for this part
            processing_time: Processing time in seconds
        """
        self.processed_parts.add(symbol_number)

        # Remove from queued and failed if it was there
        self.queued_parts.discard(symbol_number)
        if symbol_number in self.failed_parts:
            del self.failed_parts[symbol_number]

        # Update stats
        self.part_stats[symbol_number] = {
            'status': 'completed',
            'image_count': image_count,
            'processing_time': processing_time,
            'completed_at': datetime.now().isoformat()
        }

        self._upsert_status_row(symbol_number, self.part_stats[symbol_number])
        self.save_tracker()
        logger.info(f"Part {symbol_number} marked as processed with {image_count} images")

    def mark_part_failed(self, symbol_number: str, error_reason: str):
        """
        Mark a part as failed processing.

        Args:
            symbol_number: The part number
            error_reason: Reason for failure
        """
        self.failed_parts[symbol_number] = error_reason

        # Remove from processed and queued if it was there
        self.processed_parts.discard(symbol_number)
        self.queued_parts.discard(symbol_number)

        # Update stats
        self.part_stats[symbol_number] = {
            'status': 'failed',
            'error_reason': error_reason,
            'failed_at': datetime.now().isoformat()
        }

        self._upsert_status_row(symbol_number, self.part_stats[symbol_number])
        self.save_tracker()
        logger.warning(f"Part {symbol_number} marked as failed: {error_reason}")

    def is_part_queued(self, symbol_number: str) -> bool:
        """Check if a part is queued for processing."""
        return symbol_number in self.queued_parts

    def is_part_processed(self, symbol_number: str) -> bool:
        """Check if a part has been processed."""
        return symbol_number in self.processed_parts

    def is_part_failed(self, symbol_number: str) -> bool:
        """Check if a part has failed processing."""
        return symbol_number in self.failed_parts

    def get_progress_stats(self) -> Dict:
        """Get overall progress statistics."""
        self._load_state_from_db()
        processed_count = len(self.processed_parts)
        failed_count = len(self.failed_parts)
        queued_count = len(self.queued_parts)
        remaining_count = max(0, self.total_parts - processed_count - failed_count - queued_count)

        progress_percentage = 0
        if self.total_parts > 0:
            progress_percentage = (processed_count / self.total_parts) * 100

        # Calculate daily stats
        today = datetime.now().date().isoformat()
        completed_today = sum(
            1 for stats in self.part_stats.values()
            if stats.get('status') == 'completed' 
            and stats.get('completed_at', '').startswith(today)
        )
        queued_today = sum(
            1 for stats in self.part_stats.values()
            if stats.get('status') == 'queued'
            and stats.get('queued_at', '').startswith(today)
        )
        failed_today = sum(
            1 for stats in self.part_stats.values()
            if stats.get('status') == 'failed'
            and stats.get('failed_at', '').startswith(today)
        )

        return {
            'total_parts': self.total_parts,
            'processed_count': processed_count,
            'failed_count': failed_count,
            'queued_count': queued_count,
            'remaining_count': remaining_count,
            'progress_percentage': round(progress_percentage, 2),
            'success_rate': round((processed_count / max(1, processed_count + failed_count)) * 100, 2),
            'completed_today': completed_today,
            'queued_today': queued_today,
            'failed_today': failed_today
        }

    def get_queued_parts(self) -> List[str]:
        """Get list of queued part numbers."""
        self._load_state_from_db()
        return list(self.queued_parts)

    def get_processed_parts(self) -> List[str]:
        """Get list of processed part numbers."""
        self._load_state_from_db()
        return list(self.processed_parts)

    def get_failed_parts(self) -> Dict[str, str]:
        """Get dictionary of failed parts and their error reasons."""
        self._load_state_from_db()
        return self.failed_parts.copy()

    def get_remaining_parts(self, all_parts: List[str]) -> List[str]:
        """
        Get list of parts that haven't been processed yet.

        Args:
            all_parts: List of all part numbers

        Returns:
            List of unprocessed part numbers
        """
        self._load_state_from_db()
        all_parts_set = set(all_parts)
        processed_queued_and_failed = self.processed_parts.union(self.queued_parts).union(set(self.failed_parts.keys()))
        return list(all_parts_set - processed_queued_and_failed)

    def get_part_status(self, symbol_number: str) -> Optional[Dict]:
        """
        Get detailed status of a specific part.

        Args:
            symbol_number: The part number to check

        Returns:
            Dict with part status or None if not found
        """
        self._load_state_from_db()
        return self.part_stats.get(symbol_number)

    def reset_part(self, symbol_number: str):
        """
        Reset a part's status (remove from processed/failed/queued).

        Args:
            symbol_number: The part number to reset
        """
        self.processed_parts.discard(symbol_number)
        self.queued_parts.discard(symbol_number)
        if symbol_number in self.failed_parts:
            del self.failed_parts[symbol_number]
        if symbol_number in self.part_stats:
            del self.part_stats[symbol_number]

        self._delete_status_row(symbol_number)
        self.save_tracker()
        logger.info(f"Reset status for part {symbol_number}")

    def reset_all(self):
        """Reset all tracking data."""
        self.processed_parts.clear()
        self.failed_parts.clear()
        self.queued_parts.clear()
        self.part_stats.clear()
        self.total_parts = 0
        conn = self._connect_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tracker_status")
            cur.execute("DELETE FROM tracker_meta WHERE key = 'total_parts'")
            conn.commit()
        finally:
            conn.close()
        self.save_tracker()
        logger.info("Reset all tracking data")

    def replace_state(
        self,
        *,
        processed_parts: Set[str],
        queued_parts: Set[str],
        failed_parts: Dict[str, str],
        part_stats: Dict[str, Dict],
        total_parts: Optional[int] = None
    ):
        """Atomically replace tracker state (used by R2 reconciliation)."""
        self.processed_parts = set(processed_parts)
        self.queued_parts = set(queued_parts)
        self.failed_parts = dict(failed_parts)
        self.part_stats = dict(part_stats)
        if total_parts is not None:
            self.total_parts = int(total_parts)
        self._rewrite_db_from_memory()
        self.save_tracker()

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

        for symbol_number, error in self.failed_parts.items():
            report_lines.append(f"{symbol_number}: {error}")

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