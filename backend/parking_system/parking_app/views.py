"""
SmartPark – Complete Views (Fixed Authentication + All Features)
"""
from django.http import HttpResponseRedirect, JsonResponse
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
from django.contrib.auth.forms import UserCreationForm
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

# ============================================
# BACKGROUND SCHEDULER
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
# REAL-TIME SIMULATION THREADS
# ============================================
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

def update_reserved_to_active():
    while True:
        time_module.sleep(10)
        try:
            now = timezone.now()
            sessions = ParkingSession.objects.filter(status='reserved', start_time__lte=now)
            for session in sessions:
                session.status = 'active'
                session.save(update_fields=['status', 'updated_at'])
                slot = session.slot
                if slot.status != 'occupied':
                    old_status = slot.status
                    slot.status = 'occupied'
                    slot.save(update_fields=['status', 'last_updated'])
                    print(f"[AUTO] Slot {slot.slot_number}: {old_status} → occupied (session started)")
                    cache.delete(LIVE_DATA_CACHE_KEY)
        except Exception as e:
            print(f"Reservation updater error: {e}")

try:
    threading.Thread(target=simulate_realtime_updates, daemon=True).start()
    threading.Thread(target=update_reserved_to_active, daemon=True).start()
    print("✅ Real-time threads started")
except:
    pass

# ============================================
# HTML PAGE VIEWS
# ============================================
@login_required(login_url='/login/')
def home_page(request):
    return render(request, 'base.html')

@login_required(login_url='/login/')
def dashboard_page(request):
    return render(request, 'dashboard.html')

@login_required(login_url='/login/')
def map_page(request):
    return render(request, 'base.html')

def intro_page(request):
    return render(request, 'intro.html')

@login_required(login_url='/login/')
def my_bookings_page(request):
    return render(request, 'my_bookings.html')

def admin_redirect(request):
    return redirect('/admin/')

