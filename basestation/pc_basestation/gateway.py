# Based off THE GREAT PUMPKIN PLOTTER
import os
import serial
import time
import subprocess
import logging
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from datetime import datetime
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import json
from subprocess import call


############### Running On Startup ###############
# To configure this script to run on startup for unix systems
# add a command to the cron scheduler using crontab.
#
# Run "sudo crontab -e" to open the editor
#
# Paste the following line
#
# @reboot /usr/bin/python3 /home/Desktop/Biomass/pc_basestation/gateway.py &>> /home/Desktop/Biomass/pc_basestation/cronlog.log
#
# This runs the program when the device is powered on and stores the output in
# the local "cronlog.log" file. Please note that the python script outputs a more detailed
# log in the local "log.log" file.
#
# Let the computer establish a network connection on reboot
folder = "Desktop/HAUCS/basestation/pc_basestation/"
# folder = "" #for testing
#############################################
def init_serial(port):
    """
    Initialize Serial Port
    """
    global ser


    ser = serial.Serial(port=port, baudrate=9600,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                            timeout=0)

    return ser


def restart_firebase(app):
    logging.info('Attempting to restart Firebase Connection')
    firebase_admin.delete_app(app)
    time.sleep(60)
    logging.info('Current IP Address: ' + get_IP())
    new_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://haucs-monitoring-default-rtdb.firebaseio.com'})
    new_ref = db.reference('/LH_Farm')
    return new_app, new_ref

def get_IP():
    terminalResponse = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
    return terminalResponse.stdout

def get_pond_table():
    with open(folder + "ponds.json") as file:
        data = json.load(file)

    ponds = {}
    for i in data['features']:
        id = i['properties']['number']
        coords = i['geometry']['coordinates'][0]
        ponds[id] = Polygon(coords)
    
    return ponds

def get_pond_id(lat, lng):
    df = pd.read_csv(folder + 'sampling_points.csv')
    pond_ids = df.pop('pond')
    pond_gps = df.to_numpy()

    point = np.array([float(lng), float(lat)])
    point_y = np.tile(point, (pond_gps.shape[0], 1))
    #calculate euclidean distances
    distances = np.linalg.norm(pond_gps - point_y, axis=1)
    #calculate minimum distance in meters
    min_dist = distances.min() * 111_000
    #determine if min distance is acceptable
    if (min_dist < 100):
        #find pond associated with minimum distance
        pond_id = str(pond_ids[np.argmin(distances)])
    else:
        pond_id = "unknown"

    return pond_id

def get_do(p, d):
    """
    return the do associated with the highest pressure
    """
    idx = np.argmax(np.array(p, dtype='float'))
    return d[idx]

#sleep for a minute and a half before doing anything
time.sleep(90)
############### LOGGING ###############
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', filename=folder + 'log.log', encoding='utf-8', level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info('Starting with IP: ' + get_IP())

############### SERIAL PORT VARIABLES ###############
# port = '/dev/cu.usbserial-2'
# port = '/dev/cu.usbserial-0001'
port = '/dev/ttyACM'
portnum = 0
for i in range(20):
    try:
        print(port + str(i))
        ser = init_serial(port + str(i))
        break
    except:
        continue
portnum = i

############### FIREBASE VARIABLES ###############
#Store Key in separate file !!!
cred = credentials.Certificate(folder + "fb_key.json")
app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://haucs-monitoring-default-rtdb.firebaseio.com'})
ref = db.reference('/LH_Farm')

############### GLOBAL VARIABLES ###############
buf = b'' #serial input buffer

last_heartbeat = 0

## FOR fdata ##
fdata_data = dict()
fdata_timers = dict()

#startup
pond_table = get_pond_table()

############### MAIN LOOP ###############
#message: from 3 lat 27.535619 lng -80.351821 deg 0.000000 initP 1016.50 initDO 0 p 1015.75 t 28.16 do 0
while True:
    
    #HEARTBEAT
    
    if (time.time() - last_heartbeat) > 60:
        last_heartbeat = time.time()
        hbeat = {'time':time.time(), 'flagged':0}
        try:
            db.reference('LH_Farm/equipmennt/truck_basestation').set(hbeat)
        except:
            logger.warning("heartbeat failed")
            call("sudo reboot", shell=True)

    try:
        c = ser.read()
    except:
        logger.exception("reading serial buffer failed")
        ser.close()
        time.sleep(10)
        ser  = init_serial(port + str(portnum))

    if(c):
        buf = b''.join([buf, c])

        if buf[-1] == 13: #ends with carriage return
            message = buf.decode()
            message = message.split()
            buf = b''
            last_message_received = time.time()

            if len(message) >= 1:
                message_id = message[1]
                message_time = time.strftime('%Y%m%d_%H:%M:%S', time.gmtime())

                #Bathymetry
                if message_id == '4':
                    sensor_id = message_id

                    if ((len(message) - 18) % 6) == 0:
                            data = {"lat" : message[3], "lng" : message[5], "heading" : message[7],
                                    "init_pressure" : message[9], "init_do" : message[11]}
                        
                    pond_id = "unknown"
                    for i in pond_table:
                        if pond_table[i].contains(Point([float(data['lng']), float(data['lat'])])):
                            pond_id = str(i)
                            break

                    pressure = message[13::6]
                    temperature = message[15::6]
                    do = message[17::6]
                    data["pressure"] = [float(i) for i in pressure]
                    data["temp"] = [float(i) for i in temperature]
                    data['do'] = [int(i) for i in do]
                    data["pid"] = pond_id
                    data["sid"] = message[1]
                    data["type"] = "bathy"

                    #update bathy
                    try:
                        pond_ref = ref.child("bathymetry")
                        pond_ref.child(message_time).set(data)
                    except:
                        logger.warning("uploading BATHY message failed")
                        app, ref = restart_firebase(app)


                # DO Message
                elif message_id.isnumeric():
                    sensor_id = message_id
                
                    if ((len(message) - 18) % 6) == 0:
                        data = {"lat" : message[3], "lng" : message[5], "heading" : message[7],
                                 "init_pressure" : message[9], "init_do" : message[11]}
                        
                        pressure = message[13::6]
                        temperature = message[15::6]
                        do = message[17::6]
                        data["pressure"] = [float(i) for i in pressure]
                        data["temp"] = [float(i) for i in temperature]
                        data['do'] = [int(i) for i in do]
                        pond_id = get_pond_id(message[3], message[5])
                        data["pid"] = pond_id
                        data["sid"] = message[1]
                        data["type"] = "truck"

                        #update specific pond
                        try:
                            pond_ref = ref.child("pond_" + pond_id)
                            pond_ref.child(message_time).set(data)
                        except:
                            logger.warning("uploading DO message to pond_id failed .. restarting")
                            call("sudo reboot", shell=True)
                    else:
                        logger.warning("DO Message Length Mis-Match %s", message)

                # GPS Position Message
                if message_id == "lat":
                    if len(message) == 7:
                        data = {message[1] : message[2], message[3] : message[4], message[5] : message[6]}
                        try:
                            sensor_ref = ref.child("gps")
                            sensor_ref.child(message_time).set(data)
                        except:
                            logger.warning("uploading gps message failed")
                            app, ref = restart_firebase(app)
                    else:
                        logger.warning("GPS Message Length Mis-Match %s", message)

    
############### END MAIN LOOP ###############

logger.warning("Exited While Loop")
ser.close()

