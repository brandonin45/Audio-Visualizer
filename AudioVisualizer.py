# CSCE 462 Project
#Audio Visualizer
#Blake DeGroot and Brandon Namphong

import numpy as np
import scipy
import pyaudio
from PIL import Image
from PIL import ImageDraw
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from queue import Queue


SAMPLE_RATE = 44100 #sampling rate of the adc to be used
CHUNK = 2**10 # number of data points to read at a time
VOL_SCALE = 1000 #minimum unit of frequency amplitudes (placeholder value)

#32 bins for frequency grouping for the 32 led columns, 0 at end for last comparison
freqbins = [20. ,    24.8,    30.8,    38.2,    47.4,    58.9,    73. ,
          90.6,   112.5,   139.6,   173.2,   214.9,   266.7,   331. ,
         410.7,   509.7,   632.5,   784.8,   973.9,  1208.6,  1499.8,
        1861.1,  2309.6,  2866. ,  3556.6,  4413.5,  5476.8,  6796.4,
        8433.9, 10466. , 12987.6, 16116.8, 20000., 0.]
 
# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 16
options.hardware_mapping = 'audio-visualizer'

matrix = RGBMatrix(options = options)
image = Image.new("RGB", (32, 16))  # Create image object to store lines in
draw = ImageDraw.Draw(image)  # Draw object to store lines

#set up frequency bins
freqdata = np.fft.fftfreq(CHUNK,1.0/SAMPLE_RATE) # find frequency bins of data
freqdata = freqdata[:int(len(freqdata)/2)] # keep only first half
#print(freqdata)
freq_indices = [0]*32
for i in range(32):
    freq_indices[i] = np.where(np.logical_and((freqdata>freqbins[i]),(freqdata<freqbins[i+1])))[0] # select indices where the freq falls in the selected bin
    #print(freq_indices[i])

prev_volume = [0]*32 #used to slowly reduces spikes for better looking graphics

queue_size = 25
kick_ave = 0.0
snare_ave = 0.0
kick_threshold = 1250 #minimum threshold for kick detection
snare_threshold = 1000 #minimum threshold for snare detection
kick_count = 10 #won't do anything unless < 3
snare_count = 10 #won't do anything unless < 3
kick_queue = Queue(queue_size)
snare_queue = Queue(queue_size)
"""
kick_ave_low = 0.0
kick_ave_high = 0.0
snare_ave_low = 0.0
snare_ave_high = 0.0
kick_queue_low = Queue(queue_size) #a few seconds of history of 43hz frequencies for kick drum detection
kick_queue_high = Queue(queue_size) #a few seconds of history of 129hz frequencies for kick drum detection
snare_queue_low = Queue(queue_size) #a few seconds of history of 250hz frequencies for snare drum detection
snare_queue_high = Queue(queue_size) #a few seconds of history of 380hz frequencies for snare drum detection
"""

def push_freq(ave, elem, q):
    q.put(elem)
    ave = ave + ((elem - ave) / q.qsize())
    return ave

def pop_freq(ave, q):
    ave = (ave * queue_size - q.get()) / (queue_size - 1)
    return ave

p=pyaudio.PyAudio() # start the PyAudio class
stream=p.open(format=pyaudio.paInt16,channels=1,input_device_index=0,rate=SAMPLE_RATE,input=True,
              frames_per_buffer=CHUNK)

#TODO: add support for multiple channels (stereo)

