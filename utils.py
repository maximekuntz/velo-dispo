import numpy as np


def distance_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6373.0  # approximate radius of Earth (in km)

    lat1 = np.deg2rad(lat1)
    lon1 = np.deg2rad(lon1)
    lat2 = np.deg2rad(lat2)
    lon2 = np.deg2rad(lon2)

    d = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(d))
