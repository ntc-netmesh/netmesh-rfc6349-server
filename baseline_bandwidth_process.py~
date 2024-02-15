import subprocess
import asyncio
import traceback
import json
from log_settings import getStreamLogger
from datetime import datetime
from constants import *
from utilities import server_utils
from math import floor, ceil

'''
        Calculates the parameters to be used for the
        throughput testing. These values are derived
        via formulas.
        @PARAMS:
            bdp          : Bandwidth Delay Product
            mtu          : Maximum Transmission Unit
        @RETURN:
            mss          : Maximum segment size
            rwnd         : receive window size
            connections  : number of parallel connections
'''
def generate_bb_metrics(cir, mtu, rtt):
    try:
        # ASSUME CIR IS ALREADY MULTIPLIEDD
        bb_result = int(cir)
        bdp_result = floor( ((bb_result*(10**6))/8) * (float(rtt)/(10**3)) )
        actual_cir = floor( ((int(cir)*(10**6))/8) * (float(rtt)/(10**3)) )

        mss = mtu - 40
        x = 1
        rwnd = x*mss
        while(rwnd < bdp):
            x += 1
            rwnd = x*mss

        connections = ceil( rwnd / (64*1024)  )
        return mss, rwnd, connections
    except:
        GLOBAL_LOGGER.error("RWND calculation error")
        raise
    return

'''
        Wraps the entire bb attainment process
            and sends the json string of the results
            to the client
        @PARAMS:
                websocket   :   websocket object
                path        :
'''
async def measure_bandwidth(websocket, path):
    metric_params = await websocket.recv()
    bb = None
    bdp = None
    mss = None
    rwnd = None
    conn = None
    actual_rwnd = None
    fname = "tempfiles/reverse_mode/bb_temp"
    bb_proc = None
    try:
        # PARAMS
        cir = None
        mtu = None
        rtt = None
        client_params = json.loads(metric_params)
        try:
            cir = client_params["CIR"]
            mtu = client_params["MTU"]
            rtt = client_params["RTT"]
        except:
            pass

        bb, bdp, mss, rwnd, conn, actual_rwnd =\
                generate_bb_metrics()
    except:
        print("bb failed")
        traceback.print_exc()

    try:
        ret_dict = {"BB":bb, "BDP":bdp, "RWND":rwnd}
        await websocket.send(json.dumps(ret_dict))
    except:
        await websocket.close()
    # done
