import logging

'''

    returns a formatted logger object

'''

def customLogger():
    logging.basicConfig(level=logging.DEBUG,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%m-%d %H:%M',
    filename='/tmp/netmesh_server.log',
    filemode='w',
    force=True)

    console = logging.StreamHandler()
    console.setLevel(
            logging.INFO
            )
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.getLogger('websockets.protocol').setLevel(logging.ERROR)
    logging.getLogger('websockets.server').setLevel(logging.ERROR)
    return logging

#def getStreamLogger():
#    formatter = logging.Formatter("%(asctime)s   :   %(levelname)s\n\n%(message)s\n\n")
#    logger = logging.getLogger()
#    logger.setLevel(logging.ERROR)
#    ch = logging.StreamHandler()
#    ch.setLevel(logging.ERROR)
#    ch.setFormatter(formatter)
#    logger.addHandler(ch)
#    return logger
#
#def getFileLogger(filename):
#    formatter = logging.Formatter("%(asctime)s   :   %(levelname)s\n\n%(message)s\n\n")
#    logger = logging.getLogger()
#    logger.setLevel(logging.DEBUG)
#    ch = logging.FileHandler(filename)
#    ch.setLevel(logging.DEBUG)
#    ch.setFormatter(formatter)
#    logger.addHandler(ch)
#    return logger

