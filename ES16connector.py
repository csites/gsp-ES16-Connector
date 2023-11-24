# ES16 to GSPro OpenAPI connector.  V 0.3
# Csites 2023

import time
import sys
import os
import json
import math
import re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from queue import Queue
import select
import psutil
from pathlib import Path
import chime
import msvcrt
import pyttsx3
import socket
import serial

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

def print_colored_prefix(color, prefix, message):
    print(f"{color}{prefix}{Color.RESET}", message)

# Establish a shot Queue
shot_q = Queue()

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

# Club Selection helper. Create the key/value variable lists for club conversion. This is so we can go back and forth between 
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




# Load settings.json and setup environment.
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

if PORT is None:
    PORT=921
if HOST is None:
    HOST="127.0.0.1"
if METRIC is None:
    METRIC="Yards"
if AUDIBLE_READY is None:
    AUDIBLE_READY="YES"

# Setup the GSPro status variable
class c_GSPRO_Status:
    Ready = True
    ShotReceived = False
    ReadyTime = 0
    Putter = False
    DistToPin = 200
    RollingOut = False
    Club = "DR"
    Club_previous = "DR"
    
gsp_stat = c_GSPRO_Status()
gsp_stat.Putter = False
gsp_stat.Ready = True

def process_gspro(resp):
    global putter_in_use
    global gsp_stat

    code_200_found = False

    jsons = re.split('(\{.*?\})(?= *\{)', resp.decode("utf-8"))
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
                if (gsp_stat.Club != gs_stat.Club_previous):
                  voice.say("Changing clubs to "+gsclubs_2voice_mapping[gps_stat.Club][0]+".")
                  voice.runAndWait()
                  # If we want to check for an external putter application
                  # We might want to do it here, or set a trigger for it  
 
                  if (gsp_stat.Club == "LW" and  gsp_stat.DistToPin < 40):
                    Club_change = "CLUBCHPLOFT000\r"
                  else:
                    Club_change = "CLUB"+gs_to_es[gsp_stat.Club]+"LOFT000\r"

                  msg = club_change.encode('ascii') 
                  print_color_prefix(Color.RED, "|| ES16 Change Clubs ||", msg)
                  print_colored_prefix(Color.GREEN,"|| ES16 Connector    ||", f"Change Club: {gs_to_es[gsp_stat.Club]}, Distance to Pin: {gsp_stat.DistToPin}")
                  ser.write(msg)
       
                  # After club change look for OK.        
                  while (ser.inWaiting() == 0):  
                    time.sleep(0.1)
          
                  #Read the data from the port
                  data = ser.read(3)
                  string_data = data.decode('utf-8')
                  print("Expect: "+string_data)
                  ser.flush()
                  
                                            
    return code_200_found
    
