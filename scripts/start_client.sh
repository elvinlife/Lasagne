#!/bin/bash
python ./dist/client/dash_client.py -m http://${MAHIMAHI_BASE}:$1/$2 -p $3 > $4

