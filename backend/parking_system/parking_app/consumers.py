import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ParkingSlot, ParkingZone, ParkingSession
from .parking_allocator import allocator


class ParkingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time parking updates"""

    async def connect(self):
        self.group_name = 'parking_updates'

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial data
        await self.send_initial_data()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')

            if message_type == 'get_nearest':
                user_lat = data.get('lat')
                user_lng = data.get('lng')
                vehicle_type = data.get('vehicle_type', 'Sedan')

                if user_lat and user_lng:
                    nearest = await self.get_nearest_parking(user_lat, user_lng, vehicle_type)
                    await self.send(text_data=json.dumps({
                        'type': 'nearest_parking',
                        'data': nearest
                    }))

            elif message_type == 'subscribe':
                groups = data.get('groups', [])
                for group in groups:
                    await self.channel_layer.group_add(group, self.channel_name)
                await self.send(text_data=json.dumps({
                    'type': 'subscribed',
                    'groups': groups
                }))

            elif message_type == 'get_status':
                await self.send_initial_data()

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def parking_update(self, event):
        """Send parking update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'parking_update',
            'data': event['data']
        }))

    async def send_initial_data(self):
        """Send initial parking data"""
        zones_data = await self.get_zones_data()
        slots_data = await self.get_slots_data()
        stats_data = await self.get_stats_data()

        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'zones': zones_data,
            'slots': slots_data,
            'stats': stats_data,
            'timestamp': timezone.now().isoformat()
        }))

    @database_sync_to_async
    def get_zones_data(self):
        """Get all zones data"""
        zones = ParkingZone.objects.all()
        return [{
            'zone_id': z.zone_id,
            'name': z.name,
            'available_slots': z.get_available_slots_count(),
            'total_slots': z.capacity,
            'occupied': z.occupied,
            'hourly_rate': float(z.hourly_rate),
            'coordinates': {'lat': float(z.location_y) if z.location_y else 0,
                            'lng': float(z.location_x) if z.location_x else 0}
        } for z in zones]

    @database_sync_to_async
    def get_slots_data(self):
        """Get all slots data"""
        slots = ParkingSlot.objects.select_related('zone').all()
        return [{
            'slot_number': s.slot_number,
            'zone_id': s.zone.zone_id,
            'slot_type': s.slot_type,
            'status': s.status,
            'coordinates': {'lat': float(s.zone.location_y) if s.zone.location_y else 0,
                            'lng': float(s.zone.location_x) if s.zone.location_x else 0}
        } for s in slots[:50]]

    @database_sync_to_async
    def get_stats_data(self):
        """Get statistics data"""
        total_slots = ParkingSlot.objects.count()
        occupied_slots = ParkingSlot.objects.filter(status='occupied').count()
        available_slots = ParkingSlot.objects.filter(status='available').count()
        reserved_slots = ParkingSlot.objects.filter(status='reserved').count()

        return {
            'total_slots': total_slots,
            'occupied_slots': occupied_slots,
            'available_slots': available_slots,
            'reserved_slots': reserved_slots,
            'occupancy_rate': round((occupied_slots / total_slots * 100), 2) if total_slots > 0 else 0
        }

    @database_sync_to_async
    def get_nearest_parking(self, user_lat, user_lng, vehicle_type):
        """Get nearest parking slots"""
        return allocator.find_nearest_slots(user_lat, user_lng, limit=10, vehicle_type=vehicle_type)


class NearestParkingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer specifically for nearest parking tracking"""

    async def connect(self):
        self.user_id = self.scope['user'].id if self.scope['user'].is_authenticated else 'anonymous'
        self.group_name = f'nearest_parking_{self.user_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'update_location':
            user_lat = data.get('lat')
            user_lng = data.get('lng')
            vehicle_type = data.get('vehicle_type', 'Sedan')

            if user_lat and user_lng:
                nearest = await self.get_nearest_parking(user_lat, user_lng, vehicle_type)

                await self.send(text_data=json.dumps({
                    'type': 'nearest_update',
                    'nearest_slots': nearest,
                    'timestamp': timezone.now().isoformat()
                }))

    @database_sync_to_async
    def get_nearest_parking(self, user_lat, user_lng, vehicle_type):
        return allocator.find_nearest_slots(user_lat, user_lng, limit=5, vehicle_type=vehicle_type)