# WS client example

import asyncio
import websockets
import subprocess
import re

results = []

async def hello():
    async with websockets.connect(
            'ws://202.92.132.191:3001') as websocket:

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
                        results.append("Path MTU: " + mtu)
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
                        results.append("Baseline RTT: " + ave_rtt + " ms")
                await websocket.send("ping done")
            
            #iperf udp and tcp mode
            state = await websocket.recv()
            print(state)
            if state == "iperf server started":
                #UDP mode
                p = subprocess.Popen(["iperf3", "-c", "202.92.132.191", "-u", "-b", "1000M"], stdout = subprocess.PIPE)
                flag=0
                for line in p.stdout:
                    temp = line.decode("utf-8")
                    if "Jitter" in temp:
                        flag = 1
                        continue
                    if flag == 1:
                        entries = re.findall(r'\S+',temp)
                        bb = entries[6]
                        results.append("Bottleneck Bandwidth: " + bb + " Mbits/sec")
                        bdp = (float(re.split(" ", results[1])[2]) /1000) * (float(bb)* 1000000)
                        results.append("BDP: " + str(bdp) + " bits")
                        results.append("Min RWND: " + str(bdp/8 / 1000) + " Kbytes")
                        break
                
                #TCP mode - run for 5s to keep pcap small
                t = subprocess.Popen(["tshark", "-w", "testresults.pcapng"])
                rwnd = re.split(" ", results[4])[3]
                p = subprocess.Popen(["iperf3", "-c", "202.92.132.191", "-t", "5", "-w", rwnd+"K"], stdout = subprocess.PIPE)
                for line in p.stdout:
                    temp = line.decode("utf-8")
                    if "sender" in temp:
                        entries = re.findall(r'\S+',temp)
                        
                        results.append("Average TCP Throughput: " + entries[6] + " Mbits/s")

                        mtu = int(re.split(" ", results[0])[2])
                        max_throughput = (mtu-40) * 8 * 81274 /1000000 #1500 MTU 8127 FPS based on connection type
                        results.append("Ideal TCP Throughput: " + str(max_throughput) + " Mbits/s")

                        temp2 = re.split("-",entries[2])
                        actual = float(temp2[1])
                        results.append("Actual Transfer Time: " + str(actual))
                                
                        ideal = float(entries[4]) * 8 / max_throughput
                        results.append("Ideal Transfer Time: " + str(ideal))
                            
                        ttr = actual / ideal
                        results.append("TCP TTR: " + str(ttr))
                await websocket.send("iperf done")
                t.kill()

                #TCP Efficiency Processing... takes some time
                print("Processing Efficiency")
                p = subprocess.Popen(["python3", "scapy-tcp-eff-expt2.py", "testresults.pcapng", "202.92.132.191"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                for line in p.stdout:
                    temp = line.decode("utf-8")
                    results.append(temp)

                #Buffer Delay Processing... takes some time
                print("Processing Buffer Delay")
                p = subprocess.Popen(["python3", "buffer-delay.py", "testresults.pcapng", "192.168.60.21", "202.92.132.191", re.split(" ", results[1])[2]], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                for line in p.stdout:
                    temp = line.decode("utf-8")
                    results.append(temp)
                

            #show all results
            for line in results:
                print(line)
        except websockets.exceptions.ConnectionClosed:
            print("connection closed")
            pass

asyncio.get_event_loop().run_until_complete(hello())
