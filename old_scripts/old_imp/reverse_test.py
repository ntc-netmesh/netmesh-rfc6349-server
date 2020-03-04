#!/usr/bin/env python3

import sys, os, subprocess
import asyncio, websockets
import traceback
from constants import *
from mtu_process import *
from rtt_process import *
from baseline_bandwidth_process import *
from throughput_process import *

'''
    REMOTE TO LOCAL PROTOCOL HANDLER

        The remote to local protocol hosts each metric handler
        for Maximum Transmission Unit, Round Trip Time, 
        Baseline Bandwidth, and Throughput as websocket servers
        with their own respective ports defined from the constants file.

        The operations of these handlers are independent of both each other
        and with the client. It is up to the client to choose when to contact
        each handler for its service, and to provide  the necessary parameters.
        
        The parameters that are expected to be passed by the client are supposedly
        values from other metric handlers, but the metric handlers instead
        treat the parameters as mere parameters without any connection from
        the other metric handlers, meaning they would simply use the values
        provided by the client blindly and would raise respective errors in case
        of invalid parameter values.
'''
def remote_to_local_protocol(): 

    mtu_handler        = websockets.serve(measure_mtu,        MAIN_SERVER_IP, MTU_HANDLER_PORT     , ping_timeout=600)
    rtt_handler        = websockets.serve(measure_rtt,        MAIN_SERVER_IP, RTT_HANDLER_PORT     , ping_timeout=600)
    bandwidth_handler  = websockets.serve(measure_bandwidth,  MAIN_SERVER_IP, BB_HANDLER_PORT      , ping_timeout=600)
    throughput_handler = websockets.serve(measure_throughput, MAIN_SERVER_IP, THPT_HANDLER_PORT    , ping_timeout=600)
    all_grp = asyncio.gather(mtu_handler, rtt_handler, bandwidth_handler, throughput_handler)
    asyncio.get_event_loop().run_until_complete(all_grp)
    asyncio.get_event_loop().run_forever()


'''
    Same functionality as the remote_to_local_protocol function but instead of
        adding the tasks to the main loop, it returns the task objects as a list
'''
def retrieve_reverse_mode_handler(server_url=MAIN_SERVER_IP):
    mtu_handler        = websockets.serve(measure_mtu,        server_url, MTU_HANDLER_PORT     , ping_timeout=600)
    rtt_handler        = websockets.serve(measure_rtt,        server_url, RTT_HANDLER_PORT     , ping_timeout=600)
    bandwidth_handler  = websockets.serve(measure_bandwidth,  server_url, BB_HANDLER_PORT      , ping_timeout=600)
    throughput_handler = websockets.serve(measure_throughput, server_url, THPT_HANDLER_PORT    , ping_timeout=600)
    return [mtu_handler, rtt_handler, bandwidth_handler, throughput_handler]

if __name__ == "__main__":
    remote_to_local_protocol()
