"""
1. Have a function to save all non-volatile variables
- make underwater threshold nvm
- make auto sample rate nvm
- make do_calibration variable
2. Initialize and update ambient pressure
3. Initialize and update 100% DO
4. Sample while underwater
"""
import board
import microcontroller
from analogio import AnalogIn
import adafruit_dotstar
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
import time, rtc, gc, random
import asyncio
from rainbowio import colorwheel
import lps28
import math
import pwmio
import supervisor

print(gc.mem_free())
# supervisor.set_next_code_file(None, reload_on_error=True)

### DotStar Setup
pxl = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
### LED Setup
rled = pwmio.PWMOut(board.D5, frequency=5000, duty_cycle = 0)
gled = pwmio.PWMOut(board.MOSI, frequency=5000, duty_cycle=0)
led_pulse = [    0,     0,     0,     0,     0,     0,     0,     1,     1,
           1,     2,     2,     2,     3,     3,     4,     5,     5,
           6,     7,     8,     9,    10,    12,    13,    15,    17,
          19,    22,    24,    27,    31,    35,    39,    44,    49,
          55,    62,    69,    77,    87,    97,   109,   122,   137,
         153,   171,   192,   215,   241,   269,   301,   337,   377,
         422,   473,   529,   592,   662,   741,   829,   927,  1037,
        1160,  1298,  1452,  1624,  1817,  2032,  2273,  2543,  2845,
        3182,  3559,  3981,  4454,  4982,  5572,  6233,  6972,  7799,
        8723,  9758, 10914, 12208, 13656, 15275, 17085, 19111, 21376,
       23911, 26745, 29916, 33462, 37429, 41866, 46829, 52380, 58589,
       65535]
### LPS28 Setup
lps = lps28.LPS28(board.I2C())

### BLE Setup
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

### get stored parameters
nvm_size = 100
nvm_keys = ['id', 'sample_type','sample_hz', 'max_sample','init_p', 'threshold','init_do']
try:
    nvm_data = microcontroller.nvm[0:nvm_size].decode()
except:
    print("no parameters in non-volatile storage")
    nvm_data = "00," #default id
    nvm_data += "auto," #default sample type
    nvm_data += "1.0," #default sample freq
    nvm_data += "1000," #default max sample size
    nvm_data += "0.0," #default initial pressure
    nvm_data += "8.0," #default threshold
    nvm_data += "1," #default initial DO


### settings dictionary
# all settings should be strings
settings = {"stream": "0",
            "light": "off",
            }

nvm_vars = nvm_data.split(",")
for i, key in enumerate(nvm_keys):
    settings[key] = nvm_vars[i]

### global variables
sampling = 0
sample_count = 0
underwater = 0
tstamp = []
do = []
temperature = []
pressure = []
charge_state = "unknown"
battery_voltage = AnalogIn(board.A2)
charger_status = AnalogIn(board.A1)
do_voltage = AnalogIn(board.A0)

def get_voltage(pin, mult=1):
    return pin.value * 3.3 / 65536 * mult

def sample_sensors():
    do = round(do_voltage.value / int(settings['init_do']),2)
    pressure, temperature = lps.pressure_temperature

    return [do, temperature, pressure]

def save_settings():
    global nvm_keys
    nvm_data = ""
    for key in nvm_keys:
        nvm_data += settings[key] + ','
    nvm_data += (nvm_size - len(nvm_data)) * "0"
    microcontroller.nvm[0:nvm_size] = nvm_data.encode()

def calibrate_do():
    n = 10
    do = 0
    for i in range(n):
        do += do_voltage.value
    settings['init_do'] = str(int(do / n))
    print(settings)
    save_settings()

def calibrate_p():
    n = 10
    pressure = 0
    for i in range(n):
        pressure += lps.pressure
    pressure /= n
    settings['init_p'] = "{:07.2f}".format(pressure)
    print(settings)
    save_settings()
    
        
