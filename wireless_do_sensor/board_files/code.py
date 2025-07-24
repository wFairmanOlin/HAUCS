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
import alarm

#set to YY.MM.DD
CODE_VERSION = "25.07.23"
print(gc.mem_free())
supervisor.set_next_code_file(None, reload_on_error=True)

### DotStar Setup
pxl = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
### LED Setup
rled = pwmio.PWMOut(board.D5, frequency=5000, duty_cycle = 0)
gled = pwmio.PWMOut(board.MOSI, frequency=5000, duty_cycle=0)
led_pulse = [    0,     0,     0,     0,     0,     0,     0,
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
       65535, 65535, 65535]
### LPS28 Setup
lps = lps28.LPS28(board.I2C())

### BLE Setup
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

### get stored parameters
nvm_size = 100
nvm_keys = ['blight', 'id', 'sample_type', 'sample_hz', 'max_sample',
            'init_p', 'threshold', 'init_do', 'light', 'stream',
            'do_unit', 'pmode', 'pidle', 'psleep', 'pdelay']
            
nvm_types = {'blight':'string','id':'string', 'sample_type':'string','sample_hz':'float',
            'max_sample':'int', 'init_p':'float', 'threshold':'float','init_do':'float',
            'light':'string','stream':'float','do_unit':'string','pmode':'string',
            'pidle':'int','psleep':'int', 'pdelay':'int'}
            
#default nvm_data if restore needed
nvm_default = "on," #led on boot
nvm_default += "00," #default id
nvm_default += "auto," #default sample type
nvm_default += "1.0," #default sample freq
nvm_default += "1000," #default max sample size
nvm_default += "0.01," #default initial pressure
nvm_default += "2.0," #default threshold
nvm_default += "1," #default initial DO
nvm_default += "off," #default light setting
nvm_default += "0," #default stream setting
nvm_default += "percent," #unit for DO while streaming
nvm_default += "low," #power mode
nvm_default += "5," #time to idle before sleeping
nvm_default += "25," #time to sleep before rebooting
nvm_default += "300," #extra time to wait after activity

print(len(nvm_default))
try:
    nvm_data = microcontroller.nvm[0:nvm_size].decode()
except:
    nvm_data = nvm_default
    print("no parameters in non-volatile storage")

def get_setting(name):
    global settings, nvm_types
    var = settings.get(name)
    var_type = nvm_types.get(name)
    if var_type == "float":
        return float(var)
    elif var_type == "int":
        return int(var)
    else:
        return var
    
def set_setting(name, value):
    global settings, nvm_types
    var_type = nvm_types.get(name)
    if not var_type:
        print("setting doesn't exist")
    else:
        try:
            if var_type == "float":
                float(value)
            elif var_type == 'int':
                int(value)
            settings[name] = str(value)
        except:
            print("value type different from setting type")

### settings dictionary
settings = {}
nvm_default_vars = nvm_default.split(",")
nvm_vars = nvm_data.split(",")

# check if all settings are present
if len(nvm_vars) != (len(nvm_keys) + 1):
    print("settings not in nvm. Possibly due to code update")
    nvm_vars = nvm_default_vars
# write settings
for i, key in enumerate(nvm_keys):
    settings[key] = nvm_vars[i]
    try:
        get_setting(key)
    except:
        print(f"invalid setting for {key}, assigning default")
        settings[key] = nvm_default_vars[i]
        

settings["version"] = CODE_VERSION
print(settings)
### global variables
sampling = 0
sample_count = 0
underwater = 0
tstamp = []
do = []
temperature = []
pressure = []
charge_state = "not charging"
battery_voltage = AnalogIn(board.A2)
charger_status = AnalogIn(board.A1)
do_voltage = AnalogIn(board.A0)
ble_advertising = 0

def safe_ble_write(msg):
    try:
        uart.write((str(msg) + "\n").encode())
    except:
        print("failed to write " + str(msg))

def save_settings():
    global nvm_keys
    nvm_data = ""
    for key in nvm_keys:
        # always store light value as off 
        if key == "light":
            nvm_data += "off,"
        else:
            nvm_data += settings[key] + ','

    nvm_data += (nvm_size - len(nvm_data)) * "0"
    if len(nvm_data) > nvm_size:
        print("cannot save, nvm_data larger than available size")
    else:
        microcontroller.nvm[0:nvm_size] = nvm_data.encode()
        safe_ble_write("saved")

def get_voltage(pin, mult=1):
    return pin.value * 3.3 / 65536 * mult

def sample_sensors():
    do = round(do_voltage.value / get_setting('init_do'), 2)
    pressure, temperature = lps.pressure_temperature

    return [do, temperature, pressure]

