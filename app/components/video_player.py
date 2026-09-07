"""
Browser-Compatible Video Player Component (WebRTC / HLS via MediaMTX)
"""

import streamlit as st
import streamlit.components.v1 as components
from app.database.models import Camera
from app.services.stream_service import StreamService
from app.utils.config import settings

_OVERLAY_BG = "rgba(15,23,42,0.85)"
_CLOCK_STYLE = (
    "position:absolute;bottom:8px;left:8px;font-size:11px;font-family:'Roboto Mono','Courier New',monospace;"
    f"font-weight:700;color:#f8fafc;background:{_OVERLAY_BG};border:1px solid rgba(255,255,255,0.2);"
    "padding:2px 8px;border-radius:4px;pointer-events:none;z-index:10;display:flex;align-items:center;"
    "gap:6px;letter-spacing:0.5px;box-shadow:0 2px 4px rgba(0,0,0,0.5);"
)
_LIVE_DOT = '<span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:#22c55e;box-shadow:0 0 5px #22c55e;"></span>'
_RELOAD_BTN_STYLE = (
    f"position:absolute;top:8px;right:8px;background:rgba(15,23,42,0.8);border:1px solid #475569;"
    "color:#f1f5f9;border-radius:4px;padding:2px 7px;font-size:11px;cursor:pointer;z-index:10;transition:all 0.2s;"
)
_CONTAINER_BASE = "position:relative;width:100%;background:#000;border-radius:8px;overflow:hidden;display:flex;align-items:center;justify-content:center;"


def _clock_html(cam_id, el_id_prefix="cctv-clock"):
    return f'''<div id="{el_id_prefix}-{cam_id}" style="{_CLOCK_STYLE}">{_LIVE_DOT}<span id="{el_id_prefix}-val-{cam_id}">--:--:--</span></div>'''


def _clock_js(cam_id, fn_name="updateCctvClock", el_id_prefix="cctv-clock"):
    return f'''function {fn_name}(){{const now=new Date();const p=n=>String(n).padStart(2,'0');const el=document.getElementById("{el_id_prefix}-val-{cam_id}");if(el)el.innerText=`${{now.getFullYear()}}-${{p(now.getMonth()+1)}}-${{p(now.getDate())}} ${{p(now.getHours())}}:${{p(now.getMinutes())}}:${{p(now.getSeconds())}}`;}};setInterval({fn_name},500);{fn_name}();'''


