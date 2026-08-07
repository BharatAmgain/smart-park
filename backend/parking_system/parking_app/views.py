"""
SmartPark – Complete Views (Real-time Status Updates + Fixed CancelSession)
"""
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail
from datetime import datetime, timedelta
import math
import random
import threading
import time as time_module
import uuid
import hashlib
import hmac
import base64
import requests
import django
from django.db import models

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.db import connection

from .models import (
    ParkingZone, ParkingSlot, ParkingSession, Payment, PendingReservation, UserProfile
)
from .serializers import (
    ParkingZoneSerializer, ParkingSlotSerializer,
    ParkingSessionSerializer, PaymentSerializer
)
from django.conf import settings

# ========== CACHE KEY ==========
LIVE_DATA_CACHE_KEY = 'live_parking_data'
CACHE_TIMEOUT = 5

# ========== eSewa Configuration ==========
ESEWA_MERCHANT_CODE = getattr(settings, 'ESEWA_MERCHANT_CODE', 'EPAYTEST')
ESEWA_SECRET_KEY = getattr(settings, 'ESEWA_SECRET_KEY', '8gBm/:&EnhH.1,q')
ESEWA_TEST_URL = 'https://rc-epay.esewa.com.np/api/epay/main/v2/form'
ESEWA_SUCCESS_URL = getattr(settings, 'ESEWA_SUCCESS_URL', 'http://localhost:8000/api/payment-success/')
ESEWA_FAILURE_URL = getattr(settings, 'ESEWA_FAILURE_URL', 'http://localhost:8000/api/payment-failure/')

# ========== Khalti Configuration ==========
KHALTI_SECRET_KEY = getattr(settings, 'KHALTI_SECRET_KEY', 'test_secret_key_123456789')
KHALTI_TEST_URL = 'https://a.khalti.com/api/v2/epayment/initiate/'
KHALTI_VERIFY_URL = 'https://a.khalti.com/api/v2/epayment/lookup/'

# ============================================
# REASONABLE PRICE MAPPING BY ZONE TYPE
# ============================================
REASONABLE_PRICES = {
    'park': 20,
    'government': 25,
    'hospital': 30,
    'educational': 25,
    'heritage': 35,
    'commercial': 35,
    'shopping': 30,
    'cinema': 30,
    'office': 35,
    'airport': 50,
    'regular': 30,
    'default': 30
}

VEHICLE_MULTIPLIER = {
    'Motorcycle': 0.6,
    'Bike': 0.6,
    'Sedan': 1.0,
    'SUV': 1.0,
    'Compact': 1.0,
    'EV': 1.2,
}


def get_reasonable_price(zone_type):
    """Get reasonable price based on zone type"""
    return REASONABLE_PRICES.get(zone_type, REASONABLE_PRICES['default'])


def calculate_vehicle_rate(zone, vehicle_type):
    """Calculate per-hour rate based on zone and vehicle type"""
    base_rate = get_reasonable_price(zone.zone_type)
    multiplier = VEHICLE_MULTIPLIER.get(vehicle_type, 1.0)

    if vehicle_type in ['Motorcycle', 'Bike', 'motorcycle', 'bike']:
        return max(15, int(base_rate * 0.6))
    elif vehicle_type in ['EV', 'ev', 'Electric', 'electric']:
        return int(base_rate * 1.2)
    else:
        return base_rate


def calculate_price(vehicle_type, duration_hours, zone):
    """Calculate total price"""
    try:
        duration = float(duration_hours)
    except:
        duration = 1.0

    per_hour_rate = calculate_vehicle_rate(zone, vehicle_type)
    total = per_hour_rate * duration

    # Daily caps
    if vehicle_type in ['Motorcycle', 'Bike', 'motorcycle', 'bike']:
        max_daily = 150
    elif vehicle_type in ['EV', 'ev', 'Electric', 'electric']:
        max_daily = 300
    else:
        max_daily = 250

    total = min(total, max_daily)

    # Long duration discounts
    if duration >= 8:
        total = total * 0.70
    elif duration >= 5:
        total = total * 0.80
    elif duration >= 3:
        total = total * 0.90

    return int(max(20, round(total)))


def get_price_display_text(zone, vehicle_type):
    """Get display text for price"""
    per_hour_rate = calculate_vehicle_rate(zone, vehicle_type)

    if vehicle_type in ['Motorcycle', 'Bike', 'motorcycle', 'bike']:
        return f"Rs {per_hour_rate}/hour (Bike rate - 40% off)"
    elif vehicle_type in ['EV', 'ev', 'Electric', 'electric']:
        return f"Rs {per_hour_rate}/hour (EV rate - 20% premium)"
    else:
        return f"Rs {per_hour_rate}/hour (Standard rate)"


def get_display_rate(zone):
    """Get display rate for dashboard"""
    return get_reasonable_price(zone.zone_type)

# ============================================
# REAL-TIME STATUS UPDATE FUNCTION
# ============================================
def update_parking_sessions_status():
    """Update session statuses based on current time"""
    now = timezone.now()

    # Update reserved sessions that are starting (start_time <= now)
    starting_sessions = ParkingSession.objects.filter(
        status='reserved',
        start_time__lte=now
    )
    for session in starting_sessions:
        session.status = 'active'
        session.save(update_fields=['status', 'updated_at'])
        slot = session.slot
        if slot.status != 'occupied':
            slot.status = 'occupied'
            slot.save(update_fields=['status', 'last_updated'])
            print(f"[AUTO] Session {session.session_id} started for slot {slot.slot_number}")
            cache.delete(LIVE_DATA_CACHE_KEY)

    # Update active sessions that are completing (end_time <= now)
    completing_sessions = ParkingSession.objects.filter(
        status='active',
        end_time__lte=now
    )
    for session in completing_sessions:
        session.status = 'completed'
        session.save(update_fields=['status', 'updated_at'])
        slot = session.slot
        if slot.status == 'occupied':
            slot.status = 'available'
            slot.save(update_fields=['status', 'last_updated'])
            print(f"[AUTO] Session {session.session_id} completed for slot {slot.slot_number}")
            cache.delete(LIVE_DATA_CACHE_KEY)

