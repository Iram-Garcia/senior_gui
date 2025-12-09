import streamlit as st
import pydeck as pdk
from pathlib import Path
from student_db import get_all_students, get_verification_log

# -------------------------------------------------------
# Page Configuration
# -------------------------------------------------------
st.set_page_config(
    page_title="License Plate Verification System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------
# Custom CSS Styling
# -------------------------------------------------------
st.markdown("""
<style>
    /* Main app background - Orange gradient */
    .stApp {
        background: linear-gradient(135deg, #FF8C00 0%, #FF6B35 50%, #FF8C00 100%);
    }
    
    /* Header styling */
    h1 {
        color: #ffffff;
        text-align: center;
        font-size: 2.5em;
        margin-bottom: 0.5em;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    h2 {
        color: #ffffff;
        border-bottom: 3px solid #ffffff;
        padding-bottom: 10px;
    }
    
    h3 {
        color: #f0f0f0;
    }
    
    /* Card-like containers */
    .metric-card {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 10px 0;
        border-top: 4px solid #FF8C00;
    }
    
    /* Text styling */
    .stMarkdown, p, li {
        color: #f0f0f0;
        font-size: 1.05em;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.2);
    }
    
    /* Button styling - Orange */
    .stButton > button {
        background-color: #FF8C00;
        color: #ffffff;
        font-weight: bold;
        border-radius: 5px;
        border: 2px solid #ffffff;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #FF6B35;
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(255, 107, 53, 0.4);
    }
    
    /* Metric styling */
    .metric-box {
        background-color: rgba(255, 255, 255, 0.15);
        border-left: 4px solid #ffffff;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------
# Title and Subtitle
# -------------------------------------------------------
st.title("🚗 License Plate Verification System")
st.markdown("""
<div style="text-align: center; color: #ffffff; font-size: 1.2em; margin-bottom: 2em;">
    Automated license plate detection, recognition, and student database verification
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------
# Statistics Dashboard
# -------------------------------------------------------
st.markdown("## 📊 System Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    students = get_all_students()
    st.metric("👥 Registered Students", len(students), "in database")

with col2:
    logs = get_verification_log(limit=100)
    st.metric("🔍 Recent Scans", len(logs), "last 100 scans")

with col3:
    if logs:
        matches = sum(1 for log in logs if log['match_found'])
        match_rate = (matches / len(logs) * 100) if logs else 0
        st.metric("✅ Match Rate", f"{match_rate:.1f}%", f"{matches}/{len(logs)} matched")
    else:
        st.metric("✅ Match Rate", "0%", "no data")

with col4:
    interface_dir = Path(__file__).parent
    verification_folder = interface_dir / "need_verification"
    if verification_folder.exists():
        pending_images = len([f for f in verification_folder.iterdir() if f.is_file()])
    else:
        pending_images = 0
    st.metric("⚠️ Pending Review", pending_images, "images needing manual check")

# -------------------------------------------------------
# Quick Action Cards
# -------------------------------------------------------
st.markdown("## ⚡ Quick Actions")

col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    st.markdown("""
    <div class="metric-card" style="text-align: center;">
        <h3 style="color: #667eea; margin-top: 0;">👥 Manage Students</h3>
        <p style="color: #666;">View, add, or remove student records</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Page 1", key="btn_page1", use_container_width=True):
        st.switch_page("pages/page1.py")

with col_b:
    st.markdown("""
    <div class="metric-card" style="text-align: center;">
        <h3 style="color: #667eea; margin-top: 0;">🔍 Manual Review</h3>
        <p style="color: #666;">Review low-confidence scans</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Page 2", key="btn_page2", use_container_width=True):
        st.switch_page("pages/page2.py")

with col_c:
    st.markdown("""
    <div class="metric-card" style="text-align: center;">
        <h3 style="color: #667eea; margin-top: 0;">🔐 Verification</h3>
        <p style="color: #666;">Verify plates and track history</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Verify", key="btn_verify", use_container_width=True):
        st.switch_page("pages/verify.py")

with col_d:
    st.markdown("""
    <div class="metric-card" style="text-align: center;">
        <h3 style="color: #667eea; margin-top: 0;">📍 Device Status</h3>
        <p style="color: #666;">Monitor system devices</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Device Map", key="btn_devices", use_container_width=True):
        st.info("Device map is displayed below ⬇️")

# -------------------------------------------------------
# Device Map Section
# -------------------------------------------------------
st.markdown("## 🗺️ Device Monitoring")

# Hard-coded Device Coordinates
devices = {
    "Central Unit": (26.30527735920657, -98.16867744559505),
    "Trip Sensor": (26.30519793515766, -98.16865742630092),
}

# Convert devices into pydeck-friendly data
data = [
    {"name": name, "lat": coords[0], "lon": coords[1]}
    for name, coords in devices.items()
]

# Map Layer
layer = pdk.Layer(
    "ScatterplotLayer",
    data,
    get_position="[lon, lat]",
    get_color="[255, 215, 0, 200]",  # Gold dots
    get_radius=5,
    pickable=True,
)

# View state (centered on devices)
avg_lat = sum([d["lat"] for d in data]) / len(data)
avg_lon = sum([d["lon"] for d in data]) / len(data)

view_state = pdk.ViewState(
    latitude=avg_lat,
    longitude=avg_lon,
    zoom=17,
    pitch=45,
    bearing=0
)

# Layout: Map and Info
col_map, col_info = st.columns([3, 1])

with col_map:
    # Map style selector
    map_style_choice = st.radio(
        "Map Style:",
        options=["light", "dark", "road"],
        index=1,
        horizontal=True
    )
    
    # Deck object with chosen style
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=map_style_choice,
        tooltip={"text": "{name}\nLat: {lat}\nLon: {lon}"},
    )
    
    # Show map
    st.pydeck_chart(r, use_container_width=True)

with col_info:
    st.subheader("📍 Device Status")
    
    # Sample device data (can be replaced with real data from sensors/APIs)
    device_data = {
        "Central Unit": {
            "status": "Online",
            "signal": "Strong",
            "temperature": 72.5,
            "battery": 85,
            "last_checked": "2 min ago"
        },
        "Trip Sensor": {
            "status": "Online",
            "signal": "Strong",
            "temperature": 68.3,
            "battery": 92,
            "last_checked": "1 min ago"
        }
    }
    
    for device in devices.keys():
        st.markdown(f"### {device}")
        
        # Get device data (or use defaults)
        data = device_data.get(device, {
            "status": "Online",
            "signal": "Strong",
            "temperature": 70.0,
            "battery": 80,
            "last_checked": "N/A"
        })
        
        # Status and signal indicators
        col_status1, col_status2 = st.columns(2)
        with col_status1:
            st.markdown("🟢 **Online**")
            st.caption(data.get("status", "Unknown"))
        with col_status2:
            st.markdown("📶 **Signal**")
            st.caption(data.get("signal", "Unknown"))
        
        # Temperature display
        st.markdown(f"🌡️ **Temperature:** {data.get('temperature', 'N/A')}°F")
        
        # Battery display with color
        battery = data.get("battery", 0)
        if battery >= 75:
            battery_color = "🟢"
        elif battery >= 50:
            battery_color = "🟡"
        else:
            battery_color = "🔴"
        st.markdown(f"{battery_color} **Battery:** {battery}%")
        
        # Last checked display
        st.markdown(f"⏱️ **Last Checked:** {data.get('last_checked', 'N/A')}")
        
        st.markdown("---")

# -------------------------------------------------------
# System Information
# -------------------------------------------------------
st.markdown("## ℹ️ System Information")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("""
    <div class="metric-box">
        <strong>📝 Detection Model</strong><br>
        YOLO v8 (License Plate Detection)
    </div>
    """, unsafe_allow_html=True)

with col_info2:
    st.markdown("""
    <div class="metric-box">
        <strong>🔤 OCR Engine</strong><br>
        EasyOCR (Text Recognition)
    </div>
    """, unsafe_allow_html=True)

with col_info3:
    st.markdown("""
    <div class="metric-box">
        <strong>💾 Database</strong><br>
        SQLite (Students & Logs)
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------
# Footer
# -------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #f0f0f0; font-size: 0.9em; margin-top: 2em;">
    <p>🚗 License Plate Verification System | Built with Streamlit + YOLO + OCR</p>
    <p style="color: #FFD700;">Use the sidebar to navigate between pages</p>
</div>
""", unsafe_allow_html=True)
