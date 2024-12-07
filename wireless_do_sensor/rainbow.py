import time
import board
import digitalio
import adafruit_dotstar

print("starting")
pixels = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
pxl = [255, 0, 0]
pixels[0] = pxl

while True:
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
    time.sleep(0.01)