def realtime_status_checker():
    while True:
        time_module.sleep(30)
        try:
            update_parking_sessions_status()
        except Exception as e:
            print(f"Status checker error: {e}")

def simulate_realtime_updates():
    while True:
        time_module.sleep(15)
        try:
            num_updates = random.randint(1, 3)
            slots = list(ParkingSlot.objects.filter(status__in=['available', 'occupied']).only('slot_number', 'status'))
            if slots:
                selected = random.sample(slots, min(num_updates, len(slots)))
                for slot in selected:
                    old = slot.status
                    new = 'occupied' if old == 'available' else 'available'
                    slot.status = new
                    slot.save(update_fields=['status', 'last_updated'])
                    print(f"[REAL-TIME] Slot {slot.slot_number}: {old} → {new}")
                    cache.delete(LIVE_DATA_CACHE_KEY)
        except Exception as e:
            print(f"Real-time error: {e}")

try:
    threading.Thread(target=realtime_status_checker, daemon=True).start()
    threading.Thread(target=simulate_realtime_updates, daemon=True).start()
    print("✅ Real-time status checker started")
except:
    pass

# ============================================
# BACKGROUND SCHEDULER FOR REMINDERS
# ============================================
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from django_apscheduler.jobstores import DjangoJobStore

    scheduler_started = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM django_apscheduler_djangojob LIMIT 1")
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), 'default')

        def send_parking_reminders():
            now = timezone.now()
            upcoming = ParkingSession.objects.filter(status='active', end_time__gt=now, end_time__lte=now + timedelta(minutes=15))
            for session in upcoming:
                if session.user and session.user.user.email:
                    send_mail(
                        'SmartPark – Parking Session Reminder',
                        f'Your parking session at slot {session.slot.slot_number} will end at {session.end_time.strftime("%H:%M")}. Please extend or vacate.',
                        'noreply@smartpark.com',
                        [session.user.user.email],
                        fail_silently=True
                    )
                    print(f"[REMINDER] Sent email to {session.user.user.email} for slot {session.slot.slot_number}")

        scheduler.add_job(send_parking_reminders, 'interval', minutes=1, id='parking_reminders', replace_existing=True)
        scheduler.start()
        scheduler_started = True
        print("✅ Background scheduler started")
    except Exception as e:
        print(f"⚠️ Scheduler not started: {e}")
except ImportError:
    print("⚠️ django-apscheduler not installed")

# ============================================
# HTML PAGE VIEWS
# ============================================
def base_page(request):
    return render(request, 'base.html')

@login_required(login_url='/login/')
def home_page(request):
    return render(request, 'base.html')

@login_required(login_url='/login/')
def map_page(request):
    return render(request, 'map.html')

@login_required(login_url='/login/')
def dashboard_page(request):
    return render(request, 'dashboard.html')

def about_us_page(request):
    return render(request, 'about_us.html')

@login_required(login_url='/login/')
def my_bookings_page(request):
    return render(request, 'my_bookings.html')

def admin_redirect(request):
    return redirect('/admin/')

@login_required(login_url='/login/')
def search_page(request):
    return render(request, 'search.html')

# ============================================
# AUTHENTICATION
# ============================================
def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if not username or not email or not password1 or not password2:
            return render(request, 'register.html', {'error': 'All fields are required.'})
        if password1 != password2:
            return render(request, 'register.html', {'error': 'Passwords do not match.'})
        if len(password1) < 8:
            return render(request, 'register.html', {'error': 'Password must be at least 8 characters.'})
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists.'})
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email already registered.'})

        user = User.objects.create_user(username=username, email=email, password=password1)
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)
        auth_login(request, user)
        return redirect('/map/')
    else:
        return render(request, 'register.html')

def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('/map/')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password.'})
    else:
        return render(request, 'login.html')

def logout_user(request):
    auth_logout(request)
    return redirect('/')

# ============================================
# EMAIL OTP HELPERS
# ============================================
def generate_and_send_email_otp(email):
    email = email.strip().lower()
    otp = f"{random.randint(100000, 999999)}"
    cache.set(f"otp_{email}", otp, timeout=600)
    print(f"\n{'='*60}")
    print(f"🔐 OTP for {email}: {otp}")
    print(f"🔐 OTP valid for 10 minutes")
    print(f"{'='*60}\n")

    try:
        send_mail(
            'SmartPark OTP for Payment Verification',
            f'Your OTP for payment verification is: {otp}\n\nValid for 10 minutes.\n\nDo not share this OTP with anyone.\n\nThank you for using SmartPark.',
            'noreply@smartpark.com',
            [email],
            fail_silently=False
        )
        print(f"[OTP] Email sent to {email}")
    except Exception as e:
        print(f"[OTP] Failed to send email: {e}")

    return True

def verify_email_otp(email, otp):
    email = email.strip().lower()
    stored = cache.get(f"otp_{email}")
    if stored and stored == otp:
        cache.delete(f"otp_{email}")
        return True
    return False

