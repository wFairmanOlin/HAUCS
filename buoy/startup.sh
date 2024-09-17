#!/bin/bash

echo "Hello World!"
cd ~/Desktop/HAUCS

status_resp=$(git status -s --untracked-files=no)

if [ -z "$status_resp" ]
then
    pull_resp=$(git pull origin main -q)
    if [-z "$pull_resp"]
    then
        echo "nothing pulled"
    else
        echo "rebooting"
        sleep 5
        echo "$pull_resp"
    fi
else
    echo "false, local changes"
fi
