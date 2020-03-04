import subprocess
import asyncio
import traceback
import logging
from scapy.all import *
from constants import *
from utilities import server_utils
from log_settings import getStreamLogger
from datetime import datetime
from constants import *
from tcp_efficiency_analyzer import get_tcp_metrics
from buffer_delay_analyzer import get_average_rtt
#from utilities import server_utils

GLOBAL_LOGGER = getStreamLogger()

'''
        analyzes the tcp efficiency of a
        completed normal test (no window scan)
        @PARAMS:
            filename    : filename of the pcapng file containing 
                          the throughput test traffic
            client_ip   : ipv4 address of the client host
        @RETURN:
            transmitted_bytes     : amount of transmitted bytes throughout
                                    the test duration
            retransmitted_bytes   : amount of retransmitted bytes throughout
                                    the test duration
            tcp_efficiency        : ratio of transmitted to retransmitted
                                    bytes from the test results
'''
def analyze_efficiency(filename, client_ip):
    transmitted_bytes   = 0
    retransmitted_bytes = 0
    tcp_efficiency      = 0
    try:
        GLOBAL_LOGGER.debug("TCP EFFICIENCY ANALYZER started")
        transmitted_bytes, retransmitted_bytes, tcp_efficiency =\
                get_tcp_metrics(filename, client_ip)
    except:
        GLOBAL_LOGGER.error("FAILED TO ANALYZE EFFICIENCY")
        raise
    return transmitted_bytes, retransmitted_bytes, tcp_efficiency

'''
        analyzes the buffer delay of a
        completed normal test (no window scan)
        @PARAMS:
            filename    : filename of the pcapng file containing 
                          the throughput test traffic
            client_ip   : ipv4 address of the client host
            server_ip   : ipv4 address of the server host
            rtt         : value of the baseline RTT
        @RETURN:
            average_rtt           : average computed RTT from the test
            buffer_delay          : percentage increase from ideal to average rtt
'''
def analyze_buffer_delay(filename, client_ip, server_ip, rtt):
    average_rtt  = 0
    buffer_delay = 0
    try:
        GLOBAL_LOGGER.debug("BUFFER DELAY ANALYZER started")
        average_rtt, buffer_delay =\
                get_average_rtt(filename, client_ip, server_ip, rtt)
    except:
        GLOBAL_LOGGER.error("FAILED TO ANALYZE BUFFER DELAY")
        raise
    return average_rtt, buffer_delay