# ============================================
# eSewa & KHALTI HELPERS
# ============================================
def generate_esewa_signature(total_amount, transaction_uuid, product_code):
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    secret_key = ESEWA_SECRET_KEY
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    return signature_b64

def initiate_esewa_payment(amount, product_id, product_name, transaction_uuid):
    amount_int = int(amount)
    data = {
        'amount': str(amount_int),
        'product_code': ESEWA_MERCHANT_CODE,
        'total_amount': str(amount_int),
        'transaction_uuid': transaction_uuid,
        'product_service_charge': '0',
        'product_delivery_charge': '0',
        'tax_amount': '0',
        'success_url': ESEWA_SUCCESS_URL,
        'failure_url': ESEWA_FAILURE_URL,
        'signed_field_names': 'total_amount,transaction_uuid,product_code',
    }
    data['signature'] = generate_esewa_signature(amount_int, transaction_uuid, ESEWA_MERCHANT_CODE)
    return data

def initiate_khalti_payment(amount, product_name, transaction_uuid, return_url):
    """Initiate Khalti payment with correct amount"""
    headers = {'Authorization': f'Key {KHALTI_SECRET_KEY}', 'Content-Type': 'application/json'}

    # FIXED: Khalti expects amount in paisa (multiply by 100)
    # But we need to make sure the amount is correct
    amount_in_paisa = int(amount * 100)

    payload = {
        'return_url': return_url,
        'website_url': 'http://localhost:8000',
        'amount': amount_in_paisa,
        'purchase_order_id': transaction_uuid,
        'purchase_order_name': product_name,
        'customer_info': {
            'name': 'SmartPark User',
            'email': 'user@smartpark.com',
            'phone': '9800000000'
        }
    }
    try:
        response = requests.post(KHALTI_TEST_URL, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json().get('payment_url')
        return None
    except:
        return None

def verify_khalti_payment(pidx):
    headers = {'Authorization': f'Key {KHALTI_SECRET_KEY}', 'Content-Type': 'application/json'}
    payload = {'pidx': pidx}
    try:
        response = requests.post(KHALTI_VERIFY_URL, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json().get('status') == 'Completed'
        return False
    except:
        return False

USE_MOCK_ESEWA = False

# ============================================
# API VIEWS
# ============================================
class APIHomeView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'message': 'Smart Parking API', 'status': 'operational'})

class ParkingZoneViewSet(viewsets.ModelViewSet):
    queryset = ParkingZone.objects.all()
    serializer_class = ParkingZoneSerializer
    permission_classes = [AllowAny]

class ParkingSlotViewSet(viewsets.ModelViewSet):
    queryset = ParkingSlot.objects.all()
    serializer_class = ParkingSlotSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def by_vehicle(self, request):
        vehicle_type = request.query_params.get('vehicle_type', 'Sedan')
        compatibility = {
            'Sedan': ['Regular', 'Premium'],
            'SUV': ['Regular', 'Premium'],
            'Compact': ['Compact', 'Regular'],
            'EV': ['EV', 'Regular'],
            'Motorcycle': ['Compact', 'Regular'],
            'Bike': ['Compact', 'Regular'],
        }
        compatible = compatibility.get(vehicle_type, ['Regular'])
        slots = ParkingSlot.objects.filter(status='available', slot_type__in=compatible).select_related('zone')
        slots_data = []
        for slot in slots:
            price_display = get_price_display_text(slot.zone, vehicle_type)
            slots_data.append({
                'slot_number': slot.slot_number,
                'zone_id': slot.zone.zone_id,
                'zone_name': slot.zone.name,
                'slot_type': slot.slot_type,
                'status': slot.status,
                'display_rate': get_display_rate(slot.zone),
                'vehicle_rate': calculate_vehicle_rate(slot.zone, vehicle_type),
                'price_display': price_display
            })
        return Response({'success': True, 'vehicle_type': vehicle_type, 'total_available': len(slots_data), 'slots': slots_data})

    @action(detail=False, methods=['get'])
    def counts_by_vehicle(self, request):
        vehicles = ['Sedan', 'SUV', 'Compact', 'EV', 'Motorcycle', 'Truck']
        compatibility = {
            'Sedan': ['Regular', 'Premium'],
            'SUV': ['Regular', 'Premium'],
            'Compact': ['Compact', 'Regular'],
            'EV': ['EV', 'Regular'],
            'Motorcycle': ['Compact', 'Regular'],
            'Truck': ['Regular', 'Premium']
        }
        counts = {}
        for v in vehicles:
            compatible = compatibility.get(v, ['Regular'])
            counts[v] = ParkingSlot.objects.filter(status='available', slot_type__in=compatible).count()
        return Response({'success': True, 'counts': counts})

class ParkingSessionViewSet(viewsets.ModelViewSet):
    queryset = ParkingSession.objects.all().order_by('-start_time')
    serializer_class = ParkingSessionSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def active(self, request):
        sessions = ParkingSession.objects.filter(status='active')
        return Response(self.get_serializer(sessions, many=True).data)

    @action(detail=False, methods=['get'])
    def reserved(self, request):
        sessions = ParkingSession.objects.filter(status='reserved')
        return Response(self.get_serializer(sessions, many=True).data)

    @action(detail=False, methods=['get'])
    def completed(self, request):
        sessions = ParkingSession.objects.filter(status='completed')
        return Response(self.get_serializer(sessions, many=True).data)

    @action(detail=False, methods=['get'])
    def cancelled(self, request):
        sessions = ParkingSession.objects.filter(status='cancelled')
        return Response(self.get_serializer(sessions, many=True).data)

