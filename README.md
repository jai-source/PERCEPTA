# PERCEPTA

To install once and start the complete application:

```powershell
npm run install
npm run dev
```

PERCEPTA is a Perceptual Computing Interface (PCI) prototype. It converts face/head movement, hand gestures, and browser voice commands into normalized perceptual events, then sends those events through an interaction engine.

```text
Camera + microphone
        |
        v
React browser UI -- WebSocket --> FastAPI backend
                                      |
                         YOLO + gesture processing
                                      |
                              normalized events
                                      |
                         browser or OS interaction
```

## Quick Start: Windows

Requirements:

- Windows 10 or newer
- Python 3.11 or newer
- Node.js 18 or newer
- Chrome or Edge for microphone recognition
- Webcam and microphone
- Internet access on the first run for Python packages and YOLO weights

From PowerShell, install dependencies and cached model weights once:

```powershell
npm run install
```

Then start both services with one command from the project folder:

```powershell
cd C:\Users\Jai\Desktop\PERCEPTA
npm run dev
```

The launcher validates local weights, starts both services, waits for readiness, prints the backend model/WebSocket status and frontend URL, then opens two service windows:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Backend API docs: http://localhost:8000/docs

Open `http://localhost:5173` and allow camera and microphone permissions.

On later runs, the launcher reuses the existing virtual environment, `node_modules`, and `models/` checkpoints. Use `npm run build` for the frontend production bundle.

### Observed performance diagnosis

- Model downloads were not recurring: all four nano checkpoints were already cached in `models/` (about 6–21 MB each). The provider fallback could still ask Ultralytics to download a missing model, so it now fails clearly instead of downloading outside the cache.
- The cold first inference was the startup hitch: cached provider construction measured 0.11–0.22 seconds, while an un-warmed first inference measured 1.25 seconds. Startup now loads providers from the local cache and warms pose, hand, and face paths before accepting connections. The measured warmup cost was about 1.4–2.0 seconds and made the next inference about 13 ms.
- The old frame path used a 20 FPS timer and base64 JPEG JSON messages. The response gate prevented an unbounded server queue, but capture still wasted work while a frame was in flight. The new path uses 12 FPS, 640x480-or-smaller binary JPEG frames, and one outstanding request.
- Gesture smoothing is bounded at `SMOOTH_WINDOW=5`, `GESTURE_CONFIRMATION_FRAMES=3`, and `GESTURE_COOLDOWN=0.5`; those values are reasonable for a 10–15 FPS stream and were not the five-second cause.

## Stop the Application

Close the backend and frontend PowerShell windows, or press `Ctrl+C` in each service window.

## Manual Startup

Use this when you want to see each service separately.

### Backend

```powershell
cd C:\Users\Jai\Desktop\PERCEPTA\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ..\scripts\download_models.py
python main.py
```

### Frontend

Open a second PowerShell window:

```powershell
cd C:\Users\Jai\Desktop\PERCEPTA\frontend
npm install
npm run dev
```

Important: `npm run dev` must be run inside `frontend`. The repository root does not contain an npm `dev` script.

## What the Prototype Does

### Face and head

- Tracks the active person over time using bounding-box continuity.
- Detects head movement from frame displacement.
- Applies dead-zone filtering, moving average smoothing, exponential smoothing, and `K_HEAD` sensitivity.
- Maps head movement to the local OS cursor in Windows mode.
- Exposes face confidence, head deltas, active user, and tracking lock to the dashboard.

### Hand

- Automatically downloads the HaGRID YOLOv10n gesture detector as `models/yolov8n-hand.pt`.
- Reports hand model status at runtime.
- Maps supported detector labels into PERCEPTA events:
  - `HAND_OPEN`
  - `HAND_FIST`
  - `HAND_POINT`
  - `HAND_PINCH`
  - `THUMB_UP`
  - `THUMB_DOWN`
- Applies temporal confirmation and cooldown.
- Accumulates hand movement across frames for swipe direction events.
- Maps pointing to cursor movement and pinch to a click in local OS mode.

The hand checkpoint source is the HaGRID project model mirror:

```text
https://rndml-team-cv.obs.ru-moscow-1.hc.sbercloud.ru/datasets/hagrid_v2/models/YOLOv10n_gestures.pt
```

The model is downloaded automatically by `scripts/download_models.py`. Do not manually rename or replace it with a box-only hand detector.

### Voice

Voice recognition runs in the browser through the Web Speech API. Supported commands include:

- `click`
- `double click`
- `right click`
- `scroll up`
- `scroll down`
- `go left`
- `go right`
- `go up`
- `go down`
- `go back`
- `go forward`
- `stop`
- `pause`
- `resume`

The browser sends the transcript to the backend. The backend normalizes it into a `PerceptualEvent` and dispatches the corresponding interaction action.

Chrome and Edge provide the best Web Speech API support. Firefox may provide camera access but does not reliably provide browser speech recognition.

## Browser Mode and Windows Mode

A normal browser cannot move the host operating-system cursor by itself.

PERCEPTA therefore has two interaction modes:

- `windows`: the local Python backend uses PyAutoGUI for cursor, click, scroll, and keyboard actions.
- `browser`: the backend remains usable for remote/browser-only deployments, but OS cursor control is not available.

Set the mode in `backend/.env`:

```text
PERCEPTA_INTERACTION_MODE=windows
```

Use `browser` when the backend is remote or when OS-level control is not wanted.

## Configuration

Copy `.env.example` to `backend/.env` if the launcher has not already done so. Important settings:

