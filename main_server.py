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
            if len(CURRENTLY_SERVING) == 0:
                current_hash = await queue.get() #FIFO OUT
                if current_hash != previous_hash:
                    previous_hash = current_hash
                else:
                    previous_hash = None

                if current_hash in QUEUE_PLACEMENT:
                    CURRENTLY_SERVING[current_hash] = "CURRENT_TURN"
                    print("CURRENTLY SERVING ",CURRENTLY_SERVING)
                    while (current_hash in CURRENTLY_SERVING):
                        await asyncio.sleep(1)

        except:
            traceback.print_exc()


'''
'''
def get_queue_placement(client_hash):
    try:
        return QUEUE_PLACEMENT.index(client_hash)
    except:
        return 0

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
            print("number of clients: ",len(QUEUE_PLACEMENT))
            await MASTER_QUEUE.put(client_hash) #FIFO IN
            print("HASH IN QUEUE")
            await asyncio.sleep(5)

        # await for turn
        while not client_hash in CURRENTLY_SERVING:
            hash_index = get_queue_placement(client_hash)
            await websocket.send(str(hash_index))
            #await asyncio.sleep(1)

        # signal the client's turn
        await websocket.send(CURRENTLY_SERVING[client_hash])
        # client does the test
<<<<<<< HEAD
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
=======
        await websocket.recv()
>>>>>>> 56876383ac53573e130cac3251fee8f617780cc4
        await websocket.send("serve done")
        del CURRENTLY_SERVING[client_hash]
        QUEUE_PLACEMENT.remove(client_hash)
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
            
