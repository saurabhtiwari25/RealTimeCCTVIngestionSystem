# Argus Eye: Real-Time IP Surveillance Video Streaming Platform

A lightweight, robust, and production-structured MVP for real-time surveillance/IP camera ingestion, multi-camera live grid monitoring, health tracking with automatic reconnection, and on-demand stream recording.

Built with **Python 3.11+**, **Streamlit**, **MediaMTX**, **FFmpeg**, and **PostgreSQL**.

---

## 1. Project Overview

Surveillance cameras broadcast video over RTSP (Real-Time Streaming Protocol). Because modern web browsers do not natively support RTSP, streaming IP cameras directly to web applications typically requires either heavy, latency-inducing transcoding or proprietary browser plugins.

**Argus Eye** bridges this gap:
1. It ingests H.264/H.265 RTSP feeds via **MediaMTX**.
2. Remuxes them on-the-fly into browser-compatible **WebRTC** (ultra-low latency: ~200-400ms) and **HLS** (maximum compatibility fallback).
3. Embeds live feeds directly in a modern **Streamlit** dashboard.
4. Manages camera metadata and status persistently in **PostgreSQL**.
5. Manages stream recordings on-demand with **FFmpeg** using zero-CPU stream copy passthrough.

---

## 2. Key Features

- **Multi-Camera Grid**: View simultaneous live camera feeds in a responsive grid.
- **Sub-Second WebRTC & Fallback HLS**: Seamless switching between low-latency WebRTC and robust HLS.
- **Zero Browser RTSP Violations**: Strictly follows browser video standards via MediaMTX remuxing.
- **RTSP Connection Diagnostics**: Built-in testing tool probing reachability, codecs, and resolution before saving cameras.
- **Health Telemetry & Auto-Reconnect**: Detects stream dropouts and reconnects using exponential backoff without infinite tight loops.
- **Safe FFmpeg Recording**: Subprocess-isolated recordings saved sequentially as `recordings/camera_<id>/YYYY-MM-DD/recording_001.mp4`.
- **Credential Protection**: Automatic credential masking in logs and UI (never exposes camera passwords).
- **Test Stream Simulator**: Built-in synthetic test pattern generator to verify pipelines without physical IP cameras.
- **Commercial Camera Matrix**: Technical documentation and URL formats for Hikvision, Dahua, Axis, TP-Link VIGI, and Reolink.

---

## 3. Tech Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend & UI** | **Streamlit** (Python) | Reactive web dashboard, multi-camera grid layout, dynamic device management & health telemetry |
| **Media Server** | **MediaMTX** (Go) | Zero-dependency RTSP/WebRTC/HLS media gateway with dynamic REST control API |
| **Streaming Protocols** | **WebRTC**, **HLS**, **RTSP** | Sub-second latency live feeds (`WebRTC`), fallback streaming (`HLS`), IP camera ingestion (`RTSP`) |
| **Media Processing** | **FFmpeg** & **FFprobe** | Lossless stream recording (`-c copy`), RTSP stream validation/probing, and synthetic camera simulation |
| **Backend & Core** | **Python 3.11+** | Stream health monitoring, exponential backoff reconnection, asynchronous process management |
| **Database & ORM** | **PostgreSQL** & **SQLAlchemy** | Relational persistence for camera configurations, credentials, and telemetry status |
| **Containerization** | **Docker** & **Docker Compose** | Multi-service orchestration (`surveillance_streamlit`, `surveillance_mediamtx`, `surveillance_postgres`) |
| **Cloud Deployment** | **Railway** | Production-ready cloud deployment with healthchecks and auto-recovery |

---

## 4. Architecture & Data Flow

```
+-----------------------------------------------------------+
|               IP Surveillance Cameras (Real)              |
|        Hikvision / Dahua / Axis / TP-Link / Reolink       |
|                or FFmpeg Simulator (Test)                 |
+-----------------------------+-----------------------------+
                              |
                              | RTSP (TCP / UDP)
                              v
+-----------------------------------------------------------+
|                 MediaMTX Streaming Server                 |
|  - Ingests RTSP streams (:8554)                           |
|  - Exposes WebRTC WHEP / HTML player (:8889)              |
|  - Exposes HLS fMP4 / m3u8 player (:8888)                 |
|  - Dynamic path management via REST API (:9997)           |
+---------------------+-------------------------------+-----+
                      |                               |
        WebRTC Stream | (Sub-Second Latency)          | HLS (Fallback)
                      v                               v
+-----------------------------------------------------------+
|                     Streamlit Web UI                      |
|  - Dashboard: Multi-camera grid & controls                |
|  - Cameras: CRUD, credential forms, connection test       |
|  - Recordings: File browser, playback & download          |
|  - System Health: Connectivity telemetry & backoff state  |
+---------------------+-------------------------------+-----+
                      |                               |
                      | SQLAlchemy                    | Subprocess
                      v                               v
+---------------------+-----+   +---------------------+-----+
|        PostgreSQL         |   |    FFmpeg Recorder        |
|  - Cameras metadata       |   |  - Stream copy (-c copy)  |
|  - Status & last_seen     |   |  - Saves to recordings/   |
+---------------------------+   +---------------------------+
```

