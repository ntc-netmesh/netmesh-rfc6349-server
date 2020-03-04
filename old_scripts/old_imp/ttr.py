#runs on iperf3

import subprocess
import re

#server = input("Input server IP address: ")

#p = subprocess.Popen(["iperf3","-c",server],stdout=subprocess.PIPE)
p = subprocess.Popen(["iperf3","-c","192.168.1.6"],stdout=subprocess.PIPE)

for line in p.stdout:
    temp = line.decode("utf-8")
    if "receiver" in temp:
        entries = re.findall(r'\S+',temp)
        print (entries)
        
        #actual = float(entries[4]) * 8 / float(entries[6])
        temp2 = re.split("-",entries[2])
        actual = float(temp2[1])
        print("actual:" + str(actual))
        
        max_throughput = (1500-40) * 8 * 8127 /1000000 #1500 MTU 8127 FPS based on connection type
        print("max throughput: " + str(max_throughput))
        
        ideal = float(entries[4]) * 8 / max_throughput
        print("ideal:" + str(ideal))
        
        ttr = actual / ideal
        print("TCP TTR:" + str(ttr))
