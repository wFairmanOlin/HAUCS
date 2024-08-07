import json, logging, time, smtplib, os
from time import sleep
from smbus2 import SMBus, i2c_msg
import ADS1x15
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo

import firebase_admin
from firebase_admin import credentials, db

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import board, adafruit_gps

from email.message import EmailMessage
from subprocess import call

# import matplotlib.pyplot as plt
# import matplotlib.animation as animation

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
folder = "Desktop/HAUCS/"
# folder = "Desktop/" #for testing

BUOY_ID = 1

DO_ADDR = 0x09
LPS_ADDR = 0x5D
LPS_CTRL_REG2 = 0x11
LPS_PRES_OUT_XL = 0x28
LPS_TEMP_OUT_L = 0x2B
BATT_MULT = 7.16
BATT_COUNTDOWN_MAX = 10
batt_count = BATT_COUNTDOWN_MAX
pond_table = {}

fails = {'gps':0, 'batt':0, 'firebase':0, }
sampling_interval = 10 #minutes
sleep(30)

##### LOGGING #####
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', filename=folder + 'buoy/log.log', encoding='utf-8',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info('Starting')

##### EMAIL #####
def send_email(body, batt=-1):
    with open(folder + "buoy/email_cred.json") as file:
        cred = json.load(file)

    msg = EmailMessage()
    msg['Subject'] = "NABuoy " + str(BUOY_ID)
    msg['From'] = cred['from']
    msg['To'] = ', '.join(cred['to'])

    pond_id = get_pond_id()

    content = f"{time.strftime('%I:%M %p', time.localtime())}\n"
    content += f"battery: {batt}V\npond: {pond_id}\n"
    content += body
    msg.set_content(content)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(cred['user'], cred['pwd'])
        server.send_message(msg)
        server.close()
    except:
        logger.warning("failed to send an email")

##### FIREBASE #####
# Store Key in separate file !!!
cred = credentials.Certificate(folder + "fb_key.json")
app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://haucs-monitoring-default-rtdb.firebaseio.com'})

def restart_firebase(app):
    logging.info('Attempting to restart Firebase Connection')
    firebase_admin.delete_app(app)
    sleep(60)
    new_app = firebase_admin.initialize_app(cred,
                                            {'databaseURL': 'https://haucs-monitoring-default-rtdb.firebaseio.com'})
    return new_app

##### SERVO #####
#Initialize Servo
servo = Servo(18, pin_factory=PiGPIOFactory())

