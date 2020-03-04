#!/bin/bash

# Params
# $1 server_ip 
# $2 client_ip
# $3 rtt service port number
# $4 MSS
# $5 temp file name
# $6 pcap file name
SERVER_IP=$1
CLIENT_IP=$2
PORT_NO=$3
MSS=$4
TEMPFILE=$5
PCAP_FILE=$6

# compile c server
gcc -o reverse_server reverse_servertcp.c;

# run shark
tshark -w $PCAP_FILE -a duration:200 &
sharkpid=$!
sleep 5;

# run 
./reverse_server $PORT_NO $MSS &
serverpid=$!

# analyzer script
python3 rtt_analyzer.py $PCAP_FILE $CLIENT_IP $SERVER_IP $(($MSS-12)) $TEMPFILE;
