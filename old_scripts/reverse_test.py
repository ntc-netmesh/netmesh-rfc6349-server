#!/usr/bin/env python

import asyncio
import websockets
import subprocess
import re
import os, sys
import signal
from utilities import server_utils
import time

TEST_RETRIES = 5

async def shark_test(websocket, results, rwnd):
    # PREPARE THE DUMP FILE
    sharktest_list = None
    speed_plot = None
    if os.path.exists("testresults.pcapng"):
        os.remove("testresults.pcapng")
    subprocess.call(["sudo", 'touch', 'testresults.pcapng'])
    subprocess.call(["sudo", 'chmod', '+rw', 'testresults.pcapng'])
    tshark_process = subprocess.Popen(["tshark", "-w", "testresults.pcapng"])
    iperf3_process = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
    await websocket.send("start iperf tcp " + str(rwnd))

    state = await websocket.recv()
    if state == "iperf tcp done":
        tshark_process.kill()
        iperf3_process.kill()
        sharktest_list, speed_plot = server_utils.parse_sharktest(iperf3_process.stdout,
                                                                  results[0])
    if not sharktest_list:
        print("iperf3 sharktest failed")
        return
    return sharktest_list, speed_plot

def efficiency_analyzer():
    efficiency_analyzer_output = []
    eff_rplot = None
    print("ANALYZING EFFICIENCY")
    #Process TCP Efficiency
    # CHANGE DUMPFILE PERMISSIONS
    subprocess.call(["sudo","chmod", "777", "testresults.pcapng"])
    efficiency_analyzer_process = subprocess.Popen(["python3","scapy-tcp-eff-expt2.py",
                                                    "testresults.pcapng", "202.92.132.191"], 
                                                    stdout = subprocess.PIPE,
                                                    stderr = subprocess.PIPE)
    #print(efficiency_analyzer_process.stderr)
    #efficiency_analyzer_process.wait()
    #print(str(efficiency_analyzer_process.stdout)+"\n"+str(efficiency_analyzer_process.stderr))
    for line in efficiency_analyzer_process.stdout:
        temp = line.decode("utf-8")
        print(str(temp))
        if "plot" in temp:
            eff_rplot = temp
        else:
            efficiency_analyzer_output.append(temp)
    for line in efficiency_analyzer_process.stderr:
        print(line.decode("utf-8"))
    print(str(efficiency_analyzer_output))

    #efficiency_analyzer_output, eff_rplot = server_utils.efficiency_analyzer(efficiency_analyzer_process.stdout)
    if not len(efficiency_analyzer_output) >= 3:
        print("Cannot process TCP Efficiency")
        return
    return efficiency_analyzer_output, eff_rplot

async def delay_analyzer(client_ip, delay_param):
    delay_analyzer_output = None
    rtt_rplot = None
    print("Processing Buffer Delay")

    #Process Buffer Delay
    delay_analyzer_process = subprocess.Popen(["python3", "buffer-delay.py",
                                               "testresults.pcapng", "202.92.132.191",
                                               client_ip, re.split(" ", delay_param)[2]],
                                               stdout = subprocess.PIPE,
                                               stderr = subprocess.PIPE)

    delay_analyzer_output, rtt_rplot = server_utils.delay_analyzer(delay_analyzer_process.stdout)
    if not len(delay_analyzer_output) == 2:
        print("Cannot process TCP Delay")
        return
    return delay_analyzer_output, rtt_rplot

async def mtu_test(websocket):
    mtu_results = None
    try:
        plpmtu_process = subprocess.Popen(["./plpmtu_reverse"],stdout = subprocess.PIPE)
        print("plpmtu started")
        await websocket.send("plpmtu started")
        plpmtu_process.wait(timeout = 20)
        mtu_results = server_utils.parse_mtu(plpmtu_process.stdout)
        print("mtu done")
    except subprocess.TimeoutExpired:
        print("mtu timeout")
        plpmtu_process.kill()
        return
    return mtu_results

async def udp_test(websocket):
    ping_results = None
    udpping_process = subprocess.Popen(["python3", "udp-ping-server.py"],stdout = subprocess.PIPE)
    await websocket.send("start ping")
    udpping_process.wait()

    ping_results = server_utils.parse_udpping(udpping_process.stdout)
    if not ping_results:
        print("Cannot perform Ping")
        return
    return ping_results

