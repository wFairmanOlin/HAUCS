import threading
import ADS1x15
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo
import time

#Initialize Servo
servo = Servo(18, pin_factory=PiGPIOFactory())
#Initialize ADC
adc = ADS1x15.ADS1115(1)
adc.setGain(1)
time.sleep(0.05)

hall_min = 948
hall_max = 12285

def winch_control():
    dist = adc.readADC(0)
    target_dist = hall_min
    while True:
        dist = adc.readADC(0) - target_dist
        pwr = dist / (hall_max - hall_min)
        if pwr > 0.3:
            pwr = 0.3
        elif pwr < 0:
            pwr = 0
                
        if (dist < 1_000) and (servo.value > 0.0):
            servo.value = 0.0
            print("auto stop")
        elif (dist < 10_000) and (servo.value > 0.0):
            servo.value = pwr
        #print(dist)


wcontrol = threading.Thread(target=winch_control)
wcontrol.start()
while True:
    cmd = input("cmd: ")
    print(cmd)
    cmd = cmd.split(',')
    if len(cmd) < 1:
        continue
    elif (len(cmd) == 2) and (cmd[0] == 's'):
        print("setting servo to: ", float(cmd[1]))
        servo.value = float(cmd[1])
    elif cmd[0] == 'q':
        print("stopping")
        servo.detach()
    elif cmd[0] == 'p':
        print(servo.value)
