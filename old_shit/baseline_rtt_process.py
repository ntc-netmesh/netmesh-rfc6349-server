import subprocess
import asyncio
import traceback
from utilities import server_utils

'''
        Starts the server for measuring
        baseline rtt, and returns the
        subprocess object
'''
def start_baseline_measure():
    try:
        rtt_process = subprocess.Popen(["python3","udp-ping-server.py"],stdout = subprocess.PIPE)
        print("BASELINE RTT started")
    except:
        print("FAILED TO START BASELINE RTT")
        try:
            rtt_process.kill()
        except:
            pass
        raise
    return rtt_process

'''
        Waits for a baseline_rtt process
        to end and returns its parsed output
        @PARAMS:
            baseline_rtt_proc : rtt measuring process object
'''
def end_baseline_measure(baseline_rtt_proc):
    rtt_results = None
    try:
        baseline_rtt_proc.wait()
        rtt_results = server_utils.parse_udpping(baseline_rtt_proc.stdout)
        print("rtt done")
    except:
        print("mtu parsing error")
        try:
            baseline_rtt_proc.kill()
        except:
            pass
        raise
    return rtt_results

