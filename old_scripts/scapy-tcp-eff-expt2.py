from scapy.all import *
import sys
import time

def get_sec(time_str):
    """Get Seconds from time."""
    h, m, s = time_str.split(':')
    #return int(h) * 3600 + int(m) * 60 + int(s)
    return int(s)

if len(sys.argv) != 3:
	#print ("Usage: pringcomputer <scapyfile in pcap>\n  eg: pingcomputer pinganalysis2.pcap")
    sys.exit(1)

packets = rdpcap(sys.argv[1])
ip_addr = sys.argv[2] #src ip

# Let's iterate through every packet
packettotal = 0
for packet in packets:
#	print(packet)
	packettotal = packettotal + 1	
#print "There are %d packets in total" %packettotal

count = 0

tcp_packetseq = []
tcp_packetsize =[]
tcp_packet = []

while (count < packettotal):
	#print ('The current packet being processed is', count)
	pkt1=packets[count]

	if ((TCP in pkt1)) and (pkt1[IP].src == ip_addr):
		tcp_packet.append(pkt1)
		tcp_packetseq.append(pkt1[TCP].seq)
		tcp_packetsize.append(len(pkt1))
	count = count + 1

seen = set()
retransmitted_bytes = 0

#variables for plot
eff_plot_ctr = 1
eff_plot = []
curr_retrans = 0
curr_trans = 0
curr_sec = -1

for index, x in enumerate(tcp_packetseq):
	tcp_datalen = tcp_packet[index][IP].len -(20+(tcp_packet[index][TCP].dataofs*4))

	#scan for transmitted and retransmitted packets
	if (x not in seen) and tcp_datalen>0:
		seen.add(x)
		curr_trans += tcp_packetsize[index]

	elif tcp_datalen>0:
		#print(tcp[index][TCP].chksum)
		retransmitted_bytes += tcp_packetsize[index]
		curr_retrans += tcp_packetsize[index]

	#compare current time for plotting
	processed_time = get_sec(time.strftime('%H:%M:%S', time.localtime(tcp_packet[index].time/1000)))
	#print(processed_time)
	if curr_sec == -1:
		curr_sec = processed_time

	#reset if second has passed
	if processed_time != curr_sec:
		eff = (curr_trans - curr_retrans) / curr_trans * 100
		eff_plot.append([eff_plot_ctr, eff])
		eff_plot_ctr += 1
		curr_trans = 0
		curr_retrans = 0
		curr_sec = processed_time


transmitted_bytes = sum(tcp_packetsize)

print("Transmitted Bytes: " + str(transmitted_bytes))
print("Retransmitted Bytes: " + str(retransmitted_bytes))
tcp_eff = (transmitted_bytes-retransmitted_bytes)/transmitted_bytes*100
print("TCP Efficiency: " + str("{0:.2f}".format(round(tcp_eff,2))))
print("eff_plot:" + str(eff_plot))
