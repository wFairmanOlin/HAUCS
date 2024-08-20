import json, logging, time, smtplib, os
from time import sleep
from smbus2 import SMBus, i2c_msg
import ADS1x15
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo

DO_ADDR = 0x09
LPS_ADDR = 0x5D
LPS_CTRL_REG2 = 0x11
LPS_PRES_OUT_XL = 0x28
LPS_TEMP_OUT_L = 0x2B

folder = "Desktop/HAUCS/"
#Load Buoy ID from param file
with open(folder + "buoy/param.json") as file:
        param = json.load(file)

BUOY_ID = param['buoy_id']
BATT_MULT = param['batt_mult']

def get_lps_data():
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
    return round(pressure,2), round(temperature,2)

def get_do_data():
    with SMBus(1) as bus:    
        bus.write_byte(DO_ADDR, 0x01)
        sleep(0.01)
        do_low = bus.read_byte(DO_ADDR)
        bus.write_byte(DO_ADDR, 0x02)
        sleep(0.01)
        do_high = bus.read_byte(DO_ADDR)

    return do_low | (do_high << 8) 

def init_battery():
    global adc
    adc = ADS1x15.ADS1115(1)
    adc.setGain(1)
    sleep(0.05)
    val = adc.readADC(0)

def get_battery():
    val = adc.readADC(0)
    return round(val * adc.toVoltage() * BATT_MULT, 2)

init_battery()

while(True):
     batt_v = get_battery()
     p, t = get_lps_data()
     do = get_do_data()
     print(f"{batt_v}V do:{do} t:{t} p:{p}")
     sleep(2)