def wobble(secs):
    mv_time = 0.5
    cycles = int(secs//(2 * mv_time))
    for i in range(cycles):
        servo.value = -0.6
        sleep(mv_time)
        servo.value = 1
        sleep(mv_time)
    servo.value = 0
    sleep(mv_time)
    servo.detach()
        
##### PAYLOAD #####
def get_lps_data():
    try:
        with SMBus(1) as bus:
            bus.write_byte_data(LPS_ADDR, LPS_CTRL_REG2, 0x01)
            ctrl_reg2 = 0x01
            while ctrl_reg2 == 0x01:
                ctrl_reg2 = bus.read_byte_data(LPS_ADDR, LPS_CTRL_REG2)

            sleep(0.01)
            x = bus.read_i2c_block_data(LPS_ADDR, LPS_PRES_OUT_XL, 5)
            pressure = x[0] | (x[1] << 8) | (x[2] << 16)
            pressure /= 4096
            temperature = x[3] | (x[4] << 8)
            temperature /= 100.0
            
        return pressure, temperature
    except:
        logger.warning("measuring Pressure/Temperature failed")
        return -1, -1

def get_do_data():
    try:
        with SMBus(1) as bus:    
            bus.write_byte(DO_ADDR, 0x01)
            sleep(0.01)
            do_low = bus.read_byte(DO_ADDR)
            bus.write_byte(DO_ADDR, 0x02)
            sleep(0.01)
            do_high = bus.read_byte(DO_ADDR)
            # ~ print(do_low, do_high)
        return do_low | (do_high << 8) 
    except:
        logger.warning("measuring DO failed")
        return -1

##### BATTERY #####
def init_battery():
    global adc
    try:
        adc = ADS1x15.ADS1115(1)
        adc.setGain(1)
        sleep(0.05)
        val = adc.readADC(0)
    except:
        logger.warning("battery initialization failed")

def get_battery():
    try:
        val = adc.readADC(0)
        fails['batt'] = 0
        return round(val * adc.toVoltage() * BATT_MULT, 2)
    except:
        fails['batt'] += 1
        logger.warning("measuring battery voltage failed ... attempting adc soft reset")
        init_battery()
        return -1
    
def check_battery():
    global batt_count
    batt_v = get_battery()
    if batt_v < 13.4:
        logger.warning(f"low voltage detected num: {batt_count}")
        if batt_count <= 1:
            send_email(f"CRITICAL BATTERY\nsensor is now offline", batt_v)
            logger.warning(f"critical voltage: shutting down - {batt_v}V")
            sleep(10)
            call("sudo shutdown now", shell=True)
        else:
            batt_count -= 1
    else:
        batt_count = BATT_COUNTDOWN_MAX
    
    return batt_v

##### POND DISCOVERY #####
def generate_pond_table():
    global pond_table
    with open(folder + "ponds.json") as file:
        data = json.load(file)
        
    for i in data['features']:
        id = i['properties']['number']
        coords = i['geometry']['coordinates'][0]
        pond_table[id] = Polygon(coords)

def get_pond_id():
    try:
        lng = gps.longitude
        if not lng: lng = 0
        lat = gps.latitude
        if not lat: lat = 0
    except:
        logger.warning("getting gps lat/lng failed")
    location = Point([lng, lat])

    if len(pond_table) == 0:
        generate_pond_table()
    
    pond_id = "unknown"
    for i in pond_table:
        if pond_table[i].contains(location):
            pond_id = str(i)
            return pond_id
    
    return pond_id

##### GPS #####
def update_GPS(t):
    gps_time = time.time()
    try:
        while time.time() - gps_time < t:
            gps.update()
            sleep(0.01)
        fails['gps'] = 0
    except:
        logger.warning("GPS update routine failed")
        fails['gps'] += 1

##### INITIALIZATION #####
init_name = "init.json"
init_file = folder + "buoy/init.json"

#load initialization data
if init_name not in os.listdir(folder + 'buoy/'):
    init_data = {'last_boot':time.time(), 'num_boots':0, 'init_do':-1, 'init_pressure':2000, 'last_calibration':time.time()}
    with open(init_file, 'w') as file:
        json.dump(init_data, file)
else:
    with open(init_file) as file:
        init_data = json.load(file)

#rebooted within 35 minutes
if (time.time() - init_data['last_boot']) <= (35 * 60):
    init_data['num_boots'] += 1
    logger.info(f"likely problematic reboot {init_data['num_boots']}")
#else reset reboot counter
else:
    init_data['num_boots'] = 0

init_data['last_boot'] = time.time()
#shutdown system if too many reboots
if init_data['num_boots'] >= 5:
    logger.warning(f"REBOOT LOOP DETECTED: shutting off system")
    call("sudo shutdown now", shell=True)

#SAVE BOOT INFO BEFORE I2C CALLED
with open(init_file, 'w') as file:
    json.dump(init_data, file)

temp_p, temp_t = get_lps_data()
#calibrate if detected out of water
if (temp_p - init_data['init_pressure']) < 12:
    init_pressure = 0
    init_do = 0

    for i in range(10):
        temp_p, temp_t = get_lps_data()
        temp_do = get_do_data()
        sleep(1)
        init_pressure += temp_p
        init_do += temp_do
        
    init_pressure /= 10
    init_do /= 10
    init_data['init_do'] = init_do
    init_data['init_pressure'] = init_pressure
    init_data['last_calibration'] = time.time()
    logger.info("saving new calibration data")
    with open(init_file, 'w') as file:
        json.dump(init_data, file)
#otherwise init data to previous data
else:
    init_pressure = init_data['init_pressure']
    init_do = init_data['init_do']
    logger.info("using stored calibration data")

#initialize GPS
i2c = board.I2C()
gps = adafruit_gps.GPS_GtopI2C(i2c)
gps.send_command(b'PMTK314,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
gps.send_command(b"PMTK220,8000")
update_GPS(5)

#initialize battery
init_battery()
batt_v = get_battery()

send_email(f"POWERED ON\ncalibration: {round(init_do, 1)} {round(temp_t, 1)} {round(init_pressure)}", batt_v)

#time of last sample
last_sample = 0
##### MAIN LOOP #####
while True:
    sleep(10)
    #reboot system if high failure rate encountered
    for i in fails:
        if fails[i] >= 5:
            logger.warning(f"failure detected {fails} rebooting")
            if fails['internet'] == 0:
                send_email(f"FAILURE DETECTED\nattempting sensor reboot\n{fails}", batt_v)
            sleep(10)
            call("sudo reboot", shell=True)
    #sample battery voltage
    batt_v = check_battery()
    update_GPS(2)

    if (time.time() - last_sample) > (sampling_interval * 60):
        last_sample = time.time()
        wobble(25)
        
        #sample data
        size = 10
        p = [0] * size
        t = [0] * size
        do = [0] * size
        for i in range(size):
            temp_p, temp_t = get_lps_data()
            temp_do = get_do_data()
            p[i] = temp_p
            t[i] = temp_t
            do[i] = temp_do
            sleep(1)
        
        #find pond
        pond_id = get_pond_id()
        
        #get current GMT time
        message_time = time.strftime('%Y%m%d_%H:%M:%S', time.gmtime(time.time()))
        try:
            lng = gps.longitude
            lat = gps.latitude
            if not lng: lng = 0
            if not lat: lat = 0
        except:
            logger.warning("getting gps lat/lng failed")

        data = {'do':do, 'init_do':init_do, 'init_pressure':init_pressure,
         'lat':lat, 'lng':lng, 'pid':pond_id, 'pressure':p, 'sid':BUOY_ID, 'temp':t,
         'batt_v':batt_v, 'type':'buoy'}
        
        #upload to firebase
        try:
            db.reference('LH_Farm/pond_' + pond_id + '/' + message_time + '/').set(data)
            fails['internet'] = 0
        except:
            logger.warning("uploading data to firebase failed")
            fails['internet'] += 1
            # app = restart_firebase(app)