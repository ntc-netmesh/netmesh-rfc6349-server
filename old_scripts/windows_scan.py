import os
import re
import subprocess
import time
from utilities import server_utils
import logging
from log_settings import getStreamLogger
from datetime import datetime
from constants import *
from analyzer_process import analyze_efficiency, analyze_buffer_delay

GLOBAL_LOGGER = getStreamLogger()

'''
        Parses iperf3 process stdout data from
        a tempfile and returns the average and
        ideal throughput.
        @PARAMS:
            stdout_data     :   tempfile containing the Iperf3 
                                process stdout
            mtu             :   the maximum transmission unit
            recv_window     :   receiver window size of the server
        
        @RETURN:
            average_thpt    :   average throughput as taken from the
                                tempfile
            ideal_thput     :   calculated theoretical throughput
                                bound
          
''' 
def iperf_parser(stdout_data, mtu, recv_window):
    average_tcp = []
    ideal_tcp = []
    average_thpt = None
    ideal_thput = None
    with open(stdout_data,"r") as f:
        for line in f:
            temp = line
            if "sender" in temp:
                # separate via whitespace
                entries = re.findall(r'\S+',temp)

                #check if test ran in 5s
                timecheck = float(re.split("-",entries[2])[1])
                if timecheck < 5:
                    GLOBAL_LOGGER.error("Windows scan Iperf TCP incomplete")
                    return
                average_thpt = entries[6]
                average_tcp.append(entries[6] + "Mbits/s")
                ideal_thput = (recv_window * 8 / (float(mtu)/1000))/1000
                ideal_tcp.append(str("{0:.2f}".format(round(ideal_thput,2))) + "Mbits/s")
    return average_thpt, ideal_thput

'''
        Starts a windows scan iperf3 client
        subproc instance and returns the subproc object
        @PARAMS:
            server_ip    : ipv4 address of the iperf3 server
            recv_window  : specified receive window size
                           of the iperf3 server.
            o_file       : output file of the process

        @RETURN:
            thpt_process : the throughput measuring subprocess
                            object
'''
def start_window_throughput(server_ip, recv_window, o_file):
    thpt_process = None
    try:
        thpt_process = subprocess.Popen([ "iperf3",
                                          "--client", server_ip,
                                          "--time","5",
                                          "--window", str(recv_window)+"K",
                                          "--format","m",
                                          "--bandwidth","100M"
                                         ], stdout = o_file)
        GLOBAL_LOGGER.debug("WINDOW SCAN THROUGHPUT CLIENT started")
    except:
        try:
            GLOBAL_LOGGER.error("FAILED TO START WINDOW SCAN THROUGHPUT CLIENT")
            thpt_process.kill()
        except:
            pass
        raise
    return thpt_process

'''
        Waits for a windows scan throughput process
        to end and returns its parsed output
        @PARAMS:
            thpt_proc       : throughput process object
            o_file          : output file of thpt_proc
        @RETURNS:
            average_thpt    : average throughput
            ideal_thpt      : calculated theoretical ideal
                              throughput of the performed process
'''
def end_window_throughput(thpt_proc, mtu, recv_window, o_file):
    average_thpt = None
    ideal_thpt = None
    try:
        average_thpt, ideal_thpt = iperf_parser(o_file, mtu, recv_window)
        GLOBAL_LOGGER.debug("thpt done")
    except:
        GLOBAL_LOGGER.error("thpt parsing error")
        raise
    return average_thpt, ideal_thpt

'''
        Starts a "tshark" subproc instance
        and returns the subproc object
        @PARAMS:
            filename        : the filename of the pcapng outfile
        @RETURN:
            tshark_process  : the tshark process object
'''
def start_window_shark(filename):
    tshark_process = None
    try:
        tshark_process = subprocess.Popen(["tshark",
                                           "-w", filename])
        GLOBAL_LOGGER.debug("WINDOW SCAN SHARK started\n waiting 10 seconds for startup")
        time.sleep(10)
    except:
        try:
            GLOBAL_LOGGER.error("FAILED TO START WINDOW SCAN SHARK")
            tshark_process.kill()
        except:
            pass
        raise
    return tshark_process

'''
        Ends a shark process
        @PARAMS:
            shark_proc   : shark process object
'''
def end_window_shark(shark_proc):
    try:
        shark_proc.kill()
    except:
        raise
    return

'''
        Perform a single window scan process
        it is basically normal Iperf3 with custom
        parameters.
        @PARAM:
            filename    :   filename of the tempfile where to
                            dump the process stdout
            client_ip   :   IPv4 address of the client host during
                            the process
            server_ip   :   IPv4 address of the server host during
                            the process
            recv_window :   receiver window size during the process
            mtu         :   maximum transmission unit value
'''
def window_scan(filename, client_ip, server_ip, recv_window, mtu):
    average_thpt = None
    ideal_thpt = None
    window_efficiency = None
    window_rtt = None
    tshark_proc = None
    thpt_proc = None
    try:
        client_utils.file_setter(filename)
        tshark_proc = start_window_shark(filename)
        fname = "tempfiles/"+filename+".temp"
        client_utils.file_setter(fname)
        output_file = open(fname,"r+")
        thpt_proc   = start_window_throughput(server_ip, recv_window, output_file)
        thpt_proc.wait()
        output_file.close()
        average_thpt, ideal_thpt = end_window_throughput\
                (thpt_proc, mtu, recv_window, fname)
        end_window_shark(tshark_proc)
        try:
            GLOBAL_LOGGER.debug("analyzing efficiency ...")
            _,_,window_efficiency = analyze_efficiency(filename, client_ip)
            GLOBAL_LOGGER.debug("analyzing buffer delay ...")
            window_rtt,_ = analyze_buffer_delay(filename, client_ip, server_ip, 1)
        except:
            GLOBAL_LOGGER.error("error doing window_eff/window rtt")
            raise
    except:
        try:
            tshark_proc.kill()
            thpt_proc.kill()
        except:
            pass
        GLOBAL_LOGGER.error("error doing window scan")
        raise
    try:
        tshark_proc.kill()
    except:
        pass
    return average_thpt, ideal_thpt, window_efficiency, window_rtt

'''
        performs multiple instances of the windows scan process
        serially. It is performed 4 times each with varying window
        sizes.
        @PARAMS: (keyword arguments)
            recv_window :   the initial receiver window value of the
                            window scan process. This initial value would
                            serve as the base for the rest of the receiver
                            window values since each successive value is a
                            ratio of this base value.
            client_ip   :   IPv4 of the client host
            server_ip   :   IPv4 of the server host
            mtu         :   maximum transmission unit
'''
def main_window_scan(**kwargs):
    average_tcp = []
    ideal_tcp = []
    neff_plot = []
    nbuffer_plot = []
    window_size = []
    try:
        kwargs["recv_window"] *= 1000.0
        base_window = kwargs["recv_window"]
        for wnd_size_percent in range(1,5):
            x = wnd_size_percent
            kwargs["filename"] = "wnd_"+str(x)+"_percent.pcapng"
            kwargs["recv_window"] = 0.25*x*base_window
            ave, ide, eff, buf = window_scan(**kwargs)
            window_size.append(kwargs["recv_window"])
            average_tcp.append(ave)
            ideal_tcp.append(ide)
            neff_plot.append(eff)
            nbuffer_plot.append(buf)
        GLOBAL_LOGGER.debug("all windows scan test done")
    except:
        GLOBAL_LOGGER.error("all windows scan test error")
        raise
    return window_size, average_tcp, ideal_tcp, neff_plot, nbuffer_plot

