# SPDX-FileCopyrightText: 2020 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Used with ble_uart_echo_test.py. Transmits "echo" to the UARTService and receives it back.
"""

import time
import serial

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

ble = BLERadio()

def init_serial(port):
    """
    Initialize Serial Port
    """
    global ser


    ser = serial.Serial(port=port, baudrate=9600,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                            timeout=0)

    return ser

def serial_read():
    c = ser.read()
    # act if new data present 
    if(c):
        buf = b''.join([buf, c])

        if buf[-1] == 13: #ends with carriage return
            message = buf.decode()
            message = message.split()
            buf = b''
            
            try:
                if (int(message[0]) % 5) == 0:
                    print(message[0::2])
            except:
                continue

            if len(message) == 11:
                writeCSV(file, message[0::2])
while True:
    while ble.connected and any(
        UARTService in connection for connection in ble.connections
    ):
        for connection in ble.connections:
            if UARTService not in connection:
                continue
            print("echo")
            uart = connection[UARTService]
            uart.write(b"echo")
            # Returns b'' if nothing was read.
            one_byte = uart.read(4)
            if one_byte:
                print(one_byte)
            print()
        time.sleep(1)

    print("disconnected, scanning")
    for advertisement in ble.start_scan(ProvideServicesAdvertisement, timeout=1):
        if UARTService not in advertisement.services:
            continue
        ble.connect(advertisement)
        print("connected")
        break
    ble.stop_scan()