def send_shots():
    global gsp_stat
    BUFF_SIZE=1024
    POLL_TIME=10   # seconds to wait for shot ack
    
    try:
        if send_shots.create_socket:
            send_shots.sock = create_socket_connection(HOST, PORT)
            send_shots.create_socket = False
    
        # Check if we recevied any unsollicited messages from GSPRO (e.g. change of club)
        read_ready, _, _ = select.select([send_shots.sock], [], [], 0)

        data = bytes(0)
        while read_ready:
            data = data + send_shots.sock.recv(BUFF_SIZE) # Get GSPro data.
            read_ready, _, _ = select.select([send_shots.sock], [], [], 0)

        if len(data) > 0 :
            #print(f"rec'd when idle:\n{data}")
            process_gspro(data) # don't need return value at this stage But do processes
            # club changes we need to send that that to ES16.
             
        # Check if we have a shot to send.  If not, we can return
        
        try:
            # Extract Data from the shot_q.
            message = shot_q.get_nowait()
        except Exception as e:
            # No shot to send
            return

        ball_speed = message['BallData']['Speed']
        total_spin = message['BallData']['TotalSpin']
        spin_axis = message['BallData']['SpinAxis']
        hla= message['BallData']['HLA']
        vla= message['BallData']['VLA']
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
        send_shots.sock.sendall(json.dumps(message).encode())
        print_colored_prefix(Color.GREEN,"ES16 Connector ||", f"Shot {send_shots.shot_count} - Ball: {ball_speed} MPH, Spin: {total_spin} RPM, Axis: {spin_axis}°, HLA: {hla}°, VLA: {vla}°, Club: {club_speed} MPH")
        send_shots.shot_count += 1

        # Poll politely until there is a message received on the socket
        stop_time = time.time() + POLL_TIME # wait for ack
        got_ack = False
        while time.time() < stop_time:
            read_ready, _, _ = select.select([send_shots.sock], [], [], 0)
            if not read_ready:
                continue
            
            data = bytes(0)
            while read_ready:
                data = data + send_shots.sock.recv(BUFF_SIZE) # Note, we know there's a response now        
                read_ready, _, _ = select.select([send_shots.sock], [], [], 0)

            # we have a complete message now, but it may not have our ack yet
            if process_gspro(data):
                # we got acknowledgement
                print_colored_prefix(Color.BLUE, "ES16 Connector ||", "Shot data has been sent successfully...")
                send_shots.gspro_connection_notified = False;
                send_shots.create_socket = False
                got_ack = True
                break

        if not got_ack:
            print("debug: no ack")
            raise Exception
 
    except Exception as e:
        if EXTRA_DEBUG:
            print(f"send_shots: {e}")
        print_colored_prefix(Color.RED, "ES16 Connector ||", "No response from GSPRO. Retrying")
        if not send_shots.gspro_connection_notified:
            chime.error()
            send_shots.gspro_connection_notified = True;
        send_shots.create_socket = True

    return
    

# Initialize function 'send_shots' static varibles
send_shots.gspro_connection_notified = False
send_shots.shot_count = 1
send_shots.create_socket = True
send_shots.sock = None
webcam_window = None
gspro_window = None


