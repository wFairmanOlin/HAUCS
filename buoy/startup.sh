#!/bin/bash
pulled_something="Unpacking objects"

cd /home/haucs/Desktop/HAUCS

sleep 30
status_resp=$(git status -s --untracked-files=no)

# if no files have been changed
if [[ -z "$status_resp" ]]
then
    pull_resp=$(git pull origin main)
    #if local repo is updated to remote
    if [[ "$pull_resp" == *"$pulled_something"* ]]
    then
        echo "succesfully updated"
        echo "$pull_resp"
    else
        echo "pulled nothing, already up to date"
    fi
else
    echo "local changes present, can't pull"
fi
echo "running main script"
/home/haucs/buoy/bin/python3 buoy/main.py