def convert_to_mgl(do, t, p, s=0):
    '''
    do: dissolved oxygen in percent saturation
    t: temperature in celcius
    p: pressure in hPa
    s: salinity in parts per thousand
    '''
    T = t + 273.15 #temperature in kelvin
    P = p * 9.869233e-4 #pressure in atm

    DO_baseline = math.exp(-139.34411 + 1.575701e5/T - 6.642308e7/math.pow(T, 2) + 1.2438e10/math.pow(T, 3) - 8.621949e11/math.pow(T, 4))
    # SALINITY CORRECTION
    Fs = math.exp(-s * (0.017674 - 10.754/T + 2140.7/math.pow(T, 2)))
    # PRESSURE CORRECTION
    theta = 0.000975 - 1.426e-5 * t + 6.436e-8 * math.pow(t, 2)
    u = math.exp(11.8571 - 3840.7/T - 216961/math.pow(T, 2))
    Fp = (P - u) * (1 - theta * P) / (1 - u) / (1 - theta)

    DO_corrected = DO_baseline * Fs * Fp

    DO_mgl = do / 100 * DO_corrected

    return DO_mgl

def calibrate_do():
    n = 10
    do = 0
    for i in range(n):
        do += do_voltage.value
    set_setting('init_do', int(do / n))
    safe_ble_write(f"init do, {get_setting('init_do')}")
    save_settings()

def calibrate_p():
    n = 10
    pressure = 0
    for i in range(n):
        pressure += lps.pressure
    pressure /= n
    set_setting('init_p', round(pressure, 2))
    safe_ble_write(f"init p, {get_setting('init_p')}")
    save_settings()


async def light():
    """
    Output a rainbow pattern on the itsybitsy dotstar
    """
    rainbow_counter = 0
    pulse_counter = 0
    pulse_direction = 0
    while True:
        if get_setting('light') == "rainbow":
            rainbow_counter += 1
            if rainbow_counter > 255:
                rainbow_counter = 0

            rled.duty_cycle = 0
            gled.duty_cycle = 0
            pxl[0] = colorwheel(rainbow_counter)
        elif get_setting('light') == "pulse":
            pulse_counter += 1 if pulse_direction == 0 else -1
            if pulse_counter > 98:
                pulse_direction = 1
            elif pulse_counter < 1:
                pulse_direction = 0
            gled.duty_cycle = led_pulse[pulse_counter]
            rled.duty_cycle = 0
            pxl[0] = (0,255,0, led_pulse[pulse_counter]/65535)
        elif get_setting('light') == "navigation":
            pulse_counter += 1 if pulse_direction == 0 else -1
            if pulse_counter > 98:
                pulse_direction = 1
            elif pulse_counter < 1:
                pulse_direction = 0
            gled.duty_cycle = led_pulse[pulse_counter]
            rled.duty_cycle = led_pulse[pulse_counter]
            pxl[0] = (0, 0, 0)
        elif get_setting('light') == "xmas":
            pulse_counter += 1 if pulse_direction == 0 else -1
            if pulse_counter > 80:
                pulse_direction = 1
            elif pulse_counter < 20:
                pulse_direction = 0
            gled.duty_cycle = led_pulse[-pulse_counter]
            rled.duty_cycle = led_pulse[pulse_counter]
            pxl[0] = (0, 0, 0)
        elif get_setting('light') == "full":
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
                set_setting('light', 'pulse')
        elif cv > 1.3:
            if charge_state != "not charging":
                charge_state = "not charging"
                set_setting('light', 'off')
        else:
            if charge_state != "charging":
                charge_state = "charging"
                set_setting('light', "rainbow")


async def sample():
    global tstamp, do, temperature, pressure, sample_count, sampling
    sample_start = 0
    last_sample = time.monotonic()
    while True:
        await asyncio.sleep(0)
        #reached max sample count
        if sample_count >= get_setting("max_sample"):
            sampling = 0
        else:
            try:
                sampling_freq = get_setting("sample_hz")
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

async def power_manager():
    """
    Decides when to enter low power mode.
    """
    global underwater
    had_connection = 0
    awake_time = time.monotonic()
    wait_to_sleep = get_setting('pidle')
    trigger = False
    while True:
        await asyncio.sleep(1)
        #change wait time if ble connection has been established
        if had_connection:
            if wait_to_sleep != (get_setting('pdelay') + get_setting('pidle')):
                wait_to_sleep = get_setting('pdelay') + get_setting('pidle')
        elif ble.connected:
            had_connection = 1
            wait_to_sleep = get_setting('pdelay') + get_setting('pidle')
        else:
            wait_to_sleep = get_setting('pidle')

        #check to sleep
        if get_setting('pmode') == "low":
            trigger = not ble.connected
            trigger &= True if sampling == 0 else False
            trigger &= True if get_setting('stream') == 0 else False
            trigger &= True if underwater == 0 else False
            trigger &= True if charge_state == "not charging" else False
            #trigger &= True if (get_voltage(battery_voltage, 2) < 4) else False
            if trigger:
                if (time.monotonic() - awake_time) > wait_to_sleep:
                    print("alarm triggered: ", get_setting('psleep'))
                    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + get_setting('psleep'))
                    alarm.exit_and_deep_sleep_until_alarms(time_alarm)

            else:
                awake_time = time.monotonic()

