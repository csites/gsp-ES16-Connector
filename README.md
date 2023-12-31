# gsp-ES16-Connector
#
<h3>
<b>ES16Connector.py  (Release 0.9 is WORKING. WORKING BUT STILL DEBUGGING)
<b>GSPro OpenAPI to Ernest Sports ES16 Tour Plus Connector</b>
</h3><p>Please note.  The python version is a work in progress and may not work</p><p?
This is a connector application that connects to the GSPro Golf Simulator's OpenAPI interface and Ernest Sport's ES16, ES Tour Plus (V1.0 and V2.0), and the ES2020 Launch Monitors.   It's written in Python for easy portability and is open source.   The ES16 communicates via a Bluetooth connection which emulates a serial line connection and on Windows shows up as COM7.  For each successful swing, it sends two strings 168-byte strings that contain all of the ball and club data of the swing.  This is then reformated into the JSON structure used by the OpenAPI connector of GSPro.   The connector looks for changes in the Club selection and sends those to the ES16.   The GSP always lets the connector know the distance to the hole so on approach to a green if the ball is within 40 yards, it will send a special club selection called 'CHP' which enables a camera-only mode.  
</p><p>
The ES16 uses dual optical and quad aperture Doppler radar and does the following; radar is responsible for Ball Speed and Club Speed.  The optical systems are responsible for Club face angle, club path, ball spin, side spin, launch angle, etc.  The ES2020 is purely an optical system.
There are some issues I'm still trying to understand. 1) The all-optical CHP mode generates good ball data but only after issuing a miss-read. 2) On a rare occasion, the COM7 port will not be available indicating the ES16 Bluetooth has unpaired (usually at startup).  To solve this run the ES16 range app and re-pair the connection.  I'm looking for a Bluetooth Python code that can check the pairing status and initiate pairing if needed. 
 <p>
step1) Turn on your ES16.
</p><p>  
step2) Run GSPro with OpenAPI selected for LM.  With the OpenAPI panel open, run:   
</p><p>
step2) python ES16Connector.py 
</p><p>
When connected, the OpenAPI panel will change from a red border to a green border. 
You may need a few libraries installed to run.  
Special Python libraries: 
python -m pip install pyttsx3 pyserial timeit msvcrt chime 
</p><p>
 
<h3>
<b>ES16VOCALIZER.py  (WORKING)
Voice Caddy like Vocalizer for Ernest Sports ES16</b>
</h3><p>
ES16Volcalizer.py is the renamed 9th makeover of a parser I originally wrote with the Linux 'sed' command.  It's a lot like the Voice Caddy LM.  Basically, it is the tool I've used to build a proof of concept for reading the serial activity of the ES16 (and friends) parsing the data streams live and doing something.  It demonstrated one aspect I never knew of; that being the issue with "fat" shots.  On "fat" shots the ES16 returns only raw Radar data which consists of Club Speed and Ball Speed (from the front and rear radars).  The string returned begins with ESTP, which consists of 26 characters of data padded with zeros up to the word 'End" with a final length = 168.   An example would be: 
</p><p>
ESTPPrt001CS054.0BS000.0CL4Hy000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000End
</p><p>
On Good full swings, we are given two sets of data.  In other words, The first line is exactly as above; giving just the radar data.   The second line of 168 characters looks like this:
</p><p>
ES16Prt001CS067.0BS082.8CD000.0TD000.0LA12.8SP02259SF1.23CL4HySPA-10.3DIR-06.2LDA00.0AA-2.6DL17.0MH000.0SC+000.0ST+000.0CPTH-03.3CFAC-07.0SPL19.6HT00.00BV8.37VER179End
</p><p>
In addition to the radar-acquired Club Speed and Ball speed, it contains all of the optically read data from the ES16.  The ES2020 returns a similar string but it begins with ES20 and likely fills out all values.  The parser spits this up and puts it into an easy-to-use Python Key/Value array. In the ES16Vocalizer, I check the keyboard for a key press, and if the key is pressed is one of the following characters: `1234567890-=\p it will change the club selection on the ES16 corresponding to Driver, 3Wood, 5Wood, 4Hybrid, 4-9 Irons, Pitch Wedge, Gap Wedge, Sand Wedge, Lob Wedge (CHP), and Putter.  It will voice the club selection and send instructions to the ES16 to change clubs.  On a good ball swing it will speak out the Ball Speed and Club Speed from the parsed data of a swing.  The ES16Vocalizer can really help with speed training using the ES16 by giving instant feedback on club and ball speed on a golf swing.  On a misread swing (ie. fat shot), it will say "Misread swing sequence", letting you know about that quickly. 
</p>
<h3>
<b>Running the ES16Vocalizer.py (Windows)</b>
</h3>
<p>
step1) Turn on your ES16   
</p><p>
step2) python ES16Vocalizer.py 
</p><p>
You may need a few libraries installed to run.  
Special Python libraries: 
python -m pip install pyttsx3 pyserial timeit
</p><p>
Good luck.  If you need help or have questions, let me know how it goes on https://golfsimulatorforum.com in the Ernest Sports section.
</p><p>
Acknowlegements:  The ES16Connector borrows heavily from rowengb/GSPro-MLM2PRO-OCR-Connector project.  Mainly it serves as a guide to build the interface between a stock set of LM measurements and the GSPro OpenAPI.  Because the Ernest Sports Tour Plus and friends have putting built-in, the putting code has been removed as well as well.   
</p><p>
<h3>Future feature</h3>
</p><p>
Currently, I'm adding an Allexx-style putt server to the ES16connector.py.   This is a fix to overcome an issue with the new ES Tour Plus V2 putting.  Something changed in the V2 upgrade and it seems that putting relies heavily on the acoustic impact sensor which due to noise filtering, will not read short putts in the < 8ft range!  That is a game-stopper in tournament play. So as a work-around, I'm adding the Allexx putt server code to optionally handle putting from an external source.  Unfortunately, there seems to be a lot of intricacies to handle the threading of the Allexx-style putt server so considerable changes have be made to error capturing and reporting.  To make it even more challenging, I added mock-serial handling to allow the code to run without an active ES16.  This is to allow further debugging.  So, I now have introduced gspro-server-emulator.py to simulate the gsPRO's openAPI connector.  It just takes in the data and prints it to the screen.   It also allows you to change the club using the '1234567890-=\p keys and send the openAPI 201 player Json to change clubs.   If you turn on the EXTRA_DEBUG, you will want to run this first.   Next in the debugging of the Allexx-Style Putt server you can check that the putt-server is alive in a thread by simply using curl or opening a browser to HTTP://127.0.0.1:8888.  It will report the current club selected and whether putting is active.  To simulate a small 5mph putt, I have a small program that you can run in python called 'putt_server_test.py' which does a one-shot putt for testing the Allexx-style-putt-server functionallity.
</p>
 
</p>
</p>
