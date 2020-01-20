# WS client example

import asyncio
import websockets
import subprocess

async def hello():
    async with websockets.connect(
            'ws://202.92.132.191:3001') as websocket:

        await websocket.send("connecting")
        
        #mtu test
        state = await websocket.recv()
        print(state)
        if state == "plpmtu started":
            p = subprocess.Popen(["sudo", "./plpmtu", "-p", "udp", "-s", "202.92.132.191:3002"], stdout = subprocess.PIPE)
            for line in p.stdout: #parse this mtu
                print(line.decode("utf-8"))
            await websocket.send("plpmtu done")

        #ping
        state = await websocket.recv()
        print(state)
        if state == "mtu done":
            p = subprocess.Popen(["ping", "202.92.132.191", "-c", "10"], stdout = subprocess.PIPE)
            for line in p.stdout: #parse this ping
                print(line.decode("utf-8"))
            await websocket.send("ping done")
        
        #iperf udp mode
        state = await websocket.recv()
        print(state)
        if state == "iperf server udp started":
            p = subprocess.Popen(["iperf3", "-c", "202.92.132.191", "-u"], stdout = subprocess.PIPE)
            for line in p.stdout: #parse this iperf
                print(line.decode("utf-8"))
            await websocket.send("iperf udp done") ## temporary

        t = subprocess.Popen(["tshark", "-w", "testresults.pcapng"])



asyncio.get_event_loop().run_until_complete(hello())