""" 
ES16 Connector for GSPro OpenAPI
With Voice Caddy like feed back
"""
def main():
    try:
        # Check for the GSPro OpenAPI connector
        found = False
        while not found:
          for proc in psutil.process_iter():
              if 'GSPconnect.exe' == proc.name():
                  found = True
                  break
          if not found:
              print_colored_prefix(Color.RED, "ES16 Connector ||", "GSPconnect.exe is not running. Reset it via GSPRO->Settings->Game->Reset GSPro Connect->Save")
              time.sleep(1)
                
        # Check for the GSPro OpenAPI connector
        print_colored_prefix(Color.GREEN, "GSPro ||", "Connecting to OpenConnect API ({}:{})...".format(HOST, PORT))
        
        voice=pyttsx3.init() # Initialize text to speech
        voice.setProperty('rate',265)
        voice.setProperty('voice', 'Microsoft Mary')
        voice.say("E S 16 Connector is Ready!")
        voice.runAndWait()

        found = False
        while not found:
          ser = serial.Serial('COM7', baudrate=115200,timeout=1.5)
          # Check if the port is open
          if ser.isOpen():
            print_colored_prefix(Color.GREEN, "ES16  ||", "Connecting to ES16 serial port: ({}:{})...".format(COM_PORT, COM_BAUD))
            found = True
          else:
            print_colored_prefix(Color.RED, "ES16  ||", "Serial port did not open. Bluetooth setup? Is the ES16 turned on?")
            timer.sleep(5)
         
        last_sound=0 
        # Check if there is any data to read
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
                          
           
          # Try to let us know if we hit a fat ball.  This is convoluted due to 
          # how it handles a fat shot vs a good shot.  So if pass == 1, it only 
          # received the ESTP string and not the ES16 string.  ES16 will always send 
          # and ESTP string regardless of bad or good shot data.  It only sends the 
          # the second string (ES16) of data if it has good data, so in that case we
          # can only tell a fat shot if the second read pass times out. (about 1.5sec).
                
          while (ser.inWaiting() == 0):  
              time.sleep(0.1)
        
          # pass 1.   Read data + carriage return First data should be the ESTP line.
          ESTPdata = ser.read(168)
          string_ESTPdata = ESTPdata.decode('utf-8')
          print(f"Pass1 data read: {len(ESTPdata)}")
          parsed_ESTPdata = process_input_string(string_ESTPdata)
        
        
          # This should not happen unless the pass2 timeout was too short mean more that 1.5 secs.  
          if (parsed_ESTPdata != None):
            print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","ERROR. ES16 Data recieved in pass1")
            print(f"pass1. Parsed ESTPdata: {parsed_ESTPdata}")
            voice.say("Correction!  Club Speed, "+parsed_ESTPdata["CS"]+".  Ball Speed, "+parsed_ESTPdata["BS"])
            voice.runAndWait()
            ser.flush()
            continue
        
          print(string_ESTPdata)
          
          # pass 2. Need to check for the second part fukk ES16 data set.
          time.sleep(0.75) # Just a little rest time
          ES16data=b""
        
          try:
            ES16data = ser.read(168)
          except serial.SerialTimeoutException:
            voice.say("Timeout pass 2. Misread shot sequence")
            voice.runAndWait()
            ser.flush()
            continue
        
          ES16string = ES16data.decode('utf-8')
          if (len(ES16string) == 0):
              voice.say("Misread shot sequence")
              voice.runAndWait()
              ser.flush()
              continue
           
          Pdata =  process_input_string(ES16string)                               
          if (Pdata != None):
            print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","Data recieved")
            print(Pdata)
            voice.say("Club Speed, "+Pdata["CS"]+".  Ball Speed, "+Pdata["BS"])
            voice.runAndWait()
          
            message = {
              "DeviceID": "ES16 Tour Plus",
              "Units": METRIC,
              "ShotNumber": 999,
              "APIversion": "1",
              "BallData": {
                  "Speed": Pdata["BS"],
                  "SpinAxis": Pdata["SPA"],
                  "TotalSpin": Pdata["SP"],
                  "BackSpin": round(Pdata["SP"] * math.cos(math.radians(Pdata["SPA"]))),
                  "SideSpin": round(Pdata["SP"] * math.sin(math.radians(Pdata["SPA"]))),
                  "HLA": Pdata["DIR"],
                  "VLA": Pdata["LA"]
              },
              "ClubData": {
                  "Speed": Pdata["BS"],
                  "AngleOfAttack": Pdata["AA"],
                  "FaceToTarget": Pdata["CFAC"],
                  "Path": Pdata["CPTH"],
                  "Loft": Pdata["SPL"]
              },
              "ShotDataOptions": {
                  "ContainsBallData": True,
                  "ContainsClubData": True,
                  "LaunchMonitorIsReady": True,
                  "LaunchMonitorBallDetected": True,
                  "IsHeartBeat": False
              }
            }
            # Put this shot in the queue
            shot_q.put(message)
            send_shots()
            ser.flush()
            continue
          else: 
            print(f"I'm confused while parsing: {ES16string_data}")
            voice.say("Misread shot sequence")
            voice.runAndWait() 
            ser.flush()
            continue
        
    except Exception as e:
        print_colored_prefix(Color.RED, "ES16 Connector ||","An error occurred: {}".format(e))
    except KeyboardInterrupt:
        print("Ctrl-C pressed")

    finally:
        # kill and restart the GSPconnector
        path = 'none'
        try:
          for proc in psutil.process_iter():
            if 'GSPconnect.exe' == proc.name():
              proc = psutil.Process(proc.pid)
              path=proc.exe()
              proc.terminate()
              print_colored_prefix(Color.RED, "ES16 Connector ||", "Closed GSPconnect.exe.")
              break
        except Exception as e:
            print(f"Exception: Failed to close and relaunch GSPconnect.exe. {path} ({e})")
            
        if send_shots.sock:
            send_shots.sock.close()
            print_colored_prefix(Color.RED, "ES16 Connector ||", "Socket to OpenAPI connection closed...")
        voice.stop()    
        ser.close()
        print("Quit!")


if __name__ == "__main__":
    time.sleep(1)
    main()


