"""Haversine Proximity Formula — FRD §2D."""
import math


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    phi1, phi2   = math.radians(lat1), math.radians(lat2)
    d_phi        = math.radians(lat2 - lat1)
    d_lambda     = math.radians(lng2 - lng1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bounding_box(lat, lng, radius_km):
    lat_deg = radius_km / 111.0
    lng_deg = radius_km / (111.0 * math.cos(math.radians(lat)))
    return lat - lat_deg, lat + lat_deg, lng - lng_deg, lng + lng_deg
