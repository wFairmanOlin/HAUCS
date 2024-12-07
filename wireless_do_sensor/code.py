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
supervisor.set_next_code_file(None, reload_on_error=True)

### DotStar Setup
pxl = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
### LED Setup
rled = pwmio.PWMOut(board.D5, frequency=5000, duty_cycle = 0)
gled = pwmio.PWMOut(board.MOSI, frequency=5000, duty_cycle=0)
### startup lighting
for _ in range(5):
    gled.duty_cycle = 2**15
    time.sleep(0.05)
    gled.duty_cycle = 0
    time.sleep(0.05)
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
try:
    nvm_data = microcontroller.nvm[0:2]
except:
    print("no parameters in non-volatile storage")
    nvm_data = "00"
### settings dictionary
settings = {"stream": "0",
            "light": "pulse",
            "sample": "0",
            "max_sample": "1000",
            "id":nvm_data[0:2].decode()}

# global variables
sample_count = 0
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
    do = do_voltage.value
    pressure, temperature = lps.pressure_temperature

    return [do, temperature, pressure]

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
    global tstamp, do, temperature, sample_count, pressure

    sample_start = 0
    last_sample = time.monotonic()
    while True:
        await asyncio.sleep(0)
        #reached max sample count
        if sample_count >= int(settings.get("max_sample")):
            settings["sample"] = "0"
        else:
            try:
                sampling_freq = float(settings.get("sample"))
            except:
                sampling_freq = 0

            if sampling_freq > 0:
                sampling_period = 1 / sampling_freq
                if (time.monotonic() - last_sample) > sampling_period:

                    last_sample = time.monotonic()
                    if len(tstamp) == 0:
                        sample_start = last_sample
                        print("set sample start to :", sample_start)

                    print(last_sample - sample_start)
                    tstamp.append(int(1000 * (last_sample - sample_start)))
                    sensor_data = sample_sensors()
                    do.append(sensor_data[0])
                    temperature.append(sensor_data[1])
                    pressure.append(sensor_data[2])
                    sample_count += 1




async def ble_uart():
    """
    Controls BLE advertising and UART service.
    Logic for handling UART commands are here.
    """
    last_stream = time.monotonic()
    global tstamp, do, temperature, sample_count, pressure
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
                message = message.decode()
                message = message.split()
                if message[0] == "set":
                    if len(message) < 3:
                        continue
                    if message[1] == "time":
                        if len(message) != 11:
                            continue
                        args = [int(i) for i in message[2:]]
                        r.datetime = time.struct_time(args)
                        settings["stime"] = time.time()
                    elif message[1] == "id":
                        if len(message[2]) == 2:
                            microcontroller.nvm[0:2] = message[2].encode()
                            settings["id"] = message[2]
                    else:
                        settings[message[1]] = message[2]
                        print(settings)

                elif message[0] == "get":
                    if len(message) != 2:
                        continue
                    uart.write(str(settings.get(message[1])).encode())

                elif message[0] == "data":
                    if len(message) != 2:
                        continue
                    if message[1] == "print":
                        for i in range(sample_count):
                            msg = f"t,{tstamp[i]},d,{do[i]},c,{temperature[i]},p,{pressure[i]}\n"
                            uart.write(msg.encode())
                    elif message[1] == "reset":
                        sample_count = 0
                        tstamp = []
                        do = []
                        temperature = []
                        pressure = []

                elif message[0] == "single":
                    sensor_data = sample_sensors()
                    msg = f"d,{sensor_data[0]},t,{sensor_data[1]},p,{sensor_data[2]}\n"
                    uart.write(msg.encode())

                elif message[0] == "batt":
                    #1.09V = charging
                    #1.65V = not charging
                    #2.79V = fully charged
                    bv = get_voltage(battery_voltage, 2)
                    cv = get_voltage(charger_status)
                    msg = f"{charge_state},{round(bv,2)}"
                    uart.write(msg.encode())

                elif message[0] == "do":
                    v = get_voltage(do_voltage)
                    msg = f"voltage,{v}"
                    uart.write(msg.encode())
                
                elif message[0] == "reset":
                    microcontroller.reset()




async def main():
    light_task = asyncio.create_task(light())
    uart_task = asyncio.create_task(ble_uart())
    sample_task = asyncio.create_task(sample())
    charger_task = asyncio.create_task(charger())

    await uart_task
    await sample_task
    await light_task
    await charger_task


asyncio.run(main())
