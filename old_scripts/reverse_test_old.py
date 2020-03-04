#!/usr/bin/env python

import asyncio
import websockets
import subprocess
import re
import os
import signal
from utilities import server_utils as sutil

async def l_to_r(websocket, path):
    state = await websocket.recv()
    print(f"< {state}")
    if state == "reverse":
        results = []
        client_ip = websocket.remote_address[0]
        max_retr = 0

        try:
            p = subprocess.Popen(["./plpmtu_reverse"],stdout = subprocess.PIPE)
            print("plpmtu started")
            await websocket.send("plpmtu started")
            p.wait(timeout = 20)
        except subprocess.TimeoutExpired:
            print("mtu timeout")
            p.kill()

        mtu_list = sutil.mtu_list
        for line in p.stdout:
            temp = line.decode("utf-8")
            print(temp)
            
            if "PLPMTUD" in temp:
                mtu = re.split(" ", temp)[3]
                results.append("Path MTU: " + mtu)

        max_retr += 1
        if max_retr >=5:
            print("Cannot perform PLPMTUD")
            await websocket.send("mtu error")
            return

        try:
            if results[0]:
                break
        except IndexError:
            pass

            
        print("mtu done")
        await websocket.send("mtu done")
        
        max_retr = 0
        while True:
            p = subprocess.Popen(["python3", "udp-ping-server.py"],stdout = subprocess.PIPE)
            await websocket.send("start ping")
            p.wait()
            for line in p.stdout:
                ping = line.decode("utf-8")
                if "Lost" in ping:
                    break
                print("ping:" + ping[:-1])
                results.append("Baseline RTT: " + ping[:-1] + " ms")

            max_retr += 1
            if max_retr >= 5:
                print("Cannot perform Ping")
                await websocket.send("ping error")
                return

            try:
                if results[1]:
                    await websocket.send("ping done")
                    break
            except IndexError:
                pass


        #iperf udp and tcp
        max_retr = 0
        while True:
            p = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
            await websocket.send("iperf server started")

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

                        #check if test ran in 10s
                        timecheck = float(re.split("-", entries[2])[1])
                        if timecheck < 10:
                            print("iPerf UDP incomplete")
                            await websocket.send("iperf server started")
                            break

                        bb = entries[6]
                        results.append("Bottleneck Bandwidth: " + bb + " Mbits/sec")
                        bdp = (float(re.split(" ", results[1])[2]) / 1000) * (float(bb) * 1000000)
                        results.append("BDP: " + str(bdp) + " bits")
                        rwnd = bdp/8 / 1000
                        results.append("Min RWND: " + str(rwnd) + " Kbytes")

                        break

            max_retr += 1

            if max_retr >= 5:
                print("Cannot perform iPerf UDP")
                await websocket.send("iPerf UDP error")
                return

            try:
                if results[2] and results[3] and results[4]:
                    await websocket.send("iPerf UDP done")
                    break
            except IndexError:
                pass

        #TCP window scans
        #send window sizes
        await websocket.send(str(rwnd*1000/4))
        ideal_thpt = ((rwnd/4) * 8 / (float(re.split(" ", results[1])[2])/1000))/1000
        await websocket.send(str("{0:.2f}".format(round(ideal_thpt,2))) + " Mbits/s")
        await websocket.send(str(rwnd*1000/2))
        ideal_thpt = ((rwnd/2) * 8 / (float(re.split(" ", results[1])[2])/1000))/1000
        await websocket.send(str("{0:.2f}".format(round(ideal_thpt,2))) + " Mbits/s")
        await websocket.send(str(rwnd*1000*3/4))
        ideal_thpt = ((rwnd*3/4) * 8 / (float(re.split(" ", results[1])[2])/1000))/1000
        await websocket.send(str("{0:.2f}".format(round(ideal_thpt,2))) + " Mbits/s")
        await websocket.send(str(rwnd*1000))
        ideal_thpt = ((rwnd) * 8 / (float(re.split(" ", results[1])[2])/1000))/1000
        await websocket.send(str("{0:.2f}".format(round(ideal_thpt,2))) + " Mbits/s")


        #step 1 - 25%
        if os.path.exists("wnd_25_percent.pcapng"):
            os.remove("wnd_25_percent.pcapng")
        t = subprocess.Popen(["tshark", "-w", "wnd_25_percent.pcapng"])
        p = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
        await websocket.send("start iperf tcp " + str(rwnd/4))
        state = await websocket.recv()
        if state == "iperf tcp done":
            p.kill()

            for line in p.stdout:
                temp = line.decode("utf-8")
                if "sender" in temp:
                    entries = re.findall(r'\S+', temp)

                    #check if test ran in 5s
                    timecheck = float(re.split("-", entries[2])[1])
                    if timecheck < 5:
                        print("iPerf TCP incomplete")
                        break

                    print("25%:" + entries[6] + "Mbits/s")
                    await websocket.send(entries[6])

            t.kill()
            subprocess.Popen(["sudo","chmod", "777", "wnd_25_percent.pcapng"])
            p = subprocess.Popen(["python3","scapy-tcp-eff-simple.py", "wnd_25_percent.pcapng", server_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            p.wait()
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)

            p = subprocess.Popen(["python3", "buffer-delay-simple.py", "wnd_25_percent.pcapng", server_ip, client_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)

        
        #step 2 - 50%
        if os.path.exists("wnd_25_percent.pcapng"):
            os.remove("wnd_25_percent.pcapng")
        t = subprocess.Popen(["tshark", "-w", "wnd_25_percent.pcapng"])
        p = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
        await websocket.send("start iperf tcp " + str(rwnd/2))
        state = await websocket.recv()
        if state == "iperf tcp done":
            p.kill()

            for line in p.stdout:
                temp = line.decode("utf-8")
                if "sender" in temp:
                    entries = re.findall(r'\S+', temp)

                    #check if test ran in 5s
                    timecheck = float(re.split("-", entries[2])[1])
                    if timecheck < 5:
                        print("iPerf TCP incomplete")
                        break

                    print("50%:" + entries[6] + "Mbits/s")
                    await websocket.send(entries[6])

            t.kill()
            subprocess.Popen(["sudo","chmod", "777", "wnd_25_percent.pcapng"])
            p = subprocess.Popen(["python3","scapy-tcp-eff-simple.py", "wnd_25_percent.pcapng", server_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            p.wait()
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)

            p = subprocess.Popen(["python3", "buffer-delay-simple.py", "wnd_25_percent.pcapng", server_ip, client_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)

        #step 3 - 75%
        if os.path.exists("wnd_25_percent.pcapng"):
            os.remove("wnd_25_percent.pcapng")
        t = subprocess.Popen(["tshark", "-w", "wnd_25_percent.pcapng"])
        p = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
        await websocket.send("start iperf tcp " + str(rwnd*3/4))
        state = await websocket.recv()
        if state == "iperf tcp done":
            p.kill()

            for line in p.stdout:
                temp = line.decode("utf-8")
                if "sender" in temp:
                    entries = re.findall(r'\S+', temp)

                    #check if test ran in 5s
                    timecheck = float(re.split("-", entries[2])[1])
                    if timecheck < 5:
                        print("iPerf TCP incomplete")
                        break

                    print("75%:" + entries[6] + "Mbits/s")
                    await websocket.send(entries[6])

            t.kill()
            subprocess.Popen(["sudo","chmod", "777", "wnd_25_percent.pcapng"])
            p = subprocess.Popen(["python3","scapy-tcp-eff-simple.py", "wnd_25_percent.pcapng", server_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            p.wait()
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)

            p = subprocess.Popen(["python3", "buffer-delay-simple.py", "wnd_25_percent.pcapng", server_ip, client_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)


        max_retr = 0
        while True:
            if os.path.exists("testresults.pcapng"):
                os.remove("testresults.pcapng")

            #MAKE SURE DIRECTORY CAN BE ACCESSED BY ROOT
            t = subprocess.Popen(["tshark", "-w", "testresults.pcapng"])
            p = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
            await websocket.send("start iperf tcp " + str(rwnd))

            state = await websocket.recv()
            if state == "iperf tcp done":
                t.kill()
                p.kill()
                speed_plot = []
                for line in p.stdout:
                    temp = line.decode("utf-8")
                    if "sender" in temp:
                        entries = re.findall(r'\S+', temp)

                        #check if test ran in 5s
                        timecheck = float(re.split("-", entries[2])[1])
                        if timecheck < 5:
                            print("iPerf TCP incomplete")
                            break

                        await websocket.send(entries[6])

                        results.append("Average TCP Throughput: " + entries[6] + " Mbits/s")

                        mtu = int(re.split(" ", results[0])[2])
                        ideal_throughput = rwnd * 8 / (float(re.split(" ", results[1])[2])/1000)/1000
                        results.append("Ideal TCP Throughput: " + str(ideal_throughput))

                        temp2 = re.split("-", entries[2])
                        actual = float(temp2[1])
                        results.append("Actual Transfer Time: " + str(actual))

                        ideal = float(entries[4]) * 8 / ideal_throughput
                        results.append("Ideal Transfer Time: " + str(ideal))

                        ttr = actual / ideal
                        results.append("TCP TTR: " + str(ttr))

                    elif "KBytes" in temp:
                        entries = re.findall(r'\S+', temp)
                        if "Kbits" in entries[7]:
                            temp = float(entries[6])/1000
                        else:
                            temp = float(entries[6])
                        x_axis = re.split("-", entries[2])
                        x_axis = int(float(x_axis[1]))
                        speed_plot.append([x_axis, temp])

            max_retr += 1
            if max_retr >= 5:
                print("Cannot perform iPerf TCP")
                return

            try:
                if results[5] and results[6] and results[7] and results[8] and results[9]:
                    await websocket.send("iPerf TCP done")
                    break
            except IndexError:
                pass

        max_retr = 0
        await websocket.send("Processing Efficiency")
        print("Processing Efficiency")
        while True:        
            #Process TCP Efficiency
            subprocess.Popen(["sudo","chmod", "777", "testresults.pcapng"])
            p = subprocess.Popen(["python3","scapy-tcp-eff-expt2.py", "testresults.pcapng", server_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            for line in p.stdout:
                temp = line.decode("utf-8")

                if "plot" in temp:
                    eff_rplot = temp
                else:
                    results.append(temp)

            max_retr += 1
            if max_retr >= 5:
                print("Cannot process TCP Efficiency")
                await websocket.send("Cannot process TCP Efficiency")
                return

            try:
                if results[10] and results[11] and results[12]:
                    await websocket.send("TCP Efficiency Done")
                    break
            except IndexError:
                pass

        max_retr = 0
        await websocket.send("Processing Buffer Delay")
        print("Processing Buffer Delay")
        while True:
            #Process Buffer Delay
            p = subprocess.Popen(["python3", "buffer-delay.py", "testresults.pcapng", server_ip, client_ip, re.split(" ", results[1])[2]], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            for line in p.stdout:
                temp = line.decode("utf-8")
                
                if "plot" in temp:
                    rtt_rplot = temp
                else:
                    results.append(temp)

            max_retr += 1
            if max_retr >= 5:
                print("Cannot process Buffer Delay")
                return

            try:
                if results[13] and results[14]:
                    await websocket.send("Buffer Delay Done")
                    break
            except IndexError:
                pass

        #send tcp eff to wnd scan
        temp = re.split(" ", results[12])
        await websocket.send(temp[2])

        #send rtt to wnd scan
        temp = re.split(" ", results[13])
        await websocket.send(temp[2])
        
        #send test results to client
        for line in results:
            line.replace('\n', '')
            await websocket.send(line)
            print(line)

        #send bandwidth measurements to client
        await websocket.send(str(speed_plot))

        state = await websocket.recv()
        print(state)
        if state == "speed_plot received":
            await websocket.send(str(eff_rplot))

        state = await websocket.recv()
        print(state)
        if state == "reff_plot received":
            await websocket.send(str(rtt_rplot))

        asyncio.get_event_loop().stop()

if __name__ == "__main__":
	start_server = websockets.serve(l_to_r, server_ip, 3001, ping_timeout=600)

	asyncio.get_event_loop().run_until_complete(start_server)
	asyncio.get_event_loop().run_forever()