# loop that reads data from adc and performs fft, then sends instructions to led, ctrl+C to exit
try:
    while True:
        data = np.frombuffer(stream.read(CHUNK),dtype=np.int16) # read data from RCA input
        data = data * np.hamming(len(data)) # smooth the FFT by windowing data
        fftdata = abs(scipy.fft(data)) # perform FFT on data
        fftdata = fftdata[:int(len(fftdata)/2)] # keep only first half
        kick = (fftdata[1] + fftdata[2]) / 2 #take average of sample points in kick drum range
        snare = (fftdata[5] + fftdata[6]) / 2 #take average of sample points in snare drum range
        #kick_low = fftdata[1]
        #kick_high = fftdata[3]
        #snare_low = fftdata[6]
        #snare_high = fftdata[9]
        draw.rectangle((0, 0, 31, 15), fill=(0,0,0)) #clear all lines on image object
        for i in range(32):
            amplitude = np.sum(fftdata[freq_indices[i]])# sum amplitude of all elements of fftdata in current frequency range
            amplitude = amplitude / (1+0.01*i) # scale down amplitude by index to counter oversampling of higher frequencies
            volume = int(np.floor(amplitude / VOL_SCALE)) # scale amplitude to number of led rows to light up
            if volume > 16: # if volume is over max, set to max
                volume = 16
            if volume < prev_volume[i]: # if volume is lower than prev_volume, slowly lower bar rather than instantly
                volume = int(prev_volume[i]*0.99)
            xpos = 31-i
            draw.line((xpos, 0, xpos, volume), fill=(0, 0, 255)) # draw amplitude line
            if volume > 4: #if high volume, add curve around bar
                draw.line((xpos, 0, xpos, volume/2), width=5, fill=(0, 0, 255))
                draw.arc((xpos+1, 0, xpos+7, volume*2 - volume/3), 180, 270, fill=(0, 0, 255))
                draw.arc((xpos-7, 0, xpos-1, volume*2 - volume/5), 270, 0, fill=(0, 0, 255))
            prev_volume[i] = volume #store volume in previous volume array
        if kick_count < 3: # have kick and snare effects hang around for a few cycles
            draw.line((0, 0, 31, 0), fill=("red"))
            kick_count += 1
        if snare_count < 3:
            draw.line((0, 1, 31, 1), fill=("yellow"))
            snare_count += 1
        if kick_queue.full(): # if history is full, then replace last element from queue, and perform beat detection (queues always have equal size)
            """
            kick_ave_low = pop_freq(kick_ave_low, kick_queue_low) # remove popped element from kick average low
            kick_ave_high = pop_freq(kick_ave_low, kick_queue_high) # remove popped element from kick average high
            snare_ave_low = pop_freq(snare_ave_low, snare_queue_low) # remove popped element from snare average low
            snare_ave_high = pop_freq(snare_ave_high, snare_queue_high) # remove popped element from snare average high
            kick_ave_low = push_freq(kick_ave_low, kick_low, kick_queue_low) # add current amplitude to queue and calculate running average of kick average low
            kick_ave_high = push_freq(kick_ave_low, kick_high, kick_queue_high) # add current amplitude to queue and calculate running average of kick average high
            snare_ave_low = push_freq(snare_ave_low, snare_low, snare_queue_low) # add current amplitude to queue and calculate running average of snare average low
            snare_ave_high = push_freq(snare_ave_high, snare_high, snare_queue_high) # add current amplitude to queue and calculate running average of snare average high
            """
            kick_ave = pop_freq(kick_ave, kick_queue)
            snare_ave = pop_freq(snare_ave, snare_queue)
            kick_ave = push_freq(kick_ave, kick, kick_queue)
            snare_ave = push_freq(snare_ave, snare, snare_queue)
            #if kick_low >= kick_ave_low*1.5 and kick_high >= kick_ave_high*1.5 and kick_ave_low > kick_threshold and kick_ave_high > kick_threshold:
            if kick >= kick_ave*1.8 and kick_ave > kick_threshold:
                #kick detected
                draw.line((0, 0, 31, 0), fill=("red"))
                kick_count = 0
            #if snare_low >= snare_ave_low*1.5 and snare_high >= snare_ave_high*1.5 and snare_ave_low > snare_threshold and snare_ave_high > snare_threshold:
            if snare >= snare_ave*1.8 and snare_ave > snare_threshold:
                #snare detected
                draw.line((0, 1, 31, 1), fill=("yellow"))
                snare_count = 0
        else:
            """
            kick_ave_low = push_freq(kick_ave_low, kick_low, kick_queue_low) # add current amplitude to queue and calculate running average of kick average low
            kick_ave_high = push_freq(kick_ave_low, kick_high, kick_queue_high) # add current amplitude to queue and calculate running average of kick average high
            snare_ave_low = push_freq(snare_ave_low, snare_low, snare_queue_low) # add current amplitude to queue and calculate running average of snare average low
            snare_ave_high = push_freq(snare_ave_high, snare_high, snare_queue_high) # add current amplitude to queue and calculate running average of snare average high
            """
            kick_ave = push_freq(kick_ave, kick, kick_queue)
            snare_ave = push_freq(snare_ave, snare, snare_queue)
            
        matrix.Clear() #erase the image currently on matrix
        matrix.SetImage(image, 0, 0) #add new image to matrix
            
except KeyboardInterrupt:
    matrix.Clear()
    print('Program Exiting')
    # close the stream gracefully
    stream.stop_stream()
    stream.close()
    p.terminate()
    