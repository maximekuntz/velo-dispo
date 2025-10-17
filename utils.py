import numpy as np
import pandas as pd


def distance_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6373.0  # approximate radius of Earth (in km)

    lat1 = np.deg2rad(lat1)
    lon1 = np.deg2rad(lon1)
    lat2 = np.deg2rad(lat2)
    lon2 = np.deg2rad(lon2)

    d = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(d))


def find_nearest_station_with_free_docks(
    station_lat: float,
    station_lon: float,
    station_information_df: pd.DataFrame,
    station_status_df: pd.DataFrame,
    exclude_station_id: str = None
) -> dict | None:
    """
    Find the nearest station with free docks from a given location.
    
    Args:
        station_lat: Latitude of the reference station
        station_lon: Longitude of the reference station
        station_information_df: DataFrame with station information
        station_status_df: DataFrame with station status
        exclude_station_id: Station ID to exclude from search (typically the current station)
    
    Returns:
        Dictionary with station information and distance, or None if no station found
    """
    # Merge station information with status
    merged_df = station_information_df.merge(
        station_status_df[["station_id", "num_docks_available"]],
        on="station_id"
    )
    
    # Filter stations with free docks
    available_stations = merged_df[merged_df["num_docks_available"] > 0]
    
    # Exclude the current station if specified
    if exclude_station_id:
        available_stations = available_stations[available_stations["station_id"] != exclude_station_id]
    
    # If no stations with free docks found
    if available_stations.empty:
        return None
    
    # Calculate distances from the reference station
    available_stations = available_stations.copy()
    available_stations["distance_km"] = available_stations.apply(
        lambda row: distance_haversine(station_lat, station_lon, row["lat"], row["lon"]),
        axis=1,
    )
    
    # Find the nearest station
    nearest_station = available_stations.loc[available_stations["distance_km"].idxmin()].to_dict()
    
    return nearest_station
