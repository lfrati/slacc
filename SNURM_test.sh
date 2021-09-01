#!/bin/bash

echo "Sending jobs."
python SNURM_client.py "add" --cmd "python gpu_check.py" --env "deep"
python SNURM_client.py "add" --cmd "ping -c 4 www.google.com"
RET=$(python SNURM_client.py "add" --cmd "ping -c 6 www.google.com")
echo "$RET"
TOCANCEL=$(echo "$RET" | jq '.id') # get if from json response
python SNURM_client.py "add" --cmd "ping -c 5 www.google.com"
echo "Jobs sent."
sleep 0.5
python SNURM_client.py "list"
echo "Cancelling $TOCANCEL."
python SNURM_client.py "cancel" --id "$TOCANCEL"
python SNURM_client.py "list"
echo "Killing running job."
python SNURM_client.py "kill"
python SNURM_client.py "list"
