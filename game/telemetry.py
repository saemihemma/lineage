"""Telemetry system for game analytics"""
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TelemetryEvent:
    """Represents a single telemetry event"""
    timestamp: float
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)


class Telemetry:
    """Manages telemetry logging and export"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.events: List[TelemetryEvent] = []
        self.session_start = time.time()
        self.metrics: Dict[str, Any] = {
            "actions": {},
            "expedition_outcomes": {"success": 0, "failure": 0, "total": 0},
            "upload_rates": [],
            "time_to_first_womb": None,
            "clones_grown": 0,
            "clones_uploaded": 0,
            "total_expeditions": 0,
        }
    
    def log_event(self, event_type: str, **data):
        """Log a telemetry event"""
        if not self.enabled:
            return
        
        event = TelemetryEvent(
            timestamp=time.time(),
            event_type=event_type,
            data=data
        )
        self.events.append(event)
        
        # Update metrics
        self._update_metrics(event_type, data)
    
    def _update_metrics(self, event_type: str, data: Dict[str, Any]):
        """Update aggregated metrics based on event"""
        # Track action counts
        if event_type not in self.metrics["actions"]:
            self.metrics["actions"][event_type] = 0
        self.metrics["actions"][event_type] += 1
        
        # Track specific metrics
        if event_type == "womb_built" and self.metrics["time_to_first_womb"] is None:
            elapsed = time.time() - self.session_start
            self.metrics["time_to_first_womb"] = elapsed
        
        if event_type == "clone_grown":
            self.metrics["clones_grown"] += 1
        
        if event_type == "clone_uploaded":
            self.metrics["clones_uploaded"] += 1
            if "xp_retained" in data:
                self.metrics["upload_rates"].append(data["xp_retained"])
        
        if event_type == "expedition_complete":
            self.metrics["total_expeditions"] += 1
            if data.get("success", True):
                self.metrics["expedition_outcomes"]["success"] += 1
            else:
                self.metrics["expedition_outcomes"]["failure"] += 1
            self.metrics["expedition_outcomes"]["total"] += 1
    
    def export(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export telemetry data to JSON.
        
        Args:
            output_path: Optional path to save JSON file. If None, creates timestamped file.
        
        Returns:
            Dictionary containing telemetry data
        """
        session_duration = time.time() - self.session_start
        
        export_data = {
            "session_info": {
                "start_time": datetime.fromtimestamp(self.session_start).isoformat(),
                "duration_seconds": session_duration,
                "events_count": len(self.events),
            },
            "events": [asdict(event) for event in self.events],
            "metrics": self.metrics,
        }
        
        if output_path is None:
            # Create saves directory if needed
            saves_dir = Path("saves")
            saves_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = saves_dir / f"telemetry_{timestamp}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)
        
        return export_data
    
    def upload_to_api(self, session_id: str = "default") -> bool:
        """
        Upload telemetry events to API (non-blocking).
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            True if upload initiated successfully, False otherwise
        """
        if not self.enabled or not self.events:
            return False
        
        try:
            from core.api_client import get_api_client
            
            api_client = get_api_client()
            
            # Convert events to API format
            events_data = []
            for event in self.events:
                events_data.append({
                    "session_id": session_id,
                    "event_type": event.event_type,
                    "data": event.data,
                    "timestamp": datetime.fromtimestamp(event.timestamp).isoformat()
                })
            
            # Upload (may fail silently in background)
            success = api_client.upload_telemetry(events_data)
            return success
            
        except Exception:
            # Fail silently - don't block game if telemetry upload fails
            return False
    
    def clear(self):
        """Clear all telemetry data"""
        self.events.clear()
        self.session_start = time.time()
        self.metrics = {
            "actions": {},
            "expedition_outcomes": {"success": 0, "failure": 0, "total": 0},
            "upload_rates": [],
            "time_to_first_womb": None,
            "clones_grown": 0,
            "clones_uploaded": 0,
            "total_expeditions": 0,
        }

