# 🏃‍♂️ Strident for Garmin

> **Agentic run coaching, synced straight to your Garmin.**

An autonomous, feedback-driven running coach that ingests Garmin data, generates adaptive workouts, and pushes scheduled sessions back via Garmin Connect.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Protocol: MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-green.svg)](https://modelcontextprotocol.io/)

---

## ⚡ The Philosophy

* **The Problem:** Static training plans don't know when your sleep score is 45, your HRV is tanked, or your Achilles tendon is stiff. Most AI running assistants either stop at passive data analysis (read-only Strava bots) or require you to manually program 8-step interval workouts on your watch.
* **The Solution:** **Strident** executes a complete closed-loop coaching workflow:
  1. **Audits** overnight vitals (HRV balance, Sleep Score, Training Load) via Garmin MCP.
  2. **Gates** the session based on biometric fatigue and tendinopathy guardrails.
  3. **Formulates** precise interval paces enforcing the "First Rep Brake" and negative split logic.
  4. **Pushes** the structured workout directly to your Garmin watch calendar.
  5. **Debriefs** splits and cardiac drift post-run to dynamically calibrate future volume.

---

## 🛠️ System Architecture

```text
               ┌───────────────────────────────────────┐
               │         Athlete Prompt / CLI          │
               │   ("What's my interval run today?")   │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
               ┌───────────────────────────────────────┐
               │            Strident Engine            │
               │       (Antigravity / Claude Code)     │
               └───────┬───────────────────────▲───────┘
                       │                       │
      1. Query Vitals  │                       │ 3. Dispatch Structured
       (HRV, Sleep)    ▼                       │    Steps (Warmup, Intervals)
               ┌───────────────┐       ┌───────┴───────────────┐
               │  Garmin MCP   │       │  push_workout.py      │
               │ Server (SSE)  │       │ (Garmin Workout API)  │
               └───────┬───────┘       └───────┬───────────────┘
                       │                       │
                       ▼                       ▼
            =================================================
                     GARMIN CONNECT & ATHLETE WATCH
            =================================================
```

---

## 🚀 Quickstart

### 1. Install as an Antigravity / Claude Code Plugin
Install directly from GitHub into your customization directory:
```bash
# In Antigravity:
agy plugin install https://github.com/damsonaldson/strident

# Or clone directly into your workspace:
git clone https://github.com/damsonaldson/strident .agents/plugins/strident
```

### 2. Connect Your Garmin MCP Server
Run any standard Garmin MCP server (such as [eddmann/garmin-connect-mcp](https://github.com/eddmann/garmin-connect-mcp) or [Taxuspt/garmin_mcp](https://github.com/Taxuspt/garmin_mcp)) locally or in Docker:

```bash
docker run -d \
  -p 8085:8085 \
  -e GARMIN_EMAIL="your-email@example.com" \
  -e GARMIN_PASSWORD="your-password" \
  eddmann/garmin-connect-mcp
```

Add the server to your `mcp_config.json`:
```json
{
  "mcpServers": {
    "garmin": {
      "url": "http://localhost:8085/sse"
    }
  }
}
```

### 3. Initialize Your Profile
When you first interact with Strident, it will prompt you to set up your local `user_profile.md` using the included templates:
```bash
# Generate your training zones from a race benchmark or direct VDOT / LTHR:
python3 skills/strident/scripts/calc_zones.py --max-hr 190 --resting-hr 48 --dist-km 10 --time "40:00"
python3 skills/strident/scripts/calc_zones.py --lthr 168 --vdot 52.5
```

---

## 🔒 Security & Privacy (Zero-Leak Architecture)

* **No Credential Storage:** This repository contains zero tokens, secrets, or hardcoded personal credentials.
* **Local-First Data:** All training logs, personal vitals, and race goals remain inside your private local workspace.
* **Direct Watch Push:** The dispatch tool uses standard OAuth tokens stored strictly in your local environment (`~/.garmin/oauth2_token.json` or `$GARMIN_TOKEN_FILE`).

---

## 🧰 Bundled CLI Tools

| Utility | Command | Description |
| :--- | :--- | :--- |
| **Garmin Query Client** | `python3 skills/strident/scripts/mcp_client.py vitals` | Reads HRV, sleep, today's metrics, and training load via MCP |
| **Workout Dispatcher** | `python3 skills/strident/scripts/push_workout.py --name "6x1k" --reps 6 --pace-fast "4:05" --pace-slow "4:10" --schedule-today` | Validates & pushes target workout to Garmin Connect calendar |
| **Zone Calculator** | `python3 skills/strident/scripts/calc_zones.py --lthr 168 --vdot 52.5` | Calculates Karvonen/Friel HR zones & Jack Daniels VDOT pace targets |

---

## 📚 Sports Science Principles

Strident operates as a **Lead Exercise Physiologist & Performance Strategist** grounded in peer-reviewed endurance science (Daniels VDOT, Seiler polarized distribution, Bakken sub-threshold control, Cook & Purdam tendon continuum):
* **Sub-Threshold (`LT2`) vs. Critical Velocity (`CV`) Separation:** Clearly distinguishes 60-minute Lactate Threshold (`Zone 4a LT2`, paired with **45–60s passive/walking rest** to drop HR and offload the Achilles) from 40-minute 10K Race Pace (`Zone 4b CV`, paired with **90–120s easy walk/jog rest**).
* **The First Rep Brake & Grade-Adjusted Intelligence:** Rep 1 of an interval set must start at the slow boundary of the target zone to prevent premature glycolytic acidosis. Uphill splits are evaluated by internal load (HR/Power) rather than raw pace.
* **3-Tier Readiness Gating (Green / Amber / Red):** Evaluates 7-day rolling HRV trend, RHR delta, ACWR, and morning tendon stiffness (`0–10`)—applying **Minimum Effective Dose (MED)** scaling levers on Amber days (`3/10` stiffness or single-night poor sleep) and full recovery pivots on Red days ($\ge 4/10$).
* **Velocity-Normalized Biomechanics & Tendon Remodeling:** Evaluates cadence, Ground Contact Time (`GCT`), and Vertical Ratio (`VR`) relative to running speed, paired with high-drop ($\ge 8.5\text{ mm}$) base trainers and daily analgesic neutral isometric holds.

---

## 📄 License
MIT License. Free for runners, coaches, and open-source contributors.
