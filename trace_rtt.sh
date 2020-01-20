#!/bin/bash

tcptraceout=$(tcptrace -rl $1 | grep -A 51 ":$2") 
rttaverage=$(echo "$tcptraceout" | grep "avg:" | awk '{ print $3}') 
transmitbytes=$(echo "$tcptraceout" | grep "actual data bytes:" | awk '{ print  $4}')
rexmtbytes=$(echo "$tcptraceout" | grep "rexmt data bytes:" | awk '{ print  $4}')
echo "$rttaverage"
echo "$transmitbytes"
echo "$rexmtbytes"
