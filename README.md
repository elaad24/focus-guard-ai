# Focus Guard AI

A **local-only** AI procrastination warning system. It monitors your webcam and computer activity to detect likely distraction (especially phone use and idle time), calculates a distraction score, and triggers staged warnings before a final persistent alert.

This is **not** a task manager, Pomodoro app, or productivity dashboard. It is a standalone monitoring and alarm component designed to run in parallel with your existing task dashboard.

## Privacy

- Everything runs locally on your machine
- No cloud APIs
- No image/video upload
- No raw camera frames saved by default (`saveRawVideo: false`)
- Keyboard/mouse monitoring records **timestamps only** — never key content
- WebSocket and REST API bind to localhost only

The only external network activity on first run is Ultralytics downloading the YOLOv8n weights (`yolov8n.pt`) once, cached locally afterward.

## Architecture

```
Webcam (OpenCV) + YOLO + MediaPipe  →  objective signals
Keyboard/Mouse (pynput, timestamps)  →  idle detection
Signals + mode rules                 →  distraction score + focus score
State machine                        →  soft / medium / final alerts
WebSocket                            →  React dashboard
```

**Important design rule:** YOLO/MediaPipe detect objective signals (person, phone, head pose, hands). The app logic computes procrastination risk — the vision model never directly classifies "procrastination."

## Requirements

- macOS (tested target; active-window monitor uses AppKit)
- Python **3.12** (recommended via Homebrew or pyenv)
- Node.js 18+
- Webcam
- macOS permissions: **Camera**, **Accessibility** (for global keyboard/mouse listeners)

### Install Python 3.12 (if missing)

```bash
brew install python@3.12
# or
pyenv install 3.12.8
```

## Setup

### Backend

```bash
cd focus-guard-ai/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd focus-guard-ai/frontend
npm install
```

### Windows

Prerequisites: **Python 3.12**, **Node.js 18+**, PowerShell 5.1+ (or PowerShell 7).

From the project root:

```powershell
cd focus-guard-ai
npm run dev
```

`npm run dev` automatically installs missing root, frontend, and backend dependencies on first run.

Or use the helper script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

This starts:
- Backend at **http://127.0.0.1:8787**
- Frontend at **http://127.0.0.1:5700**

If PowerShell blocks scripts, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

(`npm run dev` also passes `-ExecutionPolicy Bypass` for the backend launcher.)

**Windows permissions**

- **Camera** — allow in your browser when prompted (browser camera is the default source).
- **Keyboard/mouse idle** — `pynput` global listeners may require running the terminal as Administrator on some setups.

**Windows limitations (no platform-specific code yet)**

- Active window shows `unsupported` (macOS AppKit only today).
- Desktop notifications use macOS `osascript` only; dashboard alerts and sounds still work.

## Run

You can run backend and frontend together from **one terminal**, or start them separately.

### Run both (recommended)

From the project root:

```bash
cd focus-guard-ai
npm run dev
```

On first run, `npm run dev` installs missing root, frontend, and backend dependencies automatically.

Or use the helper script:

```bash
cd focus-guard-ai
bash scripts/dev.sh
```

This starts:
- Backend at **http://127.0.0.1:8787**
- Frontend at **http://127.0.0.1:5700**

Press `Ctrl+C` once to stop both.

### Run separately

#### Backend (port 8787)

```bash
cd focus-guard-ai/backend
source .venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8787
```

#### Frontend (port 5700)

```bash
cd focus-guard-ai/frontend
npm run dev
```

Open the dashboard: **http://127.0.0.1:5700**

API docs: **http://127.0.0.1:8787/docs**

## macOS Permissions

1. **Camera** — System Settings → Privacy & Security → Camera → allow Terminal or your IDE
2. **Accessibility** — required for `pynput` global input listeners (keyboard/mouse activity timestamps)

## Configuration

Settings live in `backend/config.json` and can be changed from the dashboard Settings panel.

| Field | Default | Description |
|-------|---------|-------------|
| `mode` | `normal` | Active mode: `normal`, `video_lesson`, `ipad`, `break` |
| `softWarningAfterSeconds` | 45 | Visual-only soft warning after score above threshold |
| `mediumWarningAfterSeconds` | 60 | Stronger warning + optional short beep |
| `finalAlertAfterSeconds` | 90 | Persistent sound + modal (before 2 minutes by default) |
| `phoneUsageLimitSeconds` | 90 | Extra score weight after phone near person this long |
| `keyboardMouseIdleLimitSeconds` | 60 | Idle threshold for keyboard/mouse |
| `procrastinationScoreThreshold` | 70 | Distraction score threshold |
| `cooldownAfterDismissSeconds` | 120 | Cooldown after dismissing final alert |
| `soundEnabled` | true | Enable alert sounds |
| `notificationsEnabled` | true | macOS desktop notifications on final alert |
| `debugMode` | true | Verbose backend behavior |
| `saveRawVideo` | false | Not implemented — frames are never saved |

## Modes

| Mode | Behavior |
|------|----------|
| **Normal** | Standard rules; phone + idle are suspicious |
| **Video Lesson** | Less weight on keyboard idle and looking away; phone still suspicious |
| **iPad** | Tablet usage allowed; phone still suspicious; reduced idle/head-down weight when tablet visible |
| **Break** | Alerts disabled; passive monitoring and stats continue |

## Distraction score (signal weights)

| Signal | Weight |
|--------|--------|
| Phone near person | +40 |
| Phone near hand/face | +30 |
| Head looking down | +20 |
| Looking away from screen | +15 |
| Keyboard/mouse idle over limit | +20 |
| Body/hand idle (with KB idle) | +10 |
| No person detected | 0 (not counted as procrastination) |
| iPad mode + tablet detected | -25 |

Mode-specific multipliers adjust these weights.

## Warning & alert flow

```
Score >= threshold (continuous)
  ├─ 45s → DISTRACTION_WARNING_SOFT (dashboard visual only)
  ├─ 60s → DISTRACTION_WARNING_MEDIUM (stronger visual + short beep)
  └─ 90s → ALERT_ACTIVE (looping sound + modal + notification)

User clicks "I'm back" → DISMISSED_COOLDOWN (120s default)
Score drops below threshold for 2s → FOCUSED
```

During cooldown, signals are still tracked but new alerts are suppressed.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health |
| GET | `/settings` | Current config |
| POST | `/settings` | Update config |
| GET | `/state` | Full state snapshot |
| POST | `/mode` | Change mode |
| POST | `/alert/dismiss` | Dismiss final alert |
| GET | `/session-summary` | Session stats |
| POST | `/session/reset` | Reset session counters |
| POST | `/calibration/screen-zone` | Save screen zone rectangle |
| WS | `/ws/status` | Live status stream (~5 Hz) |

## Project structure

```
focus-guard-ai/
  backend/
    main.py
    config.json
    requirements.txt
    detection/     # camera, YOLO, MediaPipe face/hands, screen zone
    activity/      # keyboard/mouse timestamps, active window
    logic/         # scores, state machine, session tracker, modes
    alerts/        # sound + notifications
    api/           # REST + WebSocket
    assets/        # alert.wav (auto-generated on first run)
  frontend/
    src/
      components/  # 8 dashboard panels
      api/         # WebSocket hook + REST helpers
      styles/      # dark glass UI theme
```

## Future improvements

- Custom YOLO model for phone/tablet distinction
- Screen-zone calibration UI
- Active-window distraction heuristics
- SQLite session history
- Daily/weekly focus analytics
- Local API integration with your separate task dashboard

## License

Local personal use project. No cloud dependencies.
