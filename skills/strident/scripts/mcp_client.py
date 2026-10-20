#!/usr/bin/env python3
"""
Standard MCP Client for AI Running Coach.
Interfaces with a local or remote Garmin MCP server over Server-Sent Events (SSE).

Default URL: Reads GARMIN_MCP_URL or defaults to http://localhost:8085
"""

import os
import sys
import json
import time
import threading
import urllib.request
import urllib.parse
import datetime
from typing import Any, Dict, Optional

MCP_BASE_URL = os.getenv("GARMIN_MCP_URL", "http://localhost:8085").rstrip("/")

class GarminMCPClient:
    def __init__(self, base_url: str = MCP_BASE_URL, timeout: int = 30):
        self.base_url = base_url
        parsed = urllib.parse.urlparse(self.base_url)
        self.host_header = parsed.netloc or "localhost:8085"
        self.timeout = timeout
        self.endpoint_path: Optional[str] = None
        self.ready_event = threading.Event()
        self.responses: Dict[int, Any] = {}
        self.msg_counter = 10
        self._listener_thread: Optional[threading.Thread] = None
        self._stop_listener = False
        self._connect()

    def _connect(self):
        def listen():
            req = urllib.request.Request(f"{self.base_url}/sse", headers={"Host": self.host_header})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    for raw_line in resp:
                        if self._stop_listener:
                            break
                        line = raw_line.decode("utf-8").strip()
                        if line.startswith("data: /messages/"):
                            self.endpoint_path = line[6:].strip()
                            self.ready_event.set()
                        elif line.startswith("data: "):
                            try:
                                payload = json.loads(line[6:].strip())
                                msg_id = payload.get("id")
                                if msg_id is not None:
                                    self.responses[msg_id] = payload
                            except Exception:
                                pass
            except Exception:
                self.ready_event.set()

        self._listener_thread = threading.Thread(target=listen, daemon=True)
        self._listener_thread.start()

        if not self.ready_event.wait(timeout=8) or not self.endpoint_path:
            raise ConnectionError(f"Failed to connect to Garmin MCP Server at {self.base_url}/sse")

        self.post_url = f"{self.base_url}{self.endpoint_path}"
        self._initialize()

    def _send_rpc(self, msg_id: int, method: str, params: Optional[Dict[str, Any]] = None):
        payload = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            payload["params"] = params
        req = urllib.request.Request(
            self.post_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Host": self.host_header, "Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=self.timeout)

    def _initialize(self):
        self._send_rpc(1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ai-running-coach-client", "version": "1.0"}
        })
        time.sleep(0.3)
        notif_req = urllib.request.Request(
            self.post_url,
            data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode("utf-8"),
            headers={"Host": self.host_header, "Content-Type": "application/json"}
        )
        urllib.request.urlopen(notif_req, timeout=10)
        time.sleep(0.2)

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        self.msg_counter += 1
        msg_id = self.msg_counter
        self._send_rpc(msg_id, "tools/call", {"name": tool_name, "arguments": arguments or {}})

        for _ in range(200):
            if msg_id in self.responses:
                break
            time.sleep(0.1)

        resp = self.responses.get(msg_id, {})
        if "error" in resp:
            raise RuntimeError(f"MCP Tool Error ({tool_name}): {resp['error']}")

        result = resp.get("result", {})
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            raw_text = content[0].get("text", "")
            try:
                return json.loads(raw_text)
            except Exception:
                return raw_text
        return result

    # High-level helpers
    def sync(self, refresh: bool = False) -> Any:
        return self.call_tool("garmin_sync", {"refresh": refresh})

    def get_today(self) -> Any:
        return self.call_tool("garmin_today", {})

    def get_sleep(self, days: int = 2) -> Any:
        return self.call_tool("garmin_sleep", {"days": days})

    def get_hrv(self) -> Any:
        return self.call_tool("garmin_hrv", {})

    def get_training_load(self) -> Any:
        return self.call_tool("garmin_training_load", {})

    def get_activities(self, start_date: str = "", end_date: str = "", activity_type: str = "", limit: int = 20) -> Any:
        args = {"limit": limit}
        if start_date:
            args["start_date"] = start_date
        if end_date:
            args["end_date"] = end_date
        if activity_type:
            args["activity_type"] = activity_type
        return self.call_tool("garmin_activities", args)

    def get_activity_detail(self, activity_id: int = 0, last: bool = False) -> Any:
        return self.call_tool("garmin_activity_detail", {"activity_id": activity_id, "last": last})

    def calc_running_volume(self, target_annual_km: float = 1500.0, year: Optional[int] = None) -> Dict[str, Any]:
        """Calculates running totals and weekly volume targets for a given year."""
        current_year = year or datetime.date.today().year
        start_date = f"{current_year}-01-01"
        activities = self.get_activities(start_date=start_date, limit=500)
        from collections import defaultdict
        
        discipline_totals = defaultdict(lambda: {"count": 0, "km": 0.0, "hours": 0.0})
        total_running_km = 0.0
        total_running_count = 0

        for a in activities:
            t = a.get("type", "unknown")
            km = a.get("distance_km", 0.0) or 0.0
            hrs = (a.get("duration_min", 0.0) or 0.0) / 60.0
            discipline_totals[t]["count"] += 1
            discipline_totals[t]["km"] += km
            discipline_totals[t]["hours"] += hrs

            if any(k in t.lower() for k in ["run", "treadmill", "trail", "track"]):
                total_running_km += km
                total_running_count += 1

        today = datetime.date.today()
        end_of_year = datetime.date(current_year, 12, 31)
        days_remaining = max(1, (end_of_year - today).days)
        weeks_remaining = days_remaining / 7.0
        remaining_km = max(0.0, target_annual_km - total_running_km)
        req_weekly_km = remaining_km / weeks_remaining

        return {
            "year": current_year,
            "total_running_km": round(total_running_km, 2),
            "total_running_count": total_running_count,
            "disciplines": {k: {"km": round(v["km"], 2), "count": v["count"], "hours": round(v["hours"], 1)} for k, v in discipline_totals.items()},
            "target_annual_km": target_annual_km,
            "remaining_km": round(remaining_km, 2),
            "days_remaining": days_remaining,
            "weeks_remaining": round(weeks_remaining, 2),
            "required_weekly_km": round(req_weekly_km, 2)
        }

def main():
    if len(sys.argv) < 2:
        print("Usage: mcp_client.py [sync|today|vitals|volume [target_km]|last-run|activities [limit]]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    client = GarminMCPClient()

    if cmd == "sync":
        res = client.sync(refresh=True)
        print(json.dumps(res, indent=2))
    elif cmd == "today":
        res = client.get_today()
        print(json.dumps(res, indent=2))
    elif cmd == "vitals":
        vitals = {
            "today": client.get_today(),
            "hrv": client.get_hrv(),
            "sleep": client.get_sleep(days=2),
            "training_load": client.get_training_load()
        }
        print(json.dumps(vitals, indent=2))
    elif cmd == "volume":
        target = float(sys.argv[2]) if len(sys.argv) > 2 else 1500.0
        vol = client.calc_running_volume(target_annual_km=target)
        print(json.dumps(vol, indent=2))
    elif cmd == "last-run":
        detail = client.get_activity_detail(last=True)
        print(json.dumps(detail, indent=2))
    elif cmd == "activities":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        acts = client.get_activities(limit=limit)
        print(json.dumps(acts, indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
