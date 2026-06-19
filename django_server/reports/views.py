# pyrefly: ignore [missing-import]
from django.conf import settings
# pyrefly: ignore [missing-import]
from rest_framework import status
# pyrefly: ignore [missing-import]
from rest_framework.decorators import api_view, parser_classes
# pyrefly: ignore [missing-import]
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
# pyrefly: ignore [missing-import]
from rest_framework.response import Response

from .models import Report
from .serializers import ReportSerializer, ReportCreateSerializer, VoteSerializer
# pyrefly: ignore [missing-import]
from .utils.exif_check import get_exif_gps
# pyrefly: ignore [missing-import]
from .utils.haversine import haversine_km, bounding_box
# pyrefly: ignore [missing-import]
from .utils.cloud import upload_to_cloud


@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def reports_list_create(request):
    if request.method == 'GET':
        return _list_reports(request)
    return _create_report(request)


def _list_reports(request):
    for report in Report.objects.filter(status='active'):
        report.check_and_apply_decay()

    reports = Report.objects.filter(status='active')

    lat_param    = request.query_params.get('lat')
    lng_param    = request.query_params.get('lng')
    radius_param = request.query_params.get('radius')

    if lat_param and lng_param and radius_param:
        try:
            c_lat, c_lng, c_rad = float(lat_param), float(lng_param), float(radius_param)
            if c_rad > 0:
                min_lat, max_lat, min_lng, max_lng = bounding_box(c_lat, c_lng, c_rad)
                candidates = reports.filter(lat__gte=min_lat, lat__lte=max_lat,
                                            lng__gte=min_lng, lng__lte=max_lng)
                ids_in = [r.id for r in candidates if haversine_km(c_lat, c_lng, r.lat, r.lng) <= c_rad]
                reports = Report.objects.filter(id__in=ids_in, status='active')
        except (ValueError, TypeError):
            pass

    return Response({'success': True, 'reports': ReportSerializer(reports, many=True).data, 'total': reports.count()})


def _create_report(request):
    serializer = ReportCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    client_lat = serializer.validated_data['lat']
    client_lng = serializer.validated_data['lng']
    image_url  = None
    image_file = request.FILES.get('image')

    if image_file:
        image_bytes = image_file.read()
        exif_coords = get_exif_gps(image_bytes)
        if exif_coords:
            exif_lat, exif_lng = exif_coords
            dist_km = haversine_km(client_lat, client_lng, exif_lat, exif_lng)
            if dist_km > settings.EXIF_TOLERANCE_KM:
                return Response({
                    'success': False,
                    'error': f'EXIF GPS mismatch: image was taken {dist_km:.2f} km from the reported location.',
                    'exif': {'lat': exif_lat, 'lng': exif_lng},
                    'reported': {'lat': client_lat, 'lng': client_lng},
                }, status=status.HTTP_400_BAD_REQUEST)
        try:
            image_url = upload_to_cloud(image_bytes, image_file.name)
        except Exception as e:
            return Response({'success': False, 'error': f'Cloud upload failed: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

    report = Report.objects.create(
        **serializer.validated_data,
        image_url=image_url,
        user=request.user if request.user.is_authenticated else None,
    )
    return Response({'success': True, 'report': ReportSerializer(report).data}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_report(request, pk):
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        return Response({'success': False, 'error': 'Report not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'success': True, 'report': ReportSerializer(report).data})


@api_view(['PATCH'])
def vote_report(request, pk):
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        return Response({'success': False, 'error': 'Report not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VoteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    if serializer.validated_data['action'] == 'up':
        report.upvotes += 1
    else:
        report.downvotes += 1
    report.save()
    report.check_and_apply_decay()

    return Response({'success': True, 'upvotes': report.upvotes, 'downvotes': report.downvotes, 'status': report.status})


@api_view(['DELETE'])
def delete_report(request, pk):
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        return Response({'success': False, 'error': 'Report not found.'}, status=status.HTTP_404_NOT_FOUND)
    report.status = 'expired'
    report.save(update_fields=['status'])
    return Response({'success': True, 'message': 'Report marked as expired.'})