async def light():
    """
    Output a rainbow pattern on the itsybitsy dotstar
    """
    rainbow_counter = 0
    pulse_counter = 0
    pulse_direction = 0
    while True:
        if settings["light"] == "rainbow":
            rainbow_counter += 1
            if rainbow_counter > 255:
                rainbow_counter = 0
            
            rled.duty_cycle = 0
            gled.duty_cycle = 0
            pxl[0] = colorwheel(rainbow_counter)
        elif settings["light"] == "pulse":
            pulse_counter += 1 if pulse_direction == 0 else -1
            if pulse_counter > 98:
                pulse_direction = 1
            elif pulse_counter < 1:
                pulse_direction = 0
            gled.duty_cycle = led_pulse[pulse_counter]
            rled.duty_cycle = 0
            pxl[0] = (0,255,0, led_pulse[pulse_counter]/65535)
        elif settings["light"] == "navigation":
            pulse_counter += 1 if pulse_direction == 0 else -1
            if pulse_counter > 98:
                pulse_direction = 1
            elif pulse_counter < 1:
                pulse_direction = 0
            gled.duty_cycle = led_pulse[pulse_counter]
            rled.duty_cycle = led_pulse[pulse_counter]
            pxl[0] = (0, 0, 0)
        elif settings["light"] == "xmas":
            pulse_counter += 1 if pulse_direction == 0 else -1
            if pulse_counter > 80:
                pulse_direction = 1
            elif pulse_counter < 20:
                pulse_direction = 0
            gled.duty_cycle = led_pulse[-pulse_counter]
            rled.duty_cycle = led_pulse[pulse_counter]
            pxl[0] = (0, 0, 0)
        elif settings["light"] == "full":
            gled.duty_cycle = 65535
            rled.duty_cycle = 65535
            pxl[0] = (255, 255, 255)
        else:
            gled.duty_cycle = 0
            rled.duty_cycle = 0
            pxl[0] = (0, 0, 0)
            
        await asyncio.sleep(0.01)

async def charger():
    global charge_state
    while True:
        await asyncio.sleep(0)
        cv = get_voltage(charger_status)
        if cv > 2:
            if charge_state != "fully charged":
                charge_state = "fully charged"
                settings["light"] = "pulse"
        elif cv > 1.3:
            if charge_state != "not charging":
                charge_state = "not charging"
                settings["light"] = "0"
        else:
            if charge_state != "charging":
                charge_state = "charging"
                settings["light"] = "rainbow"
            

async def sample():
    global tstamp, do, temperature, pressure, sample_count, sampling
    sample_start = 0
    last_sample = time.monotonic()
    while True:
        await asyncio.sleep(0)
        #reached max sample count
        if sample_count >= int(settings.get("max_sample")):
            sampling = 0
        else:
            try:
                sampling_freq = float(settings.get("sample_hz"))
            except:
                sampling_freq = 0

            if (sampling_freq > 0) and (sampling == 1):
                sampling_period = 1 / sampling_freq
                if (time.monotonic() - last_sample) > sampling_period:

                    last_sample = time.monotonic()
                    if len(tstamp) == 0:
                        sample_start = last_sample

                    tstamp.append(int(1000 * (last_sample - sample_start)))
                    sensor_data = sample_sensors()
                    do.append(sensor_data[0])
                    temperature.append(sensor_data[1])
                    pressure.append(sensor_data[2])
                    sample_count += 1

async def auto_sensing():
    global sample_count, sampling
    while True:
        await asyncio.sleep(1)
        #only start if auto sampling enabled and empty buffer
        if settings['sample_type'] == "auto":
            p = lps.pressure
            #check if undewater
            pdiff = p - float(settings["init_p"])
            threshold = float(settings["threshold"])
            if (pdiff > threshold) and (sample_count == 0):
                sampling = 1
            elif pdiff < threshold * 0.8:
                sampling = 0

        #checks if pressure was accidentally calibrated underwater
        if lps.pressure < (float(settings["init_p"])  - float(settings["threshold"])):
            print("pressure is too low ... recalibrating")
            calibrate_p()



