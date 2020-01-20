# WS client example

import asyncio
import websockets
import subprocess
import re

#results = []
ws_url = 'ws://202.92.132.191:3001'

async def hello():
    async with websockets.connect(ws_url, ping_timeout=600) as websocket:

        try:
            await websocket.send("connecting")
            
            #mtu test
            state = await websocket.recv()
            print(state)
            if state == "plpmtu started":
                p = subprocess.Popen(["sudo", "./plpmtu", "-p", "udp", "-s", "202.92.132.191:3002"], stdout = subprocess.PIPE)
                for line in p.stdout:
                    temp = line.decode("utf-8")
                    if "PLPMTUD" in temp:
                        mtu = re.split(" ", temp)[3]
                        #results.append("Path MTU: " + mtu)
                await websocket.send("plpmtu done")

            #ping
            state = await websocket.recv()
            print(state)
            if state == "mtu done":
                p = subprocess.Popen(["ping", "202.92.132.191", "-c", "10"], stdout = subprocess.PIPE)
                for line in p.stdout:
                    temp = line.decode("utf-8")
                    if "avg" in temp:
                        rtt = re.split(" ", temp)[3]
                        ave_rtt = re.split("/", rtt)[2]
                        #results.append("Baseline RTT: " + ave_rtt + " ms")
                await websocket.send("ping done")
            
            #iperf udp and tcp mode
            state = await websocket.recv()
            print(state)
            if state == "iperf server started":
                #UDP mode
                p = subprocess.Popen(["iperf3", "-c", "202.92.132.191", "-u", "-b", "1000M", "-R"], stdout = subprocess.PIPE)
                p.wait()
                await websocket.send("iperf udp done")

            state = await websocket.recv()
            print(state)
            if "start iperf tcp" in state:
                rwnd = re.split(" ", state)[3]
                #TCP mode - run for 5s to keep pcap small
                p = subprocess.Popen(["iperf3", "-c", "202.92.132.191", "-t", "5", "-w", rwnd+"K", "-R"], stdout = subprocess.PIPE)
                p.wait()
                await websocket.send("iperf tcp done")

            state = await websocket.recv()
            print(state)

            state = await websocket.recv()
            print(state)

            while True:
                line = await websocket.recv()
                print(line)
                if "Buffer" in line:
                    break
        except websockets.exceptions.ConnectionClosed:
            print("connection closed")
            pass

asyncio.get_event_loop().run_until_complete(hello())
