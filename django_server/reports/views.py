import io
# pyrefly: ignore [missing-import]
from django.conf import settings
# pyrefly: ignore [missing-import]
from django.db.models import F
# pyrefly: ignore [missing-import]
from rest_framework import status
# pyrefly: ignore [missing-import]
from rest_framework.decorators import api_view, parser_classes
# pyrefly: ignore [missing-import]
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
# pyrefly: ignore [missing-import]
from rest_framework.response import Response
# pyrefly: ignore [missing-import]
from PIL import Image

from .models import Report
from .serializers import ReportSerializer, ReportCreateSerializer, VoteSerializer
# pyrefly: ignore [missing-import]
from .utils.exif_check import get_exif_gps
# pyrefly: ignore [missing-import]
from .utils.haversine import haversine_km, bounding_box
# pyrefly: ignore [missing-import]
from .utils.cloud import upload_to_cloud

# FIX 5 — Decompression bomb protection: reject images exceeding ~5000x5000 pixels
Image.MAX_IMAGE_PIXELS = 25_000_000

# FIX 6 — Allowed image MIME types (mapped from Pillow format names)
PILLOW_FORMAT_TO_MIME = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'WEBP': 'image/webp',
    'GIF': 'image/gif',
}
ALLOWED_IMAGE_MIMES = set(PILLOW_FORMAT_TO_MIME.values())


def _validate_image(image_file):
    """Validate uploaded image: integrity, bomb protection, and MIME type.

    Returns a Response on failure, or None on success.
    Resets file pointer after validation so callers can still read the file.
    """
    try:
        image_file.seek(0)
        img = Image.open(image_file)
        img.verify()  # checks structural integrity without full decode
    except Image.DecompressionBombError:
        # FIX 5 — Image exceeds MAX_IMAGE_PIXELS
        return Response(
            {'success': False, 'error': 'Image dimensions exceed allowed limits.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        # FIX 4 — Corrupted, disguised, or malformed image
        return Response(
            {'success': False, 'error': 'Invalid image file.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # FIX 6 — MIME type validation using Pillow's magic-byte detection
    detected_mime = PILLOW_FORMAT_TO_MIME.get(img.format)
    if detected_mime not in ALLOWED_IMAGE_MIMES:
        return Response(
            {'success': False, 'error': 'Unsupported image format.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_file.seek(0)
    return None  # valid


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
        # FIX 4/5/6 — Validate image before any EXIF or upload processing
        validation_error = _validate_image(image_file)
        if validation_error is not None:
            return validation_error

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

    # FIX 1 — Atomic update using F() expressions to prevent lost updates
    if serializer.validated_data['action'] == 'up':
        Report.objects.filter(pk=pk).update(upvotes=F('upvotes') + 1)
    else:
        Report.objects.filter(pk=pk).update(downvotes=F('downvotes') + 1)

    report.refresh_from_db()
    report.check_and_apply_decay()

    return Response({'success': True, 'upvotes': report.upvotes, 'downvotes': report.downvotes, 'status': report.status})


@api_view(['DELETE'])
def delete_report(request, pk):
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        return Response({'success': False, 'error': 'Report not found.'}, status=status.HTTP_404_NOT_FOUND)

    # FIX 2 — Authorization checks
    if request.user.is_authenticated and request.user.is_superuser:
        # Superusers can delete any report
        pass
    elif request.user.is_authenticated:
        # Authenticated users can only delete their own reports
        if report.user != request.user:
            return Response({'success': False, 'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
    else:
        # Anonymous users can only delete anonymous reports (user is NULL)
        if report.user is not None:
            return Response({'success': False, 'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    report.status = 'expired'
    report.save(update_fields=['status'])
    return Response({'success': True, 'message': 'Report marked as expired.'})