async def ble_uart():
    """
    Controls BLE advertising and UART service.
    Logic for handling UART commands are here.
    """
    last_stream = time.monotonic()
    global tstamp, do, temperature, pressure, sample_count, sampling
    while True:
        await asyncio.sleep(0)
        ble.start_advertising(advertisement)
        while not ble.connected:
            await asyncio.sleep(0)
        while ble.connected:
            await asyncio.sleep(0)

            #handle sensor streaming
            try:
                stream_fs = int(settings.get("stream"))
            except:
                stream_fs = 0
            if stream_fs > 0:
                stream_s = 1 / stream_fs
                if time.monotonic() - last_stream > stream_s:
                    last_stream = time.monotonic()
                    sensor_data = sample_sensors()
                    msg = f"d,{sensor_data[0]},t,{sensor_data[1]},p,{sensor_data[2]}\n"
                    uart.write(msg.encode())

            # Look for new messages
            message = ""
            if uart.in_waiting > 0:
                message = uart.readline()
            if message:
                full_message = message.decode()
                message = full_message.split()
                #changing settings
                if message[0] == "set":
                    if len(message) == 3:
                        settings[message[1]] = message[2]
                        print(settings)
                #reading settings
                elif message[0] == "get":
                    if len(message) == 2:
                        uart.write(str(settings.get(message[1])).encode())
                #calibrate sensors
                elif message[0] == "calibrate":
                    if len(message) == 2:
                        if message[1] == "do":
                            calibrate_do()
                        elif message[1] == "pressure":
                            calibrate_p()
                #store settings
                elif message[0] == "save":
                    save_settings()
                #handle data buffer
                elif message[0] == "sample":
                    if len(message) == 2:
                        if message[1] == "print":
                            uart.write((f"dstart,{sample_count}\n").encode())
                            for i in range(sample_count):
                                msg = f"ts,{tstamp[i]},d,{do[i]},t,{temperature[i]},p,{pressure[i]}\n"
                                uart.write(msg.encode())
                            uart.write(("dfinish\n").encode())
                        elif (message[1] == "reset")  or (message[1] == "start"):
                            sample_count = 0
                            sampling = 0 if message[1] == "reset" else 1
                            tstamp = []
                            do = []
                            temperature = []
                            pressure = []
                        elif message[1] == "stop":
                            sampling = 0
                        elif message[1] == "size":
                            uart.write(f"dsize,{sample_count}\n".encode())
                #poll and print sensor data once
                elif message[0] == "single":
                    sensor_data = sample_sensors()
                    msg = f"d,{sensor_data[0]},t,{sensor_data[1]},p,{sensor_data[2]}\n"
                    uart.write(msg.encode())
                #print battery and charging status
                elif message[0] == "batt":
                    #1.09V = charging
                    #1.65V = not charging
                    #2.79V = fully charged
                    bv = get_voltage(battery_voltage, 2)
                    cv = get_voltage(charger_status)
                    msg = f"v,{round(bv,2)},s,{charge_state}\n"
                    uart.write(msg.encode())
                #print DO voltage
                elif message[0] == "do":
                    v = get_voltage(do_voltage)
                    msg = f"dov,{v}\n"
                    uart.write(msg.encode())
                #reset microcontroller
                elif message[0] == "reset":
                    microcontroller.reset()


### Initial I/O
## startup lighting
for _ in range(5):
    gled.duty_cycle = 2**15
    time.sleep(0.05)
    gled.duty_cycle = 0
    time.sleep(0.05)
# initial pressure calibration
calibrate_p()

async def main():
    light_task = asyncio.create_task(light())
    uart_task = asyncio.create_task(ble_uart())
    sample_task = asyncio.create_task(sample())
    charger_task = asyncio.create_task(charger())
    autoSensing_task = asyncio.create_task(auto_sensing())

    await uart_task
    await sample_task
    await light_task
    await charger_task
    await autoSensing_task
asyncio.run(main())
