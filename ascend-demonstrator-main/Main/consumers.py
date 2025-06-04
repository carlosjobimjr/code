import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from Main.views import SubProcessHandler
import asyncio
from opcua import ua, Client
from asyncua import ua, Client
from django.core.cache import cache
from channels.layers import get_channel_layer
from EnergyCapture.models import PowerClamp
from datetime import datetime

import websockets
import asyncio

import logging


import traceback

import aiohttp



import asyncio
import aiohttp
import json
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import SensorDataStorage



class OPCUAClient:
    def __init__(self):
        self.url = "opc.tcp://10.10.42.11:4840"
        self.nodes = {
            'motorLoadMean_M3': 'ns=3;s="MaterialCarrierMotors_DB"."motorLoadMean_M3"',
            'ActualTorque1': 'ns=3;s="MaterialCarrierMotors_DB"."ActualTorque1"',
            'ActualTorque2': 'ns=3;s="MaterialCarrierMotors_DB"."ActualTorque2"'
        }
        self.client = None
        
    async def connect(self):
        self.client = Client(self.url)
        self.client.application_uri = "urn:SIMATIC.S7-1500.OPC-UA.Application:PressPLC"
        self.client.name = "UaExpert Client"
        await self.client.connect()
        print("Connected to OPC UA server")

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("Disconnected from OPC UA server")
            
    async def read_nodes(self):
        values = {}
        for name, node_id in self.nodes.items():
            node = self.client.get_node(node_id)
            value = await node.read_value()
            values[name] = value
        return values

class SensorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sensor_id = self.scope['url_route']['kwargs']['id']
        print(f"WebSocket connection established for sensor ID: {self.sensor_id}")
        await self.accept()

        # Start the background tasks
        print("Starting background tasks...")
        self.sensor_task = asyncio.create_task(self.fetch_sensor_data())
        self.opcua_task = asyncio.create_task(self.fetch_opcua_data())
        
    async def disconnect(self, close_code):
        print(f"WebSocket connection closed for sensor ID: {self.sensor_id} with close code: {close_code}")
        
        # Cancel sensor task
        if hasattr(self, 'sensor_task'):
            print("Cancelling sensor data fetch task...")
            self.sensor_task.cancel()
            try:
                await self.sensor_task
            except asyncio.CancelledError:
                print("Sensor data fetch task cancelled successfully.")
                
        # Cancel OPCUA task
        if hasattr(self, 'opcua_task'):
            print("Cancelling OPCUA data fetch task...")
            self.opcua_task.cancel()
            try:
                await self.opcua_task
            except asyncio.CancelledError:
                print("OPCUA data fetch task cancelled successfully.")

    @sync_to_async
    def save_to_database(self, data_type, data):
        """
        Save sensor or motor data to database
        
        Args:
            data_type (str): Type of data ('sensor' or 'motor')
            data (dict): Data to be saved
        """
        try:
            record = SensorDataStorage()
            
            if data_type == 'sensor':
                # Save noise data
                if 'noise' in data:
                    record.noise_level = data['noise']['value']
                
                # Save air quality data
                if 'air_quality' in data:
                    for sensor_data in data['air_quality'].values():
                        values = sensor_data['values']
                        record.pm1_concentration = values.get('Mass concentration of particles < 1.0 μm (μg/m³)')
                        record.pm25_concentration = values.get('Mass concentration of particles < 2.5 μm (μg/m³)')
                        record.pm10_concentration = values.get('Mass concentration of particles < 10 μm (μg/m³)')
                        break  # Use first sensor's data
                
                # Save vibration data
                if 'vibration' in data:
                    for sensor_data in data['vibration'].values():
                        values = sensor_data['values']
                        record.acceleration_x = values.get('Acceleration in X axis (m/sec²)')
                        record.acceleration_y = values.get('Acceleration in Y axis (m/sec²)')
                        record.acceleration_z = values.get('Acceleration in Z axis (m/sec²)')
                        record.angular_velocity_x = values.get('Angular velocity in X axis (deg/sec)')
                        record.angular_velocity_y = values.get('Angular velocity in Y axis (deg/sec)')
                        record.angular_velocity_z = values.get('Angular velocity in Z axis (deg/sec)')
                        record.roll_angle = values.get('Roll angle in degrees')
                        record.pitch_angle = values.get('Pitch angle in degrees')
                        record.yaw_angle = values.get('Yaw angle in degrees')
                        break  # Use first sensor's data
                
                # Save VOC data
                if 'voc' in data:
                    for sensor_data in data['voc'].values():
                        values = sensor_data['values']
                        record.temperature = values.get('Temperature Value in °C')
                        record.humidity = values.get('Humidity Value in rH')
                        record.voc_index = values.get('VOC Value in Air Quality Index')
                        break  # Use first sensor's data
                
                # Save weighing scale data
                if 'weighing_scale' in data:
                    record.weight = data['weighing_scale']['value']
                    
            elif data_type == 'motor':
                record.motor_load_mean = data.get('motorLoadMean_M3')
                record.actual_torque_percentage = data.get('ActuaTorquePercentage')
                record.actual_torque_percentage2 = data.get('ActualTorquePercentage2')
            
            record.save()
            print(f"Successfully saved {data_type} data to database")
            
        except Exception as e:
            print(f"Error saving {data_type} data to database: {e}")

    async def fetch_opcua_data(self):
        opcua_client = OPCUAClient()
        print("Starting OPCUA data fetching...")
        
        while True:
            try:
                await opcua_client.connect()
                print("Connected to OPCUA server")
                
                while True:
                    try:
                        motor_data = await opcua_client.read_nodes()
                        
                        # Save motor data to database
                        await self.save_to_database('motor', motor_data)
                        
                        # Send to WebSocket client
                        await self.send(json.dumps({
                            'type': 'motor_data',
                            'data': {
                                'motor_loads': motor_data,
                                'sensor_id': self.sensor_id
                            }
                        }))
                        print(f"Sent motor data: {motor_data}")
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"Error reading OPCUA nodes: {e}")
                        break
                        
            except Exception as e:
                print(f"OPCUA connection error: {e}")
                await asyncio.sleep(1)
                
            finally:
                await opcua_client.disconnect()

    def process_sensor_data(self, sensor_data):
        combined_data = {}
        
        # Noise Sensor Data
        if 'Noise Sensor 1' in sensor_data:
            combined_data['noise'] = {
                'timestamp': sensor_data['Noise Sensor 1']['timestamp'],
                'value': sensor_data['Noise Sensor 1']['Noise Sensor Values']['Noise measurement value in dB']
            }
        
        # Humidity Sensor Data
        if 'VOC Sensor 1' in sensor_data:
            combined_data['humidity'] = {
                'timestamp': sensor_data['VOC Sensor 1']['timestamp'],
                'value': sensor_data['VOC Sensor 1']['VOC Sensor Values']['Humidity Value in rH']
            }
        
        # Air Quality Sensors
        air_quality_data = {}
        for key in ['Air Quality Sensor 1', 'Air Quality Sensor 2', 'Air Quality Sensor 3']:
            if key in sensor_data:
                air_quality_data[key] = {
                    'timestamp': sensor_data[key]['timestamp'],
                    'sensor_name': sensor_data[key]['Sensor name'],
                    'values': sensor_data[key]['Air Quality Sensor Values']
                }
        if air_quality_data:
            combined_data['air_quality'] = air_quality_data
        
        # Vibration Sensors
        vibration_data = {}
        for key in ['Vibration Sensor 1', 'Vibration Sensor 2']:
            if key in sensor_data:
                vibration_data[key] = {
                    'timestamp': sensor_data[key]['timestamp'],
                    'sensor_name': sensor_data[key]['Sensor name'],
                    'values': sensor_data[key]['Vibration Sensor Values']
                }
        if vibration_data:
            combined_data['vibration'] = vibration_data
        
        # VOC Sensors
        voc_data = {}
        for key in ['VOC Sensor 1', 'VOC Sensor 2']:
            if key in sensor_data:
                voc_data[key] = {
                    'timestamp': sensor_data[key]['timestamp'],
                    'sensor_name': sensor_data[key]['Sensor name'],
                    'values': sensor_data[key]['VOC Sensor Values']
                }
        if voc_data:
            combined_data['voc'] = voc_data
        
        # Weighing Scale
        if 'Weighing Scale 1' in sensor_data:
            combined_data['weighing_scale'] = {
                'timestamp': sensor_data['Weighing Scale 1']['timestamp'],
                'sensor_name': sensor_data['Weighing Scale 1']['Sensor name'],
                'value': sensor_data['Weighing Scale 1']['Weighing Scale Values']['Weight in kg']
            }
            
        return combined_data

    async def fetch_sensor_data(self):
        rosbridge_url = "ws://10.10.42.126:9090"
        print(f"Connecting to ROSBridge at {rosbridge_url}")
        
        while True:
            try:
                async with websockets.connect(rosbridge_url) as websocket:
                    print("Connected to ROSBridge WebSocket.")
                    subscribe_msg = {
                        "op": "subscribe",
                        "topic": "/sensor_data",
                        "type": "std_msgs/String"
                    }
                    print(f"Subscribing to ROS topic: {subscribe_msg}")
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    while True:
                        message = await websocket.recv()
                        print(f"Received message from ROSBridge: {message}")
                        data = json.loads(message)
                        
                        if 'msg' in data:
                            sensor_data = json.loads(data['msg']['data'])
                            print("Parsed full sensor data:", sensor_data)
                            combined_data = self.process_sensor_data(sensor_data)
                            
                            # Save sensor data to database
                            await self.save_to_database('sensor', combined_data)
                            
                            # Send combined data to WebSocket client
                            await self.send(json.dumps({
                                'type': 'sensor_data',
                                'data': combined_data,
                                'sensor_id': self.sensor_id
                            }))
                            print("Sent combined sensor data to WebSocket client")
                            
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection to ROSBridge closed. Reconnecting...")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error in fetch_sensor_data: {e}")
                await asyncio.sleep(1)
        
class ShellyDataConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwd2QiLCJpYXQiOjE3MzY1MDc0MjAsInVzZXJfaWQiOiIxMTUzMTUyIiwic24iOiIxIiwidXNlcl9hcGlfdXJsIjoiaHR0cHM6XC9cL3NoZWxseS00My1ldS5zaGVsbHkuY2xvdWQiLCJuIjo2NjIxLCJmcm9tIjoic2hlbGx5LWRpeSIsImV4cCI6MTczNjU1MDYyMH0.l_6Gl__DF-qdT-oDSCFekBxhkKfJ81aRKDURFZGkv34"
        self.base_url = "https://shelly-43-eu.shelly.cloud"
        self.headers = {
            'Authorization': f"Bearer {self.token}",
            'Content-Type': 'application/json'
        }
        self.should_fetch = True
        self.device_mapping = {
            "3494546ecb06": "Big Cabinet",
            "3494546ed0bd": "KUKA Cabinet",
            "c8c9a37057ca": "CNC Router",
            "c45bbe7888f4": "Big Oven"
        }

    def watts_to_kwh(self, watts):
        """Convert Watts to kWh with min/max handling"""
        if watts == 0:
            return 0
        
        kw = watts / 1000
        return min(max(kw/10, 0.01), 0.1) if kw > 0 else 0

    async def connect(self):
        await self.accept()
        asyncio.create_task(self.monitor_devices())

    async def disconnect(self, close_code):
        self.should_fetch = False

    async def get_devices(self, session):
        """Fetch all device statuses from Shelly Cloud"""
        url = f"{self.base_url}/device/all_status"
        try:
            async with session.get(url, headers=self.headers, ssl=True) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {}).get('devices_status', {})
                else:
                    print(f"Error status: {response.status}")
                    return {}
        except Exception as e:
            print(f"Error fetching devices: {e}")
            return {}

    @sync_to_async
    def save_sensor_data(self, device_powers, total_power, average_power):
        """
        Save sensor data to database synchronously
        
        Args:
            device_powers (dict): Power consumption for each device
            total_power (float): Total power consumption
            average_power (float): Average power consumption
        """
        try:
            SensorDataStorage.objects.create(
                big_cabinet_power=device_powers.get('Big Cabinet', 0),
                kuka_cabinet_power=device_powers.get('KUKA Cabinet', 0),
                cnc_router_power=device_powers.get('CNC Router', 0),
                big_oven_power=device_powers.get('Big Oven', 0),
                total_power=total_power,
                average_power=average_power
            )
            print("Sensor data saved successfully")
        except Exception as e:
            print(f"Error saving sensor data: {e}")

    async def monitor_devices(self):
        """Monitor and process device power consumption"""
        async with aiohttp.ClientSession() as session:
            while self.should_fetch:
                try:
                    # Fetch device statuses
                    devices = await self.get_devices(session)
                    
                    if devices:
                        # Prepare data structures
                        device_data = []
                        total_power = 0
                        active_devices = 0
                        device_powers = {}

                        # Process each device
                        for mac, status in devices.items():
                            if mac.lower() in [m.lower() for m in self.device_mapping.keys()]:
                                # Calculate power consumption
                                power = status.get('total_power', 0)
                                kwh = self.watts_to_kwh(power)
                                
                                # Track active devices and total power
                                if power > 0:
                                    total_power += kwh
                                    active_devices += 1
                                
                                # Store device data
                                device_name = self.device_mapping[mac.lower()]
                                device_data.append({
                                    'name': device_name,
                                    'power': kwh,
                                    'mac': mac.lower()
                                })
                                
                                # Store power for database mapping
                                device_powers[device_name] = kwh
                                
                                # Print device power for logging
                                print(f"Device {mac}: {kwh:.3f} kWh")

                        # Calculate average for active devices
                        average_power = total_power / active_devices if active_devices > 0 else 0

                        # Prepare message
                        message = {
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'devices': device_data,
                            'average': {
                                'name': 'Average',
                                'power': average_power
                            },
                            'total': {
                                'name': 'Total',
                                'power': total_power
                            }
                        }

                        # Save to database
                        await self.save_sensor_data(device_powers, total_power, average_power)

                        # Send data via WebSocket
                        print("Sending data:", json.dumps(message, indent=2))
                        await self.send(text_data=json.dumps({
                            'type': 'energy_data',
                            'data': message
                        }))

                    # Wait before next iteration
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"Error in monitor_devices: {e}")
                    await asyncio.sleep(1)



class SubProcessConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"SubProcess_{self.room_name}"
        
        # Join room group
        try:
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            raise e
        
        try:
            await self.accept()

            # Send initial connection confirmation
            await self.send(text_data=json.dumps({
                "type": "connection_status",
                "status": "connected",
                "room": self.room_group_name
            }))
        except Exception as e:
            raise e

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            pass

    async def receive(self, text_data):
        try:
            message = text_data
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message',
                    'message': message
                }
            )
        except Exception as e:
            pass

    async def update_message(self, event):
        try:
            message = event.get('message', {})
            
            # Send the entire message structure to the client
            await self.send(text_data=json.dumps({
                'type': 'update_message',
                'message': message
            }))
        except Exception as e:
            pass

    async def chat_message(self, event):
        try:
            message = event['message']
            
            await self.send(text_data=json.dumps({
                'message': message
            }))
        except Exception as e:
            pass


