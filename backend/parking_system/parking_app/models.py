from django.db import models
from django.contrib.auth.models import User
import uuid

class ParkingZone(models.Model):
    ZONE_TYPES = [
        ('hospital', 'Hospital'),
        ('heritage', 'Heritage (Dharahara)'),
        ('shopping', 'Shopping Center'),
        ('government', 'Government Office'),
        ('cinema', 'Cinema Hall'),
        ('regular', 'Regular Parking'),
    ]
    zone_id = models.CharField(max_length=10, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPES, default='regular')
    capacity = models.IntegerField(default=0)
    occupied = models.IntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, default=50.0)
    location_x = models.FloatField(default=0.0)
    location_y = models.FloatField(default=0.0)
    address = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_availability(self):
        if self.capacity == 0:
            return 0
        return ((self.capacity - self.occupied) / self.capacity) * 100

    def get_available_slots_count(self):
        return self.capacity - self.occupied

    def update_occupancy(self):
        self.occupied = self.slots.filter(status__in=['occupied', 'reserved']).count()
        self.save(update_fields=['occupied', 'updated_at'])
        return self.occupied

    def __str__(self):
        return f"{self.zone_id} - {self.name}"

    class Meta:
        ordering = ['zone_id']


class ParkingSlot(models.Model):
    SLOT_TYPES = [
        ('Regular', 'Regular'),
        ('Compact', 'Compact'),
        ('EV', 'EV Charging'),
        ('Handicap', 'Handicap'),
        ('Premium', 'Premium'),
    ]
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Under Maintenance'),
        ('blocked', 'Blocked'),
    ]
    slot_number = models.CharField(max_length=20, unique=True, primary_key=True)
    zone = models.ForeignKey(ParkingZone, on_delete=models.CASCADE, related_name='slots')
    slot_type = models.CharField(max_length=20, choices=SLOT_TYPES, default='Regular')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_reserved = models.BooleanField(default=False)
    sensor_id = models.CharField(max_length=50, unique=True)
    location_x = models.FloatField(default=0.0)
    location_y = models.FloatField(default=0.0)
    reserved_until = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        old_status = None
        if not is_new:
            try:
                old = ParkingSlot.objects.get(pk=self.pk)
                old_status = old.status
            except ParkingSlot.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if not is_new and old_status != self.status:
            self.zone.update_occupancy()
        elif is_new:
            self.zone.update_occupancy()

    def __str__(self):
        return f"{self.slot_number} ({self.slot_type}) - {self.status}"

    class Meta:
        ordering = ['slot_number']


class UserProfile(models.Model):
    VEHICLE_TYPES = [
        ('Sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('Compact', 'Compact'),
        ('EV', 'Electric Vehicle'),
        ('Truck', 'Truck'),
        ('Motorcycle', 'Motorcycle'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True)
    vehicle_number = models.CharField(max_length=20, blank=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='Sedan')
    driver_license = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    is_premium_member = models.BooleanField(default=False)
    member_since = models.DateTimeField(auto_now_add=True)
    total_parking_hours = models.FloatField(default=0.0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class ParkingSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('reserved', 'Reserved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    vehicle_number = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_duration_hours(self):
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            return duration.total_seconds() / 3600
        return 0

    def calculate_amount(self):
        if self.end_time and self.start_time:
            duration_hours = self.get_duration_hours()
            hourly_rate = self.slot.zone.hourly_rate
            return duration_hours * hourly_rate
        return 0

    def __str__(self):
        return f"Session {self.session_id}"

    class Meta:
        ordering = ['-start_time']


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('mobile_payment', 'Mobile Payment'),
        ('cash', 'Cash'),
        ('wallet', 'Wallet'),
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
    ]
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    session = models.ForeignKey(ParkingSession, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    receipt_url = models.URLField(blank=True)

    def __str__(self):
        return f"Payment {self.payment_id} - Rs {self.amount}"

    class Meta:
        ordering = ['-payment_date']


class PendingReservation(models.Model):
    transaction_uuid = models.CharField(max_length=50, unique=True, db_index=True)
    slot_number = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=50)
    vehicle_number = models.CharField(max_length=50)
    duration_hours = models.FloatField()
    start_time = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=20)
    account_id = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_uuid} - {self.slot_number}"


# ========== SIGNALS ==========
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()