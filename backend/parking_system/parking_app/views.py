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
# REAL-TIME STATUS UPDATE FUNCTION
# ============================================
def update_parking_sessions_status():
    """Update session statuses based on current time"""
    now = timezone.now()

    # Update sessions that should become active (start_time <= now)
    starting_sessions = ParkingSession.objects.filter(
        status='reserved',
        start_time__lte=now
    )
    for session in starting_sessions:
        session.status = 'active'
        session.save(update_fields=['status', 'updated_at'])
        # Update the slot status to occupied
        slot = session.slot
        if slot.status != 'occupied':
            old_status = slot.status
            slot.status = 'occupied'
            slot.save(update_fields=['status', 'last_updated'])
            print(f"[AUTO] Session {session.session_id} started for slot {slot.slot_number} (was {old_status} → occupied)")
            cache.delete(LIVE_DATA_CACHE_KEY)

    # Update sessions that should become completed (end_time <= now)
    completing_sessions = ParkingSession.objects.filter(
        status='active',
        end_time__lte=now
    )
    for session in completing_sessions:
        session.status = 'completed'
        session.save(update_fields=['status', 'updated_at'])
        # Free up the slot
        slot = session.slot
        if slot.status == 'occupied':
            old_status = slot.status
            slot.status = 'available'
            slot.save(update_fields=['status', 'last_updated'])
            print(f"[AUTO] Session {session.session_id} completed for slot {slot.slot_number} (was {old_status} → available)")
            cache.delete(LIVE_DATA_CACHE_KEY)

def realtime_status_checker():
    """Run continuously to check and update statuses"""
    while True:
        time_module.sleep(30)
        try:
            update_parking_sessions_status()
        except Exception as e:
            print(f"Status checker error: {e}")

def simulate_realtime_updates():
    """Simulate random slot changes for demo"""
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

def update_reserved_to_active():
    """Legacy function - replaced by realtime_status_checker but kept for compatibility"""
    while True:
        time_module.sleep(10)
        try:
            update_parking_sessions_status()
        except Exception as e:
            print(f"Reservation updater error: {e}")

