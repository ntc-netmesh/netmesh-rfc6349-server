import os
import shutil

def move_pcap(region, serial):
	i=0
	while os.path.exists("pcap-files/" + region + "-" + serial + "-%s.pcapng" % i):
		i+=1

	filename = region  + "-" + serial + "-" + str(i) + ".pcapng"
	shutil.move("testresults.pcapng", "pcap-files/" + filename)

	return filename