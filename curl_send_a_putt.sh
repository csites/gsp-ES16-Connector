#!/bin/bash
# Simulate a putt, to an Allexx style putt server

curl -H 'Content-Type: application/json' \
     -d '{ "ballData":{"BallSpeed": "4.8", "TotalSpin":500, "LaunchDirection":"0.1"}}' \
     -X POST \
     http://127.0.0.1:8888
