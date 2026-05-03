from django.contrib import admin
from .models import ParkingZone, ParkingSlot, UserProfile, ParkingSession, Payment

@admin.register(ParkingZone)
class ParkingZoneAdmin(admin.ModelAdmin):
    list_display = ['zone_id', 'name', 'capacity', 'occupied', 'hourly_rate', 'is_active']
    list_filter = ['zone_type', 'is_active']
    search_fields = ['zone_id', 'name']

@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ['slot_number', 'zone', 'slot_type', 'status', 'sensor_id']
    list_filter = ['slot_type', 'status', 'zone']
    search_fields = ['slot_number', 'sensor_id']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'vehicle_number', 'vehicle_type', 'is_premium_member']
    search_fields = ['user__username', 'vehicle_number']

@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'slot', 'vehicle_number', 'status', 'start_time']
    list_filter = ['status']
    search_fields = ['vehicle_number']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'session', 'amount', 'status', 'payment_date']
    list_filter = ['status', 'payment_method']