async def auto_sensing():
    global sample_count, sampling, underwater
    while True:
        await asyncio.sleep(1)
        #only start if auto sampling enabled and empty buffer
        if get_setting('sample_type') == "auto":
            p = lps.pressure
            #check if undewater
            pdiff = p - get_setting("init_p")
            threshold = get_setting("threshold")
            if (pdiff > threshold):
                underwater = 1
                if (sample_count == 0):
                    sampling = 1
            elif pdiff < (threshold * 0.8):
                sampling = 0
                underwater = 0

        #checks if pressure was accidentally calibrated underwater
        if lps.pressure < (get_setting("init_p")  - get_setting("threshold")):
            print("pressure is too low ... recalibrating")
            calibrate_p()

async def ble_uart():
    """
    Controls BLE advertising and UART service.
    Logic for handling UART commands are here.
    """
    last_stream = time.monotonic()
    global tstamp, do, temperature, pressure, sample_count, sampling, ble_advertising
    while True:
        await asyncio.sleep(0)
        if not ble.connected:
            if ble_advertising == 0:
                ble_advertising = 1
                try:
                    ble.start_advertising(advertisement)
                except:
                    print("failed ble advertising")
        elif ble.connected:
            ble_advertising = 0
            #handle sensor streaming
            try:
                stream_fs = get_setting('stream')
                if stream_fs > 5:
                    stream_fs = 5
            except:
                stream_fs = 0

            if stream_fs > 0:
                stream_s = 1 / stream_fs
                if time.monotonic() - last_stream > stream_s:
                    last_stream = time.monotonic()
                    sensor_data = sample_sensors()
                    do = 100 * sensor_data[0]
                    if get_setting('do_unit') == "mgl":
                        try:
                            do = round(convert_to_mgl(do, sensor_data[1], get_setting('init_p')),2)
                        except:
                            do = 0
                    ftemp = round(9 / 5 * sensor_data[1] + 32,1)
                    depth = round(10.197 / 25.4 * (sensor_data[2] - get_setting('init_p')), 1)
                    msg = f"d,{do},f,{ftemp},i,{depth}"
                    safe_ble_write(msg)
            # Look for new messages
            message = ""
            try:
                if uart.in_waiting > 0:
                    message = uart.readline()
                    full_message = message.decode().lower()
                    message = full_message.split()
            except:
                print("failed to read message")
            if message:
                #print all settings
                if message[0] == "help":
                    for i in settings:
                        safe_ble_write(i)
                #changing settings
                if message[0] == "set":
                    if len(message) == 3:
                        set_setting(message[1], message[2])
                        msg = f"{message[1]},{get_setting(message[1])}"
                        safe_ble_write(msg)
                #reading settings
                elif message[0] == "get":
                    if len(message) == 2:
                        msg = f"{message[1]},{get_setting(message[1])}"
                        safe_ble_write(msg)
                #calibrate sensors
                elif message[0] == "calibrate":
                    if len(message) == 2:
                        if message[1] == "do":
                            calibrate_do()
                        elif message[1] == "pressure":
                            calibrate_p()
                #calibrate sensors
                elif message[0] == "cal":
                    if len(message) == 2:
                        if message[1] == "do":
                            calibrate_do()
                        elif message[1] == "ps":
                            calibrate_p()
                #store settings
                elif message[0] == "save":
                    save_settings()
                #handle data buffer
                elif message[0] == "sample":
                    if len(message) == 2:
                        if message[1] == "print":
                            safe_ble_write(f"dstart,{sample_count}")
                            for i in range(sample_count):
                                 msg = f"ts,{tstamp[i]},d,{do[i]},t,{temperature[i]},p,{pressure[i]}"
                                 safe_ble_write(msg)
                            safe_ble_write("dfinish")

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
                            safe_ble_write(f"dsize,{sample_count}")
                #poll and print sensor data once
                elif message[0] == "single":
                    sensor_data = sample_sensors()
                    msg = f"d,{sensor_data[0]},t,{sensor_data[1]},p,{sensor_data[2]}"
                    safe_ble_write(msg)
                #print battery and charging status
                elif message[0] == "batt":
                    #1.09V = charging
                    #1.65V = not charging
                    #2.79V = fully charged
                    bv = get_voltage(battery_voltage, 2)
                    cv = get_voltage(charger_status)
                    msg = f"v,{round(bv,2)},s,{charge_state}"
                    safe_ble_write(msg)
                #print DO voltage
                elif message[0] == "do":
                    v = get_voltage(do_voltage)
                    msg = f"dov,{v}"
                    safe_ble_write(msg)
                #reset microcontroller
                elif message[0] == "reset":
                    microcontroller.reset()

### Initial I/O
## startup lighting
# initial pressure calibration
calibrate_p()

async def main():
    light_task = asyncio.create_task(light())
    uart_task = asyncio.create_task(ble_uart())
    sample_task = asyncio.create_task(sample())
    charger_task = asyncio.create_task(charger())
    autoSensing_task = asyncio.create_task(auto_sensing())
    power_task = asyncio.create_task(power_manager())

    await uart_task
    await sample_task
    await light_task
    await charger_task
    await autoSensing_task
    await power_task

asyncio.run(main())
