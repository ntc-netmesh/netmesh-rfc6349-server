#!/usr/bin/env python

# WS server example

import asyncio
import websockets
import subprocess
import re

results = []

async def inst(websocket, path):
    state = await websocket.recv()
    print(f"< {state}")

    if state == "connecting":
        p = subprocess.Popen(["./plpmtu_reverse"],stdout = subprocess.PIPE)
        print("plpmtu started")
        await websocket.send("plpmtu started")
        p.wait()

        for line in p.stdout:
            temp = line.decode("utf-8")
            print(temp)
            
            if "PLPMTUD" in temp:
                mtu = re.split(" ", temp)[3]
                results.append("Path MTU: " + mtu)
            
    print("mtu done")
    #await websocket.send("mtu done")

    #results.append("Baseline RTT: 0.6 ms")
    p = subprocess.Popen(["python3", "udp-ping-server.py"],stdout = subprocess.PIPE)
    await websocket.send("start ping")
    p.wait()
    for line in p.stdout:
        ping = line.decode("utf-8")
    print("ping:" + ping[:-1])
    results.append("Baseline RTT: " + ping[:-1] + " ms")

    #state = await websocket.recv()
    #print(f"< {state}")
    #if state == "ping done":
    p = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
    await websocket.send("iperf server started")

    #process iperf udp and start tcp test
    state = await websocket.recv()
    print(f"< {state}")
    if state == "iperf udp done":
        flag = 0
        p.kill()
        for line in p.stdout:
            temp  =line.decode("utf-8")
            if "Jitter" in temp:
                flag = 1
                continue
            if flag == 1:
                entries = re.findall(r'\S+', temp)
                bb = entries[6]
                results.append("Bottleneck Bandwidth: " + bb + " Mbits/sec")
                bdp = (float(re.split(" ", results[1])[2]) / 1000) * (float(bb) * 1000000)
                results.append("BDP: " + str(bdp) + " bits")
                rwnd = bdp/8 / 1000
                results.append("Min RWND: " + str(rwnd) + " Kbytes")

                #MAKE SURE DIRECTORY CAN BE ACCESSED BY ROOT
                t = subprocess.Popen(["tshark", "-w", "testresults.pcapng"])
                p = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
                await websocket.send("start iperf tcp " + str(rwnd))

                state = await websocket.recv()
                if state == "iperf tcp done":
                    t.kill()
                    p.kill()
                    for line in p.stdout:
                        temp = line.decode("utf-8")
                        if "sender" in temp:
                            entries = re.findall(r'\S+', temp)

                            results.append("Average TCP Throughput: " + entries[6] + " Mbits/s")

                            mtu = int(re.split(" ", results[0])[2])
                            max_throughput = (mtu-40) * 8 * 81274 / 1000000
                            results.append("Ideal TCP Throughput: " + str(max_throughput))

                            temp2 = re.split("-", entries[2])
                            actual = float(temp2[1])
                            results.append("Actual Transfer Time: " + str(actual))

                            ideal = float(entries[4]) * 8 / max_throughput
                            results.append("Ideal Transfer Time: " + str(ideal))

                            ttr = actual / ideal
                            results.append("TCP TTR: " + str(ttr))
                break
    #Process TCP Efficiency
    await websocket.send("Processing Efficiency")
    print("Processing Efficiency")
    subprocess.Popen(["sudo","chmod", "777", "testresults.pcapng"])
    p = subprocess.Popen(["python3","scapy-tcp-eff-expt2.py", "testresults.pcapng", "202.92.132.253"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    for line in p.stdout:
        temp = line.decode("utf-8")
        results.append(temp)
    #if p.stderr:
    #    print(p.stderr)

    #Process Buffer Delay
    await websocket.send("Processing Buffer Delay")
    print("Processing Buffer Delay")
    p = subprocess.Popen(["python3", "buffer-delay.py", "testresults.pcapng", "202.92.132.191", "202.92.132.253", re.split(" ", results[1])[2]], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    for line in p.stdout:
        temp = line.decode("utf-8")
        results.append(temp)

    for line in results:
        line.replace('\n', '')
        await websocket.send(line)
        print(line)

    asyncio.get_event_loop().stop()

start_server = websockets.serve(inst, '202.92.132.191', 3001, ping_timeout=600)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
