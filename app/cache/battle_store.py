import threading
from collections import OrderedDict
from typing import Dict, List, Optional
from app.cache.models import BattleMetricsEntry


class BattleMetricsStore:
    """Stores 1v1 battle telemetry entries with head-to-head stats."""

    def __init__(self, capacity: int = 5_000):
        self.capacity = capacity
        self._battles: OrderedDict[str, BattleMetricsEntry] = OrderedDict()
        self._lock = threading.RLock()

    def add_or_update(self, entry: BattleMetricsEntry) -> None:
        with self._lock:
            if entry.battle_id in self._battles:
                self._battles.move_to_end(entry.battle_id)
            self._battles[entry.battle_id] = entry
            while len(self._battles) > self.capacity:
                self._battles.popitem(last=False)

    def get(self, battle_id: str) -> Optional[BattleMetricsEntry]:
        with self._lock:
            return self._battles.get(battle_id)

    def get_recent(self, limit: int = 50) -> List[BattleMetricsEntry]:
        with self._lock:
            values = list(self._battles.values())
            return values[-limit:]

    def get_by_user(self, user_id: str, limit: int = 20) -> List[BattleMetricsEntry]:
        with self._lock:
            matches = [
                b for b in self._battles.values()
                if b.player1.user_id == user_id or b.player2.user_id == user_id
            ]
            return matches[-limit:]

    def get_summary(self) -> dict:
        with self._lock:
            battles = list(self._battles.values())
            total = len(battles)
            if not total:
                return {"total_battles": 0, "avg_duration_sec": 0.0, "active_count": 0}

            durations = [b.duration_seconds for b in battles if b.duration_seconds > 0]
            avg_dur = sum(durations) / len(durations) if durations else 0.0
            active = len([b for b in battles if b.status == "RUNNING"])

            return {
                "total_battles": total,
                "active_battles": active,
                "avg_duration_seconds": round(avg_dur, 2),
                "completed_battles": len([b for b in battles if b.status == "FINISHED"]),
            }
