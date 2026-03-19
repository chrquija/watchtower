import streamlit as st
import pandas as pd
import pydeck as pdk


def render_map(
    latitude: float,
    longitude: float,
    *,
    height: int = 620,
    zoom: int = 14,
    label: str = "Intersection",
    registry: list = None,
):
    """Render an interactive map centered on the given coordinates with a label.

    - Places a marker and text label at the intersection location
    - Shows other intersections from the registry if provided
    - Uses OpenStreetMap tiles (no Mapbox token required)
    - Intended to be used in the right-hand column of the dashboard
    """

    # Prepare data for all points
    if registry:
        df = pd.DataFrame(registry)
        # Ensure 'name' is present for tooltips and labels
        if 'label' in df.columns and 'name' not in df.columns:
            df['name'] = df['label']
    else:
        # Fallback to single-point if no registry provided
        df = pd.DataFrame({
            "lat": [latitude],
            "lon": [longitude],
            "name": [label],
        })

    # Styling logic: Distinguish the selected intersection
    def get_color(row):
        # We compare by coordinates and label for robustness
        is_selected = (
            abs(row['lat'] - latitude) < 1e-6 and
            abs(row['lon'] - longitude) < 1e-6 and
            row['name'] == label
        )
        if is_selected:
            return [230, 57, 70, 250]  # Bright Red for selected
        return [31, 69, 130, 180]      # Theme Blue for others

    def get_radius(row):
        is_selected = (
            abs(row['lat'] - latitude) < 1e-6 and
            abs(row['lon'] - longitude) < 1e-6 and
            row['name'] == label
        )
        return 60 if is_selected else 40

    df['color'] = df.apply(get_color, axis=1)
    df['radius'] = df.apply(get_radius, axis=1)

    # Special landmark: Indian Wells Tennis Garden
    landmark_data = pd.DataFrame([{
        "lat": 33.723664,
        "lon": -116.305232,
        "name": "Indian Wells Tennis Garden",
        "icon": "★"
    }])

    # For the text layer, we show labels for ALL intersections to make it easy to see what's what,
    # but we will only apply the background box to the selected one to keep it distinguished.
    # Alternatively, we only show the label for the selected one.
    # Let's show all labels but maybe make unselected ones smaller/different?
    # User said: "make sure the dots are distinguished so users know which intersection they are analyzing"
    # Showing ONLY the selected label is the cleanest way to distinguish.
    df_labels = df[df['color'].apply(lambda x: x[0] == 230)]

    view_state = pdk.ViewState(
        latitude=latitude,
        longitude=longitude,
        zoom=zoom,
        pitch=0,
        bearing=0,
    )

    # Base map without requiring a Mapbox token
    tile_layer = pdk.Layer(
        "TileLayer",
        data="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        min_zoom=0,
        max_zoom=19,
        tile_size=256,
    )

    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat]",
        get_radius="radius",
        get_fill_color="color",
        pickable=True,
    )

    text_layer = pdk.Layer(
        "TextLayer",
        data=df_labels,
        get_position="[lon, lat]",
        get_text="name",
        get_color=[230, 57, 70, 255],
        get_size=18,
        get_alignment_baseline="bottom",
        get_pixel_offset=[0, -18],
    )

    landmark_layer = pdk.Layer(
        "TextLayer",
        data=landmark_data,
        get_position="[lon, lat]",
        get_text="icon",
        get_size=44,
        get_color=[255, 215, 0, 255],  # Gold
        get_alignment_baseline="center",
        pickable=True,
    )

    deck = pdk.Deck(
        initial_view_state=view_state,
        map_style=None,
        layers=[tile_layer, point_layer, text_layer, landmark_layer],
        tooltip={"text": "{name}\n({lat}, {lon})"},
    )


    # Add visual legend for markers above the map
    st.markdown(
        """
        <div style="display: flex; flex-direction: column; align-items: center; padding: 12px; background: var(--secondary-background-color); border-radius: 12px; margin-bottom: 10px; border: 1px solid var(--border-color); box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="font-weight: bold; color: var(--text-color); margin-bottom: 10px; border-bottom: 1px solid var(--border-color); width: 100%; text-align: center; padding-bottom: 6px; font-size: 0.9rem;">Map Legend</div>
            <div style="display: flex; justify-content: center; gap: 20px; font-size: 0.85rem; width: 100%;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="height: 12px; width: 12px; background-color: rgb(230, 57, 70); border-radius: 50%; display: inline-block; border: 2px solid white; box-shadow: 0 0 0 1px rgb(230, 57, 70);"></span>
                    <span style="font-weight: 600; color: var(--text-color);">Selected Intersection</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="height: 12px; width: 12px; background-color: rgb(31, 69, 130); border-radius: 50%; display: inline-block; border: 2px solid white; box-shadow: 0 0 0 1px rgb(31, 69, 130);"></span>
                    <span style="font-weight: 600; color: var(--text-color);">Other Intersections</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.1rem; line-height: 1; color: var(--text-color);">★</span>
                    <span style="font-weight: 600; color: var(--text-color);">Tennis Garden</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.pydeck_chart(deck, use_container_width=True, height=height)
