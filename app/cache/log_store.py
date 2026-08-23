import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional
from app.cache.models import PinoLogEntry
from app.cache.ring_buffer import ThreadSafeRingBuffer


class PinoLogStore:
    """Stores recent structured Pino logs with inverted indices for fast search."""

    def __init__(self, capacity: int = 10_000):
        self.buffer = ThreadSafeRingBuffer[PinoLogEntry](capacity=capacity)
        self._lock = threading.RLock()
        self._by_submission: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._by_battle: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._by_level: Dict[int, deque] = defaultdict(lambda: deque(maxlen=1000))

    def add_log(self, entry: PinoLogEntry) -> None:
        with self._lock:
            self.buffer.append(entry)
            self._by_level[entry.level].append(entry)
            if entry.submission_id:
                self._by_submission[str(entry.submission_id)].append(entry)
            if entry.battle_id:
                self._by_battle[str(entry.battle_id)].append(entry)

    def add_batch(self, entries: List[PinoLogEntry]) -> None:
        with self._lock:
            for entry in entries:
                self.add_log(entry)

    def get_recent(
        self,
        limit: int = 100,
        min_level: Optional[int] = None,
        submission_id: Optional[str] = None,
        battle_id: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[PinoLogEntry]:
        with self._lock:
            if submission_id:
                logs = list(self._by_submission.get(str(submission_id), []))
            elif battle_id:
                logs = list(self._by_battle.get(str(battle_id), []))
            else:
                logs = self.buffer.get_all()

            if min_level is not None:
                logs = [l for l in logs if l.level >= min_level]

            if query:
                q = query.lower()
                logs = [
                    l for l in logs
                    if q in l.msg.lower()
                    or (l.submission_id and q in l.submission_id.lower())
                    or (l.battle_id and q in l.battle_id.lower())
                    or (l.user_id and q in l.user_id.lower())
                    or (l.name and q in l.name.lower())
                ]

            return logs[-limit:]

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total_stored": self.buffer.size(),
                "total_ingested": self.buffer.total_appended(),
                "trace_count": len(self._by_level.get(10, [])),
                "debug_count": len(self._by_level.get(20, [])),
                "info_count": len(self._by_level.get(30, [])),
                "warn_count": len(self._by_level.get(40, [])),
                "error_count": len(self._by_level.get(50, [])),
                "fatal_count": len(self._by_level.get(60, [])),
                "tracked_submissions": len(self._by_submission),
                "tracked_battles": len(self._by_battle),
            }
