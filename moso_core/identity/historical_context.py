import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from moso_core.identity.models import SignalResult, WEIGHT_HISTORICAL

logger = logging.getLogger(__name__)


class HistoricalContext:
    def __init__(self, store_path: Optional[str] = None):
        if store_path is None:
            store_path = os.path.join(os.path.expanduser("~"), ".moso", "history")
        self._store_path = Path(store_path)
        self._store_path.mkdir(parents=True, exist_ok=True)
        self._usage_log: list[dict] = []
        self._load_history()
        self._session_count = 0

    def load_model(self) -> None:
        self._load_history()
        logger.info("Historical context loaded (%d records)", len(self._usage_log))

    def evaluate(self) -> SignalResult:
        hour = datetime.now().hour
        day = datetime.now().weekday()
        recent_activity = self._check_recent_activity()
        time_score = self._score_time_pattern(hour, day)
        continuity_score = self._score_conversation_continuity()
        anomaly_score = self._check_anomalies()

        combined = 0.35 * time_score + 0.30 * recent_activity + 0.20 * continuity_score + 0.15 * (1.0 - anomaly_score)

        return SignalResult(
            signal_name="historical_context",
            confidence=combined,
            weight=WEIGHT_HISTORICAL,
            details={
                "time_score": time_score,
                "recent_activity_score": recent_activity,
                "continuity_score": continuity_score,
                "anomaly_score": anomaly_score,
                "session_count": self._session_count,
                "total_interactions": len(self._usage_log),
                "normal_hour": hour in self._get_normal_hours(),
            },
        )

    def log_interaction(self, text: str, identity: str = "unknown") -> None:
        record = {
            "timestamp": time.time(),
            "text": text[:200],
            "identity": identity,
            "hour": datetime.now().hour,
            "day": datetime.now().weekday(),
        }
        self._usage_log.append(record)
        self._session_count += 1
        self._save_history()

    def _score_time_pattern(self, hour: int, day: int) -> float:
        normal_hours = self._get_normal_hours()
        if hour in normal_hours:
            return 0.9
        if 6 <= hour <= 8 or 22 <= hour <= 23:
            return 0.6
        return 0.3

    def _score_conversation_continuity(self) -> float:
        if len(self._usage_log) < 2:
            return 0.5
        recent = self._usage_log[-min(10, len(self._usage_log)):]
        if len(recent) < 2:
            return 0.5
        intervals = []
        for i in range(1, len(recent)):
            interval = recent[i]["timestamp"] - recent[i - 1]["timestamp"]
            intervals.append(interval)
        if not intervals:
            return 0.5
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval < 300:
            return 0.9
        if avg_interval < 3600:
            return 0.7
        if avg_interval < 86400:
            return 0.4
        return 0.2

    def _check_recent_activity(self) -> float:
        if not self._usage_log:
            return 0.3
        now = time.time()
        recent = [r for r in self._usage_log if now - r["timestamp"] < 3600]
        if len(recent) >= 3:
            return 0.9
        if len(recent) >= 1:
            return 0.6
        return 0.3

    def _check_anomalies(self) -> float:
        if len(self._usage_log) < 10:
            return 0.0
        recent = self._usage_log[-10:]
        hour_counts: dict[int, int] = {}
        for r in recent:
            h = r["hour"]
            hour_counts[h] = hour_counts.get(h, 0) + 1
        current_hour = datetime.now().hour
        normal_rate = sum(hour_counts.values()) / max(1, len(hour_counts))
        current_rate = hour_counts.get(current_hour, 0)
        if current_rate > normal_rate * 3 and normal_rate > 0:
            return 0.7
        return 0.1

    def _get_normal_hours(self) -> set[int]:
        if not self._usage_log:
            return set(range(8, 22))
        hour_counts: dict[int, int] = {}
        for r in self._usage_log:
            h = r["hour"]
            hour_counts[h] = hour_counts.get(h, 0) + 1
        total = sum(hour_counts.values())
        if total == 0:
            return set(range(8, 22))
        avg = total / max(1, len(hour_counts))
        normal = {h for h, c in hour_counts.items() if c >= avg * 0.5}
        return normal or set(range(8, 22))

    def _load_history(self) -> None:
        history_file = self._store_path / "usage.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)
                    self._usage_log = data.get("interactions", [])
                    self._session_count = data.get("sessions", 0)
            except Exception as e:
                logger.warning("Failed to load history: %s", e)

    def _save_history(self) -> None:
        history_file = self._store_path / "usage.json"
        try:
            with open(history_file, "w") as f:
                json.dump(
                    {
                        "interactions": self._usage_log[-500:],
                        "sessions": self._session_count,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning("Failed to save history: %s", e)

    @property
    def is_loaded(self) -> bool:
        return True

    def reset(self) -> None:
        self._usage_log.clear()
        self._session_count = 0
