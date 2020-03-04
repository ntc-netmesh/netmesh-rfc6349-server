#!/usr/bin/env python3

import sys, os, subprocess
import asyncio, websockets
import traceback
from constants import *

'''


'''
async def temp_mtu_handler(websocket, path):

    try:
        state = await websocket.recv()
        udp_server = None
        try:
            udp_server = subprocess.Popen(["python3", "udp_server.py", str(UDP_SERVER_PORT)])
            await websocket.send("servers started")
            await websocket.recv()
        except:
            traceback.print_exc()
            await websocket.close()

        try:
            udp_server.kill()
        except:
            traceback.print_exc()
            pass
    except:
        pass

if __name__ == "__main__":
	temp_mtu_handler = websockets.serve(temp_mtu, MAIN_SERVER_IP, TEMP_MTU_PORT , ping_timeout=600)
	asyncio.get_event_loop().run_until_complete(temp_mtu_handler)
	asyncio.get_event_loop().run_forever()