class LiveParkingView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # Update session statuses before returning data
        update_parking_sessions_status()

        cached_data = cache.get(LIVE_DATA_CACHE_KEY)
        if cached_data:
            return Response(cached_data)
        try:
            now = timezone.now()
            zones = ParkingZone.objects.filter(is_active=True)

            # Get accurate counts from database
            total_slots = ParkingSlot.objects.count()

            # Count slots by status - these are the actual slot statuses
            total_available = ParkingSlot.objects.filter(status='available').count()
            total_occupied = ParkingSlot.objects.filter(status='occupied').count()
            total_reserved = ParkingSlot.objects.filter(status='reserved').count()

            # Get session counts - these show the actual session statuses
            active_sessions_count = ParkingSession.objects.filter(status='active').count()
            reserved_sessions_count = ParkingSession.objects.filter(status='reserved').count()
            completed_sessions_count = ParkingSession.objects.filter(status='completed').count()
            cancelled_sessions_count = ParkingSession.objects.filter(status='cancelled').count()

            if not zones.exists():
                response_data = {
                    'success': True,
                    'zones': [],
                    'summary': {
                        'total_available': total_available,
                        'total_occupied': total_occupied,
                        'total_reserved': total_reserved,
                        'total_slots': total_slots,
                        'active_sessions': active_sessions_count,
                        'reserved_sessions': reserved_sessions_count,
                        'completed_sessions': completed_sessions_count,
                        'cancelled_sessions': cancelled_sessions_count
                    }
                }
                cache.set(LIVE_DATA_CACHE_KEY, response_data, CACHE_TIMEOUT)
                return Response(response_data)

            future_slot_pks = set(
                ParkingSession.objects.filter(
                    start_time__gt=now,
                    status__in=['reserved']
                ).values_list('slot_id', flat=True)
            )

            live_zones = []
            for zone in zones:
                slots = zone.slots.all()
                available = 0
                occupied = 0
                reserved = 0
                slots_data = []

                for slot in slots:
                    if slot.pk in future_slot_pks:
                        effective = 'reserved'
                        reserved += 1
                    elif slot.status == 'available':
                        effective = 'available'
                        available += 1
                    elif slot.status == 'occupied':
                        effective = 'occupied'
                        occupied += 1
                    else:
                        effective = slot.status

                    slots_data.append({
                        'slot_number': slot.slot_number,
                        'status': effective,
                        'slot_type': slot.slot_type,
                        'zone_name': zone.name,
                        'display_rate': get_display_rate(zone)
                    })

                lat = zone.location_y or 27.7172
                lng = zone.location_x or 85.3240
                live_zones.append({
                    'zone_id': zone.zone_id,
                    'zone_name': zone.name,
                    'available_slots': available,
                    'occupied_slots': occupied,
                    'reserved_slots': reserved,
                    'total_slots': zone.capacity,
                    'availability_percentage': round((available / zone.capacity * 100), 1) if zone.capacity else 0,
                    'display_rate': get_display_rate(zone),
                    'coordinates': {'lat': float(lat), 'lng': float(lng)},
                    'slots': slots_data
                })

            response_data = {
                'success': True,
                'zones': live_zones,
                'summary': {
                    'total_available': total_available,
                    'total_occupied': total_occupied,
                    'total_reserved': total_reserved,
                    'total_slots': total_slots,
                    'active_sessions': active_sessions_count,
                    'reserved_sessions': reserved_sessions_count,
                    'completed_sessions': completed_sessions_count,
                    'cancelled_sessions': cancelled_sessions_count
                }
            }
            cache.set(LIVE_DATA_CACHE_KEY, response_data, CACHE_TIMEOUT)
            return Response(response_data)
        except Exception as e:
            print(f"LiveParkingView ERROR: {e}")
            import traceback
            traceback.print_exc()
            total_slots = ParkingSlot.objects.count()
            total_available = ParkingSlot.objects.filter(status='available').count()
            total_occupied = ParkingSlot.objects.filter(status='occupied').count()
            total_reserved = ParkingSlot.objects.filter(status='reserved').count()
            active_sessions_count = ParkingSession.objects.filter(status='active').count()
            reserved_sessions_count = ParkingSession.objects.filter(status='reserved').count()
            completed_sessions_count = ParkingSession.objects.filter(status='completed').count()
            cancelled_sessions_count = ParkingSession.objects.filter(status='cancelled').count()
            return Response({
                'success': True,
                'zones': [],
                'summary': {
                    'total_available': total_available,
                    'total_occupied': total_occupied,
                    'total_reserved': total_reserved,
                    'total_slots': total_slots,
                    'active_sessions': active_sessions_count,
                    'reserved_sessions': reserved_sessions_count,
                    'completed_sessions': completed_sessions_count,
                    'cancelled_sessions': cancelled_sessions_count
                }
            })

