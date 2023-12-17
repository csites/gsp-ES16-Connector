# ES16 to GSPro OpenAPI connector.  V 0.4
# Csites 2023.   Added, Alexx's putt server.  I'm having a thread issue with Allexx's putt server.  So please use the release.

import time
import sys
import os
import json
import math
import re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading
from queue import Queue
import select
import psutil
from pathlib import Path
import chime
import msvcrt
import pyttsx3
import socket
import serial
import pywinauto

"""
Load settings.json and setup environment.  
"""
def load_settings():
    fname = "settings.json"
    if len(sys.argv) > 1 :
        fname = sys.argv[1]
        if os.path.exists(fname):    
            print(f"Using settings from: {fname}")
        else:
            print(f"Can't locate specified settings file: {sys.argv[1]}")
            sys.exit(1)
            
    with open(os.path.join(os.getcwd(), fname), "r") as file:
        lines = file.readlines()
        cleaned_lines = [line.split("//")[0].strip() for line in lines if not line.strip().startswith("//")]
        cleaned_json = "\n".join(cleaned_lines)
        settings = json.loads(cleaned_json)
    return settings

#load settings from settings.json
settings = load_settings()

# Host and port of GSPro OpenAPI
HOST = settings.get("HOST")
PORT = settings.get("PORT")
# METRIC = "Metric" or "Yards"
METRIC = settings.get("METRIC")
EXTRA_DEBUG = settings.get("EXTRA_DEBUG")
COM_PORT = settings.get("COM_PORT")
COM_BAUD = settings.get("COM_BAUD")
# Audible Read signal.
AUDIBLE_READY = settings.get("AUDIBLE_READY")
PUTTING_MODE = settings.get("PUTTING_MODE") # 0 = Native ES16, 1=Alexx Putt server
PUTTING_WINDOW_CONTROL = settings.get("PUTTING_WINDOW_CONTROL") # 1 means this code controls the putt window popup

if PORT is None:
    PORT=921
if HOST is None:
    HOST="127.0.0.1"
if METRIC is None:
    METRIC="Yards"
if AUDIBLE_READY is None:
    AUDIBLE_READY="YES"
if PUTTING_MODE is None:
    PUTTING_MODE = 0;     # 1 means enable webcam server  
if PUTTING_WINDOW_CONTROL is None:
    PUTTING_WINDOW_CONTROL = 0 # Let Alexx control it's own window. For clarity changed name from PUTTING_OPTION
if COM_PORT is None:   # Opps.  Forgot this option.  Thanks @YetG08
    COM_PORT = "COM7"
if COM_BAUD is None:
    COM_BAUD = 15220
        
# Setup the GSPro status variable
class c_GSPRO_Status:
    Ready = True
    ShotReceived = False
    ReadyTime = 0
    Putter = False
    DistToPin = 200
    RollingOut = False
    Club = "DR"
    Club_previous = "None"
    
gsp_stat = c_GSPRO_Status()
gsp_stat.Putter = False
gsp_stat.Ready = True