---

## 4. Port Allocation

| Port | Service | Protocol | Description |
| :--- | :--- | :--- | :--- |
| **8501** | Streamlit | HTTP | Main web interface and surveillance console |
| **8554** | MediaMTX | RTSP (TCP/UDP) | Camera RTSP ingestion and stream proxy |
| **8889** | MediaMTX | HTTP / WebRTC | Browser WebRTC playback and WHEP negotiation |
| **8189** | MediaMTX | UDP | WebRTC ICE candidate negotiation |
| **8888** | MediaMTX | HTTP / HLS | Browser HLS segmented streaming |
| **9997** | MediaMTX | HTTP | MediaMTX REST API for dynamic stream paths |
| **5432** | PostgreSQL | TCP | Camera metadata and operational status storage |

---

## 5. Project Structure

```
simplest camera/
├── app/
│   ├── streamlit_app.py          # Main entrypoint & multipage navigation
│   ├── pages/
│   │   ├── dashboard.py          # Multi-camera live grid & system metrics
│   │   ├── cameras.py            # Add/Edit/Delete cameras & RTSP probe
│   │   ├── recordings.py         # Browse, preview, and download recordings
│   │   └── system_health.py      # Telemetry & service status matrix
│   ├── components/
│   │   ├── camera_card.py        # Isolated card with player & controls
│   │   ├── video_player.py       # WebRTC & HLS browser player component
│   │   └── status_badge.py       # Visual status & recording indicators
│   ├── services/
│   │   ├── camera_service.py     # Database CRUD & input validation
│   │   ├── stream_service.py     # MediaMTX REST API path management
│   │   ├── recording_service.py  # FFmpeg recording subprocess controller
│   │   └── health_service.py     # Health checks & backoff reconnect
│   ├── database/
│   │   ├── database.py           # Engine setup & fallback handling
│   │   └── models.py             # SQLAlchemy Camera entity
│   └── utils/
│       ├── rtsp.py               # RTSP testing, URL parser, snapshot
│       ├── config.py             # Application settings from .env
│       └── logging_config.py     # Password-redacting log formatter
├── streaming/
│   ├── mediamtx.yml              # MediaMTX configuration
│   ├── simulator.py              # Synthetic RTSP camera generator
│   └── README.md                 # MediaMTX technical notes
├── recordings/
│   └── .gitkeep                  # Recording storage root
├── tests/
│   ├── test_camera.py            # Unit tests for camera CRUD
│   ├── test_stream.py            # Unit tests for stream service & RTSP
│   ├── test_health.py            # Unit tests for health & reconnect
│   ├── test_recording.py         # Unit tests for recording service
│   └── camera_test_matrix.md     # 5 commercial camera test specifications
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container definition (Python + FFmpeg)
├── docker-compose.yml            # Multi-service stack definition
├── .env.example                  # Environment configuration template
├── .gitignore
└── README.md
```

---

## 6. Quick Start (Docker Compose)

The easiest way to run the entire platform is with Docker Compose.

### Step 1: Clone & Configure
```bash
cp .env.example .env
```

### Step 2: Launch Stack
```bash
docker compose up --build -d
```