def render_video_player(camera: Camera, height: int = 280, mode: str = "webrtc", version: int = 0, stream_type: str = "main"):
    """Renders browser-compatible video stream through MediaMTX (main or sub-stream)."""
    if camera.protocol == "WEBCAM" or "laptop_cam" in camera.rtsp_url or "front camera" in camera.name.lower():
        render_webcam_player(camera, height=height, version=version)
        return

    if camera.status not in ("ONLINE", "CONNECTING"):
        render_offline_placeholder(camera, height)
        return

    urls = StreamService.get_stream_urls(camera, stream_type=stream_type)
    whep_url, hls_url, hls_playlist = urls["webrtc_whep"], urls["hls"], urls["hls_playlist"]
    is_sub = urls.get("is_sub_stream", False)

    res_badge = '<span style="position:absolute;top:8px;left:112px;font-size:10px;font-weight:700;background:rgba(2,132,199,0.85);color:#e0f2fe;padding:2px 6px;border-radius:4px;font-family:monospace;border:1px solid rgba(56,189,248,0.4);z-index:10;letter-spacing:0.5px;">⚡ SUB (720p)</span>' if is_sub else '<span style="position:absolute;top:8px;left:112px;font-size:10px;font-weight:700;background:rgba(16,185,129,0.85);color:#ecfdf5;padding:2px 6px;border-radius:4px;font-family:monospace;border:1px solid rgba(52,211,153,0.4);z-index:10;letter-spacing:0.5px;">🌟 MAIN (HD/4K)</span>'

    try:
        if mode == "hls":
            player_html = f'''
            <div id="player-hls-{camera.id}-{version}" style="{_CONTAINER_BASE}height:{height}px;border:1px solid #334155;">
                <iframe src="{hls_url}?v={version}" style="width:100%;height:100%;border:none;display:block;" allow="autoplay; fullscreen" loading="lazy"></iframe>
                {res_badge}
                {_clock_html(camera.id, "cctv-hls-clock")}
                <script>{_clock_js(camera.id, "updateHlsClock", "cctv-hls-clock")}</script>
            </div>'''
        else:
            player_html = f'''
            <div id="webrtc-container-{camera.id}-{version}" style="{_CONTAINER_BASE}height:{height}px;border:1px solid #334155;">
                <video id="webrtc-video-{camera.id}" autoplay muted playsinline controls style="width:100%;height:100%;object-fit:contain;background:#000;"></video>
                <div id="status-{camera.id}" style="position:absolute;top:8px;left:8px;font-size:11px;background:{_OVERLAY_BG};color:#4ade80;padding:2px 8px;border-radius:4px;font-family:monospace;pointer-events:none;z-index:10;border:1px solid rgba(255,255,255,0.15);">⚡ WebRTC Live</div>
                {res_badge}
                {_clock_html(camera.id)}
                <button onclick="startStream()" title="Reload Stream Feed" style="{_RELOAD_BTN_STYLE}">🔄 Reload</button>
            </div>
            <script>
            {_clock_js(camera.id)}
            let currentPc=null;let reconnectTimeout=null;
            async function startStream(){{
                if(reconnectTimeout){{clearTimeout(reconnectTimeout);reconnectTimeout=null;}}
                if(currentPc){{try{{currentPc.close();}}catch(e){{}}currentPc=null;}}
                const video=document.getElementById("webrtc-video-{camera.id}");
                const statusDiv=document.getElementById("status-{camera.id}");
                if(statusDiv){{statusDiv.innerText="⚡ Connecting...";statusDiv.style.color="#38bdf8";}}
                try{{
                    const pc=new RTCPeerConnection({{iceServers:[]}});currentPc=pc;
                    pc.onconnectionstatechange=()=>{{
                        if(pc.connectionState==='connected'){{if(statusDiv){{statusDiv.innerText="⚡ WebRTC Live";statusDiv.style.color="#4ade80";}}}}
                        else if(pc.connectionState==='disconnected'||pc.connectionState==='failed'){{if(statusDiv){{statusDiv.innerText="🔄 Reconnecting...";statusDiv.style.color="#f97316";}}reconnectTimeout=setTimeout(startStream,2000);}}
                    }};
                    pc.addTransceiver('video',{{direction:'recvonly'}});
                    pc.ontrack=function(event){{if(event.streams&&event.streams[0]){{video.srcObject=event.streams[0];video.play().catch(e=>console.log('Autoplay handled:',e));}}}};
                    const offer=await pc.createOffer();await pc.setLocalDescription(offer);
                    const controller=new AbortController();const timeoutId=setTimeout(()=>controller.abort(),3500);
                    const response=await fetch("{whep_url}",{{method:'POST',headers:{{'Content-Type':'application/sdp'}},body:offer.sdp,signal:controller.signal}});
                    clearTimeout(timeoutId);
                    if(response.ok){{const answer=await response.text();await pc.setRemoteDescription({{type:'answer',sdp:answer}});}}
                    else{{throw new Error("WHEP negotiation returned "+response.status);}}
                }}catch(err){{
                    console.warn("WebRTC unavailable, switching to HLS player:",err);
                    if(statusDiv){{statusDiv.innerText="📺 HLS Live";statusDiv.style.color="#fde047";}}
                    video.src="{hls_playlist}?v="+Date.now();video.play().catch(e=>console.log('HLS play note:',e));
                    reconnectTimeout=setTimeout(startStream,4000);
                }}
            }}
            startStream();
            </script>'''
        components.html(player_html, height=height + 8)
    except Exception as e:
        st.warning(f"Stream player error: {e}")
        render_offline_placeholder(camera, height)


