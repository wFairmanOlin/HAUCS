from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
import adafruit_dotstar
import board

ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

pixels = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
pxl = [10, 0, 0]
pixels[0] = pxl

def rainbow():
    global pxl
    if not (pxl[0] or pxl[1] or pxl[2]):
        print("starting lights")
        pxl = [10, 0, 0]

    if pxl[0] > 0 and pxl[2] == 0:
        pxl[0] -= 1
        pxl[1] += 1
    elif pxl[1] > 0:
        pxl[1] -= 1
        pxl[2] += 1
    else:
        pxl[2] -= 1
        pxl[0] += 1
    pixels[0] = pxl

while True:
    ble.start_advertising(advertisement)
    while not ble.connected:
        pixels[0] = [0,0,0]
    while ble.connected:
        rainbow()
        # Returns b'' if nothing was read.
        one_byte = uart.read(1)
        if one_byte:
            print(one_byte)
            uart.write(one_byte)