# ============================================
# AUTHENTICATION (FIXED – USES UserCreationForm)
# ============================================
def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Save email manually (UserCreationForm doesn't include email)
            email = request.POST.get('email', '')
            if email:
                user.email = email
                user.save()
            auth_login(request, user)
            return redirect('/map/')
        else:
            print("Registration errors:", form.errors)
            # Re-render the registration page with the form (which contains errors)
            return render(request, 'register.html', {'form': form})
    else:
        form = UserCreationForm()
        return render(request, 'register.html', {'form': form})

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
    cache.set(f"otp_{email}", otp, timeout=settings.OTP_EXPIRY_SECONDS)
    print(f"[OTP] Generated for {email}: {otp}")
    send_mail(
        'SmartPark OTP',
        f'Your OTP is: {otp}\nValid for {settings.OTP_EXPIRY_SECONDS//60} minutes.',
        'noreply@smartpark.com',
        [email],
        fail_silently=False
    )
    return True

def verify_email_otp(email, otp):
    email = email.strip().lower()
    stored = cache.get(f"otp_{email}")
    if stored and stored == otp:
        cache.delete(f"otp_{email}")
        return True
    return False

# ============================================
# API VIEWS (ALL ORIGINAL FUNCTIONALITY)
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
            'Truck': ['Regular', 'Premium']
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

# ========== LIVE PARKING VIEW ==========
class LiveParkingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cached_data = cache.get(LIVE_DATA_CACHE_KEY)
        if cached_data:
            return Response(cached_data)

        try:
            now = timezone.now()
            zones = ParkingZone.objects.filter(is_active=True)

            if not zones.exists():
                total_slots = ParkingSlot.objects.count()
                available = ParkingSlot.objects.filter(status='available').count()
                occupied = ParkingSlot.objects.filter(status='occupied').count()
                reserved = ParkingSlot.objects.filter(status='reserved').count()
                response_data = {
                    'success': True,
                    'zones': [],
                    'summary': {
                        'total_available': available,
                        'total_occupied': occupied,
                        'total_reserved': reserved,
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
            total_available = total_occupied = total_reserved = 0

            for zone in zones:
                slots = zone.slots.all()
                available = occupied = reserved = 0
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

                total_available += available
                total_occupied += occupied
                total_reserved += reserved

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
                    'total_slots': total_available + total_occupied + total_reserved
                }
            }
            cache.set(LIVE_DATA_CACHE_KEY, response_data, CACHE_TIMEOUT)
            return Response(response_data)

        except Exception as e:
            print(f"LiveParkingView ERROR: {e}")
            import traceback
            traceback.print_exc()
            total_slots = ParkingSlot.objects.count()
            available = ParkingSlot.objects.filter(status='available').count()
            occupied = ParkingSlot.objects.filter(status='occupied').count()
            reserved = ParkingSlot.objects.filter(status='reserved').count()
            return Response({
                'success': True,
                'zones': [],
                'summary': {
                    'total_available': available,
                    'total_occupied': occupied,
                    'total_reserved': reserved,
                    'total_slots': total_slots
                }
            })

# ========== NEAREST PARKING VIEW ==========
@method_decorator(csrf_exempt, name='dispatch')
class NearestParkingView(APIView):
    permission_classes = [AllowAny]
    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
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
            }
            compatible_types = compatibility.get(vehicle_type, ['Regular'])
            available_slots = ParkingSlot.objects.filter(status='available', slot_type__in=compatible_types).select_related('zone')
            nearest = []
            for slot in available_slots:
                zone = slot.zone
                if zone.location_x and zone.location_y:
                    slot_lat = float(zone.location_y)
                    slot_lng = float(zone.location_x)
                    dist = self.haversine(user_lat, user_lng, slot_lat, slot_lng)
                    walk_time = int(dist / 1.4 / 60) if dist > 0 else 0
                else:
                    dist = 999999
                    walk_time = 999
                nearest.append({
                    'slot_number': slot.slot_number,
                    'zone_id': zone.zone_id,
                    'zone_name': zone.name,
                    'slot_type': slot.slot_type,
                    'distance_meters': round(dist, 2),
                    'walk_time_minutes': walk_time,
                    'hourly_rate': float(zone.hourly_rate),
                })
            nearest.sort(key=lambda x: x['distance_meters'])
            return Response({'success': True, 'nearest_slots': nearest[:limit], 'vehicle_type': vehicle_type, 'total_found': len(nearest)})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

def calculate_price(vehicle_type, duration_hours):
    duration = float(duration_hours)
    if vehicle_type == 'Motorcycle':
        if duration >= 5: return 40
        elif duration <= 0.5: return 10
        else: return 10 + int((duration - 0.5) / 0.5) * 5
    elif vehicle_type == 'EV':
        if duration >= 5: return 80
        else: return 50 + int(duration - 1) * 15
    else:
        if duration >= 5: return 70
        else: return 40 + int(duration - 1) * 15

@method_decorator(csrf_exempt, name='dispatch')
class AllocationView(APIView):
    permission_classes = [AllowAny]
    VEHICLE_COMPATIBILITY = {
        'Sedan': ['Regular', 'Premium'],
        'SUV': ['Regular', 'Premium'],
        'Compact': ['Compact', 'Regular'],
        'EV': ['EV', 'Regular'],
        'Motorcycle': ['Compact', 'Regular'],
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

# ============================================
# eSewa & KHALTI HELPERS (Base64 signature)
# ============================================
def generate_esewa_signature(total_amount, transaction_uuid, product_code):
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    secret_key = settings.ESEWA_SECRET_KEY
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
        'product_code': settings.ESEWA_MERCHANT_CODE,
        'total_amount': str(amount_int),
        'transaction_uuid': transaction_uuid,
        'product_service_charge': '0',
        'product_delivery_charge': '0',
        'tax_amount': '0',
        'success_url': settings.ESEWA_SUCCESS_URL,
        'failure_url': settings.ESEWA_FAILURE_URL,
        'signed_field_names': 'total_amount,transaction_uuid,product_code',
    }
    data['signature'] = generate_esewa_signature(amount_int, transaction_uuid, settings.ESEWA_MERCHANT_CODE)
    return data

