"""
Parking Slot Allocator with Nearest Parking Tracking
Uses Haversine formula for accurate distance calculation
"""
import math
import heapq
from django.db.models import Q
from .models import ParkingSlot, ParkingZone


class ParkingAllocator:
    """Allocates parking slots with nearest parking prioritization"""

    def __init__(self):
        self.priority_queue = []

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points
        on the Earth using Haversine formula
        """
        R = 6371000  # Earth's radius in meters

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance

    def calculate_walk_time(self, distance_meters, walking_speed=1.4):
        """Calculate estimated walk time in minutes"""
        if distance_meters is None:
            return None
        walk_time_seconds = distance_meters / walking_speed
        return int(walk_time_seconds / 60)

    def get_available_slots_with_coordinates(self, vehicle_type=None, slot_type=None):
        """Get available slots that have coordinates"""
        queryset = ParkingSlot.objects.filter(status='available')

        if vehicle_type:
            # Map vehicle type to compatible slot types
            compatibility = {
                'Sedan': ['Regular', 'Premium'],
                'SUV': ['Regular', 'Premium'],
                'Compact': ['Compact', 'Regular'],
                'EV': ['EV', 'Regular'],
                'Motorcycle': ['Compact', 'Regular']
            }
            compatible = compatibility.get(vehicle_type, ['Regular'])
            queryset = queryset.filter(slot_type__in=compatible)

        if slot_type and slot_type != 'Any':
            queryset = queryset.filter(slot_type=slot_type)

        # Only get slots with valid coordinates
        queryset = queryset.select_related('zone')

        return queryset

    def find_nearest_slots(self, user_lat, user_lng, limit=5, vehicle_type=None, max_distance=2000):
        """
        Find the nearest parking slots to user's location

        This is the core function for nearest parking tracking
        """
        available_slots = self.get_available_slots_with_coordinates(vehicle_type)

        nearest_slots = []

        for slot in available_slots:
            zone = slot.zone
            if zone.location_x and zone.location_y:
                slot_lat = float(zone.location_y)
                slot_lng = float(zone.location_x)

                distance = self.haversine_distance(user_lat, user_lng, slot_lat, slot_lng)

                if distance <= max_distance:
                    walk_time = self.calculate_walk_time(distance)

                    nearest_slots.append({
                        'slot': slot,
                        'slot_number': slot.slot_number,
                        'zone_id': zone.zone_id,
                        'zone_name': zone.name,
                        'slot_type': slot.slot_type,
                        'distance_meters': round(distance, 2),
                        'walk_time_minutes': walk_time,
                        'hourly_rate': float(zone.hourly_rate),
                        'coordinates': {'lat': slot_lat, 'lng': slot_lng},
                        'status': slot.status,
                        'is_reserved': slot.is_reserved
                    })

        # Sort by distance (nearest first)
        nearest_slots.sort(key=lambda x: x['distance_meters'])

        return nearest_slots[:limit]

    def allocate_nearest_slot(self, user_lat, user_lng, vehicle_number, vehicle_type='Sedan', duration=2):
        """
        Allocate the nearest available parking slot
        """
        nearest_slots = self.find_nearest_slots(user_lat, user_lng, limit=1, vehicle_type=vehicle_type)

        if not nearest_slots:
            return {
                'success': False,
                'message': 'No available parking slots found near your location',
                'slot': None,
                'nearest_slots': []
            }

        best_slot_data = nearest_slots[0]
        best_slot = best_slot_data['slot']

        # Update slot status
        best_slot.status = 'occupied'
        best_slot.last_updated = timezone.now()
        best_slot.save()

        # Update zone occupancy
        zone = best_slot.zone
        zone.occupied = zone.slots.filter(status__in=['occupied', 'reserved']).count()
        zone.save()

        return {
            'success': True,
            'message': f'Nearest slot {best_slot.slot_number} allocated successfully',
            'slot': best_slot,
            'distance_meters': best_slot_data['distance_meters'],
            'walk_time_minutes': best_slot_data['walk_time_minutes'],
            'hourly_rate': best_slot_data['hourly_rate'],
            'nearest_slots': nearest_slots
        }

    def find_alternative_slots(self, user_lat, user_lng, vehicle_type='Sedan', max_distance=1000):
        """Find alternative parking slots within radius"""
        return self.find_nearest_slots(user_lat, user_lng, limit=10, vehicle_type=vehicle_type,
                                       max_distance=max_distance)

    def get_zone_availability_summary(self):
        """Get summary of all zones with availability"""
        zones = ParkingZone.objects.all()
        summary = []

        for zone in zones:
            available = zone.get_available_slots_count()
            total = zone.capacity
            summary.append({
                'zone_id': zone.zone_id,
                'zone_name': zone.name,
                'available_slots': available,
                'total_slots': total,
                'availability_percentage': (available / total * 100) if total > 0 else 0,
                'coordinates': {
                    'lat': float(zone.location_y) if zone.location_y else 0,
                    'lng': float(zone.location_x) if zone.location_x else 0
                },
                'hourly_rate': float(zone.hourly_rate)
            })

        return summary


# Import timezone for datetime
from django.utils import timezone

# Global instance
allocator = ParkingAllocator()