#!/bin/bash
pulled_nothing="Already up to date."

cd /home/haucs/Desktop/HAUCS

sleep 30
status_resp=$(git status -s --untracked-files=no)

if [[ -z "$status_resp" ]]
then
    pull_resp=$(git pull origin main)
    if [[ "$pull_resp" != *"$pulled_nothing"* ]]
    then
        echo "pulled $pull_resp"
        echo "rebooting"
        sleep 60
        sudo reboot
    else
        echo "pulled nothing, already up to date"
    fi
else
    echo "local changes present, can't pull"
fi
echo "running main script"
/home/haucs/buoy/bin/python3 buoy/main.py