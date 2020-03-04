#!/usr/bin/env python

# WS server example

import asyncio
import websockets
import subprocess

async def inst(websocket, path):
    state = await websocket.recv()
    print(f"< {state}")

    if state == "connecting":
        p = subprocess.Popen(["python3", "udp_server.py", "3002"])
        print("plpmtu started")
        await websocket.send("plpmtu started")

    state = await websocket.recv()
    if state == "plpmtu done":
        p.kill()
        await websocket.send("mtu done")

    state = await websocket.recv()
    print(f"< {state}")
    if state == "ping done":
        p = subprocess.Popen(["iperf3", "-s"])
        await websocket.send("iperf server started")

    state = await websocket.recv()
    print(f"< {state}")
    if state == "iperf done":
        p.kill()
        asyncio.get_event_loop().stop()
        #print("Ready to process new tests")

    #greeting = f"Hello {name}!"

    
    #print(f"> {greeting}")

start_server = websockets.serve(inst, '202.92.132.191', 3001)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
