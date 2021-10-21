#!/bin/bash
PORT=8006
UP_TRACE="./trace/12Mbps.trace"
#DOWN_TRACE="./trace/ATT-LTE-driving.down"
DOWN_TRACE="./trace/12Mbps.trace"
LOG_DIR="./log/"
./dist/server/dash_server.py -p $PORT -s 0.0.0.0 > ${LOG_DIR}/server.log &
MM_CMD="mm-delay 30 mm-link ${UP_TRACE} ${DOWN_TRACE} --downlink-queue=droptail --downlink-queue-args=\"packets=250,log_file=/dev/null,\""
$MM_CMD ./scripts/start_client.sh $PORT "dist/sample_mpd/BigBuckBunny.mpd" "netflix" ${LOG_DIR}/client.log

