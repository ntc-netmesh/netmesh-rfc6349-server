import asyncio
import websockets
import re
from datetime import datetime
import threading
import subprocess

async def simultaneous(websocket, path):
    state = await websocket.recv()
    print(f"< {state}")
    if state == "start iperf udp":
        command = [
            'iperf3 -s -p 4001',
            'iperf3 -s -p 4002'
        ]
        processes = [subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE) for cmd in command]

        await websocket.send("iperf udp started")

        state = await websocket.recv()
        print(f"< {state}")
        if state == "iperf udp done":
            for line in processes[1].stdout:
                temp = line.decode("utf-8")
                print(temp)
            for p in processes:
                p.kill()



if __name__ == "__main__":
    start_server = websockets.serve( simultaneous, '202.92.132.191', 3001, ping_timeout=600)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()