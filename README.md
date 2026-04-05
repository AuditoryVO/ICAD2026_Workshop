# ICAD 2026 Workshop
Exploring Aladin Sky Atlas through sound with SoniAladin.

SoniAladin is an application developed in the context of the Open Science initiative of the Spanish Virtual Observatory (SVO). It allows the transformation of Aladin’s virtual sky into audible representations.
![](UI.jpg)

NOTE:
The voice recognition module requires the local model vosk-model-small-en-us-0.15.

	1- Download and unzip it from: https://alphacephei.com/vosk/models
	
	2- Copy the unzipped vosk-model-small-en-us-0.15 folder in the SoniAladin folder.
	
US English model for mobile Vosk applications.
Copyright 2020 Alpha Cephei Inc.
Accuracy: 10.38 (tedlium test) 9.85 (librispeech test-clean).
Speed: 0.11xRT (desktop).
Latency: 0.15s (right context).

	3- On mac, open GarageBand an load a virtual instrument, for instance a 'Classic Electric Piano'.
	   You'll also need to activate the IAC driver in MIDI System preferences.
	   On Windows, SoniAladin uses GM directly so you don't need an additional sound engine.  

	4- Run SoniAladin.py from the Terminal.
	
	5- Say 'music' or press 'right arrow' to start the sonification. 
	   Say 'stop' or press 'left arrow' to stop the sonification. 
	   Say 'exit' or press'Esc' to finish.
