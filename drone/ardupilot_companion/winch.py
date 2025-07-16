import threading
import ADS1x15
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo
import time
import logging
import math

#Initialize Servo
servo = Servo(18, pin_factory=PiGPIOFactory())
servo.value = 0
#Initialize ADC
adc = ADS1x15.ADS1115(1)
adc.setGain(1)
time.sleep(0.05)
#hall effect settings (calibrate for every system)
hall_min = 1035
hall_max = 12285

#global variables
cycle_count = 0
cycle_limit = 0
retracted = 1
auto_state = "idle"
auto_drop = 15 #drop time for auto cycling
auto_pwr = 1.0 #retrieve power
rotation = -1 #CW, -1 CCW
drop_timer = time.time()

##### LOGGING #####
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', filename='winchlog.log', encoding='utf-8',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info('Starting')

def release():
    global retracted
    servo.value = -rotation * 0.4
    safety_timer = time.time()
    #TODO: Check BLE connection to determine location of probe
    while (retracted == 1):
        if (time.time() - safety_timer) > 0.7:
            servo.value = 0
            print("safety timer triggered")
            logger.warning("safety timer on release")
            break
        pass
    servo.value = 0

def winch_control():
    global retracted
    dist = adc.readADC(0)
    target_dist = hall_min
    pwr_limit = 0.3
    while True:
        try:
            dist = adc.readADC(0) - target_dist
        except:
            servo.value = 0
            logger.warning('failed to read hall effect')
            time.sleep(5)
        
        pwr = dist / (hall_max - hall_min)
        pwr = pwr * pwr_limit
        if pwr > 0:
            pwr = math.pow(pwr,1/3)
        

        #limit min/max power
        if pwr > pwr_limit:
            pwr = pwr_limit
        elif pwr < 0:
            pwr = 0
                
        if (dist < (target_dist + 50)):
            retracted = 1
            if (rotation * servo.value) > 0.0:
                servo.value = 0
        elif (dist < 10_000) and ((rotation * servo.value) > 0.0):
            servo.value = rotation * pwr
        elif (dist > 8_000):
            if retracted != 0:
                retracted = 0

def state_machine():
    global retracted, cycle_count, cycle_limit
    global auto, auto_state, auto_pwr
    drop_timer = time.time()
    retrieve_timer = time.time()
    while True:
        if auto_state == "idle":
            pass
        elif auto_state == "released":
            if auto_drop < (time.time() - drop_timer):
                if retracted == 0:
                    auto_state = "retrieving"
                    print("retrieve started")
                    logger.info("retrieve started")
                    servo.value = rotation * auto_pwr
                    retrieve_timer = time.time()
                else :
                    print("release failed")
                    logger.warning("release failed")
                    auto_state = "idle"

        elif auto_state == "retrieving":
            if retracted:
                auto_state = "retracted"
                cycle_count += 1
                print(f"finished cycle {cycle_count} of {cycle_limit}")
                logger.info("cylce finished: " + str(cycle_count))
                if cycle_count >= cycle_limit:
                    auto_state = "idle"
                    print(f"program ended at {cycle_count} cycles")
                    logger.info(f"program ended at {cycle_count} cycles")
                time.sleep(10)
            elif 35 < (time.time() - retrieve_timer):
                servo.value = 0
                auto_state = "idle"
                logger.warning("ran out of time to retrieve")
                print("ran out of time to retrieve")

        elif auto_state == "retracted":
            release()
            drop_timer = time.time()
            auto_state = "released"

wcontrol = threading.Thread(target=winch_control)
smachine = threading.Thread(target=state_machine)
wcontrol.start()
smachine.start()
while True:
   
   #handle user inputs
    cmd = input()
    cmd = cmd.split(',')
    if len(cmd) < 1:
        continue
    elif (len(cmd) == 2) and (cmd[0] == 's'):
        print("setting servo to: ", float(cmd[1]))
        servo.value = float(cmd[1])
    elif cmd[0] == 'q':
        print("stopping")
        auto_state = "idle"
        servo.value = 0
    elif cmd[0] == 'r':
        print("releasing")
        release()
    elif cmd[0] == 'p':
        print(f"servo pwr: {servo.value}")
        print(f"hall efct: {adc.readADC(0)}")
        print(f"    state: {auto_state}")
        print(f"retracted: {'yes' if retracted == 1 else 'no'}")
    elif cmd[0] == 'start':
        cycle_count = 0
        cycle_limit = 1
        if len(cmd) == 2:
            cycle_limit = int(cmd[1])
        print(f"running test for {cycle_limit} cycles")
        auto = 1
        auto_state = "retracted"