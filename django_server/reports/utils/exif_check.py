"""EXIF GPS Fraud Verification — FRD §2B. Uses Pillow in-memory."""
import io
# pyrefly: ignore [missing-import]
from PIL import Image
# pyrefly: ignore [missing-import]
from PIL.ExifTags import TAGS, GPSTAGS


def _convert_to_degrees(value):
    def to_float(v):
        if isinstance(v, tuple) and len(v) == 2:
            return v[0] / v[1] if v[1] != 0 else 0
        return float(v)
    return to_float(value[0]) + to_float(value[1]) / 60.0 + to_float(value[2]) / 3600.0


def get_exif_gps(image_bytes: bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif_data = img._getexif()
        if not exif_data:
            return None
        gps_info_raw = None
        for tag_id, value in exif_data.items():
            if TAGS.get(tag_id) == 'GPSInfo':
                gps_info_raw = value
                break
        if not gps_info_raw:
            return None
        gps_data = {GPSTAGS.get(k, k): v for k, v in gps_info_raw.items()}
        if 'GPSLatitude' not in gps_data or 'GPSLongitude' not in gps_data:
            return None
        lat = _convert_to_degrees(gps_data['GPSLatitude'])
        lng = _convert_to_degrees(gps_data['GPSLongitude'])
        if gps_data.get('GPSLatitudeRef', 'N') == 'S':
            lat = -lat
        if gps_data.get('GPSLongitudeRef', 'E') == 'W':
            lng = -lng
        return (lat, lng)
    except Exception:
        return None
