#!/usr/bin/env python3
"""
Physiological Zone & Pace Calculator for Running.
Computes Heart Rate training zones (Karvonen & %HRmax) and estimated training paces
based on Max HR, Resting HR, and a recent 5K or 10K benchmark time.
"""

import sys
import json
import argparse
from typing import Dict, Any

def format_pace(seconds_per_km: float) -> str:
    mins = int(seconds_per_km // 60)
    secs = int(round(seconds_per_km % 60))
    if secs == 60:
        mins += 1
        secs = 0
    return f"{mins}:{secs:02d}"

def calculate_hr_zones(max_hr: int, resting_hr: int = 50) -> Dict[str, Dict[str, Any]]:
    # Karvonen Heart Rate Reserve (HRR) formula: Target HR = ((max_hr − rest_hr) × %intensity) + rest_hr
    hrr = max_hr - resting_hr
    return {
        "Zone 1 (Active Recovery)": {
            "hr_range": f"{round(resting_hr + hrr * 0.50)}–{round(resting_hr + hrr * 0.60)} bpm",
            "intensity": "50–60% HRR (<68% HRmax)",
            "adaptation": "Circulatory flush, active recovery"
        },
        "Zone 2 (Aerobic Base)": {
            "hr_range": f"{round(resting_hr + hrr * 0.60)}–{round(resting_hr + hrr * 0.70)} bpm",
            "intensity": "60–70% HRR (68–78% HRmax)",
            "adaptation": "Mitochondrial biogenesis, lipid metabolism"
        },
        "Zone 3 (Steady / Marathon)": {
            "hr_range": f"{round(resting_hr + hrr * 0.70)}–{round(resting_hr + hrr * 0.80)} bpm",
            "intensity": "70–80% HRR (79–87% HRmax)",
            "adaptation": "Glycogen economy, sustained aerobic power"
        },
        "Zone 4 (Threshold / LT2)": {
            "hr_range": f"{round(resting_hr + hrr * 0.80)}–{round(resting_hr + hrr * 0.90)} bpm",
            "intensity": "80–90% HRR (88–92% HRmax)",
            "adaptation": "Lactate clearance capacity"
        },
        "Zone 5 (VO2 Max / Speed)": {
            "hr_range": f"{round(resting_hr + hrr * 0.90)}–{max_hr} bpm",
            "intensity": "90–100% HRR (93–100% HRmax)",
            "adaptation": "Maximum oxygen uptake, neuromuscular turnover"
        }
    }

def calculate_pace_zones(benchmark_dist_km: float, time_str: str) -> Dict[str, str]:
    parts = time_str.strip().split(":")
    if len(parts) == 3:
        total_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        total_sec = int(parts[0]) * 60 + float(parts[1])
    else:
        raise ValueError("Time must be MM:SS or HH:MM:SS")

    race_pace_sec = total_sec / benchmark_dist_km

    # Approximate 10K threshold pace baseline
    if benchmark_dist_km == 5.0:
        # 10K pace is roughly 5K pace + 10-15s/km
        lt_pace_sec = race_pace_sec + 12.0
    elif benchmark_dist_km == 10.0:
        lt_pace_sec = race_pace_sec
    elif benchmark_dist_km == 21.0975:
        lt_pace_sec = race_pace_sec - 10.0
    else:
        lt_pace_sec = race_pace_sec

    return {
        "Zone 1 (Recovery)": f"> {format_pace(lt_pace_sec + 90)} /km",
        "Zone 2 (Easy / Aerobic)": f"{format_pace(lt_pace_sec + 75)} – {format_pace(lt_pace_sec + 45)} /km",
        "Zone 3 (Steady / Marathon)": f"{format_pace(lt_pace_sec + 35)} – {format_pace(lt_pace_sec + 15)} /km",
        "Zone 4 (Threshold / LT2)": f"{format_pace(lt_pace_sec + 5)} – {format_pace(lt_pace_sec - 5)} /km",
        "Zone 5 (VO2 Max)": f"{format_pace(lt_pace_sec - 15)} – {format_pace(lt_pace_sec - 35)} /km"
    }

def main():
    parser = argparse.ArgumentParser(description="Calculate personalized HR and Pace zones")
    parser.add_argument("--max-hr", type=int, required=True, help="Maximum Heart Rate in bpm")
    parser.add_argument("--resting-hr", type=int, default=50, help="Resting Heart Rate in bpm")
    parser.add_argument("--dist-km", type=float, default=10.0, help="Benchmark race distance in km (e.g., 5.0 or 10.0)")
    parser.add_argument("--time", type=str, default="", help="Benchmark race time (e.g., '40:00' or '19:30')")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    hr_zones = calculate_hr_zones(args.max_hr, args.resting_hr)
    pace_zones = calculate_pace_zones(args.dist_km, args.time) if args.time else {}

    output = {"hr_zones": hr_zones, "pace_zones": pace_zones}

    if args.json:
        print(json.dumps(output, indent=2))
        return

    print("\n===============================")
    print("   AI COACH TRAINING ZONES")
    print("===============================\n")
    print(f"Athlete Parameters: Max HR: {args.max_hr} bpm | Resting HR: {args.resting_hr} bpm")
    if args.time:
        print(f"Benchmark: {args.dist_km} km in {args.time}")
    print("\n--- Heart Rate Zones (Karvonen HRR) ---")
    for z, data in hr_zones.items():
        print(f"• {z:<28}: {data['hr_range']:<16} ({data['intensity']})")

    if pace_zones:
        print("\n--- Calibrated Pace Zones ---")
        for z, p in pace_zones.items():
            print(f"• {z:<28}: {p}")
    print()

if __name__ == "__main__":
    main()
