import asyncio

from asyncua import Client

import logging

async def test_opcua_connection():
	logging.basicConfig(level=logging.DEBUG)
	try:
		client=Client('opc.tcp://10.10.42.11:4840')
		await client.connect()
		logging.info('Successfully connected to the OPCUA server!')
	except:
		logging.error(f'Error:')

if __name__ == "__main__":
	asyncio.run(test_opcua_connection())
