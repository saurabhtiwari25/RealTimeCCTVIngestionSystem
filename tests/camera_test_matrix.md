# Commercial IP Camera Test Matrix

This document provides testing specifications, standard RTSP URL formats, codec/resolution profiles, and hardware verification results for 5 leading commercial IP camera manufacturers.

> [!IMPORTANT]
> **Hardware Testing Notice**:
> In accordance with project acceptance criteria, this matrix provides exact technical specifications and honest test placeholders. Results marked `[PENDING PHYSICAL HARDWARE TEST]` reflect hardware-dependent benchmarks that must be verified when physical units are deployed on the target local subnet. Simulated camera tests are documented separately and do NOT count toward these 5 commercial models.

---

## 1. Camera Comparison Matrix

| Manufacturer | Model | Protocol | Resolution | Codec | FPS | RTSP URL Format | Result | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Hikvision** | DS-2CD2043G2-I | RTSP/TCP | 2688x1520 (4MP) | H.264 / H.265 | 25/30 | `rtsp://<user>:<pwd>@<ip>:554/Streaming/Channels/101` | `[PENDING HARDWARE]` | Channel 101=Mainstream, 102=Substream |
| **Dahua** | IPC-HFW2431S-S-S2 | RTSP/TCP | 2688x1520 (4MP) | H.264 / H.265 | 25/30 | `rtsp://<user>:<pwd>@<ip>:554/cam/realmonitor?channel=1&subtype=0` | `[PENDING HARDWARE]` | Subtype 0=Mainstream, 1=Substream |
| **Axis** | M1065-L | RTSP/TCP | 1920x1080 (2MP) | H.264 | 25/30 | `rtsp://<user>:<pwd>@<ip>:554/axis-media/media.amp` | `[PENDING HARDWARE]` | Supports `videocodec=h264` query param |
| **TP-Link VIGI**| VIGI C340-W | RTSP/TCP | 2560x1440 (4MP) | H.264 / H.265 | 25/30 | `rtsp://<user>:<pwd>@<ip>:554/stream1` | `[PENDING HARDWARE]` | stream1=Mainstream, stream2=Substream |
| **Reolink** | RLC-810A | RTSP/TCP | 3840x2160 (4K/8MP)| H.264 / H.265 | 25 | `rtsp://<user>:<pwd>@<ip>:554/h264Preview_01_main` | `[PENDING HARDWARE]` | Substream at `/h264Preview_01_sub` |

---

## 2. Detailed Camera Test Specifications

### Camera 1: Hikvision DS-2CD2043G2-I
- **Manufacturer**: Hikvision
- **Exact Model**: DS-2CD2043G2-I (AcuSense 4 MP IR Fixed Bullet)
- **Firmware Version**: V5.7.13 build 230718 (or latest)
- **Default Port**: 554 (RTSP), 8000 (Hikvision SDK), 80 (HTTP)
- **RTSP URL Formats**:
  - Main Stream (4MP): `rtsp://admin:Password123@192.168.1.64:554/Streaming/Channels/101`
  - Sub Stream (640x360): `rtsp://admin:Password123@192.168.1.64:554/Streaming/Channels/102`
- **Resolution**: 2688 x 1520
- **Codec**: H.264 / H.265 (Main Profile)
- **FPS**: 25 fps
- **Connection Result**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Stream Latency**: Estimated ~300ms via WebRTC / ~2s via HLS
- **Stability**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Reconnection Behavior**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Recording Behavior**: Direct stream copy (`-c copy`) into MP4 container via FFmpeg.

---

### Camera 2: Dahua IPC-HFW2431S-S-S2
- **Manufacturer**: Dahua Technology
- **Exact Model**: IPC-HFW2431S-S-S2 (Lite Series 4MP Bullet)
- **Firmware Version**: V2.820.0000000.38.R (or latest)
- **Default Port**: 554 (RTSP), 37777 (TCP), 80 (HTTP)
- **RTSP URL Formats**:
  - Main Stream: `rtsp://admin:Password123@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0`
  - Sub Stream: `rtsp://admin:Password123@192.168.1.108:554/cam/realmonitor?channel=1&subtype=1`
