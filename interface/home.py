import streamlit as st
import pydeck as pdk

# -------------------------------------------------------
# Page Configuration
# -------------------------------------------------------
st.set_page_config(page_title="Device Dashboard", layout="wide")

# Custom CSS for orange background and light text
st.markdown("""
<style>
.stApp {
    background-color: #F4A460;
    color: #F8F8FF;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------
# Title
# -------------------------------------------------------
st.title("Device Monitoring Dashboard")

# -------------------------------------------------------
# Hard-coded Device Coordinates
# -------------------------------------------------------
devices = {
    "Central Unit": (26.30527735920657, -98.16867744559505),
    "Trip Sensor": (26.30519793515766, -98.16865742630092),
}

# Convert devices into pydeck-friendly data
data = [
    {"name": name, "lat": coords[0], "lon": coords[1]}
    for name, coords in devices.items()
]

# -------------------------------------------------------
# Map Layer (ScatterplotLayer for blue dots)
# -------------------------------------------------------
layer = pdk.Layer(
    "ScatterplotLayer",
    data,
    get_position="[lon, lat]",
    get_color="[0, 0, 255, 200]",  # Blue dots
    get_radius=2,
    pickable=True,
)

# View state (centered on devices)
avg_lat = sum([d["lat"] for d in data]) / len(data)
avg_lon = sum([d["lon"] for d in data]) / len(data)

view_state = pdk.ViewState(
    latitude=avg_lat,
    longitude=avg_lon,
    zoom=17,
    pitch=60,   # tilt for 3D effect
    bearing=0
)

# -------------------------------------------------------
# Layout: Three Columns with Vertical Separator
# -------------------------------------------------------
col_map, col_sep, col_info = st.columns([2, 0.1, 1])

with col_map:
    # Header row with subheader and dropdown
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.subheader("Device Map")
    with header_col2:
        st.write("Select map style:")
        map_style_choice = st.selectbox(
            "Style",
            options=["light", "dark", "road"],
            index=2,
            label_visibility="collapsed"
        )

    # Deck object with chosen style
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=map_style_choice,
        tooltip={"text": "{name}\nLat: {lat}\nLon: {lon}"},
    )

    # Show map
    st.pydeck_chart(r)

with col_sep:
    st.markdown('<div style="border-left: 2px solid #ccc; height: 100%; min-height: 600px;"></div>', unsafe_allow_html=True)

with col_info:
    st.subheader("Device Information")
    for device in devices.keys():
        st.markdown(f"### {device} Status")
        st.write("**Status:** Online")
        st.write("**Temperature:** 98°F")
        st.write("**Battery Level:** 75%")
        st.write("**Last Update:** 10 minutes ago")
        st.markdown('<hr style="height: 3px; border: none; background-color: #ccc; margin: 20px 0;">', unsafe_allow_html=True)
