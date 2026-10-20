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
# Or generate your training zones instantly from the CLI:
python3 skills/strident/scripts/calc_zones.py --max-hr 190 --resting-hr 48 --dist-km 10 --time "40:00"
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
| **Garmin Query Client** | `python3 scripts/mcp_client.py vitals` | Reads HRV, sleep, today's metrics, and training load via MCP |
| **Workout Dispatcher** | `python3 scripts/push_workout.py --name "6x1k" --reps 6 --pace-fast "4:05" --pace-slow "4:10"` | Pushes target workout to Garmin Connect calendar |
| **Zone Calculator** | `python3 skills/strident/scripts/calc_zones.py --max-hr 185 --dist-km 5 --time "19:30"` | Calculates Karvonen HR zones & Jack Daniels pace targets |

---

## 📚 Sports Science Principles

Strident operates under strict biomechanical and physiological rules:
* **The First Rep Brake:** Rep 1 of an interval set must start at the slowest pace boundary to prevent premature lactate flooding. Negative splitting is enforced.
* **Active Aerobic Recovery:** Continuous jogging between intervals to accelerate lactate clearance and prevent recovery creep.
* **Tendon Stiffness Gating:** Morning stiffness $\ge 4/10$ automatically converts quality intervals into Zone 1/2 recovery.
* **Heel-to-Toe Drop Strategy:** High-drop trainers ($\ge 8\text{ mm}$) mandated for recovery volume to offload the Achilles tendon.

---

## 📄 License
MIT License. Free for runners, coaches, and open-source contributors.
