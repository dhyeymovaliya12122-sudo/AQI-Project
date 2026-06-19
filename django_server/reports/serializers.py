# pyrefly: ignore [missing-import]
from rest_framework import serializers
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from .models import Report


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model  = User
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ReportSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model  = Report
        fields = ['id', 'lat', 'lng', 'type', 'severity', 'description',
                  'image_url', 'upvotes', 'downvotes', 'status', 'created_at', 'username']

    def get_username(self, obj):
        return obj.user.username if obj.user else 'anonymous'


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Report
        fields = ['lat', 'lng', 'type', 'severity', 'description']

    def validate_severity(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError('severity must be between 1 and 5.')
        return value

    def validate_type(self, value):
        valid = [c[0] for c in Report.POLLUTION_TYPES]
        if value not in valid:
            raise serializers.ValidationError(f'type must be one of: {", ".join(valid)}')
        return value


class VoteSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['up', 'down'])