def initiate_khalti_payment(amount, product_name, transaction_uuid, return_url):
    headers = {'Authorization': f'Key {settings.KHALTI_SECRET_KEY}', 'Content-Type': 'application/json'}
    payload = {
        'return_url': return_url,
        'website_url': 'http://localhost:8000',
        'amount': amount * 100,
        'purchase_order_id': transaction_uuid,
        'purchase_order_name': product_name,
        'customer_info': {'name': 'SmartPark User', 'email': 'user@smartpark.com', 'phone': '9800000000'}
    }
    try:
        response = requests.post(settings.KHALTI_TEST_URL, json=payload, headers=headers)
        print(f"[KHALTI] Init response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            data = response.json()
            return data.get('payment_url')
    except Exception as e:
        print(f"Khalti error: {e}")
    return None

def verify_khalti_payment(pidx):
    headers = {'Authorization': f'Key {settings.KHALTI_SECRET_KEY}', 'Content-Type': 'application/json'}
    payload = {'pidx': pidx}
    try:
        response = requests.post(settings.KHALTI_VERIFY_URL, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get('status') == 'Completed'
    except Exception as e:
        print(e)
    return False

USE_MOCK_ESEWA = False

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
        if '@' not in account_id or '.' not in account_id:
            return Response({'error': 'Valid email required'}, status=400)
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
        request.session['pending_reservation'] = {
            'slot_number': slot_number,
            'vehicle_type': vehicle_type,
            'vehicle_number': vehicle_number,
            'duration_hours': duration_hours,
            'start_time': start_time_str,
            'payment_method': payment_method,
            'account_id': account_id,
            'amount': amount,
            'transaction_uuid': transaction_uuid,
        }

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
                        # Mock fallback (not used)
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
                        # REAL eSewa
                        esewa_data = initiate_esewa_payment(amount, slot_number, f"Parking {slot_number}", transaction_uuid)
                        return Response({
                            'success': True,
                            'payment_method': 'esewa',
                            'form_action': settings.ESEWA_TEST_URL,
                            'form_data': esewa_data
                        })
                elif payment_method == 'khalti':
                    return_url = f"{settings.ESEWA_SUCCESS_URL}?method=khalti&txn_id={transaction_uuid}"
                    payment_url = initiate_khalti_payment(amount, f"Parking {slot_number}", transaction_uuid, return_url)
                    if payment_url:
                        return Response({'success': True, 'payment_method': 'khalti', 'payment_url': payment_url})
                    else:
                        return Response({'error': 'Khalti initiation failed'}, status=500)
                return Response({'error': 'Invalid payment method'}, status=400)
            else:
                return Response({'error': 'Invalid or expired OTP'}, status=400)

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
            pending = request.session.get('pending_reservation')

        if not pending:
            slot = request.GET.get('slot')
            email = request.GET.get('email')
            if slot and email:
                try:
                    pending = PendingReservation.objects.filter(slot_number=slot, account_id=email).latest('created_at')
                except:
                    pass

        if not pending:
            return HttpResponseRedirect("/map/?payment=failed&reason=no_reservation")

        if isinstance(pending, dict):
            slot_number = pending['slot_number']
            vehicle_type = pending['vehicle_type']
            vehicle_number = pending['vehicle_number']
            duration_hours = pending['duration_hours']
            start_time_str = pending['start_time']
            payment_method = pending['payment_method']
            is_db = False
        else:
            slot_number = pending.slot_number
            vehicle_type = pending.vehicle_type
            vehicle_number = pending.vehicle_number
            duration_hours = pending.duration_hours
            start_time_str = pending.start_time
            payment_method = pending.payment_method
            is_db = True

        if method == 'khalti':
            if not pidx or not verify_khalti_payment(pidx):
                return HttpResponseRedirect("/map/?payment=failed&reason=khalti_verification_failed")
            txn_id = transaction_uuid or (pending.transaction_uuid if hasattr(pending, 'transaction_uuid') else None)
        else:
            txn_id = transaction_uuid or (pending.transaction_uuid if hasattr(pending, 'transaction_uuid') else None)

        alloc_data = {
            'slot_number': slot_number,
            'vehicle_type': vehicle_type,
            'vehicle_number': vehicle_number,
            'duration_hours': duration_hours,
            'start_time': start_time_str,
            'transaction_id': txn_id,
            'payment_method': payment_method,
        }
        response = self.do_allocation(request, alloc_data)
        if response.get('success'):
            if is_db:
                pending.delete()
            request.session.pop('pending_reservation', None)
            session_id = response.get('session_id')
            return HttpResponseRedirect(f"/map/?payment=success&slot={slot_number}&session_id={session_id}")
        else:
            return HttpResponseRedirect("/map/?payment=failed&reason=allocation_error")

    def do_allocation(self, request, data):
        try:
            slot = ParkingSlot.objects.get(slot_number=data['slot_number'])
            if slot.status != 'available':
                return {'success': False, 'error': 'Slot not available'}
            if data.get('start_time'):
                try:
                    start_time = timezone.make_aware(datetime.fromisoformat(data['start_time']))
                except:
                    start_time = timezone.now()
            else:
                start_time = timezone.now()
            end_time = start_time + timedelta(hours=float(data['duration_hours']))
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
                vehicle_number=data['vehicle_number'],
                start_time=start_time,
                end_time=end_time
            )
            Payment.objects.create(
                session=session,
                amount=calculate_price(data['vehicle_type'], data['duration_hours']),
                payment_method=data['payment_method'],
                transaction_id=data['transaction_id'],
                status='completed',
                payment_date=timezone.now()
            )
            return {'success': True, 'session_id': str(session.session_id)}
        except Exception as e:
            print(f"Allocation error: {e}")
            return {'success': False, 'error': str(e)}

class CancelSessionView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, session_id):
        try:
            session = ParkingSession.objects.get(session_id=session_id)
            if request.user.is_authenticated and session.user != request.user.profile:
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            now = timezone.now()
            if session.start_time <= now:
                return JsonResponse({'success': False, 'error': 'Cannot cancel active/past session'})
            if session.status != 'reserved':
                return JsonResponse({'success': False, 'error': 'Session not reserved'})
            slot = session.slot
            slot.status = 'available'
            slot.save()
            session.status = 'cancelled'
            session.save()
            payment = Payment.objects.get(session=session)
            payment.status = 'refunded'
            payment.save()
            return JsonResponse({'success': True, 'message': 'Booking cancelled and refunded'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class PaymentFailureView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        request.session.pop('pending_reservation', None)
        return HttpResponseRedirect("/map/?payment=failed&reason=user_cancelled")

class PaymentVerifyView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        pidx = request.data.get('pidx')
        if pidx and verify_khalti_payment(pidx):
            return Response({'success': True})
        return Response({'success': False}, status=400)

class InvoiceView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, session_id):
        if session_id == 'mock':
            return Response({'success': True, 'invoice': {'invoice_no': 'MOCK', 'date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'), 'slot_number': 'MOCK', 'zone_name': 'Mock', 'vehicle_number': 'MOCK', 'duration_hours': 1, 'amount': 0, 'payment_method': 'esewa', 'transaction_id': 'mock', 'status': 'completed'}})
        try:
            session = ParkingSession.objects.get(session_id=session_id)
            payment = Payment.objects.get(session=session)
            slot = session.slot
            zone = slot.zone
            start_local = session.start_time.astimezone(timezone.get_current_timezone())
            invoice_data = {
                'invoice_no': f"INV-{session.session_id[:8].upper()}",
                'date': start_local.strftime('%Y-%m-%d %H:%M:%S'),
                'slot_number': slot.slot_number,
                'zone_name': zone.name,
                'vehicle_number': session.vehicle_number,
                'duration_hours': (session.end_time - session.start_time).total_seconds() / 3600,
                'amount': float(payment.amount),
                'payment_method': payment.payment_method,
                'transaction_id': payment.transaction_id,
                'status': session.status
            }
            return Response({'success': True, 'invoice': invoice_data})
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=404)

