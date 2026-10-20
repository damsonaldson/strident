#!/usr/bin/env python3
"""
Physiological Zone & Pace Calculator for Running.
Computes Heart Rate training zones (Karvonen HRR, %HRmax, and Friel %LTHR) and
Jack Daniels VDOT training paces from either a direct --vdot score or a race benchmark.
"""

import sys
import math
import json
import argparse
from typing import Dict, Any, Optional, Tuple


def format_pace(seconds_per_km: float) -> str:
    mins = int(seconds_per_km // 60)
    secs = int(round(seconds_per_km % 60))
    if secs == 60:
        mins += 1
        secs = 0
    return f"{mins}:{secs:02d}"


def parse_time_to_seconds(time_str: str) -> float:
    parts = time_str.strip().split(":")
    try:
        if len(parts) == 3:
            total_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            total_sec = int(parts[0]) * 60 + float(parts[1])
        else:
            raise ValueError()
    except ValueError:
        raise ValueError(f"Invalid time '{time_str}'. Expected MM:SS or HH:MM:SS.")
    if total_sec <= 0:
        raise ValueError("Benchmark time must be greater than zero.")
    return total_sec


def compute_vdot_from_race(dist_km: float, total_seconds: float) -> float:
    """
    Jack Daniels / Jimmy Gilbert VDOT regression equation:
    VO2(v) = -4.60 + 0.182258 * v + 0.000104 * v^2
    %VO2max(t) = 0.8 + 0.1894393 * e^(-0.012778 * t) + 0.2989558 * e^(-0.1932605 * t)
    where v is velocity in meters/minute and t is duration in minutes.
    """
    if dist_km <= 0:
        raise ValueError("Distance must be greater than zero.")
    t_min = total_seconds / 60.0
    d_meters = dist_km * 1000.0
    v_m_per_min = d_meters / t_min

    vo2 = -4.60 + (0.182258 * v_m_per_min) + (0.000104 * (v_m_per_min ** 2))
    pct_vo2max = (
        0.8
        + 0.1894393 * math.exp(-0.012778 * t_min)
        + 0.2989558 * math.exp(-0.1932605 * t_min)
    )
    return round(vo2 / pct_vo2max, 2)


def vdot_intensity_to_sec_per_km(vdot: float, pct_vdot: float) -> float:
    """
    Inverts the Daniels/Gilbert oxygen cost quadratic for target VO2 = vdot * pct_vdot:
    0.000104 * v^2 + 0.182258 * v - (4.60 + target_vo2) = 0
    Returns pace in seconds per kilometer.
    """
    target_vo2 = vdot * pct_vdot
    a = 0.000104
    b = 0.182258
    c = -(4.60 + target_vo2)
    discriminant = (b ** 2) - (4.0 * a * c)
    v_m_per_min = (-b + math.sqrt(discriminant)) / (2.0 * a)
    return (1000.0 / v_m_per_min) * 60.0


def calculate_pace_zones_from_vdot(vdot: float) -> Dict[str, str]:
    """Calculates Jack Daniels & Bakken-aligned training pace zones from a VDOT score."""
    if vdot <= 15 or vdot > 95:
        raise ValueError(f"VDOT {vdot} is outside physiological bounds (15–95).")

    z1_slow = vdot_intensity_to_sec_per_km(vdot, 0.59)
    z2_slow = vdot_intensity_to_sec_per_km(vdot, 0.65)
    z2_fast = vdot_intensity_to_sec_per_km(vdot, 0.74)
    z3_slow = vdot_intensity_to_sec_per_km(vdot, 0.78)
    z3_fast = vdot_intensity_to_sec_per_km(vdot, 0.83)
    z4a_slow = vdot_intensity_to_sec_per_km(vdot, 0.86)
    z4a_fast = vdot_intensity_to_sec_per_km(vdot, 0.89)
    z4b_slow = vdot_intensity_to_sec_per_km(vdot, 0.91)
    z4b_fast = vdot_intensity_to_sec_per_km(vdot, 0.94)
    z5_slow = vdot_intensity_to_sec_per_km(vdot, 0.96)
    z5_fast = vdot_intensity_to_sec_per_km(vdot, 1.00)
    rep_slow = vdot_intensity_to_sec_per_km(vdot, 1.05)
    rep_fast = vdot_intensity_to_sec_per_km(vdot, 1.10)

    return {
        "Zone 1 (Recovery / E-)": f"> {format_pace(z1_slow)} /km",
        "Zone 2 (Easy / Aerobic E)": f"{format_pace(z2_slow)} – {format_pace(z2_fast)} /km",
        "Zone 3 (Steady / Marathon M)": f"{format_pace(z3_slow)} – {format_pace(z3_fast)} /km",
        "Zone 4a (Sub-Threshold / LT2 T)": f"{format_pace(z4a_slow)} – {format_pace(z4a_fast)} /km (45-60s walk/stand rest)",
        "Zone 4b (Critical Velocity / 10K CV)": f"{format_pace(z4b_slow)} – {format_pace(z4b_fast)} /km (90-120s easy walk/jog rest)",
        "Zone 5 (VO2 Max / Interval I)": f"{format_pace(z5_slow)} – {format_pace(z5_fast)} /km (2:00-2:30 jog rest)",
        "Zone 6 (Anaerobic Repetition R)": f"{format_pace(rep_slow)} – {format_pace(rep_fast)} /km (full recovery)",
    }


def calculate_hr_zones(
    max_hr: Optional[int] = None,
    resting_hr: int = 50,
    lthr: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Computes HR zones via Karvonen HRR (if max_hr is provided) and/or Friel %LTHR (if lthr is provided).
    """
    if max_hr is not None:
        if max_hr <= resting_hr or max_hr < 100 or max_hr > 240:
            raise ValueError("Invalid --max-hr / --resting-hr values.")
        hrr = max_hr - resting_hr
        return {
            "Zone 1 (Active Recovery)": {
                "hr_range": f"{round(resting_hr + hrr * 0.50)}–{round(resting_hr + hrr * 0.60)} bpm",
                "intensity": "50–60% HRR (<68% HRmax)",
                "adaptation": "Circulatory flush, active recovery",
            },
            "Zone 2 (Aerobic Base)": {
                "hr_range": f"{round(resting_hr + hrr * 0.60)}–{round(resting_hr + hrr * 0.70)} bpm",
                "intensity": "60–70% HRR (68–78% HRmax)",
                "adaptation": "Mitochondrial biogenesis, lipid metabolism",
            },
            "Zone 3 (Steady / Marathon)": {
                "hr_range": f"{round(resting_hr + hrr * 0.70)}–{round(resting_hr + hrr * 0.80)} bpm",
                "intensity": "70–80% HRR (79–87% HRmax)",
                "adaptation": "Glycogen economy, sustained aerobic power",
            },
            "Zone 4 (Threshold / LT2)": {
                "hr_range": f"{round(resting_hr + hrr * 0.80)}–{round(resting_hr + hrr * 0.90)} bpm",
                "intensity": "80–90% HRR (88–92% HRmax)",
                "adaptation": "Lactate clearance capacity",
            },
            "Zone 5 (VO2 Max / Speed)": {
                "hr_range": f"{round(resting_hr + hrr * 0.90)}–{max_hr} bpm",
                "intensity": "90–100% HRR (93–100% HRmax)",
                "adaptation": "Maximum oxygen uptake, neuromuscular turnover",
            },
        }

    if lthr is not None:
        if lthr < 100 or lthr > 220:
            raise ValueError("Invalid --lthr value (expected 100–220 bpm).")
        return {
            "Zone 1 (Active Recovery)": {
                "hr_range": f"< {round(lthr * 0.81)} bpm",
                "intensity": "< 81% LTHR",
                "adaptation": "Circulatory flush, active recovery",
            },
            "Zone 2 (Aerobic Base)": {
                "hr_range": f"{round(lthr * 0.81)}–{round(lthr * 0.89)} bpm",
                "intensity": "81–89% LTHR",
                "adaptation": "Mitochondrial biogenesis, lipid metabolism",
            },
            "Zone 3 (Steady / Marathon)": {
                "hr_range": f"{round(lthr * 0.90)}–{round(lthr * 0.95)} bpm",
                "intensity": "90–95% LTHR",
                "adaptation": "Glycogen economy, sustained aerobic power",
            },
            "Zone 4 (Threshold / LT2)": {
                "hr_range": f"{round(lthr * 0.96)}–{round(lthr * 1.00)} bpm",
                "intensity": "96–100% LTHR",
                "adaptation": "Lactate clearance capacity",
            },
            "Zone 5 (VO2 Max / Speed)": {
                "hr_range": f"> {round(lthr * 1.00)} bpm",
                "intensity": "101–106%+ LTHR",
                "adaptation": "Maximum oxygen uptake, neuromuscular turnover",
            },
        }

    return {}


def main():
    parser = argparse.ArgumentParser(description="Calculate personalized HR and Jack Daniels VDOT Pace zones")
    parser.add_argument("--max-hr", type=int, default=None, help="Maximum Heart Rate in bpm")
    parser.add_argument("--resting-hr", type=int, default=50, help="Resting Heart Rate in bpm (default: 50)")
    parser.add_argument("--lthr", type=int, default=None, help="Lactate Threshold Heart Rate in bpm")
    parser.add_argument("--vdot", type=float, default=None, help="Direct Jack Daniels VDOT score (e.g., 52.5)")
    parser.add_argument("--dist-km", type=float, default=10.0, help="Benchmark race distance in km (default: 10.0)")
    parser.add_argument("--time", type=str, default="", help="Benchmark race time (e.g., '40:00' or '19:30')")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    if args.max_hr is None and args.lthr is None and args.vdot is None and not args.time:
        parser.error("Provide at least one input: --max-hr, --lthr, --vdot, or --time (with --dist-km).")

    try:
        hr_zones = calculate_hr_zones(max_hr=args.max_hr, resting_hr=args.resting_hr, lthr=args.lthr)

        vdot_score: Optional[float] = args.vdot
        if vdot_score is None and args.time:
            total_sec = parse_time_to_seconds(args.time)
            vdot_score = compute_vdot_from_race(args.dist_km, total_sec)

        pace_zones = calculate_pace_zones_from_vdot(vdot_score) if vdot_score is not None else {}
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    output: Dict[str, Any] = {
        "vdot": vdot_score,
        "hr_zones": hr_zones,
        "pace_zones": pace_zones,
    }

    if args.json:
        print(json.dumps(output, indent=2))
        return

    print("\n===============================")
    print("   STRIDENT TRAINING ZONES")
    print("===============================\n")
    if args.max_hr:
        print(f"HR Parameters : Max HR: {args.max_hr} bpm | Resting HR: {args.resting_hr} bpm")
    elif args.lthr:
        print(f"HR Parameters : LTHR: {args.lthr} bpm")
    if args.time:
        print(f"Race Benchmark: {args.dist_km} km in {args.time} (VDOT: {vdot_score})")
    elif vdot_score is not None:
        print(f"VDOT Benchmark: {vdot_score}")

    if hr_zones:
        method = "Karvonen HRR" if args.max_hr else "Friel %LTHR"
        print(f"\n--- Heart Rate Zones ({method}) ---")
        for z, data in hr_zones.items():
            print(f"• {z:<28}: {data['hr_range']:<16} ({data['intensity']})")

    if pace_zones:
        print(f"\n--- Calibrated Pace Zones (Jack Daniels VDOT {vdot_score}) ---")
        for z, p in pace_zones.items():
            print(f"• {z:<32}: {p}")
    print()


if __name__ == "__main__":
    main()
