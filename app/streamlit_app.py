import streamlit as st
import geopandas as gpd
import pandas as pd
import pydeck as pdk
from pathlib import Path

@st.cache_data
def load_aoi():
    return gpd.read_file("data/aoi/sudan_aoi_buffers.geojson")

@st.cache_data
def load_firms():
    firms_fp = Path("data/raw/firms_sudan_area.csv")
    if firms_fp.exists():
        print('Loaded FIRMS data!')
        return pd.read_csv(firms_fp)
    else:
        return pd.DataFrame(columns=["latitude", "longitude", "acq_date"])

AOI = load_aoi()
FIRMS = load_firms()

st.title("Sudan Mining & Conflict Environmental OSINT Map")
st.caption("Sudan Gold Corridor • Environmental Change & Conflict Heat Explorer")

aoi_names = AOI["region"].unique().tolist()
selected_region = st.sidebar.selectbox("Select Area of Interest", aoi_names)

buffer_geom = AOI[AOI["region"] == selected_region]

st.sidebar.write("AOI:", selected_region)
st.sidebar.write("Buffered AOI Polygon Loaded ✅")

# Time slider placeholder (for once we slice monthly FIRMS & loss)
year = st.sidebar.slider("Year", 2018, 2024, 2024)

if not FIRMS.empty:
    gdf_firms = gpd.GeoDataFrame(
        FIRMS,
        geometry=gpd.points_from_xy(FIRMS.longitude, FIRMS.latitude),
        crs="EPSG:4326"
    )

    gdf_firms = gdf_firms[gdf_firms.geometry.within(buffer_geom.unary_union)]
else:
    gdf_firms = gpd.GeoDataFrame(columns=["latitude","longitude","geometry"])

layers = []

if not gdf_firms.empty:
    layers.append(
        pdk.Layer(
            "HeatmapLayer",
            data=gdf_firms,
            get_position=["longitude","latitude"],
            aggregation="SUM",
            threshold=0.3,
            radius_pixels=50,
            opacity=0.4,
        )
    )

layers.append(
    pdk.Layer(
        "GeoJsonLayer",
        data=buffer_geom.__geo_interface__,
        stroked=True,
        filled=False,
        get_line_color=[255,0,0],
        lineWidthMinPixels=2,
    )
)

midpoint = [buffer_geom.geometry.centroid.y.iloc[0], buffer_geom.geometry.centroid.x.iloc[0]]

view_state = pdk.ViewState(
    latitude=midpoint[0],
    longitude=midpoint[1],
    zoom=8,
    pitch=0
)

r = pdk.Deck(layers=layers, initial_view_state=view_state)

st.pydeck_chart(r)

# Sidebar credit
st.sidebar.markdown("---")
st.sidebar.write("**Data Sources (local)**")
st.sidebar.caption("NASA FIRMS, Hansen GFC, OSM • No external API calls")

st.sidebar.markdown("---")
st.sidebar.write("Made by **Darcy** • OSINT Environmental Analysis")
