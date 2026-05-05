from rest_framework import serializers
from rareapi.models import RareUser


class UserSummarySerializer(serializers.ModelSerializer):
    """Minimal user representation for nesting inside posts, comments, etc."""
    class Meta:
        model = RareUser
        fields = ['id', 'username']


class ProfileDetailSerializer(serializers.ModelSerializer):
    """Full user profile for the detail endpoint."""
    full_name = serializers.SerializerMethodField()
    created_on = serializers.DateField(format='%m/%d/%Y')
    user_type = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    subscriber_count = serializers.SerializerMethodField()
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = RareUser
        fields = [
            'id', 'full_name', 'username', 'email',
            'profile_image_url', 'created_on', 'user_type',
            'is_subscribed', 'subscriber_count', 'post_count',
        ]

    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip()

    def get_user_type(self, obj):
        return 'Admin' if obj.is_staff else 'Author'

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.subscribers.filter(
            follower=request.user, ended_on__isnull=True
        ).exists()

    def get_subscriber_count(self, obj):
        return obj.subscribers.filter(ended_on__isnull=True).count()

    def get_post_count(self, obj):
        return obj.posts.filter(approved=True).count()


class ProfileListSerializer(serializers.ModelSerializer):
    """Slim user profile for admin list endpoint."""
    full_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = RareUser
        fields = ['id', 'full_name', 'username', 'user_type', 'is_active']

    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip()

    def get_user_type(self, obj):
        return 'Admin' if obj.is_staff else 'Author'


class RegisterSerializer(serializers.ModelSerializer):
    """Validates and creates a new user during registration."""
    class Meta:
        model = RareUser
        fields = ['username', 'password', 'first_name', 'last_name', 'email', 'bio']
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    def create(self, validated_data):
        return RareUser.objects.create_user(
            **validated_data,
            is_active=True,
        )
