import streamlit as st
import geopandas as gpd
import pandas as pd
import pydeck as pdk
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Sudan Mining & Conflict Environmental OSINT Map", layout="wide")

@st.cache_data
def load_aoi():
    return gpd.read_file("data/aoi/sudan_aoi_buffers.geojson")

@st.cache_data
def load_firms():
    fp = Path("data/raw/firms_sudan_area.csv")
    if not fp.exists():
        return pd.DataFrame(columns=["latitude","longitude","acq_date"])
    df = pd.read_csv(fp)
    # Normalize column names for safety
    df.columns = [c.strip().lower() for c in df.columns]
    # Ensure required columns exist
    if not {"latitude","longitude"}.issubset(set(df.columns)):
        return pd.DataFrame(columns=["latitude","longitude","acq_date"])
    # Parse dates if present
    if "acq_date" in df.columns:
        try:
            df["acq_date"] = pd.to_datetime(df["acq_date"])
        except Exception:
            pass
    return df

@st.cache_data
def load_border_crossings():
    # Expect columns: name,lat,lon
    fp = Path("data/aoi/border_crossings.csv")
    if not fp.exists():
        return pd.DataFrame(columns=["name","lat","lon"])
    df = pd.read_csv(fp)
    return df

@st.cache_data
def load_mining_sites():
    # Expect columns: name,lat,lon
    fp = Path("data/aoi/key_mining_sites.csv")
    if not fp.exists():
        return pd.DataFrame(columns=["name","lat","lon"])
    df = pd.read_csv(fp)
    return df

AOI = load_aoi()
FIRMS = load_firms()
CROSS = load_border_crossings()
MINES = load_mining_sites()

st.sidebar.title("Controls")

if AOI.empty or "region" not in AOI.columns:
    st.sidebar.error("AOI file missing or invalid. Expect GeoJSON with a 'region' column.")
    aoi_names = []
else:
    aoi_names = ["(All Regions)"] + sorted(AOI["region"].unique().tolist())

selected_region = st.sidebar.selectbox("Area of Interest", aoi_names, index=0)

filter_mode = st.sidebar.radio(
    "Fire Display Mode",
    ["Only inside selected AOI", "Show all fires"],
    index=1 if selected_region == "(All Regions)" else 0
)

# Optional date filter if acq_date exists
date_filtered = False
if not FIRMS.empty and "acq_date" in FIRMS.columns and pd.api.types.is_datetime64_any_dtype(FIRMS["acq_date"]):
    min_date = FIRMS["acq_date"].min()
    max_date = FIRMS["acq_date"].max()
    st.sidebar.markdown("**Date filter**")
    date_range = st.sidebar.slider(
        "acq_date",
        min_value=min_date.to_pydatetime(),
        max_value=max_date.to_pydatetime(),
        value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
        format="YYYY-MM-DD"
    )
    FIRMS = FIRMS[(FIRMS["acq_date"] >= pd.Timestamp(date_range[0])) &
                  (FIRMS["acq_date"] <= pd.Timestamp(date_range[1]))]
    date_filtered = True

# ----------------------------
# Prep GeoDataFrames
# ----------------------------
if not FIRMS.empty:
    gdf_firms = gpd.GeoDataFrame(
        FIRMS.copy(),
        geometry=gpd.points_from_xy(FIRMS["longitude"], FIRMS["latitude"]),
        crs="EPSG:4326"
    )
else:
    gdf_firms = gpd.GeoDataFrame(columns=["latitude","longitude","geometry"], crs="EPSG:4326")

if selected_region != "(All Regions)" and not AOI.empty:
    buffer_geom = AOI[AOI["region"] == selected_region]
else:
    buffer_geom = AOI.iloc[0:0]  # empty selection

# Filter to AOI if requested and AOI chosen
if filter_mode == "Only inside selected AOI" and not buffer_geom.empty and not gdf_firms.empty:
    gdf_firms_filtered = gdf_firms[gdf_firms.geometry.within(buffer_geom.unary_union)]
else:
    gdf_firms_filtered = gdf_firms

# Border crossings
if not CROSS.empty and {"lat","lon"}.issubset(CROSS.columns):
    cross_df = CROSS.copy()