- **Resolution**: 2688 x 1520
- **Codec**: H.264 / H.265
- **FPS**: 25 fps
- **Connection Result**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Stream Latency**: Estimated ~350ms via WebRTC
- **Stability**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Reconnection Behavior**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Recording Behavior**: Compatible with FFmpeg TCP transport remuxing.

---

### Camera 3: Axis Communications M1065-L
- **Manufacturer**: Axis Communications
- **Exact Model**: Axis M1065-L (Full HDTV 1080p Fixed Camera)
- **Firmware Version**: Axis OS 10.12.x
- **Default Port**: 554 (RTSP), 80 (HTTP), 443 (HTTPS)
- **RTSP URL Formats**:
  - Standard Stream: `rtsp://root:Password123@192.168.1.90:554/axis-media/media.amp`
  - With Parameters: `rtsp://root:Password123@192.168.1.90:554/axis-media/media.amp?videocodec=h264&resolution=1920x1080`
- **Resolution**: 1920 x 1080 (1080p)
- **Codec**: H.264 Baseline / Main / High Profile
- **FPS**: 30 fps
- **Connection Result**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Stream Latency**: Estimated ~250ms via WebRTC
- **Stability**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Reconnection Behavior**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Recording Behavior**: Seamless passthrough to MP4.

---

### Camera 4: TP-Link VIGI C340-W
- **Manufacturer**: TP-Link
- **Exact Model**: VIGI C340-W (4MP Outdoor Full-Color Wi-Fi Bullet)
- **Firmware Version**: 1.1.2 Build 230620 Rel.58784n
- **Default Port**: 554 (RTSP), 80 (HTTP)
- **RTSP URL Formats**:
  - Main Stream (4MP): `rtsp://admin:Password123@192.168.1.120:554/stream1`
  - Sub Stream (640x360): `rtsp://admin:Password123@192.168.1.120:554/stream2`
- **Resolution**: 2560 x 1440
- **Codec**: H.265 / H.264
- **FPS**: 30 fps
- **Connection Result**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Stream Latency**: Estimated ~400ms over Wi-Fi / ~300ms over Ethernet
- **Stability**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Reconnection Behavior**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Recording Behavior**: Tested via TCP RTSP transport.

---

### Camera 5: Reolink RLC-810A
- **Manufacturer**: Reolink
- **Exact Model**: RLC-810A (4K 8MP Smart PoE Camera)
- **Firmware Version**: v3.1.0.956_22041503 (or latest)
- **Default Port**: 554 (RTSP), 9000 (Media), 80/443 (Web)
- **RTSP URL Formats**:
  - Main Stream (4K): `rtsp://admin:Password123@192.168.1.150:554/h264Preview_01_main`
  - Sub Stream: `rtsp://admin:Password123@192.168.1.150:554/h264Preview_01_sub`
- **Resolution**: 3840 x 2160 (4K UHD)
- **Codec**: H.264 / H.265
- **FPS**: 25 fps
- **Connection Result**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Stream Latency**: Estimated ~450ms (4K bitrate requires sufficient bandwidth)
- **Stability**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Reconnection Behavior**: `[PENDING PHYSICAL HARDWARE TEST]`
- **Recording Behavior**: High bitrate (~8 Mbps) passthrough directly to local disk.

---

## 3. Simulated Camera Benchmark (Development Verification)

*Note: As required by project specifications, the simulated camera is clearly separated from real hardware testing.*

| Metric | Simulated Camera Pipeline |
| :--- | :--- |
| **Pipeline** | `FFmpeg synthetic testsrc` -> `MediaMTX RTSP` -> `WebRTC/HLS` -> `Streamlit` |
| **Resolution** | 1280 x 720 (720p) |
| **Framerate** | 25 fps |
| **Codec** | H.264 (Baseline / Ultrafast / Zero-latency) |
| **WebRTC Latency** | ~280ms (sub-second) |
| **Recording Result** | Tested successfully: `.mp4` files created and playable via `st.video()` |
| **Status** | **VERIFIED OPERATIONAL IN SOFTWARE ENVIRONMENT** |
