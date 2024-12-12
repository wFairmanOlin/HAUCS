from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
import json, os, time, random, csv
from matplotlib import pyplot as plt
import matplotlib
from scipy.optimize import curve_fit
from datetime import datetime
import numpy as np
import pandas as pd

ble = BLERadio()
uart_connection = None

scheduled_msgs = {"batt":15, "single":5}
msg_timers = {}
for i in scheduled_msgs:
    msg_timers[i] = time.time() + random.randint(1,scheduled_msgs[i])


### INIT JSON FILE
sdata = {}
folder = "data/"
sensor_file = folder + "sensor.json"
header = ['time', 'do', 'temperature', 'pressure']

def writeCSV(file, data):
    with open(file,'a',newline='') as csvfile:
      writer = csv.writer(csvfile, delimiter=',')
      writer.writerow(data)

def init_file():
    global folder, header
    filePath = "data/"
    date = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    if not os.path.exists(filePath):
        os.mkdir(filePath)

    csvFile = filePath + date + ".csv"

    with open(csvFile,'w',newline='') as csvfile:
      writer = csv.writer(csvfile, delimiter=',')
      writer.writerow(header)

    return csvFile

def exp_func(x, a, b, c):
    return a * np.exp(-b * x) + c

def generate_graph(file):
    df = pd.read_csv(file)
    df['s'] = df['time'] / 1000

    x = np.arange(100) * 3 / 10

    popt, pcov = curve_fit(exp_func, df['s'], df['do'])
    y = exp_func(x, *popt)
    # plt.style.use('dark_background')
    with plt.rc_context({'axes.edgecolor':'red', 'xtick.color':'red', 'xtick.labelsize':25, 'ytick.labelsize':25, 'ytick.color':'red', 'figure.facecolor':'black'}):
        plt.figure()
        plt.scatter(df['s'], df['do'], color="red", linewidth=4, alpha=1)
        plt.plot(x, y, color="red", linewidth=4, alpha=0.5)
        plt.xlabel("seconds", color="red", fontsize=25)
        plt.ylabel("% Saturation",  color="red", fontsize=25)
        plt.annotate(str(round(y[-1])) + '%', (x[-1], y[-1]), xytext=(x[70], y[15]), arrowprops={"width":1, "color":"red", "headwidth":6},color="red", fontsize=25)
        plt.savefig(file[:-4] + ".png", bbox_inches="tight")

def save_json():
    global sdata
    with open(sensor_file, 'w') as file:
        json.dump(sdata, file)
        
def ble_connect():
    global uart_connection
    print("searching for sensor ...")
    for adv in ble.start_scan(ProvideServicesAdvertisement):
        if UARTService in adv.services:
            uart_connection = ble.connect(adv)
            print("connected to: ", adv.complete_name)
            sdata['name'] = adv.complete_name[9:]
            break
    ble.stop_scan()

def ble_uart_read():
    global uart_connection

    if uart_connection:
        uart_service = uart_connection[UARTService]
        if uart_connection.connected:
            msg = uart_service.readline().decode()
            return msg
        
    return "failed read, no connection"

def ble_uart_write(msg):
    global uart_connection

    if uart_connection:
        print("sending: ", msg)
        uart_service = uart_connection[UARTService]
        if uart_connection.connected:
            uart_service.write(msg.encode())
        else:
            print("failed to send")

ble_connect()
ble_uart_write("set light xmas")
time.sleep(3)          
while True:
    if not (uart_connection and uart_connection.connected):
        if sdata.get('connection') != "not connected":
            sdata['connection'] = "not connected"
            save_json()
            
        print("trying to reconnect")
        ble_connect()
        time.sleep(1)
    else:
        ### update connection status
        if sdata.get('connection') != "connected":
            sdata['connection'] = "connected"
            save_json()
        ### send scheduled messages
        for msg in scheduled_msgs:
            if time.time() - msg_timers[msg] > scheduled_msgs[msg]:
                msg_timers[msg] = time.time()
                ble_uart_write(msg)
        ### read incoming messages
        msg = ble_uart_read()
        if len(msg) > 0:
            print(msg)
            msg = msg.split(",")
        if (len(msg) == 6) and (msg[0] == 'd'):
            sdata['do'] = float(msg[1]) * 100
            sdata['temperature'] = round(9/5 * float(msg[3]) + 32, 1)
            sdata['pressure'] = float(msg[5])
            save_json()
        elif (len(msg) == 4) and (msg[0] == 'v'):
            sdata['battv'] = float(msg[1])
            sdata['batt_status'] = msg[3][:-1]
            save_json()
        elif (len(msg)==2) and (msg[0] == 'dstart'):
            print("starting sample")
            csv_file = init_file()
        elif (msg[0] == "dfinish"):
            print("sample done")
            sdata['sample_loc'] = csv_file
            generate_graph(csv_file)
            save_json()
        elif (len(msg)==8) and (msg[0] == 'ts'):
            print("appending: ", msg)
            writeCSV(csv_file, [msg[1], msg[3], msg[5], msg[7]])