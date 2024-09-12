
import csv
import os
import datetime
from gpiozero import CPUTemperature
import time

folder = "Desktop/HAUCS/buoy/"
 
def init_file(folder, header):
    filePath = str(folder) + "data"

    date = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    if not os.path.exists(filePath):
        os.mkdir(filePath)

    csvFile = filePath + "/" + date + ".csv"

    with open(csvFile,'w',newline='') as csvfile:
      writer = csv.writer(csvfile, delimiter=',')
      writer.writerow(header)

    return csvFile


header = ['time', 'temperature']
cpu = CPUTemperature()
file = init_file()
start_time = time.time()
while True:
    t = time.time() - start_time()
    with open(file,'a',newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow([t, cpu.temperature])