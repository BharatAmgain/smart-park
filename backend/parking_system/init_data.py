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


def create_zones():
    print("📊 Creating parking zones...")

    zones_data = [
        {'zone_id': 'A', 'name': 'Main Entrance', 'capacity': 50, 'hourly_rate': 2.5,
         'location_x': 85.3240, 'location_y': 27.7172, 'zone_type': 'commercial'},
        {'zone_id': 'B', 'name': 'Shopping Mall', 'capacity': 40, 'hourly_rate': 3.0,
         'location_x': 85.3300, 'location_y': 27.7200, 'zone_type': 'shopping'},
        {'zone_id': 'C', 'name': 'Office Complex', 'capacity': 60, 'hourly_rate': 2.0,
         'location_x': 85.3180, 'location_y': 27.7150, 'zone_type': 'office'},
        {'zone_id': 'D', 'name': 'EV Charging', 'capacity': 20, 'hourly_rate': 4.0,
         'location_x': 85.3350, 'location_y': 27.7250, 'zone_type': 'commercial'},
        {'zone_id': 'E', 'name': 'Premium Parking', 'capacity': 30, 'hourly_rate': 5.0,
         'location_x': 85.3280, 'location_y': 27.7220, 'zone_type': 'commercial'},
    ]

    zones_created = 0
    for zone_data in zones_data:
        zone, created = ParkingZone.objects.get_or_create(
            zone_id=zone_data['zone_id'],
            defaults={
                'name': zone_data['name'],
                'capacity': zone_data['capacity'],
                'hourly_rate': zone_data['hourly_rate'],
                'location_x': zone_data['location_x'],
                'location_y': zone_data['location_y'],
                'zone_type': zone_data['zone_type'],
                'address': f"{zone_data['name']}, Kathmandu",
                'is_active': True
            }
        )
        if created:
            zones_created += 1
            print(f"   ✅ Created zone: {zone.zone_id} - {zone_data['name']}")

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
        # Use timezone.now() for timezone-aware datetimes
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

    print("=" * 70)


def main():
    print("=" * 70)
    print("🚗 SMART PARKING SYSTEM INITIALIZATION")
    print("=" * 70)
    print("")

    # Delete existing data (optional - remove if you want to keep existing data)
    print("🗑️ Clearing existing data...")
    ParkingSession.objects.all().delete()
    print("✅ Cleared existing sessions")
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
    print("   cd backend/parking_system")
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