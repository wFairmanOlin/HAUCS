import microcontroller
import time
import pwmio
import board

rled = pwmio.PWMOut(board.D5, frequency=5000, duty_cycle = 0)
rled.duty_cycle = 2**15
time.sleep(5)
microcontroller.reset()


