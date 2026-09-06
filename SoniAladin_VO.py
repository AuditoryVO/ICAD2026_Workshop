import os
import signal
import time
import json
import queue
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from PIL import ImageGrab
from pynput import keyboard
from IPython.display import Audio
from vosk import Model, KaldiRecognizer

import cv2
import rtmidi
import matplotlib.pyplot as plt
from matplotlib.image import imread

import urllib.parse
import webbrowser

#Load the speech recognition model 
model_path = "SoniAladin/vosk-model-small-en-us-0.15"     #Remember to include the model in the software pack
model = Model(model_path)
rec = KaldiRecognizer(model, 16000)  #16kHz recording audio sample rate

q = queue.Queue()
ctrl = queue.Queue()

input_buffer = []
target_name = ""

def search_simbad(target_name):
    # Base URL for SIMBAD's identifier query
    base_url_1= "http://simbad.u-strasbg.fr/simbad/sim-id?Ident="

    # URL-encode the user input (e.g., converts spaces to %20)
    encoded_name_1 = urllib.parse.quote(target_name)

    # Construct the full URL
    full_url_1 = f"{base_url_1}{encoded_name_1}"

    # Open the URL in the default web browser
    print(f"Opening SIMBAD results for '{target_name}'...")
    webbrowser.open(full_url_1)


def search_vizier(target_name):
    base_url_2 = "https://vizier.cds.unistra.fr/viz-bin/VizieR?-c="
    encoded_name_2 = urllib.parse.quote(target_name)
    full_url_2= f"{base_url_2}{encoded_name_2}"

    print(f"\nOpening VizieR results for '{target_name}'...")
    webbrowser.open(full_url_2)


#Normalization of bright levels, fits them to match the 128 values of velocity in MIDI
def scaled_brights(brights, v_min, v_max, midi_min=0, midi_max=127):
    #Normalizes to 0-1
    normalized_brights = (brights - v_min) / (v_max - v_min)
    #Scales to MIDI range
    velocity_scaled = normalized_brights * (midi_max - midi_min) + midi_min
    #Rounds and converts to integers within MIDI range
    velocity_scaled = np.clip(np.round(velocity_scaled), midi_min, midi_max).astype(int)
    return velocity_scaled


def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))


#Keyboard control

def on_press(key):
    global running
    global input_buffer
    global target_name

    try:
        if hasattr(key, "char") and key.char is not None:
            # Append regular character keypresses directly as they are typed
            input_buffer.append(key.char)
        elif key == keyboard.Key.space:
            # Append spaces for Simbad compatibility
            input_buffer.append(" ")
        elif key == keyboard.Key.backspace and input_buffer:
            input_buffer.pop()
        elif key == keyboard.Key.enter and input_buffer:
            target_name = "".join(input_buffer).strip()
            input_buffer = []

        # Control Keys
        elif key == keyboard.Key.right:
            print("Starting sonification")
            ctrl.put("Sonification")
        elif key == keyboard.Key.left:
            print("Stopping sonification")
            ctrl.put("Stop")
        elif key == keyboard.Key.alt:
            print("Quick exploration")
            ctrl.put("Quick")
        elif key == keyboard.Key.down:
            print("Default exploration")
            ctrl.put("Default")
        elif key == keyboard.Key.ctrl:
            print("Slow exploration")
            ctrl.put("Slow")
        elif key == keyboard.Key.esc:
            print("Sonification module disconnected.")
            ctrl.put("Exit")

    except AttributeError:
        pass



#Continuous listening for sonification control
def listening():
    print("Listening... Say 'music' or press 'right arrow' to start the sonification. Say 'stop' or press 'left arrow' to stop the sonification. Say 'exit' or press'esc' to finish. Say 'quick' or press 'option', 'slow' or press 'control' and 'default' or press 'down arrow' to adjust the speed of the exploration")
    with sd.RawInputStream(samplerate=16000, blocksize=2000, dtype='int16',
                        channels=1, callback=callback):
        while True:
            data = q.get()                  #gets speech

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get('text', '').lower()
                if 'music' in text:
                    print("Starting sonification")
                    ctrl.put("Sonification")

                if 'stop' in text:
                    print("Stopping sonification")
                    ctrl.put("Stop")
                    
                if 'exit' in text:
                    print("Sonification module disconnected.")
                    ctrl.put("Exit")

                if 'slow' in text:
                    print("Slow exploration mode")
                    ctrl.put("Slow")
                
                if 'quick' in text:
                    print("Quick exploration mode")
                    ctrl.put("Quick")

                if 'default' in text:
                    print("Default exploration mode")
                    ctrl.put("Default")

 
    
t1 = threading.Thread(target=listening)
t1.start()

t2 = keyboard.Listener(on_press=on_press)
t2.start()

start_sound, fs = sf.read('SoniAladin/Audio/Start.wav')
stop_sound, fs = sf.read('SoniAladin/Audio/Stop.wav')
exit_sound, fs = sf.read('SoniAladin/Audio/Exit.wav')
mark_sound, fs = sf.read('SoniAladin/Audio/Mark.wav')

running = True

# Default Sonification parameters
high_threshold = 65   #Bright levels
low_threshold = 15
resolution = 4         #Pixels
speed = 0.05           #Exploration rate

