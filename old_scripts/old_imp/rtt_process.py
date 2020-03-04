import subprocess
import asyncio
import traceback
import logging
import json
from log_settings import getStreamLogger
from datetime import datetime
from constants import *
from utilities import server_utils

GLOBAL_LOGGER = getStreamLogger()

'''
        Starts the process for measuring
        baseline rtt, and returns the
        subprocess object
        @PARAMS:
            server_ip   : the ipv4 address of the server
                          whose RTT would be measured from
            o_file      : output file for the RTT value
'''
def start_baseline_measure(server_ip, o_file):
    rtt_process = None
    try:
        rtt_process = subprocess.Popen(["python3","udp-ping-server.py"],
                stdout = o_file)
        GLOBAL_LOGGER.debug("BASELINE RTT started")
    except:
        GLOBAL_LOGGER.error("FAILED TO START BASELINE RTT")
        try:
            rtt_process.kill()
        except:
            pass
        raise
    return rtt_process

'''
    Parses an output file where the Round Trip Time value is
        outputted by the rtt process
        @PARAMS:
            o_file            : output filename of the RTT value
        @RETURN:
            rtt_results       : Round Trip Time value
'''
def end_baseline_measure(o_file):
    rtt_results = None
    try:
        rtt_results = server_utils.parse_ping(o_file)
        GLOBAL_LOGGER.debug("rtt done")
    except:
        GLOBAL_LOGGER.error("rtt parsing error")
        raise
    return rtt_results

'''
        Wraps the entire rtt attainment process
            and sends a json string value of the results
            to the client
        @PARAMS:
                websocket   :   websocket object
                path        :
'''
async def measure_rtt(websocket, path):
    server_ip = await websocket.recv()
    rtt = None
    fname = "tempfiles/reverse_mode/rtt_temp"
    rtt_proc = None
    try:
        output_file = open(fname,"w+")
        rtt_proc = start_baseline_measure(server_ip, output_file)
        await websocket.send("rtt started")
        rtt_proc.wait(timeout=60)
        output_file.close()
        rtt = end_baseline_measure(fname)
    except:
        print("rtt failed")
        traceback.print_exc()
        try:
            rtt_proc.kill()
        except:
            pass
    try:
        ret_dict = {"RTT":rtt}
        await websocket.send(json.dumps(ret_dict))
    except:
        await websocket.close()
    # done
