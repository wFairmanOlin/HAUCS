import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import serial
import csv
import time
import os
from datetime import datetime
import re

# THE GREAT PUMPKIN PLOTTER

def writeCSV(file, time, data):
    with open(file,'a',newline='') as csvfile:
      writer = csv.writer(csvfile, delimiter=',')
      writer.writerow([time, *data])

def init_serial(port):
    global ser

    ser = serial.Serial(port=port, baudrate=9600,
                         parity=serial.PARITY_NONE,
                          stopbits=serial.STOPBITS_ONE,
                           bytesize=serial.EIGHTBITS,
                            timeout=0)
    return ser


def init_file(header):
    filePath = "data"

    date = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    if not os.path.exists(filePath):
        os.mkdir(filePath)

    csvFile = filePath + "/" + date + ".csv"

    with open(csvFile,'w',newline='') as csvfile:
      writer = csv.writer(csvfile, delimiter=',')
      writer.writerow(header)

    return csvFile


# This function is called periodically from FuncAnimation
def animate(i, do, p, t):
    global buf, time_start, init_do
    while(ser.in_waiting):
        c = ser.read()
        if(c):
            buf = b''.join([buf, c])

            if buf[-1] == 13: #ends with carriage return
                message = buf.decode()
                message = message.split()
                if (len(message) == 6):
                    #save air saturation
                    if not init_do:
                        init_do = float(message[1])
                    do.pop(0)
                    p.pop(0)
                    t.pop(0)
                    do.append(100 * float(message[1]) / init_do)
                    p.append(float(message[3]))
                    t.append(float(message[5]))
                    writeCSV(file, time.time() - time_start, [message[1], p[-1], t[-1]])
                    print(round(do[-1]), message[1], message[5])
                buf = b''


    # Update line with new Y values
    l_do.set_ydata(do)
    l_p.set_ydata(p)
    l_t.set_ydata(t)

    return l_do, l_p, l_t


header = ['time', 'do', 'pressure', 'temperature']
# port = '/dev/cu.usbmodem101'
port = '/dev/cu.usbmodem1201'
# port = '/dev/cu.usbmodem1101'
ser  = init_serial(port)
file = init_file(header)

size = 900   #number of points to plot
fs = 10 #hz

# Create figure for plotting
fig = plt.figure()
ax_do = fig.add_subplot(3, 1, 1)
plt.ylabel('DO % Saturation')
ax_p = fig.add_subplot(3,1,2)
plt.ylabel('Pressure HPa')
ax_t = fig.add_subplot(3,1,3)
plt.ylabel('Temp (C)')
plt.xlabel("seconds")
xs = [(size - i) / fs for i in range(size)]
t = [0] * size
p = [0] * size
do = [0] * size
ax_do.set_ylim([0, 110])
ax_p.set_ylim([1010, 1100])
ax_t.set_ylim([25, 41])
# Create a blank line. We will update the line in animate
l_do, = ax_do.plot(xs, do, color='b')
l_p, = ax_p.plot(xs, p, color='r')
l_t, = ax_t.plot(xs, t, color='orange')



#serial input buffer
buf = b''
time_start = time.time()
init_do = 0

# Set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig,
    animate,
    fargs=(do, p, t),
    interval=50,
    blit=True,
    cache_frame_data=False)
plt.show()
ser.close()