while running:
    try:

        msg = ctrl.get_nowait()

        if msg == "Slow":
            sd.play(start_sound, fs*2)
            resolution = 4         #Pixels
            speed = 0.5

        if msg == "Quick":
            sd.play(start_sound, fs*2)
            resolution = 5         #Pixels
            speed = 0

        if msg == "Default":
            sd.play(start_sound, fs*2)
            resolution = 4         #Pixels
            speed = 0.05
             
        if msg == "Sonification":
            print("Displaying Sonification")

            rows = 0
            chords = []
            amplitudes = []
        
            midiout = rtmidi.MidiOut()
            available_ports = midiout.get_ports()
        
            if available_ports:
                midiout.open_port(0)  # Open first available port
            else:
                midiout.open_virtual_port("Virtual Output")
    
            #IMAGE CAPTURE
            bbox = (350, 250, 1249, 940)                   #Size of the screen capture
            screenshot = ImageGrab.grab(bbox=bbox)
            screenshot.save('SoniAladin/region_screenshot.png')
    
            Aladin_img = imread("SoniAladin/region_screenshot.png")
            
            #Pre-processing: Monochrome, perceived luminance = 0.299R+0.587G+0.114B (0-255)
            brights = 0.299*Aladin_img[ :, :,0] + 0.587*Aladin_img[ :, :,1] + 0.114*Aladin_img[ :, :,2] 
            v_min = np.min(brights)
            v_max = np.max(brights)
            normalized_brights = scaled_brights(brights, v_min, v_max)

            dims = np.shape(normalized_brights)
            x_dim = dims[1]
            y_dim = dims[0]
    
            # Creates a single persistent window before the loop
            window_name = 'SoniAladin'
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(window_name, cv2.WND_PROP_VISIBLE, 1)
            
            # Starting with the image
            plt.figure(figsize=(12, 9))
            plt.imshow(Aladin_img)
            plt.axis("off") 
            plt.savefig('SoniAladin/image_aladin.png')
            img = cv2.imread("SoniAladin/image_aladin.png")
            cv2.imshow(window_name, img)
            cv2.waitKey(1)
          
            all_notes_off = [0xB0, 123, 0]
            midiout.send_message(all_notes_off)

            #Play "start" sound
            sd.play(start_sound, fs)

            with midiout:
                for y in range(y_dim):
                    if y == (y_dim/3):
                        sd.play(stop_sound, fs)
                    if y == (2*y_dim/3):
                        sd.play(mark_sound, fs)

                    try:
                        msg2 = ctrl.get_nowait()
                        if msg2 == "Stop":
                            print("Sonification stopped")
                            cv2.destroyAllWindows()
                            break
                            
                        if msg2 == "Exit":
                            msg = "Exit"
                            break
                    except queue.Empty:
                        pass
                        
                    if (y % resolution == 0):
                        blocks = 0
                        #Draws the red exploration line in the image
                        plt.axhline(y=y, color='red', linewidth=2, alpha = 0.3)
                        plt.savefig('SoniAladin/image_aladin.png')

                        for x in range(x_dim):
                            if (x % resolution == 0):
                                blocks += 1
                                note = x/10
                                amplitude = int(normalized_brights[y][x])
                    
                                if normalized_brights[y][x] >= high_threshold: #Stars and Galaxies
                                    #Sound
                                    chords.append(x)
                                    amplitudes.append(amplitude)
                                    print ("_________Note:", x)
                    
                                    #note on: channel (ch1=0x90)/ note / velocity
                                    note_on = [0x90, note, amplitude] #Channel 1
                                    #note_off = [0x80, note, amplitude]  # Note off on same channel/note
                        
                                    midiout.send_message(note_on)
                                   # midiout.send_message(note_off)
            
                                if low_threshold < normalized_brights[y][x] < high_threshold:    #Faint objects
                    
                                    #note on: channel (ch1=0x90)/ note / velocity
                                    note_on = [0x91, note, amplitude] #Channel 2
                                    #note_off = [0x81, note, amplitude]  # Note off on same channel/note
                        
                                    midiout.send_message(note_on)
                                    #midiout.send_message(note_off)
                                '''           
                                if  normalized_brights[y][x] < low_threshold:    #Background noise
                    
                                    #note on: channel (ch1=0x90)/ note / velocity
                                    note_on = [0x92, note, amplitude] #Channel 3 
                                    #note_off = [0x81, note, amplitude]  # Note off on same channel/note
                        
                                    midiout.send_message(note_on)
                                    #midiout.send_message(note_off)
                                '''
                        img = cv2.imread("SoniAladin/image_aladin.png")
                        cv2.imshow(window_name, img)
                                
                        time.sleep(speed) 
                
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            msg = "Exit"
                            break
                        rows += 1
            
                cv2.destroyAllWindows()
                cv2.waitKey(1)
                midiout.send_message(all_notes_off)
                #Play "stop" sound
                sd.play(stop_sound, fs)
                search_vizier(target_name)
                search_simbad(target_name)


        if msg == "Exit":
            midiout = rtmidi.MidiOut()
            all_notes_off = [0xB0, 123, 0]
            midiout.send_message(all_notes_off)
            #Play "exit" sound
            sd.play(exit_sound, fs)
            running = False
            os.kill(os.getppid(), signal.SIGTERM)
            t1.join()
            t2.join()
            break
    except queue.Empty:
        pass
