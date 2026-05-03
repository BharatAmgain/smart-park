import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_system.settings')
django.setup()

from django.contrib.auth.models import User
from parking_app.models import ParkingZone, ParkingSlot, ParkingSession


def create_zones():
    zones_data = [
        {'zone_id': 'A', 'name': 'Main Entrance', 'capacity': 50, 'hourly_rate': 2.5, 'location_x': 85.3240,
         'location_y': 27.7172},
        {'zone_id': 'B', 'name': 'Shopping Mall', 'capacity': 40, 'hourly_rate': 3.0, 'location_x': 85.3300,
         'location_y': 27.7200},
        {'zone_id': 'C', 'name': 'Office Complex', 'capacity': 60, 'hourly_rate': 2.0, 'location_x': 85.3180,
         'location_y': 27.7150},
        {'zone_id': 'D', 'name': 'EV Charging', 'capacity': 20, 'hourly_rate': 4.0, 'location_x': 85.3350,
         'location_y': 27.7250},
        {'zone_id': 'E', 'name': 'Premium Parking', 'capacity': 30, 'hourly_rate': 5.0, 'location_x': 85.3280,
         'location_y': 27.7220},
    ]

    for zone_data in zones_data:
        zone, created = ParkingZone.objects.get_or_create(
            zone_id=zone_data['zone_id'],
            defaults={
                'name': zone_data['name'],
                'capacity': zone_data['capacity'],
                'hourly_rate': zone_data['hourly_rate'],
                'location_x': zone_data['location_x'],
                'location_y': zone_data['location_y']
            }
        )
        if created:
            print(f"✅ Created zone: {zone.zone_id}")

            # Create slots for zone
            for i in range(1, zone_data['capacity'] + 1):
                slot_number = f"{zone_data['zone_id']}{i:03d}"
                slot_type = random.choice(['Regular', 'Regular', 'Regular', 'Compact', 'EV'])
                ParkingSlot.objects.get_or_create(
                    slot_number=slot_number,
                    defaults={
                        'zone': zone,
                        'slot_type': slot_type,
                        'status': 'available',
                        'sensor_id': f"SENSOR_{slot_number}"
                    }
                )
            print(f"   Created {zone_data['capacity']} slots")


def create_admin():
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@parking.com', 'admin123')
        print("✅ Created admin user (username: admin, password: admin123)")


def main():
    print("Initializing Smart Parking System...")
    create_zones()
    create_admin()
    print("✅ Initialization complete!")
    print("\n🔧 To run the server:")
    print("   cd backend/parking_system")
    print("   python manage.py runserver")
    print("\n🌐 Access the application:")
    print("   Home: http://localhost:8000/")
    print("   Dashboard: http://localhost:8000/dashboard/")
    print("   Live Map: http://localhost:8000/map/")
    print("   Admin: http://localhost:8000/admin/")


if __name__ == '__main__':
    main()