# To talk to GSPro OpenAPI
def create_socket_connection(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (host, port)
    sock.connect(server_address)
    sock.settimeout(5)
    return sock
    
# Color pretty print    
class Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'

def print_color_prefix(color, prefix, message):
    print(f"{color}{prefix}{Color.RESET}", message)
# So we can safely run the putt server as a thread.
lock_q = threading.Lock()
# Establish a shot Queue
shot_q = Queue()
# Also make voice global for the putt server 
voice = None

# Key/value arrays for club selection routines.
ES_gsp_Clubs="Drv DR, 3Wd W2, 3Wd W3, 4Wd W4, 5Wd W5, 7Wd W7, 7Wd W6, 2Hy H2, 3Hy H3, 4Hy H4, 5Hy H7, 5Hy H6, 5Hy H5, 2Ir I2, 2Ir I1, 3Ir I3, 4Ir I4, 5Ir I5, 6Ir I6,  7Ir I7, 8Ir I8, 9Ir I9, Ptw PW, Gpw GW, Sdw SW, Ldw LW, Chp LW, Ptt PT"

club_mapping = {
    "`": ("Driver", "Drv","DR"),
    "1": ("3 Wood", "3Wd","W3"),
    "2": ("5 Wood", "5Wd","W5"),
    "3": ("4 Hybrid", "4Hy","H4"),
    "4": ("4 Iron", "4Ir","I4"),
    "5": ("5 Iron", "5Ir","I5"),
    "6": ("6 Iron", "6Ir","I6"),
    "7": ("7 Iron", "7Ir","I7"),
    "8": ("8 Iron", "8Ir","I8"),
    "9": ("9 Iron", "9Ir","I9"),
    "0": ("Pitch Wedge", "Ptw","PW"),
    "-": ("Gap Wedge", "Gpw","GW"),
    "=": ("Sand Wedge", "Swd","SW"),
    "\\": ("Lob Wedge Chip", "Chp","LW"),
    "p": ("Putter", "Ptt","PT"),
}

gsclub_2voice_mapping = {
    "DR": ("Driver", "Drv"),
    "W3": ("3 Wood", "3Wd"),
    "W5": ("5 Wood", "5Wd"),
    "H4": ("4 Hybrid", "4Hy"),
    "H5": ("5 Hybrid", "5Hy"),
    "I4": ("4 Iron", "4Ir"),
    "I5": ("5 Iron", "5Ir"),
    "I6": ("6 Iron", "6Ir"),
    "I7": ("7 Iron", "7Ir"),
    "I8": ("8 Iron", "8Ir"),
    "I9": ("9 Iron", "9Ir"),
    "PW": ("Pitch Wedge", "Ptw"),
    "GW": ("Gap Wedge", "Gpw"),
    "SW": ("Sand Wedge", "Swd"),
    "LW": ("Lob Wedge Chip", "Chp"),
    "PT": ("Putter", "Ptt"),
}

# Club Selection helper. Create the key/value variable lists for club conversion. This is so we can go back and forth between formats.
def create_key_value_variable_lists() -> tuple[dict, dict]:
  """Creates two key/value variable lists from an ES-to-GSP club map.
  Args:
    es_gsp_clubs: The ES-to-GSP club map.
  Returns:
    A tuple containing two dictionaries: one for ES-to-GSP and one for GSP-to-ES.
 """    
  ES_gsp_Clubs="Drv DR, 3Wd W2, 3Wd W3, 4Wd W4, 5Wd W5, 7Wd W7, 7Wd W6, 2Hy H2, 3Hy H3, 4Hy H4, 5Hy H7, 5Hy H6, 5Hy H5, 2Ir I2, 2Ir I1, 3Ir I3, 4Ir I4, 5Ir I5, 6Ir I6,  7Ir I7, 8Ir I8, 9Ir I9, Ptw PW, Gpw GW, Sdw SW, Ldw LW, Chp LW, Ptt PT"

  gs_to_es = {}
  es_to_gs = {}

  for key_value_pair in ES_gsp_Clubs.split(','):
    key_value_pair_clean = key_value_pair.replace(' ','')
    es_club = key_value_pair_clean[:3]
    gs_club = key_value_pair_clean[3:] 
    print(es_club+" -- "+gs_club)
    gs_to_es[gs_club] = es_club
    es_to_gs[es_club] = gs_club
  
  return gs_to_es, es_to_gs
  
gs_to_es, es_to_gs = create_key_value_variable_lists()

# Parse ES16 Tour Plus  and ES2020.   Convert everything to a Key Value tuple.
def process_input_string(input_string):
    """
    Process_input_string takes a serialized data retrieved from an ES16 Lauch monitor.
    The ES16 data string is read from a wifi USB to serial port and shows up as COM7
    or a COM port higher than COM3.  This function converts it to a single string 
    of comma seperated Key Value,  It also filters off the Tour Plus extra line.
    """
    # Check for Tour Pluse if the input string begins with 'ESTP' and ignore it
    if input_string[:4] == "ESTP":
        return None
   
    pattern = r"([A-Z]{2,4})([+-]?\d*\.?\d+|[+-]?\d+\.\d+[^\d])"
    matches = re.findall(pattern, input_string)
    mydict = dict(matches)
    
    # Extract the three alphanumeric characters following the "CL" key
    club_regex = r"CL([a-zA-Z0-9]{3})"
    club_match = re.search(club_regex, input_string)

    # Add the extracted value to the dictionary if found
    if club_match:
        mydict['CL'] = club_match.group(1)

    return mydict

"""
After some initial testing with the ES16 TP 2.0, There exists an issue with it's putting.
The ES16 does putting OK but it does not work well for short putts.  So I think
giving the option to use Alexx's putting code (or my own fisheye code) is a good option.
So this is pulled right out of the old code.
"""
class PuttHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('content-length'))
        if length > 0 and gsp_stat.Putter:
            response_code = 200
            message = '{"result" : "OK"}'
            res = json.loads(self.rfile.read(length))
            print(res)
            
            putt = {
                "DeviceID": "ES16 Tour Plus",
                "Units": METRIC,
                "ShotNumber": 99,
                "APIversion": "1",
                "ShotDataOptions": {
                    "ContainsBallData": True,
                    "ContainsClubData": True,
                    "LaunchMonitorIsReady": True,
                    "LaunchMonitorBallDetected": True,
                    "IsHeartBeat": False
                }
            }
            putt['BallData'] = {}
            putt['BallData']['Speed'] = float(res['ballData']['BallSpeed'])
            putt['BallData']['TotalSpin'] = float(res['ballData']['TotalSpin'])
            putt['BallData']['SpinAxis'] = 0
            putt['BallData']['HLA'] = float(res['ballData']['LaunchDirection'])
            putt['BallData']['VLA'] = 0
            putt['ClubData'] = {}
            putt['ClubData']['Speed'] = float(res['ballData']['BallSpeed'])
            putt['ClubData']['Path'] = '-'
            putt['ClubData']['FaceToTarget'] = '-'
            # Put a lock on the shotq update.
