This document outlines the software setup and provides useful information for the (not a) buoy. 

# Setup
## WiFi
1. Select FAU wifi
1. Open browser and go to talon.fau.edu
1. type `ifconfig` in terminal to get wlan0 mac address
1. reboot

## System Update
1. `Sudo apt update`
2. `Sudo apt full-upgrade`
3. `Sudo apt install rpi-connect`

## Virtual Environment
1. `python3 -m venv buoy`
2. `source buoy/bin/activate`

## Github
1. `cd Desktop/`
2. `git clone https://github.com/wFairmanOlin/HAUCS.git`

## Python Libraries
1. `cd Desktop/HAUCS/buoy`
2. `pip3 install -r requirements.txt`

## Servo Setup
1. sudo systemctl enable pigpiod

## Raspberry Pi Configuration
1. `sudo raspi-config`
    - enable I2C interface
2. `sudo rpi-eeprom-config -e`
    - wake_on_gpio=0
    - power_off_on_halt=1
3. `sudo nano /boot/firmware/config.txt`
    - dtparam=i2c_arm_baudrate=10000

## Cellular Modem Configuration
1. Follow Modem Hat Setup: https://docs.sixfab.com/docs/raspberry-pi-4g-lte-cellular-modem-kit-getting-started
    - installation code will look something like this: `sudo bash -c "$(curl -sN https://install.connect.sixfab.com)" -- -t specific-code-for-each-modem-here`

1. Follow UART Setup: https://docs.sixfab.com/page/uart-configuration#:~:text=The%20UART%20is%20useful%20in,not%20supported%20over%20the%20UART
1. Follow PPP Setup:  https://docs.sixfab.com/page/setting-up-the-ppp-connection-for-sixfab-shield-hat
    -  go into Sixfab PPP librbray and modify `ppp_install.sh`
    - Add `--break-system-packages` to pip install line

## Crontab
1. `@reboot ~/buoy/bin/python3 ~/Desktop/HAUCS/buoy/main.py &>> ~/Desktop/HAUCS/buoy/cronlog.log`

## Parameter File
1. cd into HAUCS/buoy directory
1. create 'param.json' file and write the following information. The information should be updated for each buoy.
    - `{"low":-0.8, "high":0.95, "neutral":-0.4, "max_pulse":0.0025, "min_pulse":0.0008, "buoy_id":x, "batt_mult":7.16}`

## Realtime Database Key
1. Copy `fb_key.json` file into main HAUCS folder

# Useful Commands
## Switch to haucs
1. Su haucs
2. Enter password

## Track Networking with Nethogs
1. sudo nethogs ppp0 -d 5 -v 1 &> ~/Desktop/nethogs2.log &
