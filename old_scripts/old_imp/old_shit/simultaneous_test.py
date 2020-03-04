import sys
import asyncio
import websockets
import subprocess
import re
import os
import signal

async def simultaneous_test(websocket, path):

    if state == "simultaneous":
        results = []
        client_ip = websocket.remote_address[0]

        p = subprocess.Popen(["python3", "udp_server.py", "3002"])
        print("plpmtu started")
        await websocket.send("plpmtu started")

        state = await websocket.recv()
        if state == "plpmtu done":
            p.kill()
            max_retr = 0
            while True:
                try:
                    p = subprocess.Popen(["./plpmtu_reverse"],stdout = subprocess.PIPE)
                    print("plpmtu_reverse started")
                    await websocket.send("plpmtu_reverse started")
                    p.wait(timeout=20)

                except subprocess.TimeoutExpired:
                    print("mtu timeout")
                    p.kill()

                for line in p.stdout:
                    temp = line.decode("utf-8")
                    print(temp)
                
                    if "PLPMTUD" in temp:
                        mtu = re.split(" ", temp)[3]
                        results.append("Path MTU: " + mtu)

                max_retr += 1
                if max_retr>=5:
                    print("Cannot perform PLPMTUD")
                    await websocket.send("mtu error")
                    return

                try:
                    if results[0]:
                        break
                    else:
                        await websocket.send("repeat")
                except IndexError:
                    pass

            print("mtu done ")
            await websocket.send("mtu done")


        

        state = await websocket.recv()
        print(f"< {state}")
        if state == "ping done":
            max_retr = 0
            while True:
                p = subprocess.Popen(["python3", "udp-ping-server.py"],stdout = subprocess.PIPE)
                await websocket.send("start ping")
                p.wait()
                for line in p.stdout:
                    ping = line.decode("utf-8")
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

            command = [
                'iperf3 -s -p 4001',
                'iperf3 -s -p 4002'
            ]

            max_retr = 0
            while True:
                processes = [subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, preexec_fn = os.setsid) for cmd in command]
                await websocket.send("iperf udp started")

                state = await websocket.recv()
                print(f"< {state}")
                rwnd = 0
                if state == "iperf udp done":
                    for p in processes:
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)

                    flag = 0
                    udp_results = []
                    for line in processes[1].stdout:
                        temp  = line.decode("utf-8")
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
                            udp_results.append("Bottleneck Bandwidth: " + bb + " Mbits/sec")
                            bdp = (float(re.split(" ", results[1])[2]) / 1000) * (float(bb) * 1000000)
                            udp_results.append("BDP: " + str(bdp) + " bits")
                            rwnd = bdp/8 / 1000
                            udp_results.append("Min RWND: " + str(rwnd) + " Kbytes")
                            break

                    if udp_results:
                        await websocket.send("udp success")
                        print("udp success")
                    else:
                        await websocket.send("udp fail")
                        print("udp fail")



                    state = await websocket.recv()
                    print(f"< {state}")
                    if "udp success" in state:
                        for i in udp_results:
                            results.append(i)
                        break

                        print(results)
                    elif "udp fail" in state:
                        print("udp failed")

                max_retr += 1
                if max_retr >= 5: 
                    print("Cannot perform iPerf UDP")
                    return


            #TCP Window Scan Test
            #step 1 - 25%
            state = await websocket.recv()
            print(f"< {state}")
            if state == "send rwnd":
                command = [
                    'tshark -w wnd_25_percent.pcapng',
                    'iperf3 -s -p 4001',
                    'iperf3 -s -p 4002'
                ]

                rwnd_size = rwnd*1000/4
                await websocket.send("rwnd: " + str("{0:.2f}".format(round(rwnd_size,2))))

                if os.path.exists("wnd_25_percent.pcapng"):
                    os.remove("wnd_25_percent.pcapng")
                processes = [subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, preexec_fn = os.setsid) for cmd in command]
                await websocket.send("start tcp")

                state = await websocket.recv()
                print(f"< {state}")
                if state == "iperf tcp done":
                    for p in processes:
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)

            
                for line in processes[2].stdout:
                    temp  = line.decode("utf-8")

                    if "sender" in temp:
                        entries = re.findall(r'\S+', temp)

                        print("25%:" + entries[6] + "Mbits/s")
                        await websocket.send(entries[6])
                        ideal_thpt = (rwnd_size * 8 / (float(re.split(" ", results[1])[2])/1000))/1000000
                        await websocket.send(str("{0:.2f}".format(round(ideal_thpt,2))) + "Mbits/s")

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
            state = await websocket.recv()
            print(f"< {state}")
            if state == "send rwnd":
                command = [
                    'tshark -w wnd_50_percent.pcapng',
                    'iperf3 -s -p 4001',
                    'iperf3 -s -p 4002'
                ]

                rwnd_size = rwnd*1000/2
                await websocket.send("rwnd: " + str("{0:.2f}".format(round(rwnd_size,2))))

                if os.path.exists("wnd_50_percent.pcapng"):
                    os.remove("wnd_50_percent.pcapng")
                processes = [subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, preexec_fn = os.setsid) for cmd in command]
                await websocket.send("start tcp")

                state = await websocket.recv()
                print(f"< {state}")
                if state == "iperf tcp done":
                    for p in processes:
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)

            
                for line in processes[2].stdout:
                    temp  = line.decode("utf-8")

                    if "sender" in temp:
                        entries = re.findall(r'\S+', temp)

                        print("50%:" + entries[6] + "Mbits/s")
                        await websocket.send(entries[6])
                        ideal_thpt = (rwnd_size * 8 / (float(re.split(" ", results[1])[2])/1000))/1000000
                        await websocket.send(str("{0:.2f}".format(round(ideal_thpt,2))) + "Mbits/s")

            subprocess.Popen(["sudo","chmod", "777", "wnd_50_percent.pcapng"])
            p = subprocess.Popen(["python3","scapy-tcp-eff-simple.py", "wnd_50_percent.pcapng", server_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            p.wait()
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)

            p = subprocess.Popen(["python3", "buffer-delay-simple.py", "wnd_50_percent.pcapng", server_ip, client_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)


            #step 3 - 75%
            state = await websocket.recv()
            print(f"< {state}")
            if state == "send rwnd":
                command = [
                    'tshark -w wnd_75_percent.pcapng',
                    'iperf3 -s -p 4001',
                    'iperf3 -s -p 4002'
                ]

                rwnd_size = rwnd*3*1000/4
                await websocket.send("rwnd: " + str("{0:.2f}".format(round(rwnd_size,2))))

                if os.path.exists("wnd_75_percent.pcapng"):
                    os.remove("wnd_75_percent.pcapng")
                processes = [subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, preexec_fn = os.setsid) for cmd in command]
                await websocket.send("start tcp")

                state = await websocket.recv()
                print(f"< {state}")
                if state == "iperf tcp done":
                    for p in processes:
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)

            
                for line in processes[2].stdout:
                    temp  = line.decode("utf-8")

                    if "sender" in temp:
                        entries = re.findall(r'\S+', temp)

                        print("75%:" + entries[6] + "Mbits/s")
                        await websocket.send(entries[6])
                        ideal_thpt = (rwnd_size * 8 / (float(re.split(" ", results[1])[2])/1000))/1000000
                        await websocket.send(str("{0:.2f}".format(round(ideal_thpt,2))) + "Mbits/s")

            subprocess.Popen(["sudo","chmod", "777", "wnd_75_percent.pcapng"])
            p = subprocess.Popen(["python3","scapy-tcp-eff-simple.py", "wnd_75_percent.pcapng", server_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            p.wait()
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)

            p = subprocess.Popen(["python3", "buffer-delay-simple.py", "wnd_75_percent.pcapng", server_ip, client_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            for line in p.stdout:
                temp = line.decode("utf-8")
                await websocket.send(temp)


            state = await websocket.recv()
            print(f"< {state}")
            if state == "send rwnd":
                command = [
                    'tshark -w testresults.pcapng',
                    'iperf3 -s -p 4001',
                    'iperf3 -s -p 4002'
                ]


                await websocket.send("rwnd: " + str("{0:.2f}".format(round(rwnd,2))))

                max_retr = 0
                while True:
                    if os.path.exists("testresults.pcapng"):
                        os.remove("testresults.pcapng")
                    processes = [subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, preexec_fn = os.setsid) for cmd in command]
                    
                    await websocket.send("start tcp")

                    state = await websocket.recv()
                    print(f"< {state}")
                    if state == "iperf tcp done":
                        for p in processes:
                            os.killpg(os.getpgid(p.pid), signal.SIGTERM)

                        speed_plot = []
                        tcp_res = []
                        for line in processes[2].stdout:
                            temp  = line.decode("utf-8")

                            if "sender" in temp:
                                entries = re.findall(r'\S+', temp)

                                if timecheck < 5:
                                    print("iPerf TCP incomplete")
                                    break

                                tcp_res.append("Average TCP Throughput: " + entries[6] + " Mbits/s")
                                ave_tcp = entries[6]

                                mtu = int(re.split(" ", results[0])[2])
                                ideal_throughput = rwnd * 8 / (float(re.split(" ", results[1])[2])/1000)/1000
                                tcp_res.append("Ideal TCP Throughput: " + str(ideal_throughput) + " Mbits/s")
                                ideal_thpt = str("{0:.2f}".format(round(ideal_thpt,2)))

                                temp2 = re.split("-", entries[2])
                                actual = float(temp2[1])
                                tcp_res.append("Actual Transfer Time: " + str(actual))

                                ideal = float(entries[4]) * 8 / ideal_throughput
                                tcp_res.append("Ideal Transfer Time: " + str(ideal))

                                ttr = actual / ideal
                                tcp_res.append("TCP TTR: " + str(ttr))

                                break

                            elif "KBytes" in temp:
                                entries = re.findall(r'\S+', temp)
                                if "Kbits" in entries[7]:
                                    temp = float(entries[6])/1000
                                else:
                                    temp = float(entries[6])
                                x_axis = re.split("-", entries[2])
                                x_axis = int(float(x_axis[1]))
                                speed_plot.append([x_axis, temp])

                    if tcp_res:
                        await websocket.send("tcp success")
                        print("tcp success")
                    else:
                        await websocket.send("tcp fail")
                        print("tcp fail")

                    state = await websocket.recv()
                    print(f"< {state}")
                    if "tcp success" in state:
                        for i in tcp_res:
                            results.append(i)
                        break

                        print(results)
                    elif "tcp fail" in state:
                        print("tcp failed")

                    max_retr += 1
                    if max_retr >= 5:
                        print("Cannot perform iPerf TCP")
                        return

        await websocket.send(ave_tcp)
        await websocket.send(ideal_thpt + "Mbits/s")


        subprocess.Popen(["sudo","chmod", "777", "testresults.pcapng"])
        print("Processing Efficiency")
        max_retr = 0
        flag = 0
        while True:
            p = subprocess.Popen(["python3","scapy-tcp-eff-expt2.py", "testresults.pcapng", server_ip], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            for line in p.stdout:
                temp = line.decode("utf-8")

                if "plot" in temp:
                    eff_rplot = temp
                else:
                    results.append(temp)

            max_retr += 1
            if max_retr >= 5:
                print("Cannot process TCP efficiency")
                break

            try:
                if results[10] and results[11] and results[12]:
                    flag = 1
                    break
            except IndexError:
                pass

        state = await websocket.recv()
        print(state)
        if "send eff status" in state and flag == 1:
            await websocket.send("tcp eff done")
        else: 
            await websocket.send("eff fail")

        #Process Buffer Delay
        print("Processing Buffer Delay")
        max_retr = 0
        flag = 0
        while True:
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
                break

            try:
                if results[13] and results[14]:
                    flag = 1
                    break
            except IndexError:
                pass

        state = await websocket.recv()
        print(state)
        if "send buffer status" in state and flag == 1:
            await websocket.send("Buffer Delay done")
        else: 
            await websocket.send("buffer fail")

        state = await websocket.recv()
        print(f"< {state}")
        if state == "send results":
            for line in results:
                line.replace('\n', '')
                await websocket.send(line)
                print(line)

        state = await websocket.recv()
        print(f"< {state}")
        if state == "bandwidth":
            #send bandwidth measurements to client
            print(speed_plot)
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



        print("done")

    else:
        print("Invalid Mode")

if __name__ == "__main__":
	start_server = websockets.serve(simultaneous_test, '202.92.132.191', 3001 , ping_timeout=600)

	asyncio.get_event_loop().run_until_complete(start_server)
	asyncio.get_event_loop().run_forever()
