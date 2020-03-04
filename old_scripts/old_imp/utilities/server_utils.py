import re, os, subprocess
#from windows_scan import *

'''
   Parses the MTU out of an mtu process output file
   @PARAMS:
        std             :    filename of the output file

   @RETURN:
        mtu             :    maximum transmission unit
'''
def parse_mtu(std):
    mtu = None
    with open(std,"r") as f:
        for line in f:
            temp = line
            if "PLPMTUD" in temp:
                mtu = re.split(" ", temp)[3]
    f.close()
    return mtu

'''
   Parses the RTT out of an rtt process output file
   @PARAMS:
        std             :    filename of the output file

   @RETURN:
        ping            :    baseline round trip time
'''
def parse_ping(std):
    ping = None
    with open(std,"r") as f:
        for line in f:
            ping = line
            if "Lost" in ping:
                return
            print("ping:" + ping[:-1])
    f.close()
    return ping


'''
   Parses the throughput metrics out of throughput process output file
   @PARAMS:
        std             :    filename of the output file
        rtt             :    Round Trip Time

   @RETURN:
        bb              :    baseline bandwidth
        bdp             :    bandwidth delay product
        rwnd            :    receive window size
'''
def parse_iperf(std, rtt):
    bb = None
    bdp = None
    rwnd = None
    flag = 0
    with open(std,"r") as f:
        for line in f:
            temp = line
            if "Jitter" in temp:
                flag = 1
                continue
            if flag == 1:
                entries = re.findall(r'\S+', temp)
                #check if test ran in 10s
                timecheck = float(re.split("-", entries[2])[1])
                if timecheck < 10:
                    print("iPerf UDP incomplete")
                    return
                    break
                bb = entries[6]
                bdp = (float(rtt) / 1000) * (float(bb) * 1000000)
                rwnd = bdp/8 / 1000
    f.close()
    return bb, bdp, rwnd

'''
   Parses the throughput metrics out of a throughput process output file
   @PARAMS:
        stdout_data            :    filename of the output file
        mtu                    :    Maximum Transmission Unit value

   @RETURN:
        average_throughput     :    average TCP throughput
        max_throughput         :    ideal TCP throughput
        actual                 :    average transfer time
        ideal                  :    ideal transfer time
        ttr                    :    transfer time ratio between
                                      actual and ideal
        speedplot_list         :    N/A
'''
def parse_shark(std, mtu):
    speedplot_list = []
    max_throughput = None
    average_throughput = None
    actual = None
    ideal = None
    ttr = None
    with open(std,"r") as f:
        for line in f:
            temp = line
            if "sender" in temp:
                entries = re.findall(r'\S+', temp)

                #check if test ran in 5s
                timecheck = float(re.split("-", entries[2])[1])
                if timecheck < 5:
                    print("iPerf TCP incomplete")
                    return
                average_throughput = entries[6]

                if mtu:
                    max_throughput = (float(mtu)-40) * 8 * 81274 / 1000000
                    temp2 = re.split("-", entries[2])
                    actual = float(temp2[1])
                    ideal = float(entries[4]) * 8 / max_throughput
                    ttr = actual / ideal

            elif "KBytes" in temp:
                entries = re.findall(r'\S+', temp)
                if "Kbits" in entries[7]:
                    temp = float(entries[6])/1000
                else:
                    temp = float(entries[6])
                x_axis = re.split("-", entries[2])
                x_axis = int(float(x_axis[1]))
                speedplot_list.append([x_axis, temp])
    return average_throughput, max_throughput, actual, ideal, ttr, speedplot_list

#def efficiency_analyzer(std):
#    dump_analysis = []
#    eff_rplot = None
#    for line in std:
#        temp = line.decode("utf-8")
#        if "plot" in temp:
#            eff_rplot = temp
#        else:
#            dump_analysis.append(temp)
#
#    return dump_analysis, eff_rplot
#
#def delay_analyzer(std):
#    delay_analysis = []
#    rtt_rplot = None
#    for line in std:
#        temp = line.decode("utf-8")
#        if "plot" in temp:
#            rtt_rplot = temp
#        else:
#            delay_analysis.append(temp)
#
#    return delay_analysis, rtt_rplot

def prepare_file(filename):
    if os.path.exists(filename):
        os.remove(filename)
    subprocess.call(["sudo", 'touch', filename])
    subprocess.call(["sudo", 'chmod', '666', filename])
    return

def save_tempfile(orig, new):
    subprocess.call(['cp', orig, new])
    return
