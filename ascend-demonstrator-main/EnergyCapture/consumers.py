import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from channels.layers import get_channel_layer
from EnergyCapture.models import PowerClamp
from datetime import datetime, timedelta
import asyncio
import websockets

class ShellyConsumer(AsyncWebsocketConsumer):
    shelly_websocket = None
    access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwd2QiLCJpYXQiOjE3MzY1MDc0MjAsInVzZXJfaWQiOiIxMTUzMTUyIiwic24iOiIxIiwidXNlcl9hcGlfdXJsIjoiaHR0cHM6XC9cL3NoZWxseS00My1ldS5zaGVsbHkuY2xvdWQiLCJuIjo2NjIxLCJmcm9tIjoic2hlbGx5LWRpeSIsImV4cCI6MTczNjU1MDYyMH0.l_6Gl__DF-qdT-oDSCFekBxhkKfJ81aRKDURFZGkv34"
    ws_url = f"wss://shelly-43-eu.shelly.cloud:6113/shelly/wss/hk_sock?t={access_token}"

    async def connect(self):
        print("WebSocket connection attempt")
        await self.accept()
        print("WebSocket connection accepted")
        await self.channel_layer.group_add('shelly_group', self.channel_name)
        print("Added to shelly_group")

        if not self.shelly_websocket:
            await self.connect_to_shelly()

        initial_data = await self.get_initial_data()
        print(f"Sending initial data: {initial_data}")
        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'data': initial_data
        }))

    @database_sync_to_async
    def get_initial_data(self):
        print("Fetching initial data")
        cached_data = cache.get('power_clamp_data')
        if cached_data:
            print("Using cached data")
            return cached_data
        
        print("Fetching data from database")
        clamps = PowerClamp.objects.all()
        data = [{'name': clamp.name, 'deviceID': clamp.deviceID, 'total_power': clamp.total_power} for clamp in clamps]
        
        cache.set('power_clamp_data', data, timeout=300)  # Cache for 5 minutes
        return data

    async def connect_to_shelly(self):
        print("Attempting to connect to Shelly WebSocket")
        try:
            self.shelly_websocket = await websockets.connect(self.ws_url)
            print("Connected to Shelly WebSocket")
            asyncio.create_task(self.listen_to_shelly())
        except Exception as e:
            print(f"Failed to connect to Shelly: {str(e)}")

    # Example of using asyncio.gather for parallel async operations
    async def listen_to_shelly(self):
        try:
            while True:
                # Using gather to handle multiple tasks concurrently
                message = await self.shelly_websocket.recv()
                data = json.loads(message)
                if 'event' in data and data['event'] == 'Shelly:StatusOnChange':
                    power_data = self.extract_power_data(data)
                    # Run these tasks concurrently
                    await asyncio.gather(
                        self.broadcast_to_clients(power_data),
                        self.update_power_clamp(power_data)  
                    )
        except Exception as e:
            print(f"Error in Shelly WebSocket: {str(e)}")
            await self.connect_to_shelly()


    def extract_power_data(self, data):
        status = data.get('status', {})
        device = data.get('device', {})
        device_id = device.get('id', '')
        mac_address = status.get('mac', '').lower()
        
        power_data = {
            'device_id': device_id,
            'mac_address': mac_address,
            'total_power': status.get('total_power', 0),
            'time': status.get('time', '')
        }
        print(f"Extracted power data: {power_data}")
        return power_data

    async def broadcast_to_clients(self, data):
        print(f"Broadcasting to clients: {data}")
        await self.update_power_clamp(data)
        channel_layer = get_channel_layer()
        await channel_layer.group_send('shelly_group', {
            'type': 'shelly.message',
            'message': data
        })

    # Example of optimized database query to minimize delays
    @database_sync_to_async
    def update_power_clamp(self, data):
        print(f"Updating PowerClamp: {data}")
        try:
            power_clamp = PowerClamp.objects.get(deviceID__iexact=data['mac_address'])
            power_clamp.total_power = data['total_power']
            power_clamp.save()
            
            # Update cache
            cached_data = cache.get('power_clamp_data', [])
            for clamp in cached_data:
                if clamp['deviceID'].lower() == data['mac_address'].lower():
                    clamp['total_power'] = data['total_power']
                    break
            cache.set('power_clamp_data', cached_data, timeout=300)
            print("PowerClamp and cache updated successfully")
        except PowerClamp.DoesNotExist:
            print(f"No PowerClamp found for MAC address: {data['mac_address']}")

    
    async def shelly_message(self, event):
        message = event['message']
        message['timestamp'] = datetime.strptime(message['time'], "%H:%M").strftime("%H:%M:%S")
        print(f"Sending Shelly message to client: {message}")
        await self.send(text_data=json.dumps({
            'type': 'shelly_data',
            'data': message
        }))