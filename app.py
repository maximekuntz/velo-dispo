import pandas as pd
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

from feed import *
from feeds_urls import GBFS_URLS
from logger import logger
import utils


st.set_page_config(
    page_title="Vélo Dispo",
    page_icon=":bike:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title(":bike: Vélo Dispo | Trouver un vélo en libre-service")
st.write(
    "Bienvenue sur Vélo Dispo :bike:, l'application qui vous permet de trouver un vélo en libre-service à proximité de votre position."
)


@st.cache_data
def get_feed(url: str):
    response = requests.get(url)
    r = response.json()
    data = r["data"]
    if "feeds" in data:
        return data["feeds"]
    language_key = list(data.keys())[0]
    return data[language_key]["feeds"]


@st.fragment
def display_station_location(station_info: dict):
    if "distance_km" in station_info:
        distance = station_info["distance_km"]
        st.write(f"Distance : {distance:.2f} km")
    if "address" in station_info:
        address = station_info["address"]
        st.write(f"Adresse : {address}")
    latitude, longitude = station_info["lat"], station_info["lon"]
    st.write(f"Coordonnées : {latitude}, {longitude}")


@st.fragment
def display_station_metrics(station_information: dict, station_status: dict):
    col1, col2, col3 = st.columns(3)
    with col1:
        capacity = station_information["capacity"]
        st.metric("Capacité totale", capacity)
    with col2:
        num_bikes_available = station_status.get("num_bikes_available", None)
        if num_bikes_available is None:
            num_bikes_available = station_status.get("num_vehicles_available")
        st.metric(":bike: Vélos disponibles", num_bikes_available)

        # Deduplicate and prioritize vehicle type data sources
        count_by_type = None
        expander_label = ""
        if station_status.get("vehicle_types_available"):
            count_by_type = station_status["vehicle_types_available"]
            expander_label = "Types de véhicules disponibles"
            def iter_types():
                for type_count in count_by_type:
                    vehicle_type = type_count["vehicle_type_id"]
                    vehicle_qty = type_count["count"]
                    yield vehicle_type, vehicle_qty
        elif station_status.get("num_bikes_available_types"):
            count_by_type = station_status["num_bikes_available_types"]
            expander_label = "Types de vélos disponibles"
            def iter_types():
                for elt in count_by_type:
                    for vehicle_type, vehicle_qty in elt.items():
                        yield vehicle_type, vehicle_qty
        else:
            def iter_types():
                return
                yield

        if count_by_type:
            with st.expander(expander_label, expanded=False):
                for vehicle_type, vehicle_qty in iter_types():
                    icon = "⚡" if utils.is_electric_bike(vehicle_type) else ""
                    if vehicle_qty > 0:
                        st.metric(label=f"{icon}{vehicle_type}", value=vehicle_qty)

    with col3:
        num_docks_available = station_status["num_docks_available"]
        st.metric(":parking: Places libres", num_docks_available)


with st.sidebar:
    city = st.selectbox("Choisir une ville", list(GBFS_URLS.keys()))

    gbfs_url = GBFS_URLS[city]
    feeds = get_feed(url=gbfs_url)

    system_information_url = get_system_information_feed(feeds)
    system_information = requests.get(system_information_url).json()

    station_information_url = get_station_information_feed(feeds)
    station_information = requests.get(station_information_url).json()
    station_information_df = pd.DataFrame(station_information["data"]["stations"])

    station_status_url = get_station_status_feed(feeds)
    station_status = requests.get(station_status_url).json()
    station_status_df = pd.DataFrame(station_status["data"]["stations"])

    st.metric("Réseau", get_language_text(system_information["data"]["name"]))
    st.metric("Nombre de stations", len(station_information["data"]["stations"]))

    st.divider()

    st.write(f"Nous récupérons les données en temps réel des stations de vélos en libre-service [ici]({gbfs_url}).")
    operator = system_information.get("data").get("operator")
    operator_msg = f" sont fournies par {operator} et" if operator else ""
    st.write(f"Les données{operator_msg} sont mises à jour toutes les {system_information['ttl']} secondes.")
    try:
        last_update_timestamp = pd.to_datetime(station_information.get("last_updated"), unit="s")
        st.write(f"Dernière actualisation : {last_update_timestamp}")
    except:
        pass

station_information_df_names = station_information_df["name"].apply(get_language_text)

station_selection_cols = st.columns(2)
with station_selection_cols[0]:
    # Selection in a list
    station_name = st.selectbox("Choisir une station", station_information_df_names)
    station_id = station_information_df[station_information_df_names == station_name].to_dict(orient="records")[0][
        "station_id"
    ]
    selected_station_information = station_information_df[station_information_df["station_id"] == station_id].to_dict(
        orient="records"
    )[0]
with station_selection_cols[1]:
    # Selection of the closest station
    if st.button("Station la plus proche", key="geolocation_button", use_container_width=True):
        geolocation = get_geolocation(component_key="user_location")
        logger.debug(f"Geolocation data: {geolocation}")
        if not geolocation:
            st.toast("Autorisez l'accès à votre position pour utiliser cette fonctionnalité.", icon="⚠️")
        else:
            user_lat = geolocation["coords"]["latitude"]
            user_lon = geolocation["coords"]["longitude"]
            st.write(f"Votre position est : {user_lat}, {user_lon}.")
            station_information_df["distance_km"] = station_information_df.apply(
                lambda row: utils.distance_haversine(user_lat, user_lon, row["lat"], row["lon"]),
                axis=1,
            )
            selected_station_information = station_information_df.loc[
                station_information_df["distance_km"].idxmin()
            ].to_dict()
            logger.debug("Station la plus proche :", selected_station_information)
            station_name = get_language_text(selected_station_information["name"])
            station_id = selected_station_information["station_id"]

col1, col2 = st.columns(2)
with col1:
    st.write(f"Vous avez choisi la station **{station_name.strip()}** (id : {station_id})")
with col2:
    display_station_location(station_info=selected_station_information)

# Show availability
selected_station_status = station_status_df[station_status_df["station_id"] == station_id].to_dict(orient="records")[0]
display_station_metrics(station_information=selected_station_information, station_status=selected_station_status)
