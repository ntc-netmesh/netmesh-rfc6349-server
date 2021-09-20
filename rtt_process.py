import subprocess
import asyncio
import logging
import traceback
import logging
import json
from datetime import datetime
from constants import *
from utilities import server_utils
import sys
import rtt_analyzer

logger = logging.getLogger(__name__)
'''
        Starts the process for measuring
        baseline rtt, and returns the
        subprocess object
        @PARAMS:
            server_ip   : the ipv4 address of the server
                          whose RTT would be measured from
            pcap_name   : pcap trace file name where the RTT process
                            generated traffic would be saved
            mss         : Maximum segment size
'''
def start_baseline_measure(server_ip, pcap_name, mss):
    rtt_process = None
    try:
        server_utils.prepare_file(pcap_name)
        subprocess.run(["gcc","-o","reverse_rtt","reverse_servertcp.c"])
        rtt_process   = subprocess.Popen(["./reverse_rtt", str(RTT_MEASURE_PORT), str(mss)],
                stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        shark_process = subprocess.Popen(["tshark",
                                          # possible interface ?
                                          "-i", "eno2",
                                          "-w", pcap_name,
                                          "-a", "duration:20"])
        logger.info("BASELINE RTT started")
    except:
        logger.error("FAILED TO START BASELINE RTT")
        try:
            rtt_process.kill()
        except:
            raise
        raise
    return rtt_process, shark_process

'''
    Parses an output file where the Round Trip Time value is
        outputted by the rtt process
        @PARAMS:
            o_file            : output filename of the RTT value
            pcap_fname        : output pcap file of the RTT traffic
        @RETURN:
            rtt_results       : Round Trip Time value
'''
def end_baseline_measure(o_file, pcap_fname, client_ip, server_ip, mss):
    rtt_results = None
    try:
        outfile = open(o_file,"w+")
        logger.info("running rtt_analyzer.py")
        minr, maxr, avgr = rtt_analyzer.get_average_rtt(
                        pcap_fname,
                        client_ip,
                        server_ip,
                        str(int(mss)-12),
                        str(RTT_MEASURE_PORT)
                )
        logger.info('Min: %s, Max: %s, Avg: %s', minr, maxr, avgr)
        #subprocess.run(["python3",
        #                "rtt_analyzer.py",
        #                pcap_fname,
        #                client_ip,
        #                server_ip,
        #                str(int(mss)-12),
        #                o_file,
        #                str(RTT_MEASURE_PORT),
        #                ], stdout = subprocess.PIPE, stderr = subprocess.PIPE )

        rtt_results = server_utils.parse_ping(o_file)
        logger.info("rtt done")
    except:
        logger.error("rtt parsing error")
        raise
    logger.info('rtt_results: %s', rtt_results)
    if rtt_results:
        return rtt_results
    return 1

'''
        Wraps the entire rtt attainment process
            and sends a json string value of the results
            to the client
        @PARAMS:
                websocket   :   websocket object
                path        :
'''
async def measure_rtt(websocket, path):
    params = await websocket.recv()
    logger.info("Received message: %s", params)
    rtt = None
    fname = "/tmp/reverse_mode_rtt_temp"
    pcap_name = "/tmp/reverse_mode_rtt.pcap"
    rtt_proc = None
    shark_proc = None
    try:
        server_ip = websocket.local_address[0] 
        client_ip = websocket.remote_address[0]
        client_params = json.loads(params)
        mss = None
        try:
            mss = client_params["MSS"]
        except:
            pass
        rtt_proc, shark_proc = start_baseline_measure(server_ip, pcap_name, mss)
        await websocket.send("rtt started")
        logger.info("Sent Message: rtt started")
        shark_proc.wait(timeout=80)
        try:
            rtt_proc.kill()
            shark_proc.kill()
        except:
            pass
        logger.info('client IP: %s', client_ip)
        logger.info('server IP: %s', server_ip)
        rtt = end_baseline_measure(fname, pcap_name, client_ip, server_ip, mss)
    except:
        logger.error("rtt failed")
        try:
            rtt_proc.kill()
            shark_proc.kill()
        except:
            raise
        raise
    try:
        ret_dict = {"RTT":rtt}
        await websocket.send(json.dumps(ret_dict))
    except:
        await websocket.close()
        raise
    # done
