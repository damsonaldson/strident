#!/usr/bin/env python3
"""
Dynamic Workout Generator & Garmin Connect Dispatcher.
Builds structured running workouts, validates them against the Garmin Connect
workout schema, and uploads/schedules them to Garmin Connect using stdlib HTTP.

Reads Garmin OAuth2 token from:
1. --token-file argument
2. GARMIN_TOKEN_FILE environment variable
3. ~/.garmin/oauth2_token.json (default fallback)
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

DEFAULT_TOKEN_PATH = Path.home() / ".garmin" / "oauth2_token.json"
HTTP_TIMEOUT_SEC = 15

VALID_STEP_TYPES = {"warmup", "cooldown", "interval", "recovery", "rest", "repeat"}
VALID_CONDITION_KEYS = {"lap.button", "time", "distance", "iterations", "heart.rate", "calories"}


def parse_pace_to_mps(pace_str: str) -> float:
    """Converts 'MM:SS' pace per kilometer to meters per second (m/s)."""
    try:
        parts = pace_str.strip().split(":")
        if len(parts) != 2:
            raise ValueError()
        minutes = int(parts[0])
        seconds = int(parts[1])
        if minutes < 0 or seconds < 0 or seconds >= 60:
            raise ValueError()
        total_seconds = (minutes * 60) + seconds
        if total_seconds <= 0:
            raise ValueError()
        return 1000.0 / total_seconds
    except Exception:
        raise ValueError(f"Invalid pace format '{pace_str}'. Expected 'MM:SS' (e.g., '4:10').")


def get_di_token(token_path_str: Optional[str] = None) -> str:
    path = Path(token_path_str) if token_path_str else Path(os.getenv("GARMIN_TOKEN_FILE", str(DEFAULT_TOKEN_PATH)))
    path = path.expanduser()
    if not path.exists():
        print(f"Error: Garmin token file not found at {path}", file=sys.stderr)
        print("Please authenticate or export your Garmin OAuth token to ~/.garmin/oauth2_token.json", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        token = data.get("di_token") or data.get("access_token")
        if not token:
            print(f"Error: Neither 'di_token' nor 'access_token' found in {path}", file=sys.stderr)
            sys.exit(1)
        return token
    except Exception as e:
        print(f"Error reading token file {path}: {e}", file=sys.stderr)
        sys.exit(1)


def _validate_steps(steps: List[Dict[str, Any]], path: str = "workoutSteps") -> None:
    if not isinstance(steps, list) or len(steps) == 0:
        raise ValueError(f"'{path}' must be a non-empty list of workout steps.")

    for idx, step in enumerate(steps):
        step_path = f"{path}[{idx}]"
        if not isinstance(step, dict):
            raise ValueError(f"{step_path} must be a JSON object.")

        dto_type = step.get("type")
        if dto_type not in ("ExecutableStepDTO", "RepeatGroupDTO"):
            raise ValueError(f"{step_path}.type must be 'ExecutableStepDTO' or 'RepeatGroupDTO' (got {dto_type!r}).")

        step_type = step.get("stepType")
        if not isinstance(step_type, dict) or step_type.get("stepTypeKey") not in VALID_STEP_TYPES:
            raise ValueError(f"{step_path}.stepType.stepTypeKey must be one of {sorted(VALID_STEP_TYPES)}.")

        if dto_type == "RepeatGroupDTO":
            iters = step.get("numberOfIterations")
            if not isinstance(iters, int) or iters < 1:
                raise ValueError(f"{step_path}.numberOfIterations must be a positive integer.")
            _validate_steps(step.get("workoutSteps", []), path=f"{step_path}.workoutSteps")
        else:
            end_cond = step.get("endCondition")
            if not isinstance(end_cond, dict) or end_cond.get("conditionTypeKey") not in VALID_CONDITION_KEYS:
                raise ValueError(f"{step_path}.endCondition.conditionTypeKey must be one of {sorted(VALID_CONDITION_KEYS)}.")
            cond_key = end_cond.get("conditionTypeKey")
            if cond_key in ("time", "distance"):
                val = step.get("endConditionValue")
                if not isinstance(val, (int, float)) or val <= 0:
                    raise ValueError(f"{step_path}.endConditionValue must be > 0 for condition '{cond_key}'.")

            target_type = step.get("targetType")
            if not isinstance(target_type, dict) or "workoutTargetTypeKey" not in target_type:
                raise ValueError(f"{step_path}.targetType.workoutTargetTypeKey is required.")
            if target_type.get("workoutTargetTypeKey") == "pace.zone":
                low = step.get("targetValueOne")
                high = step.get("targetValueTwo")
                if not isinstance(low, (int, float)) or not isinstance(high, (int, float)) or low <= 0 or high < low:
                    raise ValueError(
                        f"{step_path} pace.zone requires 0 < targetValueOne <= targetValueTwo (in m/s)."
                    )


def validate_workout_payload(payload: Dict[str, Any]) -> None:
    """Validates a workout payload against the Garmin Connect Workout Schema."""
    if not isinstance(payload, dict):
        raise ValueError("Workout payload must be a JSON object.")

    name = payload.get("workoutName")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Workout payload requires a non-empty 'workoutName' string.")

    sport = payload.get("sportType")
    if not isinstance(sport, dict) or not sport.get("sportTypeKey"):
        raise ValueError("Workout payload requires a valid 'sportType' object with 'sportTypeKey'.")

    segments = payload.get("workoutSegments")
    if not isinstance(segments, list) or len(segments) == 0:
        raise ValueError("Workout payload requires a non-empty 'workoutSegments' list.")

    for idx, seg in enumerate(segments):
        if not isinstance(seg, dict):
            raise ValueError(f"workoutSegments[{idx}] must be a JSON object.")
        _validate_steps(seg.get("workoutSteps", []), path=f"workoutSegments[{idx}].workoutSteps")


def build_interval_workout(
    name: str,
    reps: int,
    distance_m: float,
    pace_slow_str: str,
    pace_fast_str: str,
    recovery_sec: float,
    warmup_m: float = 2000.0,
    cooldown_m: float = 1500.0,
    description: str = "",
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
            "description": f"Warmup ({int(warmup_m)}m easy progressive)",
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
            "description": f"Interval ({int(distance_m)}m @ {pace_fast_str}-{pace_slow_str}/km)",
        },
        {
            "type": "ExecutableStepDTO",
            "stepOrder": step_order + 2,
            "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": True},
            "endConditionValue": float(recovery_sec),
            "preferredEndConditionUnit": {"unitId": 2, "unitKey": "kilometer", "factor": 100000.0},
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
            "description": f"Active Jog Recovery ({int(recovery_sec)}s)",
        },
    ]

    steps.append({
        "type": "RepeatGroupDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6},
        "numberOfIterations": reps,
        "workoutSteps": repeat_steps,
        "endCondition": {"conditionTypeId": 7, "conditionTypeKey": "iterations", "displayOrder": 7, "displayable": False},
        "endConditionValue": float(reps),
        "smartRepeat": False,
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
            "description": f"Cooldown ({int(cooldown_m)}m easy flush)",
        })

    desc = description or f"{reps}x {int(distance_m)}m @ {pace_fast_str}-{pace_slow_str}/km with {int(recovery_sec)}s active jog recovery."

    payload = {
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
    validate_workout_payload(payload)
    return payload


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = HTTP_TIMEOUT_SEC) -> Tuple[int, str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace") if err.fp else str(err)
        return err.code, body


def push_workout(
    workout_payload: Dict[str, Any],
    schedule_date: Optional[str] = None,
    schedule_today: bool = False,
    token_path: Optional[str] = None,
) -> Optional[Any]:
    validate_workout_payload(workout_payload)

    target_date = datetime.now().strftime("%Y-%m-%d") if schedule_today else schedule_date
    if target_date:
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid schedule date '{target_date}'. Expected YYYY-MM-DD.")

    di_token = get_di_token(token_path)
    headers = {
        "Authorization": f"Bearer {di_token}",
        "di-backend": "connectapi.garmin.com",
        "User-Agent": "GarminConnect/4.75",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
    }

    upload_url = "https://connectapi.garmin.com/workout-service/workout"
    print(f"Uploading '{workout_payload['workoutName']}' to Garmin Connect...")
    status, body = _post_json(upload_url, workout_payload, headers)
    if status not in (200, 201):
        print(f"Upload failed ({status}): {body}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(body)
    wid = data.get("workoutId") or data.get("id")
    print(f"Workout uploaded successfully! (Workout ID: {wid})")

    if target_date and wid:
        schedule_url = f"https://connectapi.garmin.com/workout-service/schedule/{wid}"
        sched_status, sched_body = _post_json(schedule_url, {"date": target_date}, headers)
        if sched_status in (200, 201):
            print(f"Scheduled on Garmin Connect Calendar for {target_date}!")
        else:
            print(f"Warning: Schedule notice ({sched_status}): {sched_body}", file=sys.stderr)

    return wid


def main():
    parser = argparse.ArgumentParser(description="Build, validate, and push structured workouts to Garmin Connect")
    parser.add_argument("--name", default="Strident: Interval Session", help="Workout title")
    parser.add_argument("--reps", type=int, default=6, help="Number of interval repetitions")
    parser.add_argument("--distance", type=float, default=1000.0, help="Interval distance in meters")
    parser.add_argument("--pace-fast", default="4:05", help="Fast pace boundary MM:SS /km")
    parser.add_argument("--pace-slow", default="4:10", help="Slow pace boundary MM:SS /km")
    parser.add_argument("--recovery-sec", type=float, default=75.0, help="Recovery jog duration in seconds")
    parser.add_argument("--warmup-m", type=float, default=2000.0, help="Warmup distance in meters")
    parser.add_argument("--cooldown-m", type=float, default=1500.0, help="Cooldown distance in meters")
    parser.add_argument("--description", default="", help="Custom workout description")
    parser.add_argument("--date", default=None, help="Schedule workout on target calendar date YYYY-MM-DD")
    parser.add_argument("--schedule-today", action="store_true", help="Schedule the workout on today's Garmin calendar")
    parser.add_argument("--no-schedule", action="store_true", help="Upload to Garmin workout library without scheduling on calendar")
    parser.add_argument("--token-file", default=None, help="Custom path to oauth2_token.json")
    parser.add_argument("--json-file", default=None, help="Path to custom workout JSON payload (validated before upload)")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the generated JSON payload without uploading")

    args = parser.parse_args()

    try:
        if args.json_file:
            with open(args.json_file, "r", encoding="utf-8") as f:
                workout_payload = json.load(f)
            validate_workout_payload(workout_payload)
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
                description=args.description,
            )

        if args.dry_run:
            print(json.dumps(workout_payload, indent=2))
            return

        schedule_date = None
        if not args.no_schedule:
            if args.schedule_today:
                schedule_date = datetime.now().strftime("%Y-%m-%d")
            elif args.date:
                schedule_date = args.date
            else:
                schedule_date = datetime.now().strftime("%Y-%m-%d")

        push_workout(
            workout_payload,
            schedule_date=schedule_date,
            schedule_today=args.schedule_today and not args.no_schedule,
            token_path=args.token_file,
        )
    except ValueError as err:
        print(f"Validation Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
