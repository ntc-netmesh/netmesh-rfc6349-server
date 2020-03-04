import re

def parse_mtu(std):
    mtu_list = []
    for line in std:
        temp = line.decode("utf-8")
        if "PLPMTUD" in temp:
            mtu = re.split(" ", temp)[3]
            mtu_list.append("Path MTU: " + mtu)
    return mtu_list

def parse_udpping(std):
    ping_list = []
    for line in std:
        ping = line.decode("utf-8")
        if "Lost" in ping:
            return
        print("ping:" + ping[:-1])
        ping_list.append("Baseline RTT: " + ping[:-1] + " ms")
    return ping_list


def parse_iperf(std, bdp_param):
    iperf_list = []
    flag = 0
    rwnd = 0
    for line in std:
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
                #await websocket.send("iperf server started")
                return
                break

            bb = entries[6]
            iperf_list.append("Bottleneck Bandwidth: " + bb + " Mbits/sec")
            # bdp_param = results[1]
            bdp = (float(re.split(" ", bdp_param)[2]) / 1000) * (float(bb) * 1000000)
            iperf_list.append("BDP: " + str(bdp) + " bits")
            rwnd = bdp/8 / 1000
            iperf_list.append("Min RWND: " + str(rwnd) + " Kbytes")
    return iperf_list, rwnd

def parse_sharktest(std, sharktest_param):
    sharktest_list = []
    speedplot_list = []
    for line in std:
        temp = line.decode("utf-8")
        if "sender" in temp:
            entries = re.findall(r'\S+', temp)

            #check if test ran in 5s
            timecheck = float(re.split("-", entries[2])[1])
            if timecheck < 5:
                print("iPerf TCP incomplete")
                return

            sharktest_list.append("Average TCP Throughput: " + entries[6] + " Mbits/s")

            # sharktest_param = results[0]
            mtu = int(re.split(" ", sharktest_param)[2])
            max_throughput = (mtu-40) * 8 * 81274 / 1000000
            sharktest_list.append("Ideal TCP Throughput: " + str(max_throughput))

            temp2 = re.split("-", entries[2])
            actual = float(temp2[1])
            sharktest_list.append("Actual Transfer Time: " + str(actual))

            ideal = float(entries[4]) * 8 / max_throughput
            sharktest_list.append("Ideal Transfer Time: " + str(ideal))

            ttr = actual / ideal
            sharktest_list.append("TCP TTR: " + str(ttr))

        elif "KBytes" in temp:
            entries = re.findall(r'\S+', temp)
            if "Kbits" in entries[7]:
                temp = float(entries[6])/1000
            else:
                temp = float(entries[6])
            x_axis = re.split("-", entries[2])
            x_axis = int(float(x_axis[1]))
            speedplot_list.append([x_axis, temp])
    #print(str(sharktest_list)+"\n"+str(speedplot_list))
    return sharktest_list, speedplot_list

def efficiency_analyzer(std):
    dump_analysis = []
    eff_rplot = None
    for line in std:
        temp = line.decode("utf-8")
        if "plot" in temp:
            eff_rplot = temp
        else:
            dump_analysis.append(temp)

    return dump_analysis, eff_rplot

def delay_analyzer(std):
    delay_analysis = []
    rtt_rplot = None
    for line in std:
        temp = line.decode("utf-8")
        if "plot" in temp:
            rtt_rplot = temp
        else:
            delay_analysis.append(temp)

    return delay_analysis, rtt_rplot