### Step 3: Access Application
- **Surveillance UI**: [http://localhost:8501](http://localhost:8501)
- **MediaMTX WebRTC Stream**: `http://localhost:8889/<path>/`
- **MediaMTX HLS Stream**: `http://localhost:8888/<path>/`

---

## 7. Local Development Setup (Without Docker)

### Prerequisites
- Python 3.11+
- FFmpeg installed in system PATH
- MediaMTX binary or container
- PostgreSQL (or automatic fallback to SQLite)

### Step 1: Set Up Virtual Environment
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Run MediaMTX
Download and run the MediaMTX binary with our config:
```bash
mediamtx streaming/mediamtx.yml
```
*(Or run just MediaMTX via Docker: `docker run --rm -it -p 8554:8554 -p 8888:8888 -p 8889:8889 -p 9997:9997 -v ${PWD}/streaming/mediamtx.yml:/mediamtx.yml bluenviron/mediamtx`)*

### Step 3: Launch Streamlit
```bash
streamlit run app/streamlit_app.py
```

---

## Simulated Camera (Testing Without Hardware)

If you do not have physical IP cameras available on your local network, start the built-in simulator:

```bash
python streaming/simulator.py
```

1. In the Streamlit dashboard, click **" Add Simulated Test Camera"** on the Dashboard or add it manually:
   - **Name**: `Simulated Camera 01`
   - **IP Address**: `127.0.0.1`
   - **RTSP URL**: `rtsp://localhost:8554/simulated_cam`
2. Click **Start Stream**.
3. The live test pattern with a real-time running digital clock will stream directly into the browser.
4. Click **Record** to test the recording pipeline and view the resulting MP4 in the **Recordings** page.

---

## Adding a Real Commercial IP Camera

Go to the **Cameras** page and fill out the form:

1. **Camera Name**: Descriptive identifier (e.g., `Office Back Entrance`).
2. **IP Address**: The camera's static IP address on your LAN (e.g., `192.168.1.108`).
3. **Username & Password**: Camera administrative or ONVIF credentials.
4. **RTSP Stream URL**:
   - **Hikvision**: `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`
   - **Dahua**: `rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0`
   - **Axis**: `rtsp://root:password@192.168.1.90:554/axis-media/media.amp`
   - **TP-Link VIGI**: `rtsp://admin:password@192.168.1.120:554/stream1`
   - **Reolink**: `rtsp://admin:password@192.168.1.150:554/h264Preview_01_main`
5. Click **" Test Connection First"** to probe the camera before saving.
6. Click **"💾 Save Camera"**.



# MediaMTX Streaming Server

MediaMTX is an ultra-lightweight, zero-dependency RTSP, WebRTC, and HLS media server written in Go. In this platform, it acts as the bridge between RTSP cameras and web browsers.

---

## Port Allocation

| Port | Protocol | Purpose | Access |
| :--- | :--- | :--- | :--- |
| **8554** | RTSP (TCP/UDP) | Camera RTSP ingestion & publishing | Internal / Network |
| **8889** | HTTP / WebRTC | Browser WebRTC player & WHEP endpoint | Client Browser |
| **8888** | HTTP / HLS | Browser HLS streaming (`index.m3u8` & player) | Client Browser |
| **9997** | HTTP / REST API | Path configuration, stream control & diagnostics | Streamlit App |
| **8189** | UDP | WebRTC ICE candidate negotiation | Client Browser |

---

## Dynamic Stream Architecture

1. **RTSP Source**: A physical camera or FFmpeg simulator publishes/serves an RTSP stream (e.g., `rtsp://cam-ip:554/stream1`).
2. **Path Registration**: The Streamlit `stream_service.py` calls the MediaMTX API:
   ```bash
   POST http://mediamtx:9997/v3/config/paths/add/cam_{id}
   {
     "source": "rtsp://camera_ip:554/stream1",
     "sourceOnDemand": false,
     "rtspTransport": "tcp"
   }
   ```
3. **Browser Playback**:
   - **WebRTC**: Low latency (~300ms–500ms):
     `http://localhost:8889/cam_{id}/`
   - **HLS**: High compatibility fallback:
     `http://localhost:8888/cam_{id}/`
4. **Stream Deregistration**:
   When stopping a stream:
   ```bash
   DELETE http://mediamtx:9997/v3/config/paths/delete/cam_{id}
   ```

---




##  The Only Requirement

Your computer (the Docker host) must be on the **same local network** as the cameras. The typical setup is:

```
[CCTV Camera] ---(Ethernet/WiFi)--- [Router/Switch] ---(LAN)--- [Your PC running Docker]
```

Each camera has an IP address (e.g., `192.168.1.64`) assigned by your router or set statically via the camera's config tool.

---

##  RTSP URL Formats for Each Brand

### 1. CP Plus

CP Plus cameras (very popular in India) use these RTSP paths:

```
Main Stream (HD):    rtsp://admin:password@192.168.1.64:554/cam/realmonitor?channel=1&subtype=0
Sub Stream (SD):     rtsp://admin:password@192.168.1.64:554/cam/realmonitor?channel=1&subtype=1
```

| Field | Default Value |
|---|---|
| Username | `admin` |
| Password | Set during first setup (often the device serial number or a custom password) |
| Port | `554` |
| Protocol | `TCP` (recommended) |

> [!TIP]
> CP Plus cameras use the **Dahua protocol** internally. If the above URL doesn't work, try the Dahua format below — they're interchangeable.

---

### 2. Hikvision (India)

```
Main Stream (HD):    rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101
Sub Stream (SD):     rtsp://admin:password@192.168.1.64:554/Streaming/Channels/102
Third Stream:        rtsp://admin:password@192.168.1.64:554/Streaming/Channels/103
```

For **NVR** (multi-channel):
```
Channel 1 Main:      rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101
Channel 1 Sub:       rtsp://admin:password@192.168.1.64:554/Streaming/Channels/102
Channel 2 Main:      rtsp://admin:password@192.168.1.64:554/Streaming/Channels/201
Channel 3 Main:      rtsp://admin:password@192.168.1.64:554/Streaming/Channels/301
```

Pattern: `/Streaming/Channels/{channel}{stream}` where channel = `1,2,3...` and stream = `01` (main), `02` (sub)

| Field | Default Value |
|---|---|
| Username | `admin` |
| Password | Set during activation (Hikvision requires activation via SADP tool first) |
| Port | `554` |
| Protocol | `TCP` |

---

### 3. Dahua (India)

```
Main Stream (HD):    rtsp://admin:password@192.168.1.64:554/cam/realmonitor?channel=1&subtype=0
Sub Stream (SD):     rtsp://admin:password@192.168.1.64:554/cam/realmonitor?channel=1&subtype=1
```

For **NVR**:
```
Channel 2 Main:      rtsp://admin:password@192.168.1.64:554/cam/realmonitor?channel=2&subtype=0
Channel 3 Sub:       rtsp://admin:password@192.168.1.64:554/cam/realmonitor?channel=3&subtype=1
```

| Field | Default Value |
|---|---|
| Username | `admin` |
| Password | Set during first setup |
| Port | `554` |
| Protocol | `TCP` |

---

### 4. Godrej Security Solutions

Godrej cameras are typically OEM Hikvision or Dahua internally. Try **both** URL formats:

```
If Hikvision OEM:    rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101
If Dahua OEM:        rtsp://admin:password@192.168.1.64:554/cam/realmonitor?channel=1&subtype=0
Generic ONVIF:       rtsp://admin:password@192.168.1.64:554/onvif1
```

| Field | Default Value |
|---|---|
| Username | `admin` |
| Password | Usually set during initial config |
| Port | `554` |

> [!TIP]
> Use the **"Test Connection"** button in your app's Register Camera form to quickly check which URL format works.

---

### 5. Sparsh (by BSNL/BEL)

Sparsh cameras are typically Hikvision-based:

```
Main Stream:         rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101
Sub Stream:          rtsp://admin:password@192.168.1.64:554/Streaming/Channels/102
Alternative:         rtsp://admin:password@192.168.1.64:554/h264/ch1/main/av_stream
```

| Field | Default Value |
|---|---|
| Username | `admin` |
| Password | Set during setup |
| Port | `554` |

---

### 6. Qubo (by Hero Group)

Qubo smart cameras primarily use WiFi and cloud. RTSP access depends on the model:

```
Common format:       rtsp://admin:password@192.168.1.64:554/stream1
Alternative:         rtsp://admin:password@192.168.1.64:554/live/ch0
Alternative 2:       rtsp://admin:password@192.168.1.64:8554/live
```

| Field | Default Value |
|---|---|
| Username | `admin` |
| Password | Varies — may need to enable RTSP in the Qubo app settings |
| Port | `554` or `8554` |

> [!WARNING]
> Many consumer-grade Qubo cameras (like Smart Cam 360) are **cloud-only** and do **not expose RTSP**. Only their professional/enterprise models support RTSP. Check your model's specs. If yours is cloud-only, RTSP will not work.

---

### 7. Honeywell

```
Main Stream:         rtsp://admin:password@192.168.1.64:554/h264/ch1/main/av_stream
Sub Stream:          rtsp://admin:password@192.168.1.64:554/h264/ch1/sub/av_stream

Alternative (ONVIF): rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101
```

For Honeywell NVR:
```
Channel 2:           rtsp://admin:password@192.168.1.64:554/h264/ch2/main/av_stream
```

| Field | Default Value |
|---|---|
| Username | `admin` |
| Password | Set during setup (Honeywell also uses an activation wizard) |
| Port | `554` |
| Protocol | `TCP` |

---

## 🛠️ Step-by-Step: Adding a Real Camera

### Step 1: Find Your Camera's IP Address

Use one of these methods:
- **Camera's own config tool**: Hikvision SADP, Dahua Config Tool, CP Plus EZConfig
- **Router admin panel**: Check DHCP client list (usually at `192.168.1.1`)
- **Network scan**: Run `nmap -sn 192.168.1.0/24` from your PC

### Step 2: Verify RTSP Port Is Open

From your PC, test if port 554 is reachable:
```powershell
Test-NetConnection -ComputerName 192.168.1.64 -Port 554
```
You should see `TcpTestSucceeded: True`.

### Step 3: Test RTSP URL with FFprobe

```powershell
ffprobe -v error -rtsp_transport tcp -i "rtsp://admin:your_password@192.168.1.64:554/Streaming/Channels/101"
```
If this returns stream info without errors, the URL is correct.

### Step 4: Register in Your App

1. Open **http://localhost:8501** → navigate to **Cameras** page
2. Click the **"Register Camera"** tab
3. Fill in:
   - **Camera Name**: e.g., `Front Gate - Hikvision`
   - **IP Address**: e.g., `192.168.1.64`
   - **Username**: e.g., `admin`
   - **Password**: your camera's password
   - **RTSP URL**: the full URL from the brand-specific format above
   - **Protocol**: `TCP` (recommended for reliability)
4. Click **"Test Connection"** first to verify
5. If test passes, click **"Register Camera"**

### Step 5: Start the Stream

- Go to the **Dashboard** page
- Find your camera card
- Click **"Start Stream"**
- The live feed should appear via WebRTC (or HLS fallback)

---

## Simulated Camera Mode

To test streaming without a physical IP camera:
```bash
python streaming/simulator.py
```
This generates a live video pattern (with timestamp, bouncing clock, and color bars) and publishes it to `rtsp://localhost:8554/simulated_cam`.
MediaMTX automatically serves it on:
- WebRTC: `http://localhost:8889/simulated_cam/`
- HLS: `http://localhost:8888/simulated_cam/`


##  Common Issues & Fixes

| Problem | Cause | Fix |
|---|---|---|
| `Connection refused on port 554` | Camera not on same network, or RTSP disabled | Verify network connectivity; enable RTSP in camera web UI settings |
| `401 Unauthorized` | Wrong username/password | Reset camera password via its web UI (`http://camera-ip`) or config tool |
| `404 Not Found` | Wrong RTSP path | Try alternate URL paths listed for your brand above |
| `Connection timed out` | Firewall blocking, wrong IP | Check camera IP, disable any firewall rules blocking port 554 |
| Stream plays but freezes/lags | Network bandwidth issue, or using UDP on lossy WiFi | Switch to `TCP` protocol; use sub-stream (lower resolution) for WiFi cameras |
| Black video with "WebRTC Live" | MediaMTX couldn't pull from camera | Check Docker logs: `docker logs surveillance_streamlit` and `docker logs surveillance_mediamtx` |


---

## 10. Running Automated Tests

Run the full automated test suite:

```bash
pytest tests/ -v
```

The test suite covers:
- Camera CRUD operations and input validation (`test_camera.py`)
- Stream service URL generation and MediaMTX API calls with mocks (`test_stream.py`)
- RTSP socket probing and error responses (`test_stream.py`)
- Health state transitions and backoff reconnection (`test_health.py`)
- FFmpeg recording subprocess lifecycle and directory structure (`test_recording.py`)

---

## 11. Troubleshooting

| Symptom | Probable Cause | Resolution |
| :--- | :--- | :--- |
| **"MediaMTX is not reachable"** | MediaMTX container or process is not running. | Run `docker compose up -d mediamtx` or check port 9997. |
| **"Connection failed: Port closed / unreachable"** | Camera IP is wrong or port 554 is blocked by firewall. | Verify IP with `ping <camera_ip>` and check camera RTSP settings. |
| **"Authentication failed (401 Unauthorized)"** | Wrong username or password for camera. | Recheck camera credentials; some cameras require separate ONVIF users. |
| **"FFmpeg not found in PATH"** | System does not have FFmpeg installed. | Install FFmpeg via package manager or run within Docker Compose. |
| **Stream player shows "Stream Unavailable"** | Stream was stopped or MediaMTX is still negotiating RTSP handshake. | Click "Start Stream" and wait ~2 seconds for initial keyframe. |

---

## 12. Security & Performance Notes

- **Credential Masking**: All passwords in RTSP URLs are sanitized in database views and log outputs (`rtsp://user:***@host`).
- **Stream Passthrough**: Recording uses FFmpeg `-c copy` to remux packets without re-encoding, consuming minimal CPU.
- **Production Notice**: This is an MVP. For production deployment:
  - Enforce HTTPS and WSS for WebRTC streams.
  - Enable database password encryption at rest.
  - Isolate the camera network VLAN from public internet access.