@method_decorator(csrf_exempt, name='dispatch')
class NearestParkingView(APIView):
    permission_classes = [AllowAny]

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000  # Earth's radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def post(self, request):
        user_lat = request.data.get('lat')
        user_lng = request.data.get('lng')
        vehicle_type = request.data.get('vehicle_type', 'Sedan')
        limit = request.data.get('limit', 10)

        # FIXED: Set a maximum radius of 3km for nearest parking
        max_distance = request.data.get('max_distance', 3000)  # 3km default

        if not user_lat or not user_lng:
            return Response({'error': 'Location required'}, status=400)

        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)
            max_distance = float(max_distance)

            compatibility = {
                'Sedan': ['Regular', 'Premium'],
                'SUV': ['Regular', 'Premium'],
                'Compact': ['Compact', 'Regular'],
                'EV': ['EV', 'Regular'],
                'Motorcycle': ['Compact', 'Regular'],
                'Bike': ['Compact', 'Regular'],
            }

            compatible_types = compatibility.get(vehicle_type, ['Regular'])

            # FIXED: Get all available slots with their zone coordinates
            all_slots = ParkingSlot.objects.filter(
                status='available',
                slot_type__in=compatible_types
            ).select_related('zone')

            nearest = []

            for slot in all_slots:
                zone = slot.zone
                if zone.location_x and zone.location_y:
                    slot_lat = float(zone.location_y)
                    slot_lng = float(zone.location_x)
                    distance = self.haversine(user_lat, user_lng, slot_lat, slot_lng)

                    # FIXED: Only include slots within max_distance
                    if distance <= max_distance:
                        # Calculate times
                        walk_time_min = max(1, int(distance / 1.4 / 60))
                        drive_time_min = max(1, int(distance / 8.33 / 60))
                        bike_time_min = max(1, int(distance / 4.16 / 60))

                        per_hour_rate = calculate_vehicle_rate(zone, vehicle_type)
                        price_display = get_price_display_text(zone, vehicle_type)

                        nearest.append({
                            'slot_number': slot.slot_number,
                            'zone_id': zone.zone_id,
                            'zone_name': zone.name,
                            'slot_type': slot.slot_type,
                            'distance_meters': round(distance, 2),
                            'distance_km': round(distance / 1000, 2),
                            'walk_time_minutes': walk_time_min,
                            'drive_time_minutes': drive_time_min,
                            'bike_time_minutes': bike_time_min,
                            'hourly_rate': get_display_rate(zone),
                            'per_hour_rate': per_hour_rate,
                            'price_display': price_display,
                            'zone_type': zone.zone_type
                        })

            # Sort by distance (nearest first)
            nearest.sort(key=lambda x: x['distance_meters'])

            # Limit results
            result_slots = nearest[:limit]

            # FIXED: Return appropriate message if no slots found
            if len(result_slots) == 0:
                return Response({
                    'success': True,
                    'nearest_slots': [],
                    'vehicle_type': vehicle_type,
                    'total_found': 0,
                    'message': f'No available {vehicle_type} slots within {max_distance/1000}km of your location. Try increasing the search radius.'
                })

            return Response({
                'success': True,
                'nearest_slots': result_slots,
                'vehicle_type': vehicle_type,
                'total_found': len(nearest),
                'max_distance_km': round(max_distance / 1000, 1)
            })

        except Exception as e:
            print(f"[NEAREST] Error: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)

class AllocationView(APIView):
    permission_classes = [AllowAny]
    VEHICLE_COMPATIBILITY = {
        'Sedan': ['Regular', 'Premium'],
        'SUV': ['Regular', 'Premium'],
        'Compact': ['Compact', 'Regular'],
        'EV': ['EV', 'Regular'],
        'Motorcycle': ['Compact', 'Regular'],
        'Bike': ['Compact', 'Regular'],
    }
    def post(self, request):
        data = request.data
        slot_number = data.get('slot_number')
        vehicle_type = data.get('vehicle_type', 'Sedan')
        vehicle_number = data.get('vehicle_number')
        duration_hours = float(data.get('duration_hours', 1))
        start_time_str = data.get('start_time')
        transaction_id = data.get('transaction_id')
        payment_method = data.get('payment_method')

        if not slot_number or not vehicle_number:
            return Response({'error': 'Slot number and vehicle number required'}, status=400)

        # Parse start time
        if start_time_str:
            try:
                start_time = timezone.make_aware(datetime.fromisoformat(start_time_str))
            except:
                start_time = timezone.now()
        else:
            start_time = timezone.now()

        # Prevent booking for past dates
        now = timezone.now()
        if start_time < now:
            return Response({'error': 'Cannot book for past date and time. Please select a future date/time.'}, status=400)

        end_time = start_time + timedelta(hours=duration_hours)

        try:
            slot = ParkingSlot.objects.get(slot_number=slot_number)
        except ParkingSlot.DoesNotExist:
            return Response({'error': f'Slot {slot_number} does not exist'}, status=404)

        if slot.status != 'available':
            return Response({'error': f'Slot {slot_number} not available'}, status=400)

        compatible = self.VEHICLE_COMPATIBILITY.get(vehicle_type, ['Regular'])
        if slot.slot_type not in compatible:
            return Response({'error': f'Slot type not compatible with {vehicle_type}'}, status=400)

        amount = calculate_price(vehicle_type, duration_hours, slot.zone)

        if start_time > now:
            session_status = 'reserved'
            slot_status = 'reserved'
        else:
            session_status = 'active'
            slot_status = 'occupied'

        slot.status = slot_status
        slot.save()

        user_profile = request.user.profile if request.user.is_authenticated else None
        session = ParkingSession.objects.create(
            slot=slot,
            user=user_profile,
            status=session_status,
            vehicle_number=vehicle_number,
            start_time=start_time,
            end_time=end_time
        )

        Payment.objects.create(
            session=session,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            status='completed',
            payment_date=timezone.now()
        )

        cache.delete(LIVE_DATA_CACHE_KEY)

        return Response({
            'success': True,
            'message': f'Slot {slot_number} reserved. Paid Rs {amount} via {payment_method}',
            'amount': amount,
            'slot_number': slot_number,
            'session_id': str(session.session_id),
            'status': session_status,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        })

class ReservationView(AllocationView):
    pass

@method_decorator(csrf_exempt, name='dispatch')
class InitiatePaymentView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data
        slot_number = data.get('slot_number')
        vehicle_type = data.get('vehicle_type')
        vehicle_number = data.get('vehicle_number')
        duration_hours = float(data.get('duration_hours', 1))
        start_time_str = data.get('start_time')
        payment_method = data.get('payment_method')
        account_id = data.get('account_id', '').strip().lower()
        otp_code = data.get('otp_code')

        if not all([slot_number, vehicle_type, vehicle_number, payment_method]):
            return Response({'error': 'Missing fields'}, status=400)

        try:
            slot = ParkingSlot.objects.get(slot_number=slot_number)
            if slot.status != 'available':
                return Response({'error': 'Slot no longer available'}, status=400)
        except ParkingSlot.DoesNotExist:
            return Response({'error': 'Invalid slot'}, status=404)

        # FIXED: Calculate the correct amount
        amount = calculate_price(vehicle_type, duration_hours, slot.zone)
        transaction_uuid = f"PARK_{uuid.uuid4().hex[:12].upper()}"

        PendingReservation.objects.create(
            transaction_uuid=transaction_uuid,
            slot_number=slot_number,
            vehicle_type=vehicle_type,
            vehicle_number=vehicle_number,
            duration_hours=duration_hours,
            start_time=start_time_str or None,
            payment_method=payment_method,
            account_id=account_id,
            amount=amount,  # Store the correct amount
        )

        if not otp_code:
            try:
                generate_and_send_email_otp(account_id)
                return Response({'success': True, 'requires_otp': True, 'message': f'OTP sent to {account_id}'})
            except Exception as e:
                return Response({'error': f'Failed to send OTP: {str(e)}'}, status=500)
        else:
            if verify_email_otp(account_id, otp_code):
                if payment_method == 'esewa':
                    if USE_MOCK_ESEWA:
                        try:
                            slot = ParkingSlot.objects.get(slot_number=slot_number)
                            if slot.status != 'available':
                                return Response({'error': 'Slot not available'}, status=400)

                            if start_time_str:
                                try:
                                    start_time_dt = datetime.fromisoformat(start_time_str)
                                    start_time_dt = timezone.make_aware(start_time_dt)
                                except:
                                    start_time_dt = timezone.now()
                            else:
                                start_time_dt = timezone.now()

                            now = timezone.now()
                            if start_time_dt < now:
                                return Response({'error': 'Cannot book for past date and time.'}, status=400)

                            end_time_dt = start_time_dt + timedelta(hours=duration_hours)

                            if start_time_dt > now:
                                session_status = 'reserved'
                                slot_status = 'reserved'
                            else:
                                session_status = 'active'
                                slot_status = 'occupied'

                            slot.status = slot_status
                            slot.save()
                            user_profile = request.user.profile if request.user.is_authenticated else None
                            session = ParkingSession.objects.create(
                                slot=slot,
                                user=user_profile,
                                status=session_status,
                                vehicle_number=vehicle_number,
                                start_time=start_time_dt,
                                end_time=end_time_dt
                            )
                            Payment.objects.create(
                                session=session,
                                amount=amount,
                                payment_method='esewa',
                                transaction_id=transaction_uuid,
                                status='completed',
                                payment_date=timezone.now()
                            )
                            PendingReservation.objects.filter(transaction_uuid=transaction_uuid).delete()
                            cache.delete(LIVE_DATA_CACHE_KEY)
                            return Response({
                                'success': True,
                                'payment_method': 'esewa',
                                'form_action': f"/map/?payment=success&slot={slot_number}&session_id={session.session_id}",
                                'form_data': {}
                            })
                        except Exception as e:
                            print(f"Mock allocation error: {e}")
                            return Response({'error': 'Payment processing failed'}, status=500)
                    else:
                        esewa_data = initiate_esewa_payment(amount, slot_number, f"Parking {slot_number}", transaction_uuid)
                        html_content = f'''
                        <!DOCTYPE html>
                        <html>
                        <head><title>Redirecting to eSewa...</title>
                        <style>body{{margin:0;padding:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:linear-gradient(135deg,#0a0f2a,#02040c);font-family:Arial,sans-serif;}}.container{{text-align:center;color:white;}}.spinner{{width:50px;height:50px;border:4px solid rgba(255,255,255,0.3);border-top:4px solid #2ecc71;border-radius:50%;animation:spin 1s linear infinite;margin:20px auto;}}@keyframes spin{{0%{{transform:rotate(0deg);}}100%{{transform:rotate(360deg);}}}}</style>
                        </head>
                        <body>
                            <div class="container">
                                <div class="spinner"></div>
                                <h2>Redirecting to eSewa Payment Gateway...</h2>
                                <p>Please wait, do not close this page.</p>
                            </div>
                            <form id="esewaForm" method="POST" action="{ESEWA_TEST_URL}">
                        '''
                        for key, value in esewa_data.items():
                            html_content += f'<input type="hidden" name="{key}" value="{value}">'
                        html_content += '''
                            </form>
                            <script>document.getElementById('esewaForm').submit();</script>
                        </body>
                        </html>
                        '''
                        return HttpResponse(html_content)
                elif payment_method == 'khalti':
                    # FIXED: Pass the correct amount to Khalti
                    return_url = f"{ESEWA_SUCCESS_URL}?method=khalti&txn_id={transaction_uuid}"
                    payment_url = initiate_khalti_payment(amount, f"Parking {slot_number}", transaction_uuid, return_url)
                    if payment_url:
                        return Response({
                            'success': True,
                            'payment_method': 'khalti',
                            'payment_url': payment_url,
                            'amount': amount  # Return the amount for display
                        })
                    else:
                        return Response({'error': 'Khalti initiation failed'}, status=500)
                return Response({'error': 'Invalid payment method'}, status=400)
            else:
                return Response({'error': 'Invalid or expired OTP. Please try again.'}, status=400)

class PaymentSuccessView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        transaction_uuid = (request.GET.get('transaction_uuid') or request.GET.get('txn_id') or
                           request.GET.get('purchase_order_id') or request.GET.get('oid'))
        method = request.GET.get('method', 'esewa')
        pending = None
        pidx = request.GET.get('pidx')

        if transaction_uuid and transaction_uuid != 'mock':
            try:
                pending = PendingReservation.objects.get(transaction_uuid=transaction_uuid)
            except PendingReservation.DoesNotExist:
                pass

        if not pending:
            return HttpResponseRedirect("/map/?payment=failed&reason=no_reservation")

        if method == 'khalti':
            if not pidx or not verify_khalti_payment(pidx):
                return HttpResponseRedirect("/map/?payment=failed&reason=khalti_verification_failed")

        try:
            slot = ParkingSlot.objects.get(slot_number=pending.slot_number)
            if slot.status != 'available':
                return HttpResponseRedirect("/map/?payment=failed&reason=slot_unavailable")

            if pending.start_time:
                try:
                    if isinstance(pending.start_time, str):
                        start_time = datetime.fromisoformat(pending.start_time)
                        start_time = timezone.make_aware(start_time)
                    else:
                        start_time = pending.start_time
                except:
                    start_time = timezone.now()
            else:
                start_time = timezone.now()

            now = timezone.now()
            if start_time < now:
                return HttpResponseRedirect("/map/?payment=failed&reason=past_date_not_allowed")

            end_time = start_time + timedelta(hours=float(pending.duration_hours))

            if start_time > now:
                session_status = 'reserved'
                slot_status = 'reserved'
            else:
                session_status = 'active'
                slot_status = 'occupied'

            slot.status = slot_status
            slot.save()

            session = ParkingSession.objects.create(
                slot=slot,
                status=session_status,
                vehicle_number=pending.vehicle_number,
                start_time=start_time,
                end_time=end_time
            )

            Payment.objects.create(
                session=session,
                amount=pending.amount,
                payment_method=pending.payment_method,
                transaction_id=transaction_uuid,
                status='completed',
                payment_date=timezone.now()
            )

            pending.delete()
            cache.delete(LIVE_DATA_CACHE_KEY)
            return HttpResponseRedirect(f"/map/?payment=success&slot={pending.slot_number}&session_id={session.session_id}")

        except Exception as e:
            print(f"Error: {e}")
            return HttpResponseRedirect("/map/?payment=failed&reason=allocation_error")

class PaymentFailureView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return HttpResponseRedirect("/map/?payment=failed")

class PaymentVerifyView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        pidx = request.data.get('pidx')
        if pidx and verify_khalti_payment(pidx):
            return Response({'success': True})
        return Response({'success': False}, status=400)

class CancelSessionView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, session_id):
        try:
            session = None
            try:
                session = ParkingSession.objects.get(session_id=session_id)
            except (ParkingSession.DoesNotExist, ValueError):
                sessions = ParkingSession.objects.filter(session_id__startswith=session_id)
                if sessions.exists():
                    session = sessions.first()

            if not session:
                return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)

            if request.user.is_authenticated and session.user and session.user != request.user.profile:
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

            now = timezone.now()

            if session.status == 'active':
                session.status = 'completed'
                session.actual_end_time = now
                session.save()
                slot = session.slot
                slot.status = 'available'
                slot.save()
                cache.delete(LIVE_DATA_CACHE_KEY)
                return JsonResponse({'success': True, 'message': 'Session ended successfully'})

            if session.start_time <= now and session.status == 'reserved':
                slot = session.slot
                slot.status = 'available'
                slot.save()
                session.status = 'cancelled'
                session.save()
                payment = Payment.objects.filter(session=session).first()
                if payment and payment.status == 'completed':
                    payment.status = 'refunded'
                    payment.save()
                cache.delete(LIVE_DATA_CACHE_KEY)
                return JsonResponse({'success': True, 'message': 'Booking cancelled and refunded'})

            if session.status == 'reserved':
                slot = session.slot
                slot.status = 'available'
                slot.save()
                session.status = 'cancelled'
                session.save()

                payment = Payment.objects.filter(session=session).first()
                if payment and payment.status == 'completed':
                    payment.status = 'refunded'
                    payment.save()

                cache.delete(LIVE_DATA_CACHE_KEY)
                return JsonResponse({'success': True, 'message': 'Booking cancelled and refunded successfully'})

            return JsonResponse({'success': False, 'error': 'Cannot cancel this session'}, status=400)
        except Exception as e:
            print(f"CancelSessionView error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class DashboardView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        update_parking_sessions_status()

        try:
            total_slots = ParkingSlot.objects.count()
            available_slots = ParkingSlot.objects.filter(status='available').count()
            occupied_slots = ParkingSlot.objects.filter(status='occupied').count()
            reserved_slots = ParkingSlot.objects.filter(status='reserved').count()

            active_sessions_count = ParkingSession.objects.filter(status='active').count()
            reserved_sessions_count = ParkingSession.objects.filter(status='reserved').count()
            completed_sessions_count = ParkingSession.objects.filter(status='completed').count()
            cancelled_sessions_count = ParkingSession.objects.filter(status='cancelled').count()

            zones_data = []
            for zone in ParkingZone.objects.filter(is_active=True):
                slots = zone.slots.all()
                total = slots.count()
                available = slots.filter(status='available').count()
                occupied = slots.filter(status='occupied').count()
                reserved = slots.filter(status='reserved').count()
                zones_data.append({
                    'zone_id': zone.zone_id,
                    'zone_name': zone.name,
                    'total_slots': total,
                    'available_slots': available,
                    'occupied_slots': occupied,
                    'reserved_slots': reserved,
                    'occupancy_rate': round((occupied / total * 100), 1) if total > 0 else 0,
                    'display_rate': get_display_rate(zone),
                })

            all_slots = []
            for slot in ParkingSlot.objects.select_related('zone').all():
                all_slots.append({
                    'slot_number': slot.slot_number,
                    'zone_id': slot.zone.zone_id,
                    'zone_name': slot.zone.name,
                    'slot_type': slot.slot_type,
                    'status': slot.status,
                    'display_rate': get_display_rate(slot.zone),
                })

            recent_sessions = []
            for session in ParkingSession.objects.select_related('slot', 'slot__zone').order_by('-start_time')[:50]:
                start_time_local = session.start_time
                payment = session.payments.first()
                recent_sessions.append({
                    'session_id': str(session.session_id),
                    'slot_number': session.slot.slot_number,
                    'zone_id': session.slot.zone.zone_id,
                    'zone_name': session.slot.zone.name,
                    'vehicle_number': session.vehicle_number,
                    'start_time': start_time_local.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': session.status,
                    'payment_method': payment.payment_method if payment else 'N/A'
                })

            return Response({
                'success': True,
                'overview': {
                    'total_slots': total_slots,
                    'available_slots': available_slots,
                    'occupied_slots': occupied_slots,
                    'reserved_slots': reserved_slots,
                    'active_sessions': active_sessions_count,
                    'reserved_sessions': reserved_sessions_count,
                    'completed_sessions': completed_sessions_count,
                    'cancelled_sessions': cancelled_sessions_count
                },
                'zones': zones_data,
                'all_slots': all_slots,
                'recent_sessions': recent_sessions
            })
        except Exception as e:
            print(f"DashboardView error: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': True,
                'overview': {
                    'total_slots': 0,
                    'available_slots': 0,
                    'occupied_slots': 0,
                    'reserved_slots': 0,
                    'active_sessions': 0,
                    'reserved_sessions': 0,
                    'completed_sessions': 0,
                    'cancelled_sessions': 0
                },
                'zones': [],
                'all_slots': [],
                'recent_sessions': []
            })

class ZoneStatisticsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            zones = ParkingZone.objects.filter(is_active=True)
            stats = []
            for zone in zones:
                slots = zone.slots.all()
                total = slots.count()
                available = slots.filter(status='available').count()
                occupied = slots.filter(status='occupied').count()
                reserved = slots.filter(status='reserved').count()
                stats.append({
                    'zone_id': zone.zone_id,
                    'zone_name': zone.name,
                    'total_slots': total,
                    'available': available,
                    'occupied': occupied,
                    'reserved': reserved,
                    'availability_percentage': round((available / total * 100), 1) if total else 0,
                    'display_rate': get_display_rate(zone),
                    'coordinates': {'lat': float(zone.location_y or 27.7172), 'lng': float(zone.location_x or 85.3240)}
                })
            return Response({'success': True, 'zones': stats})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class SearchSlotsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        q = request.query_params.get('q', '').strip().upper()
        if not q:
            return Response({'success': False, 'error': 'No query provided'}, status=400)
        try:
            slots = ParkingSlot.objects.filter(slot_number__icontains=q).select_related('zone')
            results = []
            for slot in slots:
                results.append({
                    'slot_number': slot.slot_number,
                    'zone_id': slot.zone.zone_id,
                    'zone_name': slot.zone.name,
                    'slot_type': slot.slot_type,
                    'status': slot.status,
                    'display_rate': get_display_rate(slot.zone),
                    'coordinates': {
                        'lat': float(slot.zone.location_y or 27.7172),
                        'lng': float(slot.zone.location_x or 85.3240)
                    }
                })
            return Response({'success': True, 'results': results})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class TestAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({
            'status': 'ok',
            'message': 'SmartPark API is working',
            'timestamp': timezone.now().isoformat(),
            'django_version': django.get_version()
        })

class InvoiceView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, session_id):
        try:
            session = ParkingSession.objects.get(session_id=session_id)
            payment = Payment.objects.filter(session=session).first()
            if not payment:
                return Response({'success': False, 'error': 'No payment found'}, status=404)
            invoice = {
                'invoice_no': f"INV-{session.session_id[:8].upper()}",
                'date': session.start_time.strftime("%Y-%m-%d %H:%M"),
                'slot_number': session.slot.slot_number,
                'zone_name': session.slot.zone.name,
                'vehicle_number': session.vehicle_number,
                'duration_hours': (session.end_time - session.start_time).total_seconds() / 3600,
                'amount': float(payment.amount),
                'payment_method': payment.payment_method,
                'transaction_id': payment.transaction_id,
                'status': payment.status
            }
            return Response({'success': True, 'invoice': invoice})
        except ParkingSession.DoesNotExist:
            return Response({'success': False, 'error': 'Session not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)