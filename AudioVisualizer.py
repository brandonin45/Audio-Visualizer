# CSCE 462 Project
#Audio Visualizer
#Blake DeGroot and Brandon Namphong

import RPi.GPIO as GPIO
import numpy as np
import pyaudio
import time
import matplotlib.pyplot as plt
 
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

SAMPLE_RATE = 44100 #sampling rate of the adc to be used
CHUNK = 2**13 # number of data points to read at a time
#FPS = 30 #speed at which the display will update, frames per second
xres = 32 #number of leds in the x plane, rows
yres = 16 #number of leds in the y plane, columns

#32 bins for frequency grouping for the 32 led columns, 0 at end for last comparison
freqbins = [20. ,    24.8,    30.8,    38.2,    47.4,    58.9,    73. ,
          90.6,   112.5,   139.6,   173.2,   214.9,   266.7,   331. ,
         410.7,   509.7,   632.5,   784.8,   973.9,  1208.6,  1499.8,
        1861.1,  2309.6,  2866. ,  3556.6,  4413.5,  5476.8,  6796.4,
        8433.9, 10466. , 12987.6, 16116.8, 20000., 0.]


p=pyaudio.PyAudio() # start the PyAudio class
stream=p.open(format=pyaudio.paInt16,channels=1,input_device_index=0,rate=SAMPLE_RATE,input=True,
              frames_per_buffer=CHUNK) #uses default input device

#TODO: add support for multiple channels (stereo)

# infinite loop that reads data from adc and performs fft, then sends instructions to led
try:
    while True:
        data = np.frombuffer(stream.read(CHUNK),dtype=np.int16)
        data = data * np.hamming(len(data)) # smooth the FFT by windowing data
        fft = abs(np.fft.fft(data).real)
        fft = fft[:int(len(fft)/2)] # keep only first half
        freq = np.fft.fftfreq(CHUNK,1.0/SAMPLE_RATE)
        freq = freq[:int(len(freq)/2)] # keep only first half
        for i in range(0,xres):
            #select indices where the freq falls in the selected bin
            freq_indices = np.where(np.logical_and((freq>freqbins[i]),(freq<freqbins[i+1])))[0]
            amplitude = np.sum(fft[freq_indices])
            #TODO: add led instructions
            
except KeyboardInterrupt:
    print('Program Exiting')

# close the stream gracefully
stream.stop_stream()
stream.close()
p.terminate()
