import threading
import ADS1x15
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo
import time

#Initialize Servo
servo = Servo(18, min_pulse_width=param['min_pulse'], max_pulse_width=param['max_pulse'], pin_factory=PiGPIOFactory())
#Initialize ADC
adc = ADS1x15.ADS1115(1)
adc.setGain(1)
time.sleep(0.05)

def winch_control():
    dist = adc.readADC(0)
    while True:
        time.sleep(1)
        dist = adc.readADC(0)
        print(dist)


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