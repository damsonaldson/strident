# Athlete Profile

## 1. Physiological Profile
- **Age:** <AGE>
- **Resting Heart Rate (RHR):** <RHR_BPM> bpm
- **Max Heart Rate (HRmax):** <MAX_HR_BPM> bpm
- **Lactate Threshold Heart Rate (LTHR):** <LTHR_BPM> bpm (~88–92% HRmax)
- **Lactate Threshold Pace:** <MM:SS> /km
- **Current VDOT / Fitness Benchmark:** <BENCHMARK_TIME_AND_DISTANCE> (e.g., 5K in 19:30 or 10K in 40:00)

---

## 2. Calculated Heart Rate & Pace Zones
*(Calibrated via `scripts/calc_zones.py` or Jack Daniels VDOT)*

| Zone | Name | % HRmax | Target Pace (/km) | Primary Adaptation |
| :--- | :--- | :--- | :--- | :--- |
| **Zone 1** | Active Recovery | < 68% | > <Z1_PACE> | Glycogen replenishment, active flush |
| **Zone 2** | Aerobic Base / Easy | 68–78% | <Z2_SLOW> – <Z2_FAST> | Mitochondrial density, fat oxidation |
| **Zone 3** | Steady / Marathon Pace | 79–87% | <Z3_SLOW> – <Z3_FAST> | Glycogen economy, sustained aerobic power |
| **Zone 4** | Threshold / Tempo (LT2) | 88–92% | <Z4_SLOW> – <Z4_FAST> | Lactate clearance capacity |
| **Zone 5** | Interval / VO2 Max | 93–98% | <Z5_SLOW> – <Z5_FAST> | Maximum oxygen uptake, stroke volume |

---

## 3. Shoe Quiver & Drop Strategy
| Shoe Model | Category | Heel-to-Toe Drop | Primary Use Case |
| :--- | :--- | :--- | :--- |
| *Example: Nike Pegasus / Brooks Ghost* | Daily Trainer | 10 mm | Easy runs, recovery, long base runs |
| *Example: Saucony Endorphin Speed* | Tempo / Interval Trainer | 8 mm | Threshold intervals, progression runs |
| *Example: Nike Vaporfly / Saucony Endorphin Elite* | Race Day / Carbon Racer | 8 mm | Target races, periodic time trials |

---

## 4. Injury History & Guardrails
- **Vulnerable Tissues:** <e.g., Achilles tendon, Plantar fascia, Shin splints, None>
- **Morning Stiffness Protocol:** Rate stiffness on a 1–10 scale. Any score $\ge 4/10$ forces conversion of hard sessions to easy spin or rest.
- **Strength Maintenance:** <e.g., Heavy Slow Resistance (HSR) calf raises 3x/week, Single-leg squats>
- **Terrain Guardrails:** Flat track or tarmac for threshold; soft non-technical trails for recovery; avoid steep descents (>6%).
