import asyncio
import websockets
import random
import json
from datetime import datetime
import traceback
import normal_test, reverse_test
from constants import *

# results provider queue
QUEUE_PLACEMENT = []
MASTER_QUEUE = asyncio.Queue()
CURRENTLY_SERVING = {}

'''
    This function is responsible for exhausting the queue
    and notifying the queue_handler via a the shared resource
    CURRENTLY_SERVING
'''
async def queue_consumer(queue):
    current_hash = None
    previous_hash = None
    while True:
        try:
            current_hash = await queue.get() #FIFO OUT
            print(previous_hash,"\n")
            print(CURRENTLY_SERVING,"\n")
            while (previous_hash in CURRENTLY_SERVING):
                await asyncio.sleep(1)
            CURRENTLY_SERVING[current_hash] = "CURRENT_TURN"
            if previous_hash == current_hash:
                print("DELETED ",current_hash)
                del CURRENTLY_SERVING[current_hash]
                previous_hash = None
                current_hash = None

            else:
                previous_hash = current_hash
        except:
            traceback.print_exc()


'''
'''
def get_queue_placement(client_hash):
    try:
        return str(QUEUE_PLACEMENT.index(client_hash))
    except:
        return


'''
    This server function should be the first contact point of the client
    before executing any protocol mode (normal or reverse), as this function
    indicates whether it is the client's turn in a queue
'''
async def queue_handler(websocket, path):
    client_hash = None
    queue_log_file = "tempfiles/queue/queue_log"
    try:
        client_hash = await websocket.recv()
        if client_hash not in QUEUE_PLACEMENT:
            print("HASH NOT IN QP")
            QUEUE_PLACEMENT.append(client_hash)
            await MASTER_QUEUE.put(client_hash) #FIFO IN
            await asyncio.sleep(5)
        else:
            pass
        # await for turn
        while not client_hash in CURRENTLY_SERVING:
            hash_index = get_queue_placement(client_hash)
            if hash_index == "0":
                CURRENTLY_SERVING[client_hash] = "CURRENT_TURN"
                break

            await websocket.send(hash_index)
            #await asyncio.sleep(1)

        # signal the client's turn
        await websocket.send(CURRENTLY_SERVING[client_hash])
        # client does the test
        while True:
            try:
                print("waiting....")
                await websocket.recv()
                break
            except:
                traceback.print_exc()
        try:
            del CURRENTLY_SERVING[client_hash]
            QUEUE_PLACEMENT.remove(client_hash)
        except:
            pass
        await websocket.send("serve done")
        #await websocket.send("serve done : "+str(SHARED_RESULTS.pop(hashtxt)))
    except:
        try:
            if client_hash in CURRENTLY_SERVING:
                del CURRENTLY_SERVING[client_hash]
            if client_hash in QUEUE_PLACEMENT:
                QUEUE_PLACEMENT.remove(client_hash)
            #time_str = datetime.today().strftime('%Y-%m-%d-%H-%M-%S : ') 
            logf = open(queue_log_file,"a+")
            traceback.print_exc(file=logf)
            logf.close()
        except:
            pass
        # add to error logs

'''
    retrieves the coroutines for serving the queueing functionality
'''
def retrieve_queueing_services():
    queue_server = websockets.serve(queue_handler, MAIN_SERVER_IP, QUEUE_PORT, ping_timeout=600)
    consumer = queue_consumer(MASTER_QUEUE)
    return [queue_server, consumer]

'''
    retrieves the coroutines for serving the queueing functionality
        in addition to the applications for serving the normal and reverse mode
'''
def retrieve_services():
    queueing_handler = retrieve_queueing_services()
    normal_test_handler = normal_test.retrieve_normal_mode_handler()
    reverse_test_handler = reverse_test.retrieve_reverse_mode_handler()
    return queueing_handler + normal_test_handler + reverse_test_handler

'''
    Starts all mode services and queueing services into the main event loop
'''
def start_server():
    services = retrieve_services()
    all_grp = asyncio.gather(*services)
    asyncio.get_event_loop().run_until_complete(all_grp)
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    start_server()
            
