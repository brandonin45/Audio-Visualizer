# CSCE 462 Project
#Audio Visualizer
#Blake DeGroot and Brandon Namphong

import RPi.GPIO as GPIO
import numpy as np
import time
 
delay = 0.000001

#LED Panel Setup
"""
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
red1_pin = 17
green1_pin = 18
blue1_pin = 22
red2_pin = 23
green2_pin = 24
blue2_pin = 25
clock_pin = 3
a_pin = 7
b_pin = 8
c_pin = 9
latch_pin = 4
oe_pin = 2
 
GPIO.setup(red1_pin, GPIO.OUT)
GPIO.setup(green1_pin, GPIO.OUT)
GPIO.setup(blue1_pin, GPIO.OUT)
GPIO.setup(red2_pin, GPIO.OUT)
GPIO.setup(green2_pin, GPIO.OUT)
GPIO.setup(blue2_pin, GPIO.OUT)
GPIO.setup(clock_pin, GPIO.OUT)
GPIO.setup(a_pin, GPIO.OUT)
GPIO.setup(b_pin, GPIO.OUT)
GPIO.setup(c_pin, GPIO.OUT)
GPIO.setup(latch_pin, GPIO.OUT)
GPIO.setup(oe_pin, GPIO.OUT)
"""

SAMPLE_RATE = 48000
FPS = 30

def computeMagnitude(data):
    dataMag = []
    for i in range(0,len(data)):
        dataMag.append(np.abs(data[i]))
    return dataMag

def applyWindow(data):
    data *= np.hamming(int(SAMPLE_RATE / FPS))
    return data


test = np.exp(2j * np.pi * np.arange(8) / 8)
print(test)
fft_window = np.hamming(8)
test *= fft_window
testfft = np.fft.fft(test)
print(testfft)
print(computeMagnitude(testfft))