from Main.models import SubProcess
class OPCUAConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.client_lock = asyncio.Lock()
        self.running = True
        self.monitoring_tasks = []
        self.reconnect_delay = 5  # Initial reconnect delay in seconds
        self.max_reconnect_delay = 30  # Maximum reconnect delay
        self.session_timeout = 10000  # Session timeout in milliseconds
        self.connection_retries = 0
        self.max_retries = 3
        
        # Set up logging for this instance
        self.logger = logging.getLogger('OPCUAConsumer')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        self.power_monitoring = {}

    async def connect(self):
        """Handle WebSocket connection"""
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"OPCUA_{self.room_name}"

        try:
            # First add to channel layer and accept connection
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Initialize OPC UA connection
            await self.initialize_opcua_connection()

        except Exception as e:
            self.logger.error(f"Error during connection: {str(e)}")
            await self.close()

    async def initialize_opcua_connection(self):
        """Initialize OPC UA connection with retry logic"""
        while self.running and self.connection_retries < self.max_retries:
            try:
                self.logger.info("Starting OPCUA connection...")
                
                # Create client with explicit configuration
                self.client = Client("opc.tcp://10.10.42.11:4840")
                self.client.application_uri = "urn:client:pressure:machine"
                
                # Configure session parameters
                self.client.session_timeout = self.session_timeout
                self.client.secure_channel_timeout = self.session_timeout
                
                # Connect with session parameters
                await self.client.connect()
                self.logger.info("Successfully connected to OPCUA server")
                
                # Reset connection attempts on successful connection
                self.connection_retries = 0
                self.reconnect_delay = 5
                
                # Start monitoring tasks with pressure monitoring added
                self.monitoring_tasks = [
                    asyncio.create_task(self.monitor_switch_states()),
                    asyncio.create_task(self.start_data_collection()),
                    asyncio.create_task(self.monitor_temperature_parameters()),
                    asyncio.create_task(self.monitor_blank_loading()),
                    asyncio.create_task(self.monitor_mould_cooling()),
                    asyncio.create_task(self.monitor_high_temperature()),
                    asyncio.create_task(self.monitor_motor_status()),
                    asyncio.create_task(self.monitor_power_consumption()),
                    asyncio.create_task(self.monitor_pressure()),  
                ]
                
                return True

            except ua.uaerrors.BadTooManySessions:
                self.logger.warning("Too many sessions, attempting cleanup...")
                await self.cleanup_connection()
                self.connection_retries += 1
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                
            except Exception as e:
                self.logger.error(f"Connection error: {str(e)}")
                self.connection_retries += 1
                await asyncio.sleep(self.reconnect_delay)
                
        if self.connection_retries >= self.max_retries:
            self.logger.error("Max connection retries reached")
            await self.close()
            return False

    async def cleanup_connection(self):
        """Clean up OPC UA connection"""
        if self.client:
            try:
                if hasattr(self.client, 'session') and self.client.session:
                    await self.client.close_session()
                if hasattr(self.client, 'security_policy'):
                    await self.client.close_secure_channel()
                await self.client.disconnect()
            except Exception as e:
                self.logger.error(f"Error during cleanup: {str(e)}")
            finally:
                self.client = None

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        self.running = False
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error cancelling task: {str(e)}")

        # Clean up OPC UA connection
        await self.cleanup_connection()

        # Remove from channel layer
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except Exception as e:
            self.logger.error(f"Error removing from channel layer: {str(e)}")

    async def receive(self, text_data):
        try:
            message = json.loads(text_data)
            message_type = message.get('type', '')

            if message_type == 'request_data':
                await self.handle_data_request(message)
            elif message_type == 'control_command':
                await self.handle_control_command(message)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Unknown message type'
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

        
    async def monitor_power_consumption(self):
        """Monitor power consumption for specific subprocesses"""
        while self.running:
            try:
                # Get all active subprocesses of the specified types
                monitored_subprocesses = await sync_to_async(lambda: list(SubProcess.objects.filter(
                    name__in=['Initialisation', 'Blank Inside Press', 'Machine Returns To Home Location'],
                    status__in=[1, 2]  # Monitor both active and just completed
                )))()
                print(f"Found {len(monitored_subprocesses)} subprocesses to monitor")

                # Read current values from OPC UA
                current1_node = self.client.get_node('ns=3;s="MaterialCarrierMotors_DB"."Current1"')
                current2_node = self.client.get_node('ns=3;s="MaterialCarrierMotors_DB"."Current2"')
                
                current1 = await current1_node.read_value()
                current2 = await current2_node.read_value()
                
                # Print raw values
                print(f"Raw Readings - Current1: {current1}A, Current2: {current2}A")
                total_current = current1 + current2
                print(f"Total Current: {total_current}A")
                
                # Calculate power
                power_watts = total_current * 400
                power_kwh = power_watts / (1000 * 3600)  # Convert to kWh for this second
                print(f"Calculated Power: {power_watts}W = {power_kwh}kWh")

                # Process each subprocess
                for subprocess in monitored_subprocesses:
                    subprocess_id = str(subprocess.id)
                    
                    # Initialize monitoring for new active subprocesses
                    if subprocess.status == 1 and subprocess_id not in self.power_monitoring:
                        print(f"Starting power monitoring for {subprocess.name} (ID: {subprocess_id})")
                        self.power_monitoring[subprocess_id] = {
                            'power_sum': 0,
                            'samples': 0,
                            'name': subprocess.name
                        }
                        
                    # Accumulate power for active subprocesses
                    if subprocess.status == 1 and subprocess_id in self.power_monitoring:
                        self.power_monitoring[subprocess_id]['power_sum'] += power_kwh
                        self.power_monitoring[subprocess_id]['samples'] += 1
                        accumulated = self.power_monitoring[subprocess_id]['power_sum']
                        print(f"{subprocess.name} - Accumulated Power: {accumulated}kWh")
                        
                    # Save and cleanup completed subprocesses
                    if subprocess.status == 2 and subprocess_id in self.power_monitoring:
                        total_power = self.power_monitoring[subprocess_id]['power_sum']
                        print(f"Saving final power data for {subprocess.name}: {total_power}kWh")
                        
                        # Save to database
                        await sync_to_async(lambda: setattr(subprocess, 'power', total_power))()
                        await sync_to_async(subprocess.save)()
                        print(f"Successfully saved power {total_power} kWh to subprocess {subprocess.name}")
                        
                        # Cleanup
                        del self.power_monitoring[subprocess_id]
                        print(f"Completed power monitoring for {subprocess.name}")

                # Send current monitoring state via WebSocket
                await self.send(text_data=json.dumps({
                    'type': 'power_update',
                    'data': {
                        'current_reading': {
                            'current1': current1,
                            'current2': current2,
                            'total_current': total_current,
                            'power_watts': power_watts,
                            'power_kwh': power_kwh
                        },
                        'monitored_processes': {
                            subprocess_id: {
                                'name': data['name'],
                                'accumulated_power': data['power_sum'],
                                'samples': data['samples']
                            }
                            for subprocess_id, data in self.power_monitoring.items()
                        }
                    }
                }))
                
            except Exception as e:
                print(f"Error monitoring power consumption: {e}")
                
            await asyncio.sleep(1)  

    async def update_subprocess_power(self, process_name, subprocess, power_kwh):
        """Update power monitoring for a specific subprocess"""
        if subprocess:
            status = await sync_to_async(lambda: subprocess.status)()
            process_time = await sync_to_async(lambda: subprocess.processTime)()
            interface_time = await sync_to_async(lambda: subprocess.interfaceTime)()
            
            # Check if monitoring should be active
            should_monitor = (status == 1 and (process_time is not None or interface_time is not None))
            
            if should_monitor and not self.power_monitoring[process_name]['active']:
                # Start monitoring
                self.power_monitoring[process_name]['active'] = True
                self.power_monitoring[process_name]['power_sum'] = 0
                self.power_monitoring[process_name]['samples'] = 0
            
            elif not should_monitor and self.power_monitoring[process_name]['active']:
                # Stop monitoring and save final value
                self.power_monitoring[process_name]['active'] = False
                if self.power_monitoring[process_name]['samples'] > 0:
                    total_power = self.power_monitoring[process_name]['power_sum']
                    
                    # Update subprocess power data
                    subprocess.power = total_power  # Changed from powerData to power
                    await sync_to_async(subprocess.save)()
                    
                    print(f"Saved power data for {process_name}: {total_power} kWh to subprocess.power field")
            
            elif should_monitor:
                # Continue monitoring
                self.power_monitoring[process_name]['power_sum'] += power_kwh
                self.power_monitoring[process_name]['samples'] += 1
                print(f"{process_name} - Current kWh: {power_kwh}, Total accumulated kWh: {self.power_monitoring[process_name]['power_sum']}")

    async def monitor_mould_cooling(self):
        """Monitor cooling parameters and fan states"""
        while self.running:
            try:
                # Read fan states
                fan1_node = self.client.get_node('ns=3;s="Q_xPressAuto_Fan1"')
                fan2_node = self.client.get_node('ns=3;s="Q_xPressAuto_Fan2"')
                
                fan1_state = await fan1_node.read_value()
                fan2_state = await fan2_node.read_value()
                fans_active = fan1_state and fan2_state
                
                try:
                    # Read centre and side temperatures
                    temp_centre_node = self.client.get_node('ns=3;s="07_PART_RELEASE_DB"."setTempCentre"[0]')
                    temp_side_node = self.client.get_node('ns=3;s="07_PART_RELEASE_DB"."setTempSide"[0]')
                    
                    current_temp_centre = await temp_centre_node.read_value()
                    current_temp_side = await temp_side_node.read_value()
                    
                    # Get slave temperatures
                    slave_temps = await self.fetch_temperature_data(self.client)
                    
                    # Process temperatures
                    if current_temp_centre is not None:
                        current_temp_centre = min(max(int(current_temp_centre), 0), 65535)
                        
                    if current_temp_side is not None:
                        current_temp_side = min(max(int(current_temp_side), 0), 65535)
                    
                    await self.send(text_data=json.dumps({
                        'type': 'mould_cooling_update',
                        'data': {
                            'fans_active': fans_active,
                            'fan1_state': fan1_state,
                            'fan2_state': fan2_state,
                            'current_temp_centre': current_temp_centre,
                            'temp_centre': current_temp_centre,
                            'current_temp_side': current_temp_side,
                            'temp_side': current_temp_side,
                            'temperatureData': slave_temps  
                        }
                    }))
                    
                except Exception as e:
                    print(f"Error reading temperatures: {e}")
                    await self.send(text_data=json.dumps({
                        'type': 'mould_cooling_update',
                        'data': {
                            'fans_active': fans_active,
                            'fan1_state': fan1_state,
                            'fan2_state': fan2_state
                        }
                    }))
            
            except Exception as e:
                print(f"Error monitoring mould cooling: {e}")
            
            await asyncio.sleep(1)

    async def monitor_blank_loading(self):
        while self.running:
            try:
                blank_loading_node = self.client.get_node('ns=3;s="BlankInPbOut"')
                blank_loading_state = await blank_loading_node.read_value()
                
                state_value = bool(blank_loading_state)
                
                await self.send(text_data=json.dumps({
                    'type': 'blank_loading_update',
                    'state': state_value
                }))

            except Exception as e:
                print(f"Error monitoring blank loading: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
            await asyncio.sleep(0.1)

    async def monitor_motor_status(self):
        """Monitor motor error status"""
        while self.running:
            try:
                # Use exact node names from PLC
                motor1_node = self.client.get_node('ns=3;s="MaterialCarrierMotors_DB"."Motor1ErrorStatus"')
                motor3_node = self.client.get_node('ns=3;s="MaterialCarrierMotors_DB"."Motor3ErrorStatus"')
                
                # Read values
                motor1_error = await motor1_node.read_value()
                motor3_error = await motor3_node.read_value()
                
                print(f"[OPCUA] Motor Status - M1: {motor1_error} (type: {type(motor1_error)}), M3: {motor3_error} (type: {type(motor3_error)})")
                
                # Send motor data
                message = {
                    'type': 'motor_data',
                    'data': {
                        'motor_loads': {
                            'Motor1ErrorStatus': bool(motor1_error),
                            'Motor3ErrorStatus': bool(motor3_error)
                        }
                    }
                }
                
                print(f"[OPCUA] Sending message: {message}")
                await self.send(text_data=json.dumps(message))
                
            except Exception as e:
                print(f"[OPCUA] Error in monitor_motor_status: {str(e)}")
                import traceback
                traceback.print_exc()
                
            await asyncio.sleep(1)



    async def monitor_temperature_parameters(self):
        """Monitor temperature parameters including the high value temperature setting"""
        while self.running:
            try:
                # Get temperature setting nodes
                temp_centre_node = self.client.get_node('ns=3;s="07_PART_RELEASE_DB"."SET_TEMP_CENTRE"[0]')
                temp_side_node = self.client.get_node('ns=3;s="07_PART_RELEASE_DB"."SET_TEMP_SIDE"[0]')
                temp_high_node = self.client.get_node('ns=3;s="01_TOOL_HEAT_CALL_DB"."UAMethod_InParameters"."TEMP_HIGH_VALUE"[0]')
                
                # Read current set values
                current_centre_temp = await temp_centre_node.read_value()
                current_side_temp = await temp_side_node.read_value()
                current_high_temp = await temp_high_node.read_value()
                
                # Get temperature readings for monitoring
                temp_data = await self.fetch_temperature_data(self.client)
                
                # Get user-set temperatures from handler
                handler = SubProcessHandler()
                try:
                    tool_heat_params = handler.tool_heat_params
                    target_temp1 = tool_heat_params.get('temp1', 0)
                    mould_cooling_params = handler.handlers['Mould Cooling'][1]
                    target_centre_temp = mould_cooling_params.get('temp_centre', 0)
                    target_side_temp = mould_cooling_params.get('temp_side', 0)
                except:
                    # If no parameters set yet, use defaults
                    target_temp1 = 0
                    target_centre_temp = 0
                    target_side_temp = 0
                
                # Convert all values to integers for comparison
                current_centre_temp = int(current_centre_temp if current_centre_temp is not None else 0)
                current_side_temp = int(current_side_temp if current_side_temp is not None else 0)
                current_high_temp = int(current_high_temp if current_high_temp is not None else 0)
                target_centre_temp = int(target_centre_temp)
                target_side_temp = int(target_side_temp)
                target_temp1 = int(target_temp1)
                
                # Check if temperatures match their targets
                is_matching_centre = current_centre_temp == target_centre_temp
                is_matching_side = current_side_temp == target_side_temp
                is_matching_temp1 = current_high_temp == target_temp1
                
                print(f"High Temperature - Current: {current_high_temp}, Target: {target_temp1}, Match: {is_matching_temp1}")
                print(f"Centre Temperature - Current: {current_centre_temp}, Target: {target_centre_temp}, Match: {is_matching_centre}")
                print(f"Side Temperature - Current: {current_side_temp}, Target: {target_side_temp}, Match: {is_matching_side}")
                
                # Send update
                await self.send(text_data=json.dumps({
                    'type': 'temperature_parameter_update',
                    'temperature_data': {
                        'current_centre_temp': current_centre_temp,
                        'current_side_temp': current_side_temp,
                        'current_high_temp': current_high_temp,
                        'target_temp1': target_temp1,
                        'target_centre_temp': target_centre_temp,
                        'target_side_temp': target_side_temp,
                        'is_matching_centre': is_matching_centre,
                        'is_matching_side': is_matching_side,
                        'is_matching_temp1': is_matching_temp1
                    }
                }))
                
            except Exception as e:
                print(f"Error in monitor_temperature_parameters: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
                
            await asyncio.sleep(1)

    async def monitor_switch_states(self):
        last_et = None
        while self.running:
            try:
                platten_down_node = self.client.get_node('ns=3;s="I_xPistonControl_DownSensorSwitch"')
                shuttle_node = self.client.get_node('ns=3;s="MaterialCarrier_DB"."mcHome"')
                shuttle_press_node = self.client.get_node('ns=3;s="MaterialCarrier_DB"."mcPress"')
                platten_up_node = self.client.get_node('ns=3;s="I_xPistonControl_UpSensorSwitch"')
                timer_node = self.client.get_node('ns=3;s="05_BLANK_PRESSED_DB"."PROCESS_TIMER_ET"')
                timer_set_node = self.client.get_node('ns=3;s="05_BLANK_PRESSED_DB"."PROCESS_TIME"')
                
                platten_down_value = await platten_down_node.read_value()
                shuttle_home_value = await shuttle_node.read_value()
                shuttle_press_value = await shuttle_press_node.read_value()
                platten_up_value = await platten_up_node.read_value()
                timer_et = await timer_node.read_value()
                timer_total = await timer_set_node.read_value()

                print(f"Timer ET: {timer_et}, Timer Total: {timer_total}")

                # Detect if timer has actually started (ET changed from None or 0)
                timer_started = last_et is not None and last_et == 0 and timer_et > 0
                timer_active = timer_et is not None and timer_et > 0
                # Timer completed when ET returns to 0 after having been active
                timer_completed = last_et is not None and last_et > 0 and timer_et == 0

                last_et = timer_et

                print(f"Timer Started: {timer_started}, Timer Active: {timer_active}, Timer Completed: {timer_completed}")

                switch_status = {
                    'platten_down': bool(platten_down_value),
                    'shuttle_home': bool(shuttle_home_value),
                    'platten_up': bool(platten_up_value),
                    'shuttle_press': bool(shuttle_press_value),
                    'timer_et': timer_et,
                    'timer_total': timer_total,
                    'timer_active': timer_active,
                    'timer_completed': timer_completed,
                    'timer_started': timer_started
                }

                print(f"Switch Status: {switch_status}")

                await self.send(text_data=json.dumps({
                    'type': 'switch_status_update',
                    'status': switch_status
                }))

            except Exception as e:
                print(f"Error monitoring switch states: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
            await asyncio.sleep(0.1)  # Poll every 100ms for smooth countdown


    async def monitor_high_temperature(self):
        """Monitor and set TEMP_HIGH_VALUE[0] as UInt16 and compare with temp1"""
        while self.running:
            try:
                # Get the handler's temp1 value
                handler = SubProcessHandler()
                target_temp1 = handler.tool_heat_params.get('temp1', 0)
                
                # Convert temp1 to UInt16 range
                target_temp1 = min(max(int(target_temp1), 0), 65535)
                
                # Get node and set temp1 value
                high_temp_node = self.client.get_node('ns=3;s="01_TOOL_HEAT_CALL_DB"."UAMethod_InParameters"."TEMP_HIGH_VALUE"[0]')
                
                # Write temp1 to TEMP_HIGH_VALUE[0] as UInt16
                dv = ua.DataValue(ua.Variant(target_temp1, ua.VariantType.UInt16))
                await high_temp_node.set_value(dv)
                
                # Read back the current value
                current_high_temp = await high_temp_node.read_value()
                current_high_temp = int(current_high_temp if current_high_temp is not None else 0)
                
                # Check if they match
                is_matching = current_high_temp == target_temp1
                
                print(f"High Temperature Monitor - Current: {current_high_temp} (UInt16), Target: {target_temp1} (UInt16), Match: {is_matching}")
                
                # Send update to frontend
                await self.send(text_data=json.dumps({
                    'type': 'high_temperature_update',
                    'data': {
                        'current_temp': current_high_temp,
                        'target_temp': target_temp1,
                        'is_matching': is_matching
                    }
                }))
                
            except Exception as e:
                print(f"Error monitoring high temperature: {e}")
            
            await asyncio.sleep(1)  

    async def start_data_collection(self):
        while self.running:
            try:
                temperature_data = await self.fetch_temperature_data(self.client)

                if temperature_data is not None:
                    # Get high temperature comparison for temperature bounds check
                    high_temp_node = self.client.get_node('ns=3;s="01_TOOL_HEAT_CALL_DB"."UAMethod_InParameters"."TEMP_HIGH_VALUE"[0]')
                    current_high_temp = await high_temp_node.read_value()
                    handler = SubProcessHandler()
                    target_temp1 = handler.tool_heat_params.get('temp1', 0)

                    await self.send(text_data=json.dumps({
                        'type': 'temperature_update',
                        'temperatureData': temperature_data,
                        'bounds': {
                            'upper': target_temp1,
                            'lower': max(0, target_temp1 - 10)
                        }
                    }))

            except Exception as e:
                print(f"Error during data collection: {e}")

            await asyncio.sleep(1)

    async def fetch_temperature_data(self, client):
        try:
            # Only fetch values for thermocouples 1-3
            node_strings = [
                f'ns=3;s="00MBCollection_DB".slave{i}'
                for i in range(1, 4)  # Changed range from (1, 7) to (1, 4)
            ]
            
            nodes = [client.get_node(node_string) for node_string in node_strings]
            values = await client.read_values(nodes)
            
            # Map thermocouple values:
            # T1 -> T4
            # T2 -> T5
            # T3 -> T6
            result = {
                f"slave{i+1}": value
                for i, value in enumerate(values)
            }
            
            # Duplicate values for thermocouples 4-6
            result['slave4'] = result['slave1']  # T4 gets T1's value
            result['slave5'] = result['slave2']  # T5 gets T2's value
            result['slave6'] = result['slave3']  # T6 gets T3's value
            
            print("Temperature Slave Values:", result)
            return result
                
        except Exception as e:
            print(f"Error fetching temperature data: {e}")
            return None

    async def fetch_pressure_data(self, client):
        try:
            node = client.get_node('ns=3;s="Sensors_DB"."p1"')
            print("Pressure value:", node)
            return await node.get_value()
        except Exception as e:
            print(f"Error in fetch_pressure_data: {e}")
            return None
    async def monitor_pressure(self):
        """Monitor pressure data and send constant 6.1 bar value"""
        while self.running:
            try:
                # Send constant pressure value of 6.1 bar
                await self.send(text_data=json.dumps({
                    'type': 'pressure_update',
                    'data': {
                        'pressure': 6.1,
                        'timestamp': datetime.now().isoformat()
                    }
                }))
                
            except Exception as e:
                print(f"Error monitoring pressure: {e}")
                
            await asyncio.sleep(0.1)
    async def handle_data_request(self, message):
        data_type = message.get('data_type')
        if data_type == 'temperature':
            data = await self.fetch_temperature_data(self.client)
            await self.send(text_data=json.dumps({
                'type': 'temperature_data',
                'data': data
            }))
        elif data_type == 'pressure':
            data = await self.fetch_pressure_data(self.client)
            await self.send(text_data=json.dumps({
                'type': 'pressure_data',
                'data': data
            }))

    async def set_timer(self, timer_value: int) -> bool:
        try:
            async with Client("opc.tcp://10.10.42.11:4840") as client:
                timer_node = client.get_node('ns=3;s="05_BLANK_PRESSED_DB"."PROCESS_TIME"')
                timer_et_node = client.get_node('ns=3;s="05_BLANK_PRESSED_DB"."PROCESS_TIMER_ET"')
                
                # Set PROCESS_TIME value
                dv = ua.DataValue(ua.Variant(timer_value, ua.VariantType.Int32))
                print(f"Setting PROCESS_TIME to {timer_value}ms")
                await timer_node.set_value(dv)
                
                # Reset ET timer
                et_dv = ua.DataValue(ua.Variant(0, ua.VariantType.Int32))
                await timer_et_node.set_value(et_dv)
                
                # Verify the value was set correctly
                set_time_value = await timer_node.read_value()
                return set_time_value == timer_value
                
        except ua.uaerrors.UaError as e:
            print(f"❌ Timer error: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return False


    async def handle_control_command(self, message):
        """Handle various control commands from the WebSocket"""
        command = message.get('command')
        
        if command == 'set_centre_temp':
            try:
                temp_centre = int(message.get('temp_centre', 0))
                
                # Validate range
                if not (0 <= temp_centre <= 65535):
                    raise ValueError("Temperature must be between 0 and 65535")
                
                # Set the value
                node = self.client.get_node('ns=3;s="07_PART_RELEASE_DB"."setTempCentre"[0]')
                dv = ua.DataValue(ua.Variant(temp_centre, ua.VariantType.UInt16))
                await node.set_value(dv)
                
                # The mould_cooling monitor will handle verification and UI updates
                
            except Exception as e:
                print(f"Error setting centre temperature: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
        elif command == 'set_side_temp':
            try:
                temp_side = int(message.get('temp_side', 0))
                
                # Validate range
                if not (0 <= temp_side <= 65535):
                    raise ValueError("Temperature must be between 0 and 65535")
                
                # Set the value
                node = self.client.get_node('ns=3;s="07_PART_RELEASE_DB"."setTempSide"[0]')
                dv = ua.DataValue(ua.Variant(temp_side, ua.VariantType.UInt16))
                await node.set_value(dv)
                
                
            except Exception as e:
                print(f"Error setting side temperature: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
                
        elif command == 'set_timer':
            try:
                timer_value = int(message.get('timer_value', 0))
                print(f"Setting timer to {timer_value}ms")
                
                if await self.set_timer(timer_value):
                    await self.send(text_data=json.dumps({
                        'type': 'timer_set',
                        'value': timer_value,
                        'status': 'success'
                    }))
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Failed to set timer value'
                    }))
                    
            except ValueError as e:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid timer value provided'
                }))
            except Exception as e:
                print(f"Error setting timer: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Error setting timer: {str(e)}'
                }))
        
        elif command == 'set_high_temp':
            try:
                temp_value = int(message.get('value', 0))
                
                # Validate range for UInt16
                if not (0 <= temp_value <= 65535):
                    raise ValueError("Temperature value must be between 0 and 65535")
                
                # Create UInt16 variant and set the value
                high_temp_node = self.client.get_node('ns=3;s="01_TOOL_HEAT_CALL_DB"."UAMethod_InParameters"."TEMP_HIGH_VALUE"[0]')
                dv = ua.DataValue(ua.Variant(temp_value, ua.VariantType.UInt16))
                await high_temp_node.set_value(dv)
                
                # Verify the write was successful
                actual_value = await high_temp_node.read_value()
                success = int(actual_value) == temp_value
                
                print(f"Set high temperature - Value: {temp_value}, Success: {success}")
                
                if success:
                    await self.send(text_data=json.dumps({
                        'type': 'high_temp_set',
                        'success': True,
                        'value': temp_value
                    }))
                else:
                    raise ValueError(f"Failed to verify temperature set. Expected: {temp_value}, Got: {actual_value}")
                    
            except ValueError as e:
                print(f"Error in set_high_temp: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
            except Exception as e:
                print(f"Error setting high temperature: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Error setting high temperature: {str(e)}'
                }))
                
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Unknown command: {command}'
            }))