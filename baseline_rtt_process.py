import subprocess
import asyncio
import traceback
import json
from log_settings import getStreamLogger
from datetime import datetime
from constants import *
from utilities import server_utils

'''
        Starts a "iperf3 -s" subproc instance
        and returns the subproc object
        @PARAMS:
            ofile   :   the output file to pipe the 
                        subprocess's output on
'''
def start_bandwidth_measure(ofile):
    try:
        bb_process = subprocess.Popen(["iperf3", "-s",
                                      "--port", str(BB_IPERF_PORT)
                                      ],stdout = ofile)
        print("BB server started")
    except:
        print("FAILED TO START BB SERVER")
        try:
            bb_process.kill()
        except:
            pass
        raise
    return bb_process

'''
    Parses bandwidth metrics from an output file and returns the results
        @PARAMS:
            ofile           : the output file of the bb process
            baseline_rtt    : baseline rtt value 
        @RETURN:
            bb              : baseline bandwidth
            bdp             : bandwidth delay product
            rwnd            : receive window size
'''
def end_bandwidth_measure(ofile, baseline_rtt):
    rwnd = None
    bb_result = None
    bdp_result = None
    try:
        bb_result, bdp_result, rwnd = server_utils.parse_iperf(ofile, baseline_rtt)
        print("bb done")
    except:
        print("bb parsing error")
        raise
    return bb_result, bdp_result, rwnd

'''
        Wraps the entire bb attainment process
            and sends the json string of the results
            to the client
        @PARAMS:
                websocket   :   websocket object
                path        :
'''
async def measure_bandwidth(websocket, path):
    baseline_rtt = await websocket.recv()
    bb = None
    bdp = None
    rwnd = None
    fname = "tempfiles/reverse_mode/bb_temp"
    bb_proc = None
    try:
        output_file = open(fname,"w+")
        bb_proc = start_bandwidth_measure(output_file)
        await websocket.send("bb started")
        stop_signal = await websocket.recv()
        bb_proc.kill()
        output_file.close()
        bb, bdp, rwnd = end_bandwidth_measure(fname, baseline_rtt)
    except:
        print("bb failed")
        traceback.print_exc()
        try:
            bb_proc.kill()
        except:
            pass
    try:
        ret_dict = {"BB":bb, "BDP":bdp, "RWND":rwnd}
        await websocket.send(json.dumps(ret_dict))
    except:
        await websocket.close()
    # done
