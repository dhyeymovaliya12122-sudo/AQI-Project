import math
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from reports.models import Report

GRID_CELL_DEG = 0.005  # ~500m grid


def grid_key(lat, lng):
    return (math.floor(lat / GRID_CELL_DEG), math.floor(lng / GRID_CELL_DEG))


def cell_center(key):
    return (key[0] + 0.5) * GRID_CELL_DEG, (key[1] + 0.5) * GRID_CELL_DEG


def get_active_reports():
    qs = list(Report.objects.filter(status='active'))
    for r in qs:
        r.check_and_apply_decay()
    return list(Report.objects.filter(status='active'))


@api_view(['GET'])
def heatmap(request):
    active = get_active_reports()
    cells = {}
    for r in active:
        cells.setdefault(grid_key(r.lat, r.lng), []).append(r)

    points = []
    for key, reports in cells.items():
        c_lat, c_lng = cell_center(key)
        avg_sev = sum(r.severity for r in reports) / len(reports)
        avg_upvote = sum(
            r.upvotes / (r.upvotes + r.downvotes) if (r.upvotes + r.downvotes) > 0 else 0.5
            for r in reports
        ) / len(reports)
        density   = min(len(reports) / 10, 1.0)
        intensity = (avg_sev / 5) * 0.6 + avg_upvote * 0.2 + density * 0.2
        points.append({'lat': round(c_lat, 6), 'lng': round(c_lng, 6),
                        'intensity': round(intensity, 4), 'count': len(reports)})

    return Response({'success': True, 'points': points})


@api_view(['GET'])
def stats(request):
    active = get_active_reports()
    all_r  = list(Report.objects.all())

    type_count = {t[0]: 0 for t in Report.POLLUTION_TYPES}
    for r in active:
        type_count[r.type] = type_count.get(r.type, 0) + 1

    avg_sev = round(sum(r.severity for r in active) / len(active), 2) if active else 0

    sev_dist = [{'level': l, 'count': sum(1 for r in active if r.severity == l)} for l in range(1, 6)]

    cells = {}
    for r in active:
        cells.setdefault(grid_key(r.lat, r.lng), []).append(r)
    top = sorted(cells.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    hotspots = [{'lat': round(cell_center(k)[0], 6), 'lng': round(cell_center(k)[1], 6),
                  'count': len(v), 'avgSeverity': round(sum(r.severity for r in v)/len(v), 2)} for k, v in top]

    return Response({'success': True, 'stats': {
        'totalActive': len(active), 'totalAll': len(all_r),
        'totalExpired': len(all_r) - len(active), 'avgSeverity': avg_sev,
        'typeBreakdown': type_count, 'severityDistribution': sev_dist, 'topHotspots': hotspots,
    }})


@api_view(['GET'])
def cdi(request):
    active = get_active_reports()
    if not active:
        return Response({'success': True, 'zones': [], 'cityAvgCDI': 0})

    cells = {}
    for r in active:
        cells.setdefault(grid_key(r.lat, r.lng), []).append(r)

    now = timezone.now()
    raw_scores = []
    for key, reports in cells.items():
        c_lat, c_lng = cell_center(key)
        avg_sev   = sum(r.severity for r in reports) / len(reports)
        density   = len(reports)
        recency   = sum(max(0, 1 - (now - r.created_at).total_seconds() / (72*3600)) for r in reports) / len(reports)
        raw_scores.append({'lat': round(c_lat, 6), 'lng': round(c_lng, 6),
                            'rawCDI': avg_sev * density * recency,
                            'density': density, 'avgSeverity': round(avg_sev, 2)})

    max_raw = max((z['rawCDI'] for z in raw_scores), default=1) or 1
    zones = sorted([{'lat': z['lat'], 'lng': z['lng'],
                      'cdiScore': round((z['rawCDI'] / max_raw) * 100, 1),
                      'reportCount': z['density'], 'avgSeverity': z['avgSeverity']}
                     for z in raw_scores], key=lambda z: z['cdiScore'], reverse=True)

    return Response({'success': True, 'zones': zones,
                     'cityAvgCDI': round(sum(z['cdiScore'] for z in zones) / len(zones), 1)})
