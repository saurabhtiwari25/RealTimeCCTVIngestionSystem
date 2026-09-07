"""
Status Badge UI Component: High-End Precision Micro-Indicators
"""

import streamlit as st

_BADGE_CONFIGS = {
    "ONLINE": ("#22c55e", "0 0 4px rgba(34,197,94,0.8)", "rgba(34,197,94,0.08)", "rgba(34,197,94,0.3)", "#4ade80", "ONLINE"),
    "CONNECTING": ("#eab308", "0 0 4px rgba(234,179,8,0.8)", "rgba(234,179,8,0.08)", "rgba(234,179,8,0.3)", "#fde047", "CONNECTING"),
    "OFFLINE": ("#64748b", "none", "rgba(100,116,139,0.08)", "rgba(100,116,139,0.25)", "#94a3b8", "OFFLINE"),
    "ERROR": ("#ef4444", "0 0 4px rgba(239,68,68,0.8)", "rgba(239,68,68,0.08)", "rgba(239,68,68,0.3)", "#f87171", "ERROR"),
}

def render_status_badge(status: str, is_recording: bool = False):
    """Renders a sleek, minimalist status badge with an ultra-fine micro-dot indicator."""
    dot_color, glow, bg, border, text, label = _BADGE_CONFIGS.get((status or "OFFLINE").upper(), _BADGE_CONFIGS["OFFLINE"])

    rec_badge = (
        '<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(220,38,38,0.12);border:1px solid rgba(239,68,68,0.5);'
        'color:#fca5a5;padding:2px 7px;border-radius:9999px;font-size:10px;font-weight:700;letter-spacing:0.6px;">'
        '<span style="display:inline-block;width:4.5px;height:4.5px;border-radius:50%;background:#ef4444;box-shadow:0 0 4px #ef4444;"></span>REC</span>'
    ) if is_recording else ""

    st.markdown(f'''
    <div style="display:flex;align-items:center;gap:5px;margin:1px 0 4px 0;">
        <span style="display:inline-flex;align-items:center;gap:5px;background:{bg};border:1px solid {border};color:{text};padding:2px 8px;border-radius:9999px;font-size:10px;font-weight:600;letter-spacing:0.8px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;text-transform:uppercase;">
            <span style="display:inline-block;width:4.5px;height:4.5px;border-radius:50%;background:{dot_color};box-shadow:{glow};flex-shrink:0;"></span>
            <span>{label}</span>
        </span>
        {rec_badge}
    </div>''', unsafe_allow_html=True)
