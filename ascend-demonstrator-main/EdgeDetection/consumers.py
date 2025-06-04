import json
import asyncio
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class EdgeDetectionConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rosbridge_task = None
        self.rosbridge_connected = False

    async def connect(self):
        """Initialize WebSocket connection"""
        await self.channel_layer.group_add("edge_detection_group", self.channel_name)
        await self.accept()
        print("[WebSocket] Client connected")

        # Start ROSBridge connection
        self.rosbridge_task = asyncio.create_task(self.connect_to_rosbridge())

    async def connect_to_rosbridge(self):
        """Connect to ROSBridge on IPC and maintain connection"""
        rosbridge_url = "ws://10.10.42.126:9090"
        print(f"[ROSBridge] Connecting to {rosbridge_url}")
        
        while True:
            try:
                async with websockets.connect(rosbridge_url) as websocket:
                    print("[ROSBridge] Connected successfully")
                    self.rosbridge_connected = True

                    # Subscribe to topics
                    topics = ['/edge_detection/parameters', '/sensor_data']  
                    for topic in topics:
                        subscribe_msg = {
                            "op": "subscribe",
                            "topic": topic,
                            "type": "std_msgs/String"
                        }
                        await websocket.send(json.dumps(subscribe_msg))
                    print("[ROSBridge] Subscribed to topics")

                    # Keep connection alive and handle messages
                    while True:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            await self.handle_rosbridge_message(data)
                        except websockets.exceptions.ConnectionClosed:
                            print("[ROSBridge] Connection closed")
                            break
                        except Exception as e:
                            print(f"[ROSBridge] Message error: {e}")
                            continue

            except Exception as e:
                print(f"[ROSBridge] Connection error: {e}")
                self.rosbridge_connected = False
                await asyncio.sleep(2)  # Wait before retry

    async def handle_rosbridge_message(self, data):
        try:
            if data['op'] == 'publish':
                topic = data['topic']
                
                if topic == '/sensor_data':
                    # Parse result data
                    result = json.loads(data['msg']['data'])
                    if result.get('status') == 'success':
                        # Send images to frontend
                        await self.send(json.dumps({
                            'type': 'image_update',
                            'image_type': 'original',
                            'image_data': result['data']['images']['original_image']
                        }))
                        await self.send(json.dumps({
                            'type': 'image_update',
                            'image_type': 'ed',
                            'image_data': result['data']['images']['output_image']
                        }))
                        
        except Exception as e:
            print(f"[ROSBridge] Message processing error: {e}")

    async def receive(self, text_data):
        """Handle messages from frontend"""
        try:
            data = json.loads(text_data)
            command = data.get('command')

            if command == 'run_detection':
                if not self.rosbridge_connected:
                    await self.send(json.dumps({
                        'type': 'error',
                        'message': 'Edge detection service not connected'
                    }))
                    return

                # Ensure DXF content is properly handled
                dxf_content = data.get('dxf_content')
                tolerance = float(data.get('tolerance', 1.0))
                
                if not dxf_content:
                    await self.send(json.dumps({
                        'type': 'error',
                        'message': 'No DXF content provided'
                    }))
                    return

                print(f"[WebSocket] Sending detection request with tolerance: {tolerance}mm")

                # Send parameters to IPC
                ros_message = {
                    'op': 'publish',
                    'topic': '/edge_detection/parameters',
                    'type': 'std_msgs/String',
                    'msg': {
                        'data': json.dumps({
                            'dxf_content': dxf_content,
                            'dxf_filename': 'demoPart.DXF',  # Add the original filename
                            'tolerance': tolerance,
                            'timestamp': str(asyncio.get_event_loop().time())
                        })
                    }
                }

                try:
                    async with websockets.connect("ws://10.10.42.126:9090") as ws:
                        await ws.send(json.dumps(ros_message))
                        print(f"[ROSBridge] Parameters sent: tolerance={tolerance}mm, DXF content length: {len(dxf_content)}")
                        await self.send(json.dumps({
                            'type': 'status',
                            'message': 'Parameters sent'
                        }))
                except Exception as e:
                    print(f"[ROSBridge] Send error: {e}")
                    await self.send(json.dumps({
                        'type': 'error',
                        'message': 'Failed to send parameters'
                    }))

        except Exception as e:
            print(f"[WebSocket] Error: {e}")
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def disconnect(self, close_code):
        """Clean up on WebSocket disconnection"""
        print("[WebSocket] Client disconnecting")
        if self.rosbridge_task:
            self.rosbridge_task.cancel()
            try:
                await self.rosbridge_task
            except asyncio.CancelledError:
                print("[ROSBridge] Connection task cancelled")
        
        self.rosbridge_connected = False
        await self.channel_layer.group_discard("edge_detection_group", self.channel_name)