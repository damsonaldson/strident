#!/usr/bin/env python3
"""
Dynamic Workout Generator & Garmin Connect Dispatcher.
Builds structured running workouts and uploads/schedules them to Garmin Connect.

Reads Garmin OAuth2 token from:
1. --token-file argument
2. GARMIN_TOKEN_FILE environment variable
3. ~/.garmin/oauth2_token.json (default fallback)
"""

import os
import sys
import json
import httpx
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_TOKEN_PATH = Path.home() / ".garmin" / "oauth2_token.json"

def parse_pace_to_mps(pace_str: str) -> float:
    """Converts 'MM:SS' pace per kilometer to meters per second (m/s)."""
    try:
        parts = pace_str.strip().split(":")
        minutes = int(parts[0])
        seconds = int(parts[1]) if len(parts) > 1 else 0
        total_seconds = (minutes * 60) + seconds
        if total_seconds <= 0:
            raise ValueError()
        return 1000.0 / total_seconds
    except Exception:
        raise ValueError(f"Invalid pace format '{pace_str}'. Expected 'MM:SS' (e.g., '4:10').")

def get_di_token(token_path_str: Optional[str] = None) -> str:
    path = Path(token_path_str) if token_path_str else Path(os.getenv("GARMIN_TOKEN_FILE", str(DEFAULT_TOKEN_PATH)))
    if not path.exists():
        print(f"❌ Error: Garmin token file not found at {path}")
        print("Please authenticate or export your Garmin OAuth token to ~/.garmin/oauth2_token.json")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        token = data.get("di_token") or data.get("access_token")
        if not token:
            print(f"❌ Error: Neither 'di_token' nor 'access_token' found in {path}")
            sys.exit(1)
        return token
    except Exception as e:
        print(f"❌ Error reading token file {path}: {e}")
        sys.exit(1)

def build_interval_workout(
    name: str,
    reps: int,
    distance_m: float,
    pace_slow_str: str,
    pace_fast_str: str,
    recovery_sec: float,
    warmup_m: float = 2000.0,
    cooldown_m: float = 1500.0,
    description: str = ""
) -> Dict[str, Any]:
    slow_mps = parse_pace_to_mps(pace_slow_str)
    fast_mps = parse_pace_to_mps(pace_fast_str)

    # Ensure slow boundary <= fast boundary in m/s (slower pace has lower m/s)
    target_low_mps = min(slow_mps, fast_mps)
    target_high_mps = max(slow_mps, fast_mps)

    steps = []
    step_order = 1

    # 1. Warmup
    if warmup_m > 0:
        steps.append({
            "type": "ExecutableStepDTO",
            "stepOrder": step_order,
            "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance", "displayOrder": 3, "displayable": True},
            "endConditionValue": float(warmup_m),
            "preferredEndConditionUnit": {"unitId": 2, "unitKey": "kilometer", "factor": 100000.0},
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
            "description": f"Warmup ({int(warmup_m)}m easy progressive)"
        })
        step_order += 1

    # 2. Repeat Group
    repeat_steps = [
        {
            "type": "ExecutableStepDTO",
            "stepOrder": step_order + 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance", "displayOrder": 3, "displayable": True},
            "endConditionValue": float(distance_m),
            "preferredEndConditionUnit": {"unitId": 2, "unitKey": "kilometer", "factor": 100000.0},
            "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone", "displayOrder": 6},
            "targetValueOne": target_low_mps,
            "targetValueTwo": target_high_mps,
            "description": f"Interval ({int(distance_m)}m @ {pace_fast_str}-{pace_slow_str}/km)"
        },
        {
            "type": "ExecutableStepDTO",
            "stepOrder": step_order + 2,
            "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": True},
            "endConditionValue": float(recovery_sec),
            "preferredEndConditionUnit": {"unitId": 2, "unitKey": "kilometer", "factor": 100000.0},
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
            "description": f"Active Jog Recovery ({int(recovery_sec)}s)"
        }
    ]

    steps.append({
        "type": "RepeatGroupDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6},
        "numberOfIterations": reps,
        "workoutSteps": repeat_steps,
        "endCondition": {"conditionTypeId": 7, "conditionTypeKey": "iterations", "displayOrder": 7, "displayable": False},
        "endConditionValue": float(reps),
        "smartRepeat": False
    })
    step_order += 3

    # 3. Cooldown
    if cooldown_m > 0:
        steps.append({
            "type": "ExecutableStepDTO",
            "stepOrder": step_order,
            "stepType": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance", "displayOrder": 3, "displayable": True},
            "endConditionValue": float(cooldown_m),
            "preferredEndConditionUnit": {"unitId": 2, "unitKey": "kilometer", "factor": 100000.0},
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
            "description": f"Cooldown ({int(cooldown_m)}m easy flush)"
        })

    desc = description or f"{reps}x {int(distance_m)}m @ {pace_fast_str}-{pace_slow_str}/km with {int(recovery_sec)}s active jog recovery."

    return {
        "sportType": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
        "workoutName": name,
        "description": desc,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
                "workoutSteps": steps,
            }
        ],
    }