else:
    cross_df = pd.DataFrame(columns=["name","lat","lon"])

# Mining sites
if not MINES.empty and {"lat","lon"}.issubset(MINES.columns):
    mines_df = MINES.copy()
else:
    mines_df = pd.DataFrame(columns=["name","lat","lon"])

# ----------------------------
# Map view calculation
# ----------------------------
def default_view_state():
    # Wide regional view over Sudan & neighbours
    return pdk.ViewState(latitude=13.5, longitude=30.5, zoom=5.2, pitch=0)

def aoi_view_state(gdf):
    if gdf.empty:
        return default_view_state()
    centroid = gdf.geometry.unary_union.centroid
    return pdk.ViewState(latitude=centroid.y, longitude=centroid.x, zoom=8, pitch=0)

if selected_region != "(All Regions)" and not buffer_geom.empty:
    view_state = aoi_view_state(buffer_geom)
else:
    view_state = default_view_state()

layers = []

# Base style – use a free vector style (no Mapbox token required)
map_style = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# FIRMS heatmap (if we have data)
if not gdf_firms_filtered.empty:
    layers.append(
        pdk.Layer(
            "HeatmapLayer",
            data=gdf_firms_filtered,
            get_position=["longitude","latitude"],
            aggregation="SUM",
            threshold=0.3,
            radius_pixels=50,
            opacity=0.4,
        )
    )

# AOI outline (only highlight selected)
if not buffer_geom.empty:
    layers.append(
        pdk.Layer(
            "GeoJsonLayer",
            data=buffer_geom.__geo_interface__,
            stroked=True,
            filled=False,
            get_line_color=[255, 0, 0],
            lineWidthMinPixels=2,
        )
    )

# Border crossings (blue markers)
if not cross_df.empty:
    cross_df = cross_df.assign(kind="Border crossing")
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=cross_df,
            get_position=["lon","lat"],
            get_radius=6000,
            pickable=True,
            get_fill_color=[0, 92, 230, 200],
            auto_highlight=True
        )
    )

# Mining sites (gold markers)
if not mines_df.empty:
    mines_df = mines_df.assign(kind="Mining site")
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=mines_df,
            get_position=["lon","lat"],
            get_radius=6000,
            pickable=True,
            get_fill_color=[232, 185, 35, 220],
            auto_highlight=True
        )
    )

tooltip = {
    "html": "<b>{kind}</b><br/>{name}",
    "style": {"backgroundColor": "rgba(0,0,0,0.8)", "color": "white"}
}

# ----------------------------
# Render
# ----------------------------
st.title("Sudan Mining & Conflict Environmental OSINT Map")
st.caption("Sudan Gold Corridor • Environmental Change & Conflict Heat Explorer")

col1, col2 = st.columns([4, 1])

with col1:
    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_provider="carto",
        map_style=map_style,
        tooltip=tooltip
    )
    st.pydeck_chart(r, use_container_width=True)

with col2:
    st.markdown("### Legend")
    st.markdown("- FIRMS heatmap (last N days, appended daily)")
    st.markdown("- **Red outline**: Selected AOI")
    st.markdown("- **Blue dots**: Border crossings")
    st.markdown("- **Gold dots**: Key mining sites")

    if not FIRMS.empty:
        n_all = len(FIRMS)
        n_shown = len(gdf_firms_filtered)
        date_note = ""
        if date_filtered and "acq_date" in FIRMS.columns:
            date_note = f" (filtered to selected dates)"
        st.markdown(f"**FIRMS detections shown**: {n_shown:,} of {n_all:,}{date_note}")

# Sidebar credit
st.sidebar.markdown("---")
st.sidebar.write("**Data Sources (local)**")
st.sidebar.caption("NASA FIRMS (more coming)")
st.sidebar.markdown(
    """
    <div style="text-align: center, color:white;">
        <a href="https://x.com/frogtypebeat_" target="_blank" style="margin-right: 15px;">
            <img src="https://simpleicons.org/icons/x.svg" width="22" style="vertical-align:middle;">
        </a>
        <a href="mailto:darcyjfmccarthy@gmail.com">
            <img src="https://simpleicons.org/icons/maildotru.svg" width="22" style="vertical-align:middle;">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)