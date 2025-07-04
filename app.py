import pandas as pd
import requests
import streamlit as st


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


def get_specific_feed(feeds: dict, feed_name: str):
    for feed in feeds:
        if feed["name"] == feed_name:
            return feed["url"]
    raise ValueError(f"No '{feed_name}' feed found")


def get_system_information_feed(feeds: dict):
    return get_specific_feed(feeds, "system_information")


def get_language_text(texts: list[dict] | str, language: str | None = None):
    if type(texts) is str:
        print("Not a list, returning value.")
        return texts

    if language is None:
        return texts[0]["text"]
    for name in texts:
        if name["language"] == language:
            return name["text"]
    raise ValueError(f"No text found for language '{language}'")


def get_station_information_feed(feeds: dict):
    return get_specific_feed(feeds, "station_information")


def get_station_status_feed(feeds: dict):
    return get_specific_feed(feeds, "station_status")


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
station_name = st.selectbox("Choisir une station", station_information_df_names)
station_id = station_information_df[station_information_df_names == station_name]["station_id"].values[0]

station_information_selected = station_information_df[station_information_df["station_id"] == station_id]
station_status_selected = station_status_df[station_status_df["station_id"] == station_id]


col1, col2 = st.columns(2)
with col1:
    st.write(f"Vous avez choisi la station **{station_name.strip()}** (id : {station_id})")
with col2:
    if "address" in station_information_selected.columns:
        address = station_information_selected["address"].values[0]
        st.write(f"Adresse : {address}")
    latitude = station_information_selected["lat"].values[0]
    longitude = station_information_selected["lon"].values[0]
    st.write(f"Coordonnées : {latitude}, {longitude}")

col1, col2, col3 = st.columns(3)
with col1:
    capacity = station_information_selected["capacity"].values[0]
    st.metric("Capacité totale", capacity)
with col2:
    num_bikes_available = station_status_selected["num_bikes_available"].values[0]
    st.metric(":bike: Vélos disponibles", num_bikes_available)
with col3:
    num_docks_available = station_status_selected["num_docks_available"].values[0]
    st.metric(":parking: Places libres", num_docks_available)
