#!/bin/bash
cd /home/haucs/Desktop/HAUCS

sleep 60
status_resp=$(git status -s --untracked-files=no)

if [ -z "$status_resp" ]
then
    pull_resp=$(git pull origin main -q)
    if [ -z "$pull_resp" ]
    then
        echo "nothing pulled"
    else
        echo "rebooting"
        sleep 5
        sudo reboot
    fi
else
    echo "local changes, won't pull"
fi
echo "running  main script"
/home/haucs/buoy/bin/python3 buoy/main.py