class DashboardView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        nepal_tz = timezone.get_current_timezone()
        now = timezone.now()
        total_slots = ParkingSlot.objects.count()
        available = ParkingSlot.objects.filter(status='available').count()
        occupied = ParkingSlot.objects.filter(status='occupied').count()
        reserved_slots = ParkingSession.objects.filter(start_time__gt=now, status__in=['reserved', 'active']).values('slot').distinct().count()
        reserved = reserved_slots
        zones_data = []
        for zone in ParkingZone.objects.filter(is_active=True):
            zones_data.append({
                'zone_id': zone.zone_id,
                'zone_name': zone.name,
                'total_slots': zone.capacity,
                'available_slots': zone.get_available_slots_count(),
                'occupied_slots': zone.slots.filter(status='occupied').count(),
                'reserved_slots': ParkingSession.objects.filter(slot__zone=zone, start_time__gt=now, status__in=['reserved', 'active']).values('slot').distinct().count(),
                'occupancy_rate': round((zone.slots.filter(status='occupied').count() / zone.capacity * 100), 1) if zone.capacity else 0,
                'hourly_rate': float(zone.hourly_rate),
            })
        all_slots = [{'slot_number': s.slot_number, 'zone_id': s.zone.zone_id, 'zone_name': s.zone.name, 'slot_type': s.slot_type, 'status': s.status, 'hourly_rate': float(s.zone.hourly_rate)} for s in ParkingSlot.objects.select_related('zone')]
        recent_sessions = ParkingSession.objects.select_related('slot', 'slot__zone').prefetch_related('payments').order_by('-start_time')[:20]
        sessions_data = []
        for s in recent_sessions:
            if s.start_time > now:
                display_status = 'Reserved'
            else:
                display_status = 'Active' if s.status == 'active' else 'Completed' if s.status == 'completed' else 'Cancelled' if s.status == 'cancelled' else s.status.capitalize()
            payment = s.payments.first()
            payment_method = payment.payment_method if payment else 'N/A'
            start_time_local = s.start_time.astimezone(nepal_tz)
            sessions_data.append({
                'session_id': str(s.session_id)[:8],
                'slot_number': s.slot.slot_number,
                'zone_id': s.slot.zone.zone_id,
                'vehicle_number': s.vehicle_number,
                'start_time': start_time_local.strftime('%Y-%m-%d %H:%M:%S'),
                'status': display_status,
                'payment_method': payment_method.upper(),
            })
        return Response({'success': True, 'overview': {'total_slots': total_slots, 'available_slots': available, 'occupied_slots': occupied, 'reserved_slots': reserved}, 'zones': zones_data, 'all_slots': all_slots, 'recent_sessions': sessions_data})

class ZoneStatisticsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        zones = ParkingZone.objects.filter(is_active=True)
        data = [{'zone_id': z.zone_id, 'zone_name': z.name, 'available_slots': z.get_available_slots_count(), 'hourly_rate': float(z.hourly_rate)} for z in zones]
        return Response({'success': True, 'zones': data})

class SearchSlotsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        q = request.query_params.get('q', '')
        if not q:
            return Response({'error': 'Query required'}, status=400)
        slots = ParkingSlot.objects.filter(slot_number__icontains=q).select_related('zone')[:20]
        results = []
        for slot in slots:
            results.append({
                'slot_number': slot.slot_number,
                'zone_name': slot.zone.name,
                'slot_type': slot.slot_type,
                'status': slot.status,
                'hourly_rate': float(slot.zone.hourly_rate),
                'coordinates': {'lat': float(slot.zone.location_y) or 27.7172, 'lng': float(slot.zone.location_x) or 85.3240}
            })
        return Response({'success': True, 'results': results})

class TestAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'success': True, 'message': 'API is working'})