#            with lock_q:
            shot_q.put(putt)
#                send_shots()
            print(f"Putt! Ball speed. {putt['BallData']['Speed']}, H L A {putt['BallData']['HLA']} Degrees.")
            voice.say("Putt! Ball speed {putt['BallData']['Speed']}, H L A {putt['BallData']['HLA']} Degrees.")
            voice.runAndWait()
            threading.enumerate()
        else:
            if not gsp_stat.Putter:
                print_color_prefix(Color.RED, "Putting Server ||", "Ignoring detected putt, since putter isn't selected")
            response_code = 500
            message = '{"result" : "ERROR"}'
        self.send_response_only(response_code) # how to quiet this console message?
        self.end_headers()
        self.wfile.write(str.encode(message))
        return

"""
PuttServer.   This is an http server to process an Allexx type putting applicatoin.
It runs a the server as a thread in the background which waits for data on the http
port 8888.  The putt application passes it data via json encoded data, which is 
put into the shotq.  Through the magic of a Shared Memory multiProcessor (SMP), it gets 
to the other threads. I modify the server threading by declaring daemon=True.
One thing I noticed is Alleexx's client sends to http://127.0.0.1:8888/putting but 
it looks like '/putting' portion of the url is ignored. 
"""
class PuttServer(threading.Thread):
    def run(self):
        print_color_prefix(Color.GREEN, "Putting Server ||", "Starting. Use ball_tracking from https://github.com/alleexx/cam-putting-py")
        self.server = ThreadingHTTPServer(('0.0.0.0', 8888), PuttHandler).serve_forever()
        threading.enumberate()
        return
 #       self.server.serve_forever()
 #       server_thread = threading.Thread(target=self.server.serve_forever, daemon=False)
 #       server_thread.start()

    def stop(self):
        print_color_prefix(Color.RED, "Putting Server ||", "Shutting down")
        self.server.shutdown()

"""
Process_gspro.   This function takes data returned from a socket read (what GSPro 
sends to us) and Decodes the messages.  200 is a standard ACK message that it 
received our message data and it was properly formated.  201 is an update data
message, Usually for Club change events. 202 203 and 204 are other messages.
"""
def process_gspro(resp):
    global putter_in_use
    global gsp_stat
    global voice
    global ser
    
    code_200_found = False
    # You've got to love this.
    jsons = re.split('(\{.*?\})(?= *\{)', resp.decode("utf-8"))
    print(jsons)
    for this_json in jsons:
        if len(this_json) > 0 :
            print(this_json)
            msg = json.loads(this_json)
            if msg['Code'] == 200 :
                gsp_stat.ShotReceived = True
                code_200_found = True
            if msg['Code'] == 201:
                gsp_stat.Ready = True
                gsp_stat.ReadyTime = time.perf_counter()
                gsp_stat.RollingOut = True
                gsp_stat.DistToPin = msg['Player']['DistanceToTarget']
                gsp_stat.Club = msg['Player']['Club']

                # We beed to send the CLub selected to ES16.  But if its a wedge, we need to look at Distance to Target.  If That is < 30 yards, we want to 
                # to Send club change to 'Chip' mode for pure optical
                # Send date to Club change to ES16.
                if (gsp_stat.Club != gsp_stat.Club_previous):
                      voice.say("Changing clubs to "+gsclub_2voice_mapping[gsp_stat.Club][0]+".")
                      voice.runAndWait()

                      # If we want to check for an external putter application
                      # We might want to do it here, or set a trigger for it  
     
                      if (gsp_stat.Club == "LW" and  gsp_stat.DistToPin <= 40.0):
                        Club_change = "CLUBCHPLOFT000\r"
                      else:
                        Club_change = "CLUB"+gs_to_es[gsp_stat.Club]+"LOFT000\r"

                      msg = Club_change.encode('ascii') 
                      print_color_prefix(Color.RED, "|| ES16 Change Clubs ||", msg)
                      print_color_prefix(Color.GREEN,"|| ES16 Connector    ||", f"Change Club: {gs_to_es[gsp_stat.Club]}, Distance to Pin: {gsp_stat.DistToPin}")
                      ser.write(msg)
           
                      # After club change look for OK.        
                      while (ser.inWaiting() == 0):  
                        time.sleep(0.1)
              
                      #Read the data from the port
                      data = ser.read(3)
                      string_data = data.decode('utf-8')
                      print("Expect: "+string_data)
                      ser.flush()
                # Check for putter
                threading.enumerate()
                print(f"Checking club for putter: {gsp_stat.Club} gsp_stat.Putter: {gsp_stat.Putter}")
                if gsp_stat.Club == "PT" and gsp_stat.Putter == False:
                    gsp_stat.Putter = True
                    
                # Check to see how we handle the putting window do we auto popup the putt window? 
                if PUTTING_MODE != 0 and  PUTTING_WINDOW_CONTROL != 0:
                    if gsp_stat.Club == "PT":
                        if not gsp_stat.Putter:
                            print_color_prefix(Color.GREEN, "ES16 Connector ||", "Putting Mode")
                            gsp_stat.Putter = True
                        if webcam_window is not None and gspro_window is not None:
                            # Pop up putting window on putt?
                            try:
                                app = pywinauto.Application()
                                app.connect(handle=webcam_window)
                                app_dialog = app.top_window()
                                if not app_dialog.has_focus():
                                    app_dialog.set_focus()
                            except Exception as e:
                                print_color_prefix(Color.RED, "ES16 Connector ||", "Unable to find Putting View window")
                                if EXTRA_DEBUG == 1:
                                    print(f"Exception: {e}")
                                    for win in pywinauto.findwindows.find_elements():
                                        if 'PUTTING VIEW' in str(win).upper():
                                            print(str(win))
                    else:
                        if gsp_stat.Putter:
                            print_color_prefix(Color.GREEN, "ES16 Connector ||", "Full-shot Mode")
                            gsp_stat.Putter = False
                        if webcam_window is not None and gspro_window is not None:
                            try:
                                app = pywinauto.Application()
                                app.connect(handle=gspro_window)
                                app_dialog = app.top_window()
                                if not app_dialog.has_focus():
                                    app_dialog.set_focus()
                            except Exception as e:
                                print_color_prefix(Color.RED, "ES16 Connector ||", "Unable to find GSPRO window")
                                if EXTRA_DEBUG == 1:
                                    print(f"Exception: {e}")
                                    for win in pywinauto.findwindows.find_elements():
                                        if 'GSPRO' in str(win).upper():
                                            print(str(win))
                gsp_stat.Club_previous = gsp_stat.Club                                    
    print("Exit process_gspro()")                                            
    return code_200_found

"""
send_shots.  This function handles all the communication with the openAPI.  It
creates a socket if one doesn't exist.  It check for any pending data on the
socket being sent from GSPro (ie. msg[Code]=200...etc).  It then pulls a message 
off the shotq FIFO and send it down the pipe to the OpenAPI to GSPro.  It then checks 
for a return message on the socket, and checks for an ack (msg[Code]=200... etc).  
"""
def send_shots():
    global gsp_stat
    global send_shots_create_socket
    global send_shots_socket
    BUFF_SIZE=1024
    POLL_TIME=10   # seconds to wait for shot ack
    
    try:
        if send_shots_create_socket:
            send_shots_socket = create_socket_connection(HOST, PORT)
            send_shots_create_socket = False
    
        # Check if we recevied any unsollicited messages from GSPRO (e.g. change of club)
        read_ready, _, _ = select.select([send_shots_socket], [], [], 0)

        data = bytes(0)
        while read_ready:
            data = data + send_shots_socket.recv(BUFF_SIZE) # Get GSPro data.
            read_ready, _, _ = select.select([send_shots_socket], [], [], 0)

        if len(data) > 0 :
            print(f"rec'd when idle:\n{data}")
            process_gspro(data) # don't need return value at this stage But do processes
            # club changes we need to send that that to ES16.
             
        # Check if we have a shot to send.  If not, we can return
        
        try:
            # Extract Data from the shot_q.
            message = shot_q.get_nowait()
            print(message)
        except Exception as e:
            # No shot to send
            return
        if message['ShotNumber'] != 0:
            ball_speed = message['BallData']['Speed']
            total_spin = message['BallData']['TotalSpin']
            spin_axis = message['BallData']['SpinAxis']
            hla= message['BallData']['HLA']
            vla= message['BallData']['VLA']
            if message['ShotDataOptions']['ContainsClubData']:
              club_speed= message['ClubData']['Speed']
              path_angle= message['ClubData']['Path']
              if path_angle == '-':
                  del message['ClubData']['Path']
              face_angle= message['ClubData']['FaceToTarget']
              if face_angle == '-':
                  del message['ClubData']['FaceToTarget']
    
            message['ShotNumber'] = send_shots.shot_count
    
            # Ready to send.  Clear the received flag and send it
            gsp_stat.ShotReceived = False
            gsp_stat.Ready = False
    
            # Send shot data to gspro. 
            print(json.dumps(message))
            send_shots_socket.sendall(json.dumps(message).encode())
            if message['ShotDataOptions']['ContainsClubData']:
               print_color_prefix(Color.GREEN,"ES16 Connector ||", f"Shot {send_shots.shot_count} - Ball: {ball_speed} MPH, Spin: {total_spin} RPM, Axis: {spin_axis}Ã‚Â°, HLA: {hla}Ã‚Â°, VLA: {vla}Ã‚Â°, Club: {club_speed} MPH")
            else:
                print_color_prefix(Color.GREEN,"ES16 Connector ||", f"Shot {send_shots.shot_count} - Ball: {ball_speed} MPH, Spin: {total_spin} RPM, Axis: {spin_axis}Ã‚Â°, HLA: {hla}Ã‚Â°, VLA: {vla}Ã‚Â°")
            send_shots.shot_count += 1
        else:
            # When ShotNumber == 0 send the heartbeat message
            send_shots_socket.sendall(json.dumps(message).encode())
            # Apperantly the heartbeat does not reply, so just return.
            return
            
        # Poll politely until there is a message received on the socket
        stop_time = time.time() + POLL_TIME # wait for ack
        got_ack = False
        while time.time() < stop_time:
            read_ready, _, _ = select.select([send_shots_socket], [], [], 0)
            if not read_ready:
                continue
            
            data = bytes(0)
            while read_ready:
                data = data + send_shots_socket.recv(BUFF_SIZE) # Note, we know there's a response now        
                read_ready, _, _ = select.select([send_shots_socket], [], [], 0)

            # we have a complete message now, but it may not have our ack yet
            if process_gspro(data):
                # we got acknowledgement
                print_color_prefix(Color.BLUE, "ES16 Connector ||", "Shot data has been sent successfully...")
                send_shots.gspro_connection_notified = False;
                send_shots_create_socket = False
                got_ack = True
                break

        if not got_ack:
            print("debug: no ack")
            print(message)
            raise Exception
 
    except Exception as e:

        # if EXTRA_DEBUG:
        print(f"send_shots: {e}")
        print_color_prefix(Color.RED, "ES16 Connector ||", "No response from GSPRO. Retrying")
        if not send_shots.gspro_connection_notified:
            # If you hear a screem... this is it.
            chime.error()
            send_shots.gspro_connection_notified = True;
        send_shots_create_socket = True

    return
    