def render_webcam_player(camera: Camera, height: int = 240, version: int = 0):
    """Renders live browser hardware webcam stream directly from the user's laptop front camera."""
    cid = camera.id
    player_html = f'''
    <div id="webcam-container-{cid}-{version}" style="{_CONTAINER_BASE}height:{height}px;border:1px solid #0284c7;box-shadow:0 0 15px rgba(2,132,199,0.15);">
        <video id="webcam-video-{cid}" autoplay muted playsinline controls style="width:100%;height:100%;object-fit:contain;background:#000;"></video>
        <div id="status-{cid}" style="position:absolute;top:8px;left:8px;font-size:11px;background:{_OVERLAY_BG};color:#38bdf8;padding:2px 8px;border-radius:4px;font-family:monospace;pointer-events:none;z-index:10;border:1px solid rgba(56,189,248,0.3);display:flex;align-items:center;gap:5px;">
            <span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:#38bdf8;box-shadow:0 0 5px #38bdf8;"></span>📷 Laptop Front Camera (Live)
        </div>
        {_clock_html(cid)}
        <button onclick="startWebcam()" title="Reload Webcam Feed" style="{_RELOAD_BTN_STYLE}">🔄 Reload</button>
        <div id="permission-msg-{cid}" style="display:none;position:absolute;inset:0;background:rgba(15,23,42,0.92);flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:20px;z-index:15;">
            <div style="font-size:28px;margin-bottom:8px;">📷</div>
            <div style="font-size:14px;font-weight:600;color:#f8fafc;margin-bottom:4px;">Camera Access Needed</div>
            <div style="font-size:12px;color:#94a3b8;max-width:280px;margin-bottom:12px;">Click below to grant your browser access to your front webcam ("720p HD Camera").</div>
            <button onclick="startWebcam()" style="background:#0284c7;color:#fff;border:none;padding:6px 14px;border-radius:4px;font-size:12px;font-weight:600;cursor:pointer;">Grant Camera Access</button>
        </div>
    </div>
    <script>
    {_clock_js(cid)}
    let localStream=null;
    async function startWebcam(){{
        const video=document.getElementById("webcam-video-{cid}");
        const status=document.getElementById("status-{cid}");
        const permDiv=document.getElementById("permission-msg-{cid}");
        if(permDiv)permDiv.style.display="none";
        try{{
            if(localStream){{localStream.getTracks().forEach(t=>t.stop());}}
            const stream=await navigator.mediaDevices.getUserMedia({{video:{{width:{{ideal:1280}},height:{{ideal:720}},facingMode:"user"}},audio:false}});
            localStream=stream;video.srcObject=stream;video.play().catch(e=>console.log("Webcam play note:",e));
            if(status){{status.innerHTML='<span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:#22c55e;box-shadow:0 0 5px #22c55e;"></span> 📷 Laptop Front Camera (Live)';status.style.color="#4ade80";}}
        }}catch(err){{
            console.warn("Camera access error:",err);
            if(permDiv)permDiv.style.display="flex";
            if(status){{status.innerText="⚠️ Camera Access Needed";status.style.color="#f87171";}}
        }}
    }}
    startWebcam();
    </script>'''
    components.html(player_html, height=height + 8)


def render_offline_placeholder(camera: Camera, height: int = 280):
    """Renders a styled placeholder when stream is offline or unavailable."""
    is_connecting = camera.status == "CONNECTING"
    label = "Connecting..." if is_connecting else "Stream Unavailable"
    sub = "Negotiating RTSP connection with MediaMTX..." if is_connecting else "Stream is offline. Click 'Start Stream' to initiate live broadcast."
    icon = "⏳" if is_connecting else "📹"
    error_div = f'<div style="font-size:11px;color:#ef4444;margin-top:8px;font-family:monospace;">{camera.last_error}</div>' if camera.last_error else ''

    components.html(f'''
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;height:{height}px;background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);border:1px dashed #475569;border-radius:8px;color:#94a3b8;text-align:center;padding:20px;box-sizing:border-box;">
        <div style="font-size:36px;margin-bottom:8px;">{icon}</div>
        <div style="font-size:15px;font-weight:600;color:#f1f5f9;margin-bottom:4px;">{label}</div>
        <div style="font-size:12px;color:#64748b;max-width:80%;">{sub}</div>
        {error_div}
    </div>''', height=height + 8)
