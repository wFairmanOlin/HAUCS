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
def animate(i, do):
    # Update line with new Y values
    line.set_ydata(do)

    return line,


header = ['time', 'do', 'pressure', 'temperature']
# port = '/dev/cu.usbmodem101'
# port = '/dev/cu.usbmodem1201'
port = '/dev/cu.usbmodem2101'
ser  = init_serial(port)
file = init_file(header)

size = 100   #number of points to plot
y_range = [0 110]
# Create figure for plotting
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
xs = list(range(0, size))
t = np.ones(size);
p = np.ones(size);
do = np.ones(size);
ax.set_ylim(y_range)
# Create a blank line. We will update the line in animate
line, = ax.plot(xs, do)
# Add labels
plt.xlabel('Samples')
plt.ylabel('DO (deg C)')

time_start = time.time()
time_csv = time.time()
time_graph = time.time()

#serial input buffer
buf = b''

# Set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig,
    animate,
    fargs=(do,),
    interval=50,
    blit=True)
plt.show()

while True:
    
    c = ser.read()
    if(c):
        buf = b''.join([buf, c])

        if buf[-1] == 13: #ends with carriage return
            message = buf.decode()
            message = message.split()
            if (len(message) == 6):
                do = np.concatenate((do[: -1], [message[1]]))
                p = np.concatenate((p[: -1], [message[3]]))
                t = np.concatenate((t[: -1], [message[5]]))
            elif (len(message) == 2):
                do = np.concatenate((do[: -1], [message[1]]))
            buf = b''

    if time.time() - time_graph > .2:
        time_graph = time.time()
        print(round(time.time() - time_start, 1), " do: ", do[-1], " pressure: ", p[-1], " temperature: ", t[-1])
            
    if time.time() - time_csv > .5:
        time_csv = time.time()
        writeCSV(file, time_csv - time_start, [do[-1], p[-1], t[-1]])

ser.close()
