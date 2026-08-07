"""
SmartPark Database Initialization Script (Simple Version)
"""

import os
import django
import random
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_system.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from parking_app.models import ParkingZone, ParkingSlot, ParkingSession

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


def get_reasonable_price(zone_type):
    """Get reasonable price based on zone type"""
    return REASONABLE_PRICES.get(zone_type, REASONABLE_PRICES['default'])


def create_zones():
    print("📊 Creating parking zones...")

    zones_data = [
        {'zone_id': 'A', 'name': 'Main Entrance', 'capacity': 50, 'zone_type': 'commercial'},
        {'zone_id': 'B', 'name': 'Shopping Mall', 'capacity': 40, 'zone_type': 'shopping'},
        {'zone_id': 'C', 'name': 'Office Complex', 'capacity': 60, 'zone_type': 'office'},
        {'zone_id': 'D', 'name': 'EV Charging', 'capacity': 20, 'zone_type': 'commercial'},
        {'zone_id': 'E', 'name': 'Premium Parking', 'capacity': 30, 'zone_type': 'commercial'},
    ]

    zones_created = 0
    for zone_data in zones_data:
        # Get reasonable price based on zone type
        hourly_rate = get_reasonable_price(zone_data['zone_type'])

        zone, created = ParkingZone.objects.get_or_create(
            zone_id=zone_data['zone_id'],
            defaults={
                'name': zone_data['name'],
                'capacity': zone_data['capacity'],
                'hourly_rate': hourly_rate,
                'location_x': 85.3240,  # Default Kathmandu coordinates
                'location_y': 27.7172,
                'zone_type': zone_data['zone_type'],
                'address': f"{zone_data['name']}, Kathmandu",
                'is_active': True
            }
        )

        # Update coordinates for specific zones
        if zone_data['zone_id'] == 'A':
            zone.location_x, zone.location_y = 85.3240, 27.7172
        elif zone_data['zone_id'] == 'B':
            zone.location_x, zone.location_y = 85.3300, 27.7200
        elif zone_data['zone_id'] == 'C':
            zone.location_x, zone.location_y = 85.3180, 27.7150
        elif zone_data['zone_id'] == 'D':
            zone.location_x, zone.location_y = 85.3350, 27.7250
        elif zone_data['zone_id'] == 'E':
            zone.location_x, zone.location_y = 85.3280, 27.7220

        zone.save()

        if created:
            zones_created += 1
            print(f"   ✅ Created zone: {zone.zone_id} - {zone_data['name']} (Rs {hourly_rate}/hour)")

            # Create slots for zone
            slots_created = 0
            for i in range(1, zone_data['capacity'] + 1):
                slot_number = f"{zone_data['zone_id']}{i:03d}"

                # Assign slot types with distribution
                if i % 10 == 0:
                    slot_type = 'EV'
                elif i % 4 == 0:
                    slot_type = 'Compact'
                elif i % 7 == 0:
                    slot_type = 'Premium'
                else:
                    slot_type = 'Regular'

                # 75% available, 25% occupied for demo
                if i <= int(zone_data['capacity'] * 0.75):
                    status = 'available'
                else:
                    status = 'occupied'

                slot, slot_created = ParkingSlot.objects.get_or_create(
                    slot_number=slot_number,
                    defaults={
                        'zone': zone,
                        'slot_type': slot_type,
                        'status': status,
                        'sensor_id': f"SENSOR_{slot_number}",
                        'location_x': zone.location_x + random.uniform(-0.0005, 0.0005),
                        'location_y': zone.location_y + random.uniform(-0.0005, 0.0005)
                    }
                )
                if slot_created:
                    slots_created += 1

            print(f"      ✅ Created {slots_created} slots for {zone_data['name']}")

    print(f"✅ Total zones created: {zones_created}")


def create_admin():
    print("👤 Creating admin user...")

    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@smartpark.com', 'admin123')
        print("✅ Admin user created: admin / admin123")
    else:
        print("ℹ️ Admin user already exists")


def create_sample_sessions():
    """Create sample parking sessions for demonstration (optional)"""
    print("📝 Creating sample parking sessions...")

    # Get some random slots that are occupied
    occupied_slots = ParkingSlot.objects.filter(status='occupied')[:5]

    sessions_created = 0
    for slot in occupied_slots:
        start_time = timezone.now() - timedelta(hours=random.randint(1, 3))
        end_time = start_time + timedelta(hours=random.randint(1, 3))

        session, created = ParkingSession.objects.get_or_create(
            slot=slot,
            start_time=start_time,
            defaults={
                'status': 'active',
                'vehicle_number': f"BA{random.randint(1,99)}KHA{random.randint(1000,9999)}",
                'end_time': end_time,
                'payment_status': 'paid'
            }
        )
        if created:
            sessions_created += 1

    print(f"✅ Created {sessions_created} sample sessions")


def show_summary():
    """Display database summary"""
    print("")
    print("=" * 70)
    print("📊 DATABASE SUMMARY")
    print("=" * 70)

    total_zones = ParkingZone.objects.count()
    total_slots = ParkingSlot.objects.count()
    available_slots = ParkingSlot.objects.filter(status='available').count()
    occupied_slots = ParkingSlot.objects.filter(status='occupied').count()
    reserved_slots = ParkingSlot.objects.filter(status='reserved').count()

    print(f"Total Zones: {total_zones}")
    print(f"Total Slots: {total_slots}")
    print(f"Available Slots: {available_slots}")
    print(f"Occupied Slots: {occupied_slots}")
    print(f"Reserved Slots: {reserved_slots}")

    print("")
    print("📊 Vehicle Compatibility Summary:")
    print("-" * 50)

    vehicle_data = [
        ('Sedan', ['Regular', 'Premium']),
        ('SUV', ['Regular', 'Premium']),
        ('Compact', ['Compact', 'Regular']),
        ('EV', ['EV', 'Regular']),
        ('Motorcycle', ['Compact', 'Regular']),
    ]

    for vehicle, types in vehicle_data:
        count = ParkingSlot.objects.filter(status='available', slot_type__in=types).count()
        print(f"✅ {vehicle}: {count} available slots")

    print("")
    print("📊 Price Summary by Zone Type:")
    print("-" * 40)
    for zone_type, price in REASONABLE_PRICES.items():
        if zone_type != 'default':
            count = ParkingZone.objects.filter(zone_type=zone_type).count()
            print(f"  {zone_type.upper()}: Rs {price}/hour ({count} zones)")

    print("=" * 70)


def main():
    print("=" * 70)
    print("🚗 SMART PARKING SYSTEM INITIALIZATION")
    print("=" * 70)
    print("")

    # Delete existing data
    print("🗑️ Clearing existing data...")
    ParkingSession.objects.all().delete()
    ParkingSlot.objects.all().delete()
    ParkingZone.objects.all().delete()
    print("✅ Cleared all existing data")
    print("")

    create_zones()
    print("")
    create_admin()
    print("")
    create_sample_sessions()
    print("")
    show_summary()

    print("")
    print("=" * 70)
    print("✅ INITIALIZATION COMPLETE!")
    print("=" * 70)
    print("")
    print("🔧 To run the server:")
    print("   python manage.py runserver")
    print("")
    print("🌐 Access the application:")
    print("   Home: http://localhost:8000/")
    print("   Dashboard: http://localhost:8000/dashboard/")
    print("   Live Map: http://localhost:8000/map/")
    print("   Admin: http://localhost:8000/admin/")
    print("=" * 70)


if __name__ == '__main__':
    main()