# Analysis regions. Each India zone is a set of sample points (approx. 1 per ~100 km);
# each point is one NASA POWER request (one MERRA-2 grid cell).
# Code generated with AI assistance (Claude, Anthropic).
import numpy as np

ZONES = {
    "Northwest India": {
        "desc": "Drier north-western plains and desert fringe",
        "points": [(30.9, 75.8, "near Ludhiana"), (28.6, 77.2, "near Delhi"), (26.9, 75.8, "near Jaipur"),
                   (26.3, 73.0, "near Jodhpur"), (26.9, 70.9, "near Jaisalmer"), (24.6, 73.7, "near Udaipur")],
    },
    "Western India": {
        "desc": "Western coast and Deccan edge",
        "points": [(19.1, 72.9, "near Mumbai"), (18.5, 73.9, "near Pune"), (15.5, 73.8, "near Goa"),
                   (21.2, 72.8, "near Surat"), (23.0, 72.6, "near Ahmedabad"), (19.9, 75.3, "near Aurangabad")],
    },
    "Central India": {
        "desc": "Central plateau and Vidarbha",
        "points": [(23.3, 77.4, "near Bhopal"), (21.1, 79.1, "near Nagpur"), (21.2, 81.6, "near Raipur"),
                   (23.2, 79.9, "near Jabalpur"), (22.7, 75.9, "near Indore"), (19.1, 82.0, "near Jagdalpur")],
    },
    "Northeast India": {
        "desc": "High-rainfall north-east hills and Brahmaputra valley",
        "points": [(26.1, 91.7, "near Guwahati"), (25.6, 91.9, "near Shillong"), (24.8, 93.9, "near Imphal"),
                   (27.1, 93.6, "Arunachal foothills"), (23.8, 91.3, "near Agartala"), (25.7, 94.1, "near Kohima")],
    },
    "Southern India": {
        "desc": "Peninsular India",
        "points": [(8.5, 76.9, "near Thiruvananthapuram"), (9.9, 76.3, "near Kochi"), (13.0, 80.3, "near Chennai"),
                   (13.0, 77.6, "near Bengaluru"), (17.4, 78.5, "near Hyderabad"), (11.0, 77.0, "near Coimbatore")],
    },
}


def india_points():
    """-> list of dicts {zone, lat, lon, label}"""
    out = []
    for zname, z in ZONES.items():
        for lat, lon, label in z["points"]:
            out.append({"zone": zname, "lat": lat, "lon": lon, "label": label})
    return out


def point_scope(lat, lon):
    return [{"zone": "Selected point", "lat": round(float(lat), 4), "lon": round(float(lon), 4), "label": "custom point"}]


def box_scope(lat_min, lat_max, lon_min, lon_max, max_per_axis=4):
    """Sample a rectangle on a regular grid (>= ~1 deg spacing, at most 4 x 4 points)."""
    nlat = int(np.clip(round((lat_max - lat_min) / 1.0) + 1, 2, max_per_axis))
    nlon = int(np.clip(round((lon_max - lon_min) / 1.0) + 1, 2, max_per_axis))
    pts = []
    for la in np.linspace(lat_min, lat_max, nlat):
        for lo in np.linspace(lon_min, lon_max, nlon):
            pts.append({"zone": "Custom box", "lat": round(float(la), 4), "lon": round(float(lo), 4), "label": "box sample"})
    return pts
