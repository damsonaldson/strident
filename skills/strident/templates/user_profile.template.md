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

| Zone | Name | % HRmax | Target Pace (/km) | Primary Adaptation & Recovery |
| :--- | :--- | :--- | :--- | :--- |
| **Zone 1** | Active Recovery (`Rec`) | < 68% | > <Z1_PACE> | Glycogen replenishment, capillary flush |
| **Zone 2** | Aerobic Base / Easy (`E`) | 68–78% | <Z2_SLOW> – <Z2_FAST> | Mitochondrial density, fat oxidation |
| **Zone 3** | Steady / Marathon Pace (`S`) | 79–85% | <Z3_SLOW> – <Z3_FAST> | Glycogen economy, sustained aerobic power |
| **Zone 4a** | Sub-Threshold / LT2 (`T`) | 86–90% | <Z4A_SLOW> – <Z4A_FAST> | MLSS lactate shuttle (45–60s walk/stand rest) |
| **Zone 4b** | Critical Velocity / 10K (`CV`) | 90–94% | <Z4B_SLOW> – <Z4B_FAST> | 10K pace durability, H+ buffering (90–120s rest) |
| **Zone 5** | Interval / VO2 Max (`I`) | 95–100% | <Z5_SLOW> – <Z5_FAST> | Maximal oxygen uptake, stroke volume (2:00+ jog rest) |

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