try:
    threading.Thread(target=realtime_status_checker, daemon=True).start()
    threading.Thread(target=simulate_realtime_updates, daemon=True).start()
    threading.Thread(target=update_reserved_to_active, daemon=True).start()
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
    """Landing page - professional marketing page without map"""
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
    """Search page - all parking search features"""
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
        # Ensure profile is created
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
    print(f"[OTP] Verification - Email: {email}, Stored: {stored}, Received: {otp}")

    if stored and stored == otp:
        cache.delete(f"otp_{email}")
        print(f"[OTP] ✅ OTP verified successfully!")
        return True

    print(f"[OTP] ❌ OTP verification failed!")
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
    print("\n" + "="*60)
    print("[ESEWA] Message:", message)
    print("[ESEWA] Base64 Signature:", signature_b64)
    print("="*60 + "\n")
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
    headers = {'Authorization': f'Key {KHALTI_SECRET_KEY}', 'Content-Type': 'application/json'}
    payload = {
        'return_url': return_url,
        'website_url': 'http://localhost:8000',
        'amount': amount * 100,
        'purchase_order_id': transaction_uuid,
        'purchase_order_name': product_name,
        'customer_info': {'name': 'SmartPark User', 'email': 'user@smartpark.com', 'phone': '9800000000'}
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
# HELPER FUNCTIONS
# ============================================
def calculate_price(vehicle_type, duration_hours):
    """Calculate price based on vehicle type and duration"""
    try:
        duration = float(duration_hours)
    except:
        duration = 1.0

    if vehicle_type in ['Motorcycle', 'Bike']:
        # Bike pricing: Rs 10 per hour, max Rs 50
        if duration >= 5:
            return 40
        elif duration <= 0.5:
            return 10
        else:
            # Rs 10 for first 0.5 hours, then Rs 5 per additional 0.5 hour
            extra_half_hours = max(0, (duration - 0.5) / 0.5)
            return 10 + int(extra_half_hours) * 5
    elif vehicle_type == 'EV':
        # EV pricing: Rs 20 per hour, max Rs 100
        if duration >= 5:
            return 80
        else:
            return 20 + int(duration - 1) * 15
    elif vehicle_type in ['Compact', 'Sedan', 'SUV']:
        # Car pricing: Rs 15 per hour, max Rs 75
        if duration >= 5:
            return 70
        else:
            return 15 + int(duration - 1) * 15
    else:
        # Default car pricing
        if duration >= 5:
            return 70
        else:
            return 15 + int(duration - 1) * 15

def get_current_timezone():
    """Get current timezone aware datetime"""
    return timezone.now()

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
        slots_data = [{
            'slot_number': s.slot_number,
            'zone_id': s.zone.zone_id,
            'zone_name': s.zone.name,
            'slot_type': s.slot_type,
            'status': s.status,
            'hourly_rate': float(s.zone.hourly_rate)
        } for s in slots]
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

class LiveParkingView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # Update statuses before sending response
        update_parking_sessions_status()

        cached_data = cache.get(LIVE_DATA_CACHE_KEY)
        if cached_data:
            return Response(cached_data)
        try:
            now = timezone.now()
            zones = ParkingZone.objects.filter(is_active=True)

            total_slots = ParkingSlot.objects.count()
            total_available = ParkingSlot.objects.filter(status='available').count()
            total_occupied = ParkingSlot.objects.filter(status='occupied').count()
            total_reserved = ParkingSlot.objects.filter(status='reserved').count()

            if not zones.exists():
                response_data = {
                    'success': True,
                    'zones': [],
                    'summary': {
                        'total_available': total_available,
                        'total_occupied': total_occupied,
                        'total_reserved': total_reserved,
                        'total_slots': total_slots
                    }
                }
                cache.set(LIVE_DATA_CACHE_KEY, response_data, CACHE_TIMEOUT)
                return Response(response_data)

            future_slot_pks = set(
                ParkingSession.objects.filter(
                    start_time__gt=now,
                    status__in=['reserved', 'active']
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
                        if effective == 'available':
                            available += 1
                        elif effective == 'occupied':
                            occupied += 1
                        else:
                            reserved += 1

                    slots_data.append({
                        'slot_number': slot.slot_number,
                        'status': effective,
                        'slot_type': slot.slot_type,
                        'zone_name': zone.name,
                        'hourly_rate': float(zone.hourly_rate)
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
                    'hourly_rate': float(zone.hourly_rate),
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
                    'total_slots': total_slots
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
            return Response({
                'success': True,
                'zones': [],
                'summary': {
                    'total_available': total_available,
                    'total_occupied': total_occupied,
                    'total_reserved': total_reserved,
                    'total_slots': total_slots
                }
            })

@method_decorator(csrf_exempt, name='dispatch')
class NearestParkingView(APIView):
    permission_classes = [AllowAny]

    def haversine(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in meters"""
        R = 6371000
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

        if not user_lat or not user_lng:
            return Response({'error': 'Location required'}, status=400)

        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)

            compatibility = {
                'Sedan': ['Regular', 'Premium'],
                'SUV': ['Regular', 'Premium'],
                'Compact': ['Compact', 'Regular'],
                'EV': ['EV', 'Regular'],
                'Motorcycle': ['Compact', 'Regular'],
                'Bike': ['Compact', 'Regular'],
            }

            compatible_types = compatibility.get(vehicle_type, ['Regular'])

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

                    walk_time_min = int(distance / 1.4 / 60)
                    drive_time_min = int(distance / 8.33 / 60)
                    bike_time_min = int(distance / 4.16 / 60)

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
                        'hourly_rate': float(zone.hourly_rate),
                    })

            nearest.sort(key=lambda x: x['distance_meters'])
            result_slots = nearest[:limit]

            return Response({
                'success': True,
                'nearest_slots': result_slots,
                'vehicle_type': vehicle_type,
                'total_found': len(nearest)
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

        if start_time_str:
            try:
                start_time = timezone.make_aware(datetime.fromisoformat(start_time_str))
            except:
                start_time = timezone.now()
        else:
            start_time = timezone.now()

        end_time = start_time + timedelta(hours=duration_hours)

        if ParkingSession.objects.filter(vehicle_number=vehicle_number, status__in=['active', 'reserved'], start_time__lt=end_time, end_time__gt=start_time).exists():
            return Response({'error': 'Vehicle already has active/reserved session'}, status=400)

        try:
            slot = ParkingSlot.objects.get(slot_number=slot_number)
        except ParkingSlot.DoesNotExist:
            return Response({'error': f'Slot {slot_number} does not exist'}, status=404)

        if slot.status != 'available':
            return Response({'error': f'Slot {slot_number} not available'}, status=400)

        compatible = self.VEHICLE_COMPATIBILITY.get(vehicle_type, ['Regular'])
        if slot.slot_type not in compatible:
            return Response({'error': f'Slot type not compatible with {vehicle_type}'}, status=400)

        amount = calculate_price(vehicle_type, duration_hours)
        now = timezone.now()

        if start_time <= now:
            session_status = 'active'
            slot_status = 'occupied'
        else:
            session_status = 'reserved'
            slot_status = 'reserved'

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

        return Response({
            'success': True,
            'message': f'Slot {slot_number} reserved. Paid Rs {amount} via {payment_method}',
            'amount': amount,
            'slot_number': slot_number,
            'session_id': str(session.session_id),
            'status': session_status
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

        amount = calculate_price(vehicle_type, duration_hours)
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
            amount=amount,
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
                                    start_time_dt = timezone.make_aware(datetime.fromisoformat(start_time_str))
                                except:
                                    start_time_dt = timezone.now()
                            else:
                                start_time_dt = timezone.now()
                            end_time_dt = start_time_dt + timedelta(hours=duration_hours)
                            now = timezone.now()
                            if start_time_dt <= now:
                                session_status = 'active'
                                slot_status = 'occupied'
                            else:
                                session_status = 'reserved'
                                slot_status = 'reserved'
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
                        <head>
                            <title>Redirecting to eSewa...</title>
                            <style>
                                body {{ margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #0a0f2a, #02040c); font-family: Arial, sans-serif; }}
                                .container {{ text-align: center; color: white; }}
                                .spinner {{ width: 50px; height: 50px; border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid #2ecc71; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }}
                                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                            </style>
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
                            <script>
                                if (!window.formSubmitted) {
                                    window.formSubmitted = true;
                                    document.getElementById('esewaForm').submit();
                                }
                            </script>
                        </body>
                        </html>
                        '''
                        return HttpResponse(html_content)
                elif payment_method == 'khalti':
                    return_url = f"{ESEWA_SUCCESS_URL}?method=khalti&txn_id={transaction_uuid}"
                    payment_url = initiate_khalti_payment(amount, f"Parking {slot_number}", transaction_uuid, return_url)
                    if payment_url:
                        return Response({'success': True, 'payment_method': 'khalti', 'payment_url': payment_url})
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
                    start_time = timezone.make_aware(datetime.fromisoformat(pending.start_time))
                except:
                    start_time = timezone.now()
            else:
                start_time = timezone.now()

            end_time = start_time + timedelta(hours=float(pending.duration_hours))
            now = timezone.now()

            if start_time <= now:
                session_status = 'active'
                slot_status = 'occupied'
            else:
                session_status = 'reserved'
                slot_status = 'reserved'

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

            # For active sessions, allow early ending
            if session.status == 'active':
                # End the session early
                session.status = 'completed'
                session.actual_end_time = now
                session.save()
                # Free up the slot
                slot = session.slot
                slot.status = 'available'
                slot.save()
                # Calculate refund for unused time
                remaining_time = (session.end_time - now).total_seconds() / 3600
                if remaining_time > 0:
                    payment = Payment.objects.filter(session=session).first()
                    if payment:
                        payment.status = 'refunded'
                        payment.save()
                return JsonResponse({'success': True, 'message': 'Session ended successfully'})

            # For reserved sessions (future), cancel normally
            if session.start_time <= now:
                return JsonResponse({'success': False, 'error': 'Cannot cancel active/past session'})

            if session.status != 'reserved':
                return JsonResponse({'success': False, 'error': 'Session not reserved'})

            slot = session.slot
            slot.status = 'available'
            slot.save()
            session.status = 'cancelled'
            session.save()

            payment = Payment.objects.filter(session=session).first()
            if payment and payment.status == 'completed':
                payment.status = 'refunded'
                payment.save()

            return JsonResponse({'success': True, 'message': 'Booking cancelled and refunded successfully'})
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
                    'hourly_rate': float(zone.hourly_rate),
                })

            all_slots = []
            for slot in ParkingSlot.objects.select_related('zone').all():
                all_slots.append({
                    'slot_number': slot.slot_number,
                    'zone_id': slot.zone.zone_id,
                    'zone_name': slot.zone.name,
                    'slot_type': slot.slot_type,
                    'status': slot.status,
                    'hourly_rate': float(slot.zone.hourly_rate),
                })

            recent_sessions = []
            for session in ParkingSession.objects.select_related('slot', 'slot__zone').order_by('-start_time')[:50]:
                start_time_local = session.start_time.astimezone(timezone.get_current_timezone())
                status_display = 'Reserved' if session.status == 'reserved' else ('Active' if session.status == 'active' else ('Completed' if session.status == 'completed' else 'Cancelled'))
                payment = session.payments.first()
                recent_sessions.append({
                    'session_id': str(session.session_id),
                    'slot_number': session.slot.slot_number,
                    'zone_id': session.slot.zone.zone_id,
                    'zone_name': session.slot.zone.name,
                    'vehicle_number': session.vehicle_number,
                    'start_time': start_time_local.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': status_display,
                    'payment_method': payment.payment_method if payment else 'N/A'
                })

            return Response({
                'success': True,
                'overview': {
                    'total_slots': total_slots,
                    'available_slots': available_slots,
                    'occupied_slots': occupied_slots,
                    'reserved_slots': reserved_slots,
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
                    'hourly_rate': float(zone.hourly_rate),
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
                    'hourly_rate': float(slot.zone.hourly_rate),
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