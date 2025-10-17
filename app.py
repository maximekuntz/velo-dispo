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
        num_bikes_available = station_status["num_bikes_available"]
        st.metric(":bike: Vélos disponibles", num_bikes_available)
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

# Button to find nearest station with free space when station is full
if selected_station_status["num_docks_available"] == 0:
    st.warning("⚠️ Cette station est pleine, il n'y a pas de places libres pour déposer un vélo.")
    if st.button("🔍 Trouver la station la plus proche avec des places libres", use_container_width=True):
        nearest_station = utils.find_nearest_station_with_free_docks(
            station_lat=selected_station_information["lat"],
            station_lon=selected_station_information["lon"],
            station_information_df=station_information_df,
            station_status_df=station_status_df,
            exclude_station_id=station_id
        )
        
        if nearest_station:
            st.success(f"✅ Station trouvée avec des places libres !")
            st.divider()
            st.subheader(f":bike: {get_language_text(nearest_station['name']).strip()}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**ID de la station** : {nearest_station['station_id']}")
                if "address" in nearest_station:
                    st.write(f"**Adresse** : {nearest_station['address']}")
                st.write(f"**Coordonnées** : {nearest_station['lat']}, {nearest_station['lon']}")
            with col2:
                st.write(f"**Distance** : {nearest_station['distance_km']:.2f} km")
                st.write(f"**Places libres** : {int(nearest_station['num_docks_available'])}")
                st.write(f"**Capacité totale** : {nearest_station['capacity']}")
        else:
            st.error("❌ Aucune station avec des places libres n'a été trouvée dans le réseau.")