| Setting | Default | Purpose |
|---|---:|---|
| `PERCEPTA_K_HEAD` | `3.0` | Head cursor sensitivity |
| `PERCEPTA_DEAD_ZONE` | `4.0` | Ignore small head movement |
| `PERCEPTA_ALPHA` | `0.35` | Exponential smoothing factor |
| `PERCEPTA_SMOOTH_WINDOW` | `5` | Moving-average window |
| `PERCEPTA_GESTURE_CONFIDENCE_THRESHOLD` | `0.65` | Gesture confidence threshold |
| `PERCEPTA_GESTURE_CONFIRMATION_FRAMES` | `3` | Frames needed to confirm a gesture |
| `PERCEPTA_GESTURE_COOLDOWN` | `0.5` | Delay between repeated gesture actions |
| `PERCEPTA_TARGET_FPS` | `20` | Camera frame target |
| `PERCEPTA_DEVICE` | `auto` | CUDA when available, otherwise CPU |
| `PERCEPTA_INTERACTION_MODE` | `windows` | `windows`, `linux`, `macos`, or `browser` |

The React Settings page also exposes interaction parameters and sends updates over WebSocket.

## Dashboard

The React dashboard provides:

- Live camera preview
- Face and hand tracking state
- Current gesture and confidence
- Active-user lock and multiple-user warning
- Voice command events
- Normalized event stream
- FPS and inference latency
- CPU/CUDA device information
- Face and hand model load status
- Calibration, Settings, Gestures, Telemetry, and About pages

The dashboard does not generate demo telemetry. Event rows are populated from backend WebSocket results or browser voice recognition.

## Project Structure

```text
PERCEPTA/
├── backend/
│   ├── api/                 FastAPI routes and WebSocket endpoint
│   ├── calibration/         Calibration storage and logic
│   ├── events/              PerceptualEvent, normalization, event bus
│   ├── gestures/            Face, hand, voice, and temporal logic
│   ├── interaction/         Browser and OS adapters
│   ├── perception/          YOLO providers and frame processing
│   ├── tracking/            Active-user tracking
│   ├── config.py            Environment-backed configuration
│   └── main.py              FastAPI application
├── frontend/
│   ├── src/pages/           Dashboard and application pages
│   ├── src/hooks/           Camera, voice, and WebSocket hooks
│   ├── src/services/        Frame, voice, and WebSocket services
│   ├── src/store/           Zustand application state
│   └── vite.config.ts       Dev server and backend proxy
├── models/                  Downloaded YOLO checkpoints
├── config/                  Default JSON configuration
├── scripts/
│   ├── download_models.py   Model download and validation
│   └── run_percepta.ps1     One-command Windows launcher
└── tests/                   Backend tests
```

## Event Contract

All modalities are converted into the same event shape:

```json
{
  "event_type": "HAND_PINCH",
  "modality": "HAND",
  "timestamp": 0,
  "confidence": 0.91,
  "payload": {},
  "source_user_id": 0
}
```

Examples include:

```text
HEAD_MOVE_LEFT
HEAD_NOD
EYEBROW_RAISE
BLINK
HAND_OPEN
HAND_FIST
HAND_POINT
HAND_PINCH
HAND_SWIPE_LEFT
HAND_SWIPE_RIGHT
HAND_SWIPE_UP
HAND_SWIPE_DOWN
THUMB_UP
THUMB_DOWN
VOICE_CLICK
VOICE_SCROLL_DOWN
VOICE_GO_BACK
VOICE_STOP
```

## WebSocket Flow

The frontend connects to:

```text
ws://localhost:8000/ws
```

Camera messages contain base64 JPEG frames:

```json
{
  "type": "frame",
  "data": "base64-jpeg-data",
  "timestamp": 0
}
```

Voice messages contain the browser transcript:

```json
{
  "type": "voice",
  "command": "VOICE_CLICK",
  "transcript": "click",
  "confidence": 0.95
}
```

The backend responds with perception data, model status, cursor state, and normalized events.

## Testing

Install test dependencies in the selected Python environment, then run:

```powershell
cd C:\Users\Jai\Desktop\PERCEPTA
python -m pytest tests/test_backend.py -q
```

The test suite covers:

- Event creation and event types
- Head dead-zone and smoothing math
- Cursor clamping
- Temporal confirmation and cooldown
- Voice command normalization
- Active-user tracking
- Sticky multi-user behavior
- YOLO result normalization

Frontend build check:

```powershell
cd C:\Users\Jai\Desktop\PERCEPTA\frontend
npm run build
```

## Troubleshooting

### `npm run dev` says Missing script

You are in the repository root. Run it inside `frontend`:

```powershell
cd frontend
npm run dev
```

### `localhost` refuses connection

Check that a Vite window is running and that port `5173` is listening. Restart with:

```powershell
cd C:\Users\Jai\Desktop\PERCEPTA\frontend
npm run dev
```

Then open `http://localhost:5173`.

### Camera or microphone is denied

Use Chrome or Edge, click the lock/camera icon beside the address bar, allow camera and microphone access, and reload the page.

### Hand model is unavailable

Run:

```powershell
cd C:\Users\Jai\Desktop\PERCEPTA
python scripts\download_models.py
```

Check that `models\yolov8n-hand.pt` exists and is several megabytes in size. The dashboard reports the actual hand model status; it does not silently claim that hand tracking is active.

### OS cursor does not move

Set this in `backend/.env`:

```text
PERCEPTA_INTERACTION_MODE=windows
```

Run the backend locally on the same Windows machine. Browser security prevents a remote browser page from controlling the host cursor directly.

## Privacy

Camera frames are processed in memory by the local backend and are not recorded by default. Browser voice recognition uses the browser's speech recognition implementation. PERCEPTA does not intentionally store camera or microphone recordings.

## License and Model Notes

PERCEPTA project code is maintained as a university PBL prototype. The YOLO and HaGRID model files are third-party assets and remain subject to their respective project licenses and usage terms. Review those terms before redistribution or commercial deployment.
