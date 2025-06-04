from asyncua import Client, ua
import asyncio
import logging
import signal
import sys

class OPCUAClient:
    def __init__(self, url, node_id):
        self.url = url
        self.node_id = node_id
        self.client = None
        self.running = True
        
    async def connect(self):
        try:
            self.client = Client(self.url)
            self.client.application_uri = "urn:SIMATIC.S7-1500.OPC-UA.Application:PressPLC"
            self.client.description = "Siemens S7-1500 PLC"
            
            # Connect to server
            await self.client.connect()
            print("Connected to server")
            
            return True
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
            
    async def read_loop(self):
        try:
            node = self.client.get_node(self.node_id)
            while self.running:
                try:
                    value = await node.read_value()
                    print(f"Node value: {value}")
                    await asyncio.sleep(1)  # Read every second
                except Exception as e:
                    logging.error(f"Error reading value: {e}")
                    await asyncio.sleep(1)
                    # Try to reconnect if reading fails
                    if not await self.connect():
                        await asyncio.sleep(5)  # Wait before retry
        except Exception as e:
            logging.error(f"Read loop error: {e}")
            
    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("Disconnected from server")
            
    def stop(self):
        self.running = False

async def main():
    # Server configuration
    url = "opc.tcp://10.10.42.11:4840"
    node_id = 'ns=3;s="MaterialCarrierMotors_DB"."motorLoadMean_M3"'
    
    client = OPCUAClient(url, node_id)
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, client.stop)
    
    try:
        if await client.connect():
            await client.read_loop()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())