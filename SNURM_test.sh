#!/bin/bash

echo "Sending jobs."
python SNURM/client.py "add" --cmd "python gpu_check.py" --env "deep"
python SNURM/client.py "add" --cmd "ping -c 4 www.google.com"
RET=$(python SNURM/client.py "add" --cmd "ping -c 6 www.google.com")
echo "$RET"
TOCANCEL=$(echo "$RET" | jq '.id') # get if from json response
python SNURM/client.py "add" --cmd "ping -c 5 www.google.com"
echo "Jobs sent."
sleep 0.5
python SNURM/client.py "list"
echo "Cancelling $TOCANCEL."
python SNURM/client.py "cancel" --id "$TOCANCEL"
python SNURM/client.py "list"
echo "Killing running job."
python SNURM/client.py "kill"
python SNURM/client.py "list"