""" 
ES16 Connector for GSPro OpenAPI with voice synthesized feed back.
Here we are at the main function.  We begin the main function by initializing all of the 
global variables, search and wait for the OpenAPI to be running.  We open the Ernest Sport 
serial port (typically COM7) and enable the vocalizer.  We then send an a heartbeat message 
to the openAPI to wakeit up (which creates the socket connection on the first message). We 
then proceed to our main loop which continues until we quit or exit.
"""
# Initialize function 'send_shots' static varibles
send_shots.gspro_connection_notified = False
send_shots.shot_count = 1
send_shots_create_socket = True
send_shots_socket = None
webcam_window = None
gspro_window = None
voice = None
ser = None

""" 
MAIN
"""
def main():
    global voice
    global ser
    global send_shots_create_socket
    global send_shots_socket
    global gsp_stat    
    
    # Let's setup a big error trap in-case anything goes wrong in setup.
    try:
        # Check for the GSPro OpenAPI connector
        found = False
        while not found:        
          for proc in psutil.process_iter():
              if 'GSPconnect.exe' == proc.name():
                  found = True
                  break
          if not found:
              print_color_prefix(Color.RED, "ES16 Connector ||", "GSPconnect.exe is not running. Reset it via GSPRO->Settings->Game->Reset GSPro Connect->Save")
              time.sleep(1)
                
        # Check for the GSPro OpenAPI connector
        print_color_prefix(Color.GREEN, "GSPro ||", "Connecting to OpenConnect API ({}:{})...".format(HOST, PORT))
        
        voice=pyttsx3.init() # Initialize text to speech
        voice.setProperty('rate',265)
        voice.setProperty('voice', 'Microsoft Mary')
        voice.say("E S 16 Connector is Ready!")
        voice.runAndWait()
        
        # Now start up the PuttServer in background if we are using Allexx's style putting.
        if PUTTING_MODE == 1:    
            putt_server = PuttServer()
            putt_server.run()
            print_color_prefix(Color.GREEN, "ES16 Connector ||", "PUTT SERVER is running")
            gsp_stat.Putter=False  # Means we are in putting mode.

        found = False
        while not found:
          ser = serial.Serial(COM_PORT, COM_BAUD, timeout=1.5)
          # Check if the port is open
          if ser.isOpen():
            print_color_prefix(Color.GREEN, "ES16  ||", "Connecting to ES16 serial port: ({}:{})...".format(COM_PORT, COM_BAUD))
            found = True
          else:
            print_color_prefix(Color.RED, "ES16  ||", "Serial port did not open. Bluetooth setup? Is the ES16 turned on?")
            timer.sleep(5)
         
