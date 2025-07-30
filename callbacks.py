import streamlit as st
from streamlit_js_eval import get_geolocation

from feed import get_language_text
from logger import logger
import utils


def update_selected_station_from_list():
    st.session_state.station_id = st.session_state.station_information_df[
        st.session_state.station_information_df_names == st.session_state.station_name
    ].to_dict(orient="records")[0]["station_id"]
    st.session_state.selected_station_information = (
        st.session_state.station_information_df[
            st.session_state.station_information_df["station_id"]
            == st.session_state.station_id
        ].to_dict(orient="records")[0]
    )


def update_selected_station_from_geolocation():
    geolocation = get_geolocation(component_key="user_location")
    logger.debug(f"Geolocation data: {geolocation}")
    if not geolocation:
        st.toast(
            "Autorisez l'accès à votre position pour utiliser cette fonctionnalité.",
            icon="⚠️",
        )
    else:
        user_lat = geolocation["coords"]["latitude"]
        user_lon = geolocation["coords"]["longitude"]
        st.write(f"Votre position est : {user_lat}, {user_lon}.")
        st.session_state.station_information_df["distance_km"] = (
            st.session_state.station_information_df.apply(
                lambda row: utils.distance_haversine(
                    user_lat, user_lon, row["lat"], row["lon"]
                ),
                axis=1,
            )
        )
        st.session_state.selected_station_information = (
            st.session_state.station_information_df.loc[
                st.session_state.station_information_df["distance_km"].idxmin()
            ].to_dict()
        )
        logger.debug(
            "Station la plus proche :", st.session_state.selected_station_information
        )
        st.session_state.station_name = get_language_text(
            st.session_state.selected_station_information["name"]
        )
        st.session_state.station_id = st.session_state.selected_station_information[
            "station_id"
        ]
