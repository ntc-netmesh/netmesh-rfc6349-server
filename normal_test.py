#!/usr/bin/env python3

import sys, os, subprocess
import asyncio, websockets
import traceback
from constants import *

'''

    LOCAL TO REMOTE PROTOCOL HANDLER
    
    serial steps are as follows:
        
        client                                              server
                          < CONNECTION_ESTABLISHED >
                    ---- send arbitrary start message >>>>  <recv()>
        <recv()>          < SERVER_PROCESSING_TIME >        <start_udp_server>
        <recv()>          < SERVER_PROCESSING_TIME >        <start_iperf_server>
        <recv()>    <<<<  send servers are up signal  ----  <recv()>
        <process>         < CLIENT_PROCESSING_TIME >         <recv()>
        <done>      ----      send finish message     >>>>  <recv()>
        <done>            < SERVER_PROCESSING_TIME >        <kill_udp_server>
        <done>            < SERVER_PROCESSING_TIME >        <kill_iperf_server>
                           < CONNECTION_TEARDOWN >


'''
async def local_to_remote_protocol(websocket, path):

    try:
        state = await websocket.recv()
        udp_server = None
        iperf_server = None
        try:
            rtt_compile = subprocess.run(["gcc", "-o","servertcp","servertcp.c"])
            rtt_server = subprocess.Popen(["./servertcp",str(RTT_MEASURE_PORT)])
        except:
            traceback.print_exc()
            await websocket.close()
        try:
            udp_server = subprocess.Popen(["python3", "udp_server.py", str(UDP_SERVER_PORT)])
        except:
            traceback.print_exc()
            await websocket.close()
        try:
            iperf_server = subprocess.Popen(["iperf3", "-s","--port", str(THPT_NORMAL_PORT)])
        except:
            traceback.print_exc()
            await websocket.close()
                                             
        await websocket.send("servers started")
        await websocket.recv()

        try:
            iperf_server.kill()
            udp_server.kill()
            rtt_server.kill()
        except:
            traceback.print_exc()
            pass
    except:
        pass

'''
    Returns a websockets.serve task for hosting the normal_mode handler as an application bound to a port
'''
def retrieve_normal_mode_handler():
    normal_test_handler = websockets.serve(local_to_remote_protocol, MAIN_SERVER_IP, LOCAL_TO_REMOTE_PROTOCOL_PORT , ping_timeout=600)
    return [normal_test_handler]

if __name__ == "__main__":
	normal_test_handler = websockets.serve(local_to_remote_protocol, MAIN_SERVER_IP, LOCAL_TO_REMOTE_PROTOCOL_PORT , ping_timeout=600)
	asyncio.get_event_loop().run_until_complete(normal_test_handler)
	asyncio.get_event_loop().run_forever()