async def iperf_test(websocket, results):
    iperf_list = None
    rwnd = None
    iperf_process = subprocess.Popen(["iperf3", "-s"], stdout = subprocess.PIPE)
    await websocket.send("iperf server started")

    # WAIT FOR CLIENT TO FINISH USING IPERF SERVER
    state = await websocket.recv()
    iperf_process.kill()

    iperf_list, rwnd = server_utils.parse_iperf(p.stdout, results[1])
    if not iperf_list:
        print("IPERF test failed")
        return
    return iperf_list, rwnd

async def reverse_test(websocket, path):
    # go signal
    state = await websocket.recv()

    results = {}
    client_ip = websocket.remote_address[0]

    mtu_result = None
    try:
        mtu_reverse_proc = mtu_procs.start_mtu_reverse()
        await websocket.send("plpmtu started")
        mtu_result = mtu_procs.end_mtu_reverse(mtu_reverse_proc)
        results["MTU"] = mtu_result
    except:
        print("plpmtu failed")
        await websocket.send("mtu error")
        traceback.print_exc()
    await websocket.send("mtu done")

    rtt_result = None
    try:
        baseline_rtt_proc = baseline_rtt.start_baseline_measure()
        await websocket.send("rtt started")
        rtt_result = baseline_rtt.end_baseline_measure(baseline_rtt_proc)
        results["RTT"] = rtt_result
    except:
        print("baseline rtt failed")
        await websocket.send("rtt error")
        traceback.print_exc()
    await websocket.send("rtt done")

    rwnd = None
    bb_result = None
    bdp_result = None
    try:
        bb_proc = baseline_bandwidth.start_bandwidth_measure()
        await websocket.send("BB started")
        await websocket.recv()
        bb_result, bdp_result, rwnd = baseline_bandwidth.end_bandwidth_measure(bb_proc)
        results["BB"] = bb_result
        results["BDP"] = bdp_result
        results["RWND"] = rwnd
    except:
        print("baseline bandwidth failed")
        await websocket.send("bb error")
        traceback.print_exc()
    await websocket.send("bb done")

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










    speed_plot = None
    throughput_average = None
    throughput_ideal = None
    transfer_time_average = None
    transfer_time_ideal = None
    tcp_ttr = None
    try:
        shark_proc, thpt_proc = throughput_test.start_throughput_measure()
        await websocket.send("start iperf tcp " + str(rwnd))
        throughput_average, throughput_ideal, transfer_time_average, transfer_time_ideal, tcp_ttr, speed_plot = throughput_test.end_throughput_measure(shark_proc, thpt_proc, mtu_result)
        results["THPT_AVG"] = throughput_average
        results["THPT_IDEAL"] = throughput_ideal
        results["TRANSFER_AVG"] = transfer_time_average
        results["TRANSFER_IDEAL"] = transfer_time_ideal
        results["TCP_TTR"] = tcp_ttr
    except:
        print("throughput measurement failed")
        await websocket.send("throughput error")
        traceback.print_exc()
    await websocket.send("throughput done")

    # EFFICIENCY ANALYZER
    await websocket.send("Processing Efficiency")
    efficiency_analyzer_output, eff_rplot = efficiency_analyzer(websocket)
    if not efficiency_analyzer_output):
        print("efficiency fail")
        await websocket.send("Cannot process TCP Efficiency")
        continue
    await websocket.send("TCP Efficiency Done")
    results += efficiency_analyzer_output

    # DELAY ANALYZER
    await websocket.send("Processing Buffer Delay")
    delay_analyzer_output, rtt_rplot = delay_analyzer(websocket, client_ip, results[1])
    if not efficiency_analyzer_output):
        print("buffer fail")
        await websocket.send("Cannot process Buffer Delay")
        continue
    await websocket.send("Buffer Delay Done")
    results += delay_analyzer_output

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
	start_server = websockets.serve(reverse_test, '202.92.132.191', 3001, ping_timeout=600)

	asyncio.get_event_loop().run_until_complete(start_server)
	asyncio.get_event_loop().run_forever()