# Initialize the OpenAPI with heartbeat.  
        last_sound=0 
        message = {
          "DeviceID": "ES16 Tour Plus",
          "Units": METRIC,
          "ShotNumber": 0,
          "APIversion": "1",
          "ShotDataOptions": {
              "ContainsBallData": False,
              "ContainsClubData": False,
              "LaunchMonitorIsReady": True,
              "LaunchMonitorBallDetected": True,
              "IsHeartBeat": True
          }
        }
        shot_q.put(message)
        send_shots()
        
        # MAIN LOOP:  Check the keyboard for quit or club change option.  Check the serial ports for
        # data if there is any, read and parse the data and format shot data to jsaon.  Send it up 
        # to the OpenAPI if there is any.   PLUS we have to deal with the Ernes Sports odd way of 
        # sending swing data.   
        loop=True
        while (loop == True):
          key = ""
          while (ser.inWaiting() == 0):
              # Check if a key has been pressed
              if msvcrt.kbhit():
                key = msvcrt.getch()
                if (ord(key) == ord('q')):
                  loop = False
                  break
                skey = str(chr(ord(key)))          
                if skey in club_mapping:
        
                  voice.say("Club Selected,"+club_mapping[skey][0])
                  voice.runAndWait()
                  # Get the corresponding string from the dictionary
                  string = club_mapping[skey][1]
                  # Construct the message string
                  club_change_string = "CLUB" + string + "LOFT000\r"
                  msg = club_change_string.encode('ascii') 
                  print_color_prefix(Color.RED, "|| ES16 Change Clubs ||", msg)
                  ser.write(msg)
          
                  # After club change look for OK.        
                  while (ser.inWaiting() == 0):  
                    time.sleep(0.1)
          
                  #Read the data from the port
                  data = ser.read(3)
                  string_data = data.decode('utf-8')
                  print("Expect: "+string_data)
                  ser.flush()
                  break
                else:
                  print("You pressed key: ",skey)

              # Check the socket for a 201 message.
              if send_shots_create_socket == False:
                  #  Check if we recevied any unsollicited messages from GSPRO (e.g. change of club)
                  read_ready, _, _ = select.select([send_shots_socket], [], [], 0)

                  data = bytes(0)
                  while read_ready:
                      data = data + send_shots_socket.recv(1024) # Get GSPro data.
                      read_ready, _, _ = select.select([send_shots_socket], [], [], 0)
                  if len(data) > 0 :
                      print(f"rec'd when idle:\n{data}")
                      process_gspro(data) # don't need return value at this stage But do processes
                      # Look for the club changes we need to send that that to ES16.

          # If we are putting with Alexx's putt server We don't need to read the serial port
          # So just flush the serial port and continue           
          if PUTTING_MODE == 1:
            if gsp_stat.Putter == True:
              ser.flush()
              continue
                         
          # Try to let us know if we hit a fat ball.  This is convoluted due to 
          # how it handles a fat shot vs a good shot (ie. radar with good optical data).  So 
          # if pass == 1, and it only received the 'ESTP' prefixed string and not the 
          # 'ES16' prefixed string, the unit has to read until a timeout occurs or and 
          # 'ES16' prefixed string occurs.  If the ES16 appears, at that point the ES16
          # LM will always have a good radar and good optical measurement of the ball data.
          # If it only sends the 'ESTP' then it never saw good optical data.  So in that case we
          # can only assume a fat shot and the read pass will timeout. (about 1.5sec)
          # Note, this is where the ES16 Audio trigger can be accidntally triggered.  If 
          # You see several fat ESTP signals with 0 ball speed.  It was likely a false 
          # audio signal.
          retry_cnt = 15     
          while (ser.inWaiting() == 0 and retry_cnt > 0):  
              time.sleep(0.1)
              retry_cnt = retry_cnt - 1
          if retry_cnt == 0:
              # Nothing waiting on the serial port
              continue
              
          # pass 1.   Read data + carriage return First data should be the ESTP line.
          ESTPdata = ser.read(168)
          string_ESTPdata = ESTPdata.decode('utf-8')
          print(f"Pass1 data read: {len(ESTPdata)}")
          parsed_ESTPdata = process_input_string(string_ESTPdata)
        
        
          # This should not happen unless the pass2 timeout was too short mean more that 1.5 secs.   It shouldn't but it does.  
          if (parsed_ESTPdata != None):
            print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","ERROR. ES16 Data recieved in pass1")
 
            ser.flush()
            # Minimum ball data needed for simulaton would be BS, HLA, VLA.  SP and SPA would be nice to have.
            keys_to_check = ["BS", "LA", "DIR", "SP", "SPA" ]
            all_keys_exist = True
            for key in keys_to_check:
              if key not in parsed_ESTPdata:
                all_keys_exist = False
                break
            if all_keys_exist:  
                Pdata = parsed_ESTPdata
                message = {
                  "DeviceID": "ES16 Tour Plus",
                  "Units": METRIC,
                  "ShotNumber": 999,
                  "APIversion": "1",
                  "BallData": {
                      "Speed": float(Pdata["BS"]),
                      "SpinAxis": float(Pdata["SPA"]),
                      "TotalSpin": float(Pdata["SP"]),
                      "BackSpin": round(float(Pdata["SP"]) * math.cos(math.radians(float(Pdata["SPA"])))),
                      "SideSpin": round(float(Pdata["SP"]) * math.sin(math.radians(float(Pdata["SPA"])))),
                      "HLA": float(Pdata["DIR"]),
                      "VLA": float(Pdata["LA"])
                  },
                  "ShotDataOptions": {
                      "ContainsBallData": True,
                      "ContainsClubData": False,
                      "LaunchMonitorIsReady": True,
                      "LaunchMonitorBallDetected": True,
                      "IsHeartBeat": False
                  }
                }
                # Put this shot in the queue
                shot_q.put(message)
                send_shots()
              # We need to go-ahead and send the shot data for late data events like this.
            print(f"pass1. Parsed ESTPdata: {parsed_ESTPdata}")
            voice.say("Correction!  Club Speed, "+parsed_ESTPdata["CS"]+".  Ball Speed, "+parsed_ESTPdata["BS"])
            voice.runAndWait()

            ser.flush()
            continue
        
          print(string_ESTPdata)
          
          # pass 2. Need to check for the second part of the ES16 data set.
          time.sleep(0.75) # Just a little rest time
          ES16data=b""
        
          try:
            ES16data = ser.read(168)
          except serial.SerialTimeoutException:
            voice.say("Timeout pass 2. Misread shot sequence")
            voice.runAndWait()
            ser.flush()
            continue
 
          # Typical of ESTP (radar) only data.       
          ES16string = ES16data.decode('utf-8')
          if (len(ES16string) == 0):
              voice.say("Mis red shot sequence")
              voice.runAndWait()
              ser.flush()
              continue
           
          # Finally we have a full read of radar and optical data. 
          # Note: Need to find a way to kick the voice into a thread in the background.
          Pdata =  process_input_string(ES16string)                               
          if (Pdata != None):
            print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","Data recieved")
            print(Pdata)
            # Here is your main data we send to the OpenAPI.          
            message = {
              "DeviceID": "ES16 Tour Plus",
              "Units": METRIC,
              "ShotNumber": 999,
              "APIversion": "1",
              "BallData": {
                  "Speed": float(Pdata["BS"]),
                  "SpinAxis": float(Pdata["SPA"]),
                  "TotalSpin": float(Pdata["SP"]),
                  "BackSpin": round(float(Pdata["SP"]) * math.cos(math.radians(float(Pdata["SPA"])))),
                  "SideSpin": round(float(Pdata["SP"]) * math.sin(math.radians(float(Pdata["SPA"])))),
                  "HLA": float(Pdata["DIR"]),
                  "VLA": float(Pdata["LA"])
              },
              "ClubData": {
                  "Speed": float(Pdata["CS"]),
                  "AngleOfAttack": float(Pdata["AA"]),
                  "FaceToTarget": float(Pdata["CFAC"]),
                  "Path": float(Pdata["CPTH"]),
                  "Loft": float(Pdata["SPL"])
              },
              "ShotDataOptions": {
                  "ContainsBallData": True,
                  "ContainsClubData": True,
                  "LaunchMonitorIsReady": True,
                  "LaunchMonitorBallDetected": True,
                  "IsHeartBeat": False
              },
              "Player": {
                  "Handed": "RH",
                  "Club": "8I"
              }
            }
            # Put this shot in the queue
            shot_q.put(message)
            send_shots()
            ser.flush()
            voice.say("Club Speed, "+Pdata["CS"]+".  Ball Speed, "+Pdata["BS"])
            voice.runAndWait()
            continue
          else: 
            print(f"I'm confused while parsing: {ES16string}")
            voice.say("Miss red shot sequence")
            voice.runAndWait() 
            ser.flush()
            continue
        
    except Exception as e:
        print_color_prefix(Color.RED, "ES16 Connector ||","An error occurred in main before line 779: {}".format(e))
    except KeyboardInterrupt:
        print("Ctrl-C pressed")

    finally:
        # Exit from loop. End the GSPconnector and closr the serial ports.  We are done.
        path = 'none'
        try:
          for proc in psutil.process_iter():
            if 'GSPconnect.exe' == proc.name():
              proc = psutil.Process(proc.pid)
              path=proc.exe()
              proc.terminate()
              print_color_prefix(Color.RED, "ES16 Connector ||", "Closed GSPconnect.exe.")
              break
        except Exception as e:
            print(f"Exception: Failed to close and relaunch GSPconnect.exe. {path} ({e})")
            
        if send_shots_socket:
            send_shots_socket.close()
            print_color_prefix(Color.RED, "ES16 Connector ||", "Socket to OpenAPI connection closed...")
        voice.stop()    
        ser.close()
        print("Quit!")


if __name__ == "__main__":


    time.sleep(1)
    main()


