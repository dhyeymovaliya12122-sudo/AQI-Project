# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from rest_framework import status
# pyrefly: ignore [missing-import]
from rest_framework.decorators import api_view
# pyrefly: ignore [missing-import]
from rest_framework.response import Response
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


@api_view(['POST'])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    user = serializer.save()
    return Response({'success': True, 'message': 'Account created successfully.',
                     'username': user.username, **get_tokens_for_user(user)}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'success': False, 'error': 'username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.check_password(password):
        return Response({'success': False, 'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({'success': True, 'username': user.username, **get_tokens_for_user(user)})