async def dispatch_workout_to_garmin(workout_payload: Dict[str, Any], schedule_date: str, token_path: Optional[str] = None):
    di_token = get_di_token(token_path)

    headers = {
        "Authorization": f"Bearer {di_token}",
        "di-backend": "connectapi.garmin.com",
        "User-Agent": "GarminConnect/4.75",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
    }

    upload_url = "https://connectapi.garmin.com/workout-service/workout"
    async with httpx.AsyncClient(timeout=15.0) as client:
        print(f"Uploading '{workout_payload['workoutName']}' to Garmin Connect...")
        res = await client.post(upload_url, json=workout_payload, headers=headers)
        if res.status_code in [200, 201]:
            data = res.json()
            wid = data.get("workoutId") or data.get("id")
            print(f"✓ Workout uploaded successfully! (Workout ID: {wid})")

            schedule_url = f"https://connectapi.garmin.com/workout-service/schedule/{wid}"
            sched_res = await client.post(schedule_url, json={"date": schedule_date}, headers=headers)
            if sched_res.status_code in [200, 201]:
                print(f"✓ Scheduled on Garmin Connect Calendar for {schedule_date}!")
            else:
                print(f"⚠️ Schedule notice ({sched_res.status_code}): {sched_res.text}")
        else:
            print(f"❌ Upload failed ({res.status_code}): {res.text}")

def main():
    parser = argparse.ArgumentParser(description="Build and push structured workouts to Garmin Connect")
    parser.add_argument("--name", default="AI Coach: Interval Session", help="Workout title")
    parser.add_argument("--reps", type=int, default=6, help="Number of interval repetitions")
    parser.add_argument("--distance", type=float, default=1000.0, help="Interval distance in meters")
    parser.add_argument("--pace-fast", default="4:05", help="Fast pace boundary MM:SS /km")
    parser.add_argument("--pace-slow", default="4:10", help="Slow pace boundary MM:SS /km")
    parser.add_argument("--recovery-sec", type=float, default=75.0, help="Recovery jog duration in seconds")
    parser.add_argument("--warmup-m", type=float, default=2000.0, help="Warmup distance in meters")
    parser.add_argument("--cooldown-m", type=float, default=1500.0, help="Cooldown distance in meters")
    parser.add_argument("--description", default="", help="Custom workout description")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Target calendar date YYYY-MM-DD")
    parser.add_argument("--token-file", default=None, help="Custom path to oauth2_token.json")
    parser.add_argument("--json-file", default=None, help="Path to raw custom workout JSON payload")

    args = parser.parse_args()

    if args.json_file:
        with open(args.json_file, "r", encoding="utf-8") as f:
            workout_payload = json.load(f)
    else:
        workout_payload = build_interval_workout(
            name=args.name,
            reps=args.reps,
            distance_m=args.distance,
            pace_slow_str=args.pace_slow,
            pace_fast_str=args.pace_fast,
            recovery_sec=args.recovery_sec,
            warmup_m=args.warmup_m,
            cooldown_m=args.cooldown_m,
            description=args.description
        )

    asyncio.run(dispatch_workout_to_garmin(workout_payload, schedule_date=args.date, token_path=args.token_file))

if __name__ == "__main__":
    main()
