import pandas as pd
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

from feed import *
from logger import logger
import utils


GBFS_URLS = {
    "Rennes": "https://eu.ftp.opendatasoft.com/star/gbfs/gbfs.json",
    "Paris et communes limitrophes": "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json",
    "Lyon": "https://download.data.grandlyon.com/files/rdata/jcd_jcdecaux.jcdvelov/gbfs.json",
    "Marseille": "https://api.omega.fifteen.eu/gbfs/2.2/marseille/en/gbfs.json?&key=MjE0ZDNmMGEtNGFkZS00M2FlLWFmMWItZGNhOTZhMWQyYzM2",
    "Agen": "https://api.gbfs.ecovelo.mobi/tempovelo/gbfs.json",
    "Bordeaux": "https://bdx.mecatran.com/utw/ws/gbfs/bordeaux/v3/gbfs.json?apiKey=opendata-bordeaux-metropole-flux-gtfs-rt",
    "Brest": "https://gbfs.partners.fifteen.eu/gbfs/2.2/brest/en/gbfs.json",
    "Carcassonne": "https://api.gbfs.ecovelo.mobi/cyclolibre/gbfs.json",
    "Lille": "https://media.ilevia.fr/opendata/gbfs.json",
    "Montpellier": "https://montpellier-fr.fifteen.site/gbfs/gbfs.json",
    "Mulhouse": "https://api.cyclocity.fr/contracts/mulhouse/gbfs/gbfs.json",
    "Nancy": "https://api.cyclocity.fr/contracts/nancy/gbfs/gbfs.json",
    "Nantes": "https://api.cyclocity.fr/contracts/nantes/gbfs/gbfs.json",
    "Niort": "https://api.gbfs.ecovelo.mobi/tanlib/gbfs.json",
    "Saint-Brieuc": "https://gateway.prod.partners-fs37hd8.zoov.site/gbfs/2.2/saintbrieuc/en/gbfs.json?key=YmE1ZDVlNDYtMGIwNy00MGEyLWIxZWYtNGEwOGQ4NTYxNTYz",
    "Strasbourg": "https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_ae/gbfs.json",
    "Tarbes": "https://api.gbfs.ecovelo.mobi/tlpmobilites/gbfs.json",
    "Epinal": "https://gbfs.partners.fifteen.eu/gbfs/epinal/gbfs.json",
    "La Bresse Gérardmer": "https://api.gbfs.v3.0.ecovelo.mobi/labresse/gbfs.json",
    "Valenciennes": "https://stables.donkey.bike/api/public/gbfs/2/donkey_valenciennes/gbfs",
    "Vichy": "https://gbfs.partners.fifteen.eu/gbfs/vichy/gbfs.json",
}

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
