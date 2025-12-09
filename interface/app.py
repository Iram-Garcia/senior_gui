# app.py - LIVE Device Monitoring Dashboard
import streamlit as st
import pydeck as pdk
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd 
import altair as alt

# --- Configuration ---
TIMEOUT_SECONDS = 30
SENSOR_FILE = Path("latest_sensor.json")
MAX_HISTORY_POINTS = 30 # Store last 30 readings (60 seconds)
CHART_POINTS_TO_SHOW = 5 # Show last 5 points in the charts

# -------------------------------------------------------
# Page Configuration
# -------------------------------------------------------
st.set_page_config(page_title="Device Dashboard", layout="wide")

# -------------------------------------------------------
# Enhanced Styling (White/Light Background, Orange Accents)
# -------------------------------------------------------
st.markdown("""
<style>
/* Main App Background (Now White/Light) */
.stApp {
    background-color: #F8F8FF; /* Ghost White / Light Background */
    color: #333333; /* Dark text */
}

/* Titles and Headers */
h1, h2, h3, h4 { color: #333333 !important; }

/* Customizing Streamlit's primary element (e.g., progress bar, sidebar highlight) */
:root {
    --primary-color: #F4A460; /* Sandy Brown / Orange Accent */
}

/* Metric styling for prominence */
.stMetric {
    background-color: #FFFFFF;
    border-radius: 10px;
    padding: 10px 15px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* Override for map/pydeck background */
.stDeckGl, .stAltairChart {
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    background-color: #FFFFFF;
}

/* Status text color (ensuring it shows up well) */
.stMarkdown h3 {
    font-size: 1.5rem !important;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------
# Title
# -------------------------------------------------------
st.title("🛰️ Device Monitoring Dashboard")

# -------------------------------------------------------
# Data Loading Functions
# -------------------------------------------------------

def load_sensor_data():
    if SENSOR_FILE.exists():
        try:
            with open(SENSOR_FILE, "r") as f:
                data = json.load(f)
            temp = data.get("temperature", "N/A")
            battery = data.get("battery", "N/A")
            distance = data.get("distance", "N/A") # Load distance
            last_update = data.get("last_update", None)
            dt = None
            if last_update:
                dt = datetime.fromisoformat(last_update.replace("Z", "+00:00")) 
                last_update_str = dt.strftime("%I:%M:%S %p")
            else:
                last_update_str = "Never"
            
            # Fix: Check if distance has unit and strip it before conversion
            distance_val = distance
            if isinstance(distance, str) and distance != "N/A":
                 # Strip non-numeric characters (assuming unit is 'cm' or similar)
                 distance_val = ''.join(filter(lambda x: x.isdigit() or x in ['.', '-'], distance))
                 if not distance_val: distance_val = "N/A" # Handle case where only unit was present

            # Use distance_val for conversion
            return float(temp) if temp != "N/A" else None, float(battery) if battery != "N/A" else None, float(distance_val) if distance_val != "N/A" else None, last_update_str, dt
        except:
            # If any error occurs, return None for data fields
            return None, None, None, "Error reading data", None
    return None, None, None, "No data yet", None

def determine_status(temp, last_update_dt):
    is_online = temp is not None
    
    if last_update_dt is not None:
        current_time = datetime.now(last_update_dt.tzinfo)
        time_diff = current_time - last_update_dt
        
        if time_diff.total_seconds() > TIMEOUT_SECONDS:
            is_online = False
    
    status_color = "🟢" if is_online else "🔴"
    status_text = 'Online' if is_online else 'Offline / No Recent Data'
    
    return is_online, status_color, status_text

# -------------------------------------------------------
# Load Data & Update Session State History
# -------------------------------------------------------

temp, battery, distance, last_update_str, last_update_dt = load_sensor_data() 
is_online, status_color, status_text = determine_status(temp, last_update_dt)

# Initialize session state for history if it doesn't exist
if 'temp_history' not in st.session_state:
    st.session_state.temp_history = []
if 'distance_history' not in st.session_state: 
    st.session_state.distance_history = []

# Update temperature history
if is_online and temp is not None:
    new_reading = {
        "Time": last_update_dt.strftime("%H:%M:%S"), 
        "Temperature": temp
    }
    st.session_state.temp_history.append(new_reading)

# Update distance history (if distance is also valid)
if is_online and distance is not None:
    new_distance_reading = {
        "Time": last_update_dt.strftime("%H:%M:%S"),
        "Distance": distance
    }
    st.session_state.distance_history.append(new_distance_reading)

# Keep only the last MAX_HISTORY_POINTS readings for overall storage
if len(st.session_state.temp_history) > MAX_HISTORY_POINTS:
    st.session_state.temp_history = st.session_state.temp_history[-MAX_HISTORY_POINTS:]
if len(st.session_state.distance_history) > MAX_HISTORY_POINTS:
    st.session_state.distance_history = st.session_state.distance_history[-MAX_HISTORY_POINTS:]

# Slice the data to create DataFrames for the charts
chart_temp_data = st.session_state.temp_history[-CHART_POINTS_TO_SHOW:]
temp_df = pd.DataFrame(chart_temp_data)

chart_distance_data = st.session_state.distance_history[-CHART_POINTS_TO_SHOW:] 
distance_df = pd.DataFrame(chart_distance_data) 

# -------------------------------------------------------
# Hard-coded Device Coordinates
# -------------------------------------------------------
devices = {
    "Central Unit": (26.30527735920657, -98.16867744559505),
    "Trip Sensor": (26.30519793515766, -98.16865742630092),
}

data = [
    {"name": name, "lat": coords[0], "lon": coords[1]}
    for name, coords in devices.items()
]

avg_lat = sum(d["lat"] for d in data) / len(data)
avg_lon = sum(d["lon"] for d in data) / len(data)


# -------------------------------------------------------
# Layout: Sidebar
# -------------------------------------------------------

# Sidebar for map controls
with st.sidebar:
    st.header("Map Controls")
    st.write("Select the underlying map style.")
    map_style = st.selectbox("Map Style", ["road", "light", "dark", "satellite"])

    st.markdown("---")
    st.info(f"Dashboard status refresh rate: **2 seconds**.")
    st.warning(f"Device considered offline if no update in **{TIMEOUT_SECONDS} seconds**.")


# -------------------------------------------------------
# Layout: Main Content
# -------------------------------------------------------

## 1. Top Status & Metrics
st.subheader("Central Unit Status")
st.markdown(f"## {status_color} **Device Status:** {status_text}")

st.markdown("---")

# UPDATED: 4 columns for metrics
col_temp, col_bat, col_dist, col_update = st.columns(4) 

# Temperature Metric
with col_temp:
    if is_online and temp is not None:
        # THRESHOLD: 130F for critical/fire warning
        if temp >= 130: 
            temp_emoji = "🔥 CRITICAL"
            delta_color = "inverse"
        elif temp >= 90:
            temp_emoji = "🌡️ Warning"
            delta_color = "off"
        else:
            temp_emoji = "🌤️ Normal"
            delta_color = "normal"
            
        st.metric(label="Temperature", 
                  value=f"{temp:.1f}°F", 
                  delta=temp_emoji,
                  delta_color=delta_color)
    else:
        st.metric(label="Temperature", value="N/A", delta="Offline")

# Battery Metric
with col_bat:
    if is_online and battery is not None:
        if battery >= 80:
            bat_delta = "Excellent"
        elif battery >= 50:
            bat_delta = "Good"
        elif battery >= 20:
            bat_delta = "Low"
        else:
            bat_delta = "Critical"
            
        st.metric(label="Battery Level", 
                  value=f"{battery:.0f}%", 
                  delta=bat_delta,
                  delta_color=("inverse" if battery < 20 else "normal"))
    else:
        st.metric(label="Battery Level", value="N/A", delta="Offline")

# Distance Metric (NEW)
with col_dist:
    if is_online and distance is not None:
        if distance <= 10.0:
            dist_delta = "🚨 Dangerously Close"
            delta_color = "inverse"
        elif distance <= 50.0:
            dist_delta = "⚠️ Close Proximity"
            delta_color = "off"
        else:
            dist_delta = "✅ Safe Distance"
            delta_color = "normal"
            
        st.metric(label="Distance", 
                  value=f"{distance:.1f} cm", 
                  delta=dist_delta,
                  delta_color=delta_color)
    else:
        st.metric(label="Distance", value="N/A", delta="Offline")

# Last Update Metric
with col_update:
    st.metric(label="Last Data Update", value=last_update_str, delta=None)

st.markdown("---")

## 2. Map View

st.subheader("📍 Device Location Map")

# Map layer
layer = pdk.Layer(
    "ScatterplotLayer",
    data,
    get_position="[lon, lat]",
    get_color="[0, 120, 255, 220]",
    get_radius=8,
    pickable=True,
)

view_state = pdk.ViewState(latitude=avg_lat, longitude=avg_lon, zoom=17, pitch=45)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    map_style=map_style,
    tooltip={"text": "{name}"}
)
st.pydeck_chart(deck)

st.markdown("---")

## 3. Distance History Chart
st.subheader("📏 Live Distance History")

# Ensure DataFrame has data before charting
if not distance_df.empty:
    chart_distance = alt.Chart(distance_df).mark_line(point=True).encode(
        x=alt.X('Time', axis=alt.Axis(labelAngle=0)), 
        y=alt.Y('Distance', title='Distance (cm)'), # Updated label
        color=alt.value("#4682B4"), 
        tooltip=['Time', 'Distance']
    ).properties(
        title=f'Distance Trend (Last {CHART_POINTS_TO_SHOW} Readings)'
    ).interactive()

    # Left-aligned, full width chart
    st.altair_chart(chart_distance, use_container_width=True, theme=None) 
else:
    st.info("Waiting for distance data to populate the graph...")

st.markdown("---")

## 4. Temperature History Chart
st.subheader("📊 Live Temperature History")

# Ensure DataFrame has data before charting
if not temp_df.empty:
    chart_temp = alt.Chart(temp_df).mark_line(point=True).encode(
        x=alt.X('Time', axis=alt.Axis(labelAngle=0)), 
        y=alt.Y('Temperature', title='Temperature (°F)'),
        color=alt.value("#F4A460"), 
        tooltip=['Time', 'Temperature']
    ).properties(
        title=f'Temperature Trend (Last {CHART_POINTS_TO_SHOW} Readings)'
    ).interactive()

    # Left-aligned, full width chart
    st.altair_chart(chart_temp, use_container_width=True, theme=None) 
else:
    st.info("Waiting for temperature data to populate the graph...")

st.markdown("---")

## 5. Recent Flagged Events (in an Expander)

flagged_dir = Path("FLAGGED")
if flagged_dir.exists():
    flagged_images = sorted(flagged_dir.glob("*.jpg"), reverse=True)[:6]
    if flagged_images:
        with st.expander("🚨 Recent Unauthorized Vehicle Detections"):
            st.write("Images captured due to unauthorized vehicle presence.")
            
            cols = st.columns(min(len(flagged_images), 3)) 
            for i, img_path in enumerate(flagged_images):
                with cols[i % 3]:
                    st.image(str(img_path), use_column_width=True)
                    st.caption(f"Captured: {img_path.name[-19:-4]}")
        
else:
    st.info("Flagged image directory not found.")


# Footer & Auto-Refresh
st.markdown("---")
st.caption("Dashboard auto-refreshes every 2 seconds • Data from main.py via latest_sensor.json")

# -------------------------------------------------------
# Auto-Refresh Mechanism
# -------------------------------------------------------
time.sleep(2)
st.rerun()