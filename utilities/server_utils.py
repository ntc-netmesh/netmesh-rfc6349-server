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
            if "avg" in line:
                ping = line.split(" ")[2]
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
        std                    :    filename of the output file
        mtu                    :    Maximum Transmission Unit value
        rtt                    :    Baseline Round Trip Time

   @RETURN:
        average_throughput     :    average TCP throughput
        max_throughput         :    ideal TCP throughput
        actual                 :    average transfer time
        ideal                  :    ideal transfer time
        ttr                    :    transfer time ratio between
                                      actual and ideal
        speedplot_list         :    N/A
'''
def parse_shark(std, recv_window, rtt):
    speed_plot = []
    ave_tcp = None
    ave_tt = None
    ide_tt = None
    tcp_ttr = None
    ide_tcp = (float(recv_window) * 8 / (float(rtt)/1000))/(10**6)
    offset = 0
    multiplier = 1
    with open(std,"r") as f:
        for line in f:
            temp = line
            if "sender" in temp:
                entries = re.findall(r'\S+',temp)
                if "SUM" in temp:
                    offset = 1
                try:
                    ave_tcp = float(entries[6-offset])
                    # average transfer time
                    temp2 = re.split("-",entries[2-offset])
                    ave_tt = float(temp2[1])
                    if "KBytes" in entries[5-offset]:
                        multiplier = 1000

                    ide_tt = ( float(entries[4-offset]) * 8 * multiplier ) / ( ide_tcp )
                    tcp_ttr = ide_tt / ave_tt
                except:
                    pass
    return ave_tcp, ide_tcp, ave_tt, ide_tt, tcp_ttr, speed_plot

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
