import json, logging, time, smtplib
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
BATT_COUNTDOWN_MAX = 6
batt_count = BATT_COUNTDOWN_MAX
pond_table = {}


sampling_interval = 10 #minutes
sleep(30)

##### LOGGING #####
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', filename=folder + 'buoy/log.log', encoding='utf-8',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info('Starting')

##### EMAIL #####
def send_email(body):
    with open(folder + "buoy/email_cred.json") as file:
        cred = json.load(file)

    msg = EmailMessage()
    msg['Subject'] = "NABuoy " + str(BUOY_ID)
    msg['From'] = cred['from']
    msg['To'] = ', '.join(cred['to'])

    batt_v = get_battery()
    pond_id = get_pond_id()


    content = f"{time.strftime('%I:%M %p', time.localtime())}\n"
    content += f"battery: {batt_v}V\npond: {pond_id}\n"
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
servo = Servo(18, min_pulse_width=0.0009, max_pulse_width=0.0026, pin_factory=PiGPIOFactory())

def wobble(secs):
    mv_time = 0.31
    cycles = int(secs//(2 * mv_time))
    for i in range(cycles):
        servo.value = -1
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
def get_battery():
    try:
        adc = ADS1x15.ADS1115(1)
        adc.setGain(1)
        val = adc.readADC(0)
        sleep(0.1)
        val = adc.readADC(0)
        return round(val * adc.toVoltage() * BATT_MULT, 2)
    except:
        logger.warning("measuring battery voltage failed")
        return -1
    
def check_battery():
    global batt_count
    batt_v = get_battery()
    if batt_v < 13.4:
        # print("low voltage!")
        if batt_count <= 1:
            send_email(f"CRITICAL BATTERY\nsensor is now offline")
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


##### INITIALIZATION #####
#GPS
i2c = board.I2C()
gps = adafruit_gps.GPS_GtopI2C(i2c)
gps.send_command(b'PMTK314,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
gps.send_command(b"PMTK220,4000") #update every 10 secs
# gps.debug = True #REMOVE REMOVE REMOVE
gps_time = time.time()
while time.time() - gps_time < 5:
    gps.update()
    sleep(0.01)

#calibration
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
batt_v = get_battery()

send_email(f"POWERED ON\ncalibration: {round(init_do, 1)} {round(temp_t, 1)} {round(init_pressure)}")

#time of last sample
last_sample = 0

##### MAIN LOOP #####
while True:
    sleep(10)
    #sample battery voltage
    batt_v = check_battery()
    gps_time = time.time()
    try:
        while time.time() - gps_time < 2:
            gps.update()
            sleep(0.01)
    except:
        logger.warning("GPS update routine failed")

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
        except:
            logger.warning("uploading data to firebase failed")

            send_email(f"DATA UPLOAD FAILED\nbackup msg:\nDO: {100 * round(do[-1] / init_do)}%")
            app = restart_firebase(app)
            
    
# ~ def animate(i, do):
    # ~ '''
    # ~ Main Loop Called by FuncAnimation
    # ~ '''
    # ~ do_val = get_do_data()
    # ~ do.pop(0)
    # ~ do.append(do_val)
    # ~ l_do.set_ydata(do)
    # ~ return l_do,


# ~ size = 300
# ~ t_ms = 100
# ~ fig = plt.figure()
# ~ ax_do = fig.add_subplot(1,1,1)
# ~ plt.ylabel('DO')
# ~ plt.xlabel("seconds")
# ~ xs = [i * t_ms/1e3 for i in range(size)]
# ~ do = [0] * size
# ~ ax_do.set_ylim([0, 125])
# ~ l_do, = ax_do.plot(xs, do, color='b')

# ~ ani = animation.FuncAnimation(fig,
    # ~ animate,
    # ~ fargs=(do,),
    # ~ interval=t_ms,
    # ~ blit=True,
    # ~ cache_frame_data=False)
# ~ plt.show()
