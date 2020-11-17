# CSCE 462 Project
#Audio Visualizer
#Blake DeGroot and Brandon Namphong

import numpy as np
import scipy
import pyaudio
from PIL import Image
from PIL import ImageDraw
from PIL import ImageColor
import time
import math
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from queue import Queue


SAMPLE_RATE = 44100 #sampling rate of the adc to be used
CHUNK = 2**10 # number of data points to read at a time
VOL_SCALE = 50000 #minimum unit of frequency amplitudes

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
freq_indices = [0]*32
for i in range(32):
    freq_indices[i] = np.where(np.logical_and((freqdata>freqbins[i]),(freqdata<freqbins[i+1])))[0] # select indices where the freq falls in the selected bin

prev_volume = [0]*32 #used to slowly reduces spikes for better looking graphics

queue_size = 43 #stores 1 second of history
beat_ave = 0.0
beat_threshold = 1.5*VOL_SCALE #minimum threshold for beat detection
beat_count = 10 #won't do anything unless < 3
beat_queue = Queue(queue_size) #queue for average sample energy

def push_freq(beat_ave, beat, beat_queue): #add amplitdue average to history, and calculate new running average
    beat_queue.put(beat)
    beat_ave = beat_ave + ((beat - beat_ave) / beat_queue.qsize()) 
    return beat_ave

def pop_freq(ave, q): #remove old average from history and calculate new running average
    ave = (ave * queue_size - q.get()) / (queue_size - 1)
    return ave

def draw_beat(): #effect to draw when beat detected
    draw.line((31, 0, 31, 15), fill=("blue"))
    draw.line((0, 0, 0, 15), fill=("blue"))
    draw.line((0, 15, 31, 15), fill=("blue"))

waveStart = time.time() #time for wave shifting
colorIterator = 0 #iterator for wave shifting
#shift from green to blue
colorArr = [(5,229,0), (4,197,31), (3, 166, 63), (2, 135, 95), (0, 104, 127), (0,73,159), (0,42,191), (0,73,159), (0, 104, 127), (2, 135, 95), (3, 166, 63), (4,197,131)] #rainbow rgb values

p=pyaudio.PyAudio() # start the PyAudio class
stream=p.open(format=pyaudio.paInt16,channels=2,input_device_index=0,rate=SAMPLE_RATE,input=True,
              frames_per_buffer=CHUNK)

# loop that reads data from adc and performs fft, then sends instructions to led, ctrl+C to exit
try:
    while True:
        data = np.frombuffer(stream.read(CHUNK),dtype=np.int16) # read data from input
        data = data * np.hamming(len(data)) # smooth the FFT by windowing data
        #separate left and right channels
        left = data[0::2]
        right = data[1::2]
        #perform fft on each channel
        fftleft = abs(scipy.fft(left)) # perform FFT on left data
        fftleft = fftleft[:int(len(fftleft)/2)] # keep only first half
        fftright = abs(scipy.fft(right)) # perform FFT on right data
        fftright = fftright[:int(len(fftright)/2)] # keep only first half
        fftdata = np.add(fftleft, fftright) #combine results from both channels
        beat = sum((fftdata[1:4]))/len(fftdata[1:4]) # average of current sample amplitudes
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
            draw.line((xpos, 0, xpos, volume), fill=(0, 255, 0)) # draw amplitude line
            if volume > 3: #if high volume, add curve around bar
                draw.line((xpos, 0, xpos, volume/2), width=5, fill=(0, 255, 0))
                draw.arc((xpos+1, 0, xpos+7, volume*2 - volume/3), 180, 270, fill=(0, 255, 0))
                draw.arc((xpos-7, 0, xpos-1, volume*2 - volume/5), 270, 0, fill=(0, 255, 0))
            prev_volume[i] = volume #store volume in previous volume array
                
        #replace colors to match rising amplitude
        for i in range(32):
            colorindex = math.floor((i+colorIterator)/3 % 12) #find color index for this bar
            if time.time() > (waveStart + 0.05): #shift wave when > then 0.01 seconds
                if colorIterator == 35: #iterator for shifting color array
                    colorIterator = 0
                else:
                    colorIterator += 1
                waveStart = time.time() #set new wave time
            for j in range(16):
                xy = x,y = i,j
                if image.getpixel(xy) != (0,0,0):
                    color = colorArr[colorindex]
                    temp = list(color)
                    temp[0] = temp[0] + j*30
                    temp[1] = temp[1] - j*16
                    temp[2] = temp[2] - j*16
                    color = tuple(temp)
                    draw.point(xy, fill=color)
        
        if beat_count < 3: # have beat effects hang around for a few cycles
            draw_beat()
            beat_count += 1
        
        if beat_queue.full(): # if history is full, then replace last element from queue, and perform beat detection
            beat_ave = pop_freq(beat_ave, beat_queue)
            beat_ave = push_freq(beat_ave, beat, beat_queue)
            #compute variance of beat vs average
            variance = 0.0
            for elem in list(beat_queue.queue):
                variance += abs(elem - beat_ave)
            variance = variance / 43
            c = 1.6 - (variance*0.000003) #sensitivity factor
            if beat >= beat_ave*c and beat_ave > beat_threshold:
                #beat detected
                draw_beat()
                beat_count = 0
        else:
            beat_ave = push_freq(beat_ave, beat, beat_queue)
                    
        matrix.Clear() #erase the image currently on matrix
        matrix.SetImage(image, 0, 0) #add new image to matrix
            
except KeyboardInterrupt:
    matrix.Clear()
    print('Program Exiting')
    # close the stream gracefully
    stream.stop_stream()
    stream.close()
    p.terminate()