import json, logging, time, smtplib, os
from time import sleep
from smbus2 import SMBus, i2c_msg
import ADS1x15
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo
from matplotlib import pyplot as plt
from matplotlib import animation

DO_ADDR = 0x09
LPS_ADDR = 0x5D
LPS_CTRL_REG2 = 0x11
LPS_PRES_OUT_XL = 0x28
LPS_TEMP_OUT_L = 0x2B


def get_do_data():
    try:
        with SMBus(1) as bus:    
            bus.write_byte(DO_ADDR, 0x01)
            sleep(0.01)
            do_low = bus.read_byte(DO_ADDR)
            bus.write_byte(DO_ADDR, 0x02)
            sleep(0.01)
            do_high = bus.read_byte(DO_ADDR)
            print(do_low | (do_high << 8))
        return do_low | (do_high << 8) 
    except:
        return -1
    
def animate(i, do):
    '''
    Main Loop Called by FuncAnimation
    '''
    do_val = get_do_data()
    do.pop(0)
    do.append(do_val)
    l_do.set_ydata(do)
    return l_do,

size = 300
t_ms = 100
fig = plt.figure()
ax_do = fig.add_subplot(1,1,1)
plt.ylabel('DO')
plt.xlabel("seconds")
xs = [i * t_ms/1e3 for i in range(size)]
do = [0] * size
ax_do.set_ylim([0, 125])
l_do, = ax_do.plot(xs, do, color='b')

ani = animation.FuncAnimation(fig,
    animate,
    fargs=(do,),
    interval=t_ms,
    blit=True,
    cache_frame_data=False)
plt.show()