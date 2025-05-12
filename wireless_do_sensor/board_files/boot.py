import microcontroller
import time
import pwmio
import board


gled = pwmio.PWMOut(board.MOSI, frequency=5000, duty_cycle=0)
rled = pwmio.PWMOut(board.D5, frequency=5000, duty_cycle = 0)
# gled.duty_cycle = 0

try:
    nvm_data = microcontroller.nvm[0:100].decode()
except:
    nvm_data = ""

    
if nvm_data:
    nvm_data = nvm_data.split(',')
    if nvm_data[0] == "on":
        gled.duty_cycle = 65535
        time.sleep(0.5)
else:
    rled.duty_cycle =  65535
    time.sleep(0.5)
gled.duty_cycle = 0
rled.duty_cycle = 0
time.sleep(0.1)