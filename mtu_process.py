import subprocess
import asyncio
import traceback
import json
from log_settings import getStreamLogger
from datetime import datetime
from constants import *
from utilities import server_utils

'''
        Starts a "plpmtu_reverse" subproc instance
        and returns the subproc object
        @PARAMS:
            ofile           :   the output file for the reverse
                                mtu function
        @RETURN:
            plpmtu_process  :   process object of the reverse mtu
                                measurer
'''
def start_mtu_reverse(ofile):
    try:
        plpmtu_process = subprocess.Popen(["sudo","./plpmtu_reverse"],stdout = ofile, stderr = ofile)
        print("PLPMTU REVERSE started")
    except:
        print("FAILED TO START PLPMTU REVERSE")
        try:
            plpmtu_process.kill()
        except:
            pass
        raise
    return plpmtu_process

'''
    Parses mtu subprocess output from a file
        @PARAMS:
            ofile       :   the output filename of the reverse mtu process
        @RETURN:
            mtu_results :   mtu value
'''
def end_mtu_reverse(ofile):
    mtu_results = None
    try:
        mtu_results = server_utils.parse_mtu(ofile)
        print("mtu done")
    except:
        print("mtu parsing error")
        raise
    return mtu_results

'''
    wrapper for the entire reverse mtu measurement process
        and returns the json string value of the
        Maximum Transmission Unit
    @PARAMS:
            websocket   :   websocket object
            path        :
'''
async def measure_mtu(websocket, path):
    go_signal = await websocket.recv()
    print(go_signal)
    mtu = None
    filename = "tempfiles/reverse_mode/mtu_reverse_temp"
    mtu_reverse_proc = None
    try:
        ofile = open(filename, "w+")
        mtu_reverse_proc = start_mtu_reverse(ofile)
        await websocket.send("plpmtu started")
        mtu_reverse_proc.wait(timeout=20)
        ofile.close()
        mtu = end_mtu_reverse(filename)
    except:
        print("plpmtu failed")
        traceback.print_exc()
        try:
            mtu_reverse_proc.kill()
        except:
            pass
    try:
        ret_dict = {"MTU":mtu}
        await websocket.send(json.dumps(ret_dict))
    except:
        await websocket.close()
    # done

