import json, logging, time, smtplib, os
from time import sleep
from smbus2 import SMBus, i2c_msg
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo

folder = "Desktop/HAUCS/"
#Load Buoy ID from param file
with open(folder + "buoy/param.json") as file:
        param = json.load(file)

##### SERVO #####
#Initialize Servo
servo = Servo(18, min_pulse_width=param['min_pulse'], max_pulse_width=param['max_pulse'], pin_factory=PiGPIOFactory())

def wobble(secs):
    mv_time = 1
    cycles = int(secs//(2 * mv_time))
    for i in range(cycles):
        servo.value = param['high']
        sleep(mv_time)
        servo.value = param['low']
        sleep(mv_time)
    servo.value = param['high']
    sleep(mv_time)
    servo.detach()


wobble(4)