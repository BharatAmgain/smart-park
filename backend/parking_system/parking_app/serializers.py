from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ParkingZone, ParkingSlot, UserProfile, ParkingSession, Payment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'phone_number', 'vehicle_number', 'vehicle_type',
                  'is_premium_member', 'total_parking_hours', 'total_spent']


class ParkingZoneSerializer(serializers.ModelSerializer):
    available_slots = serializers.SerializerMethodField()
    availability_percentage = serializers.SerializerMethodField()

    class Meta:
        model = ParkingZone
        fields = ['zone_id', 'name', 'description', 'zone_type', 'capacity', 'occupied',
                  'hourly_rate', 'location_x', 'location_y', 'is_active',
                  'available_slots', 'availability_percentage', 'created_at', 'updated_at']

    def get_available_slots(self, obj):
        return obj.get_available_slots_count()

    def get_availability_percentage(self, obj):
        return obj.get_availability()


class ParkingSlotSerializer(serializers.ModelSerializer):
    zone = ParkingZoneSerializer(read_only=True)
    zone_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ParkingSlot
        fields = ['slot_number', 'zone', 'zone_id', 'slot_type', 'status', 'is_reserved',
                  'sensor_id', 'location_x', 'location_y', 'reserved_until', 'last_updated']
        read_only_fields = ['last_updated']


class ParkingSessionSerializer(serializers.ModelSerializer):
    slot = ParkingSlotSerializer(read_only=True)
    slot_number = serializers.CharField(write_only=True, required=False)
    duration_hours = serializers.SerializerMethodField()

    class Meta:
        model = ParkingSession
        fields = ['session_id', 'user', 'slot', 'slot_number', 'start_time', 'end_time',
                  'actual_end_time', 'status', 'payment_status', 'total_amount',
                  'vehicle_number', 'notes', 'duration_hours', 'created_at', 'updated_at']
        read_only_fields = ['session_id', 'created_at', 'updated_at']

    def get_duration_hours(self, obj):
        return obj.get_duration_hours()


class PaymentSerializer(serializers.ModelSerializer):
    session = ParkingSessionSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ['payment_id', 'session', 'amount', 'payment_method',
                  'transaction_id', 'status', 'payment_date', 'receipt_url']
        read_only_fields = ['payment_id', 'payment_date']


class ParkingRequestSerializer(serializers.Serializer):
    """Serializer for parking allocation request"""
    vehicle_type = serializers.ChoiceField(
        choices=['Sedan', 'SUV', 'Compact', 'EV', 'Truck', 'Motorcycle', 'Any'],
        default='Sedan'
    )
    vehicle_number = serializers.CharField(max_length=20)
    user_lat = serializers.FloatField(required=False, allow_null=True)
    user_lng = serializers.FloatField(required=False, allow_null=True)
    user_location_x = serializers.FloatField(required=False, allow_null=True)
    user_location_y = serializers.FloatField(required=False, allow_null=True)
    priority = serializers.ChoiceField(
        choices=['nearest', 'cheapest', 'premium', 'ev_charging', 'fastest'],
        default='nearest'
    )
    duration = serializers.IntegerField(min_value=1, max_value=24, default=2)
    is_reservation = serializers.BooleanField(default=False)
    preferred_zone = serializers.CharField(required=False, max_length=10, allow_null=True)


class AllocationResponseSerializer(serializers.Serializer):
    """Serializer for parking allocation response"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    slot_number = serializers.CharField(required=False, allow_null=True)
    zone_id = serializers.CharField(required=False, allow_null=True)
    session_id = serializers.CharField(required=False, allow_null=True)
    distance_meters = serializers.FloatField(required=False, allow_null=True)
    walk_time_minutes = serializers.IntegerField(required=False, allow_null=True)
    hourly_rate = serializers.FloatField(required=False, allow_null=True)