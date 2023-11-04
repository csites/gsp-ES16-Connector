from concurrent.futures import ThreadPoolExecutor
import time
import sys
import os
import json
import ctypes
from socket_connection import create_socket_connection
from PIL import Image
from datetime import datetime
import cv2
from matplotlib import pyplot as plt
import platform
import random
import math
import re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading
from queue import Queue
import select
import pywinauto
import psutil
from pathlib import Path
import chime

import socket
import serial

# To talk to GSPro OpenAPI
def create_socket_connection(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (host, port)
    sock.connect(server_address)
    sock.settimeout(5)
    return sock

# To Read the ES16 Tour Plus LM.

def read_serial_data(ser):
    buffer = []

    while True:
        if ser.inWaiting():
            c = b""
            while True:
                val = ser.read(1)
                if val == b"\r":
                    break
                else:
                    c += val
            buffer.append(c.decode('utf-8'))  # Decode the bytes to a string

        if len("".join(buffer)) >= 168:
            return buffer

# Send Club Change to ES16
def send_serial_club(port):

  return

# Create the key/value variable lists for club conversion.
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


# Print the temporary directory created at runtime, due to --onefile
# print(os.listdir(sys._MEIPASS))

chime.theme('big-sur')
screenshot_folder = "bad_screenshots"
shot_q = Queue()


class TestModes :
    none = 0
    auto_shot = 1 # allows debugging without having to hit shots

# Loading settings
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
        
test_mode = TestModes.none
#test_mode = TestModes.auto_shot

class Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'

def print_colored_prefix(color, prefix, message):
    print(f"{color}{prefix}{Color.RESET}", message)

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
gsp_stat.Ready = test_mode == TestModes.auto_shot

def process_gspro(resp):
    global putter_in_use
    global gsp_stat

    code_200_found = False

    jsons = re.split('(\{.*?\})(?= *\{)', resp.decode("utf-8"))
    for this_json in jsons:
        if len(this_json) > 0 :
            #print(this_json)
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
                  if (gsp_stat.Club == "LW" and gsp_stat.DistToPin < 40):
                    Club_change = "CLUBCHPLOFT000\r"
                  else:
                    Club_change = "CLUB"+gs_to_es[gsp_stat.Club]+"LOFT000\r"
                  ser.send(Club_change)
                  gsp_stat.Club_previous == gsp_stat.Club
                        
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
            process_gspro(data) # don't need return value at this stage
            # OK, if club changes we need to send that that to ES16.
             
        # Check if we have a shot to send.  If not, we can return
        try:
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
        send_shots.sock.sendall(json.dumps(message).encode())

        print_colored_prefix(Color.GREEN,"MLM2PRO Connector ||", f"Shot {send_shots.shot_count} - Ball: {ball_speed} MPH, Spin: {total_spin} RPM, Axis: {spin_axis}°, HLA: {hla}°, VLA: {vla}°, Club: {club_speed} MPH")

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
                print_colored_prefix(Color.BLUE, "MLM2PRO Connector ||", "Shot data has been sent successfully...")
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
        print_colored_prefix(Color.RED, "MLM2PRO Connector ||", "No response from GSPRO. Retrying")
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


def main():
    global api
    global gspro_window
        
    AUTOSHOT_DELAY = 1 # number of seconds between automatic shots
    try:


        # Check for the GSPro OpenAPI connector
        found = False
        while not found:
            for proc in psutil.process_iter():
                if 'GSPconnect.exe' == proc.name():
                    found = True
                    break
            if not found:
                print_colored_prefix(Color.RED, "MLM2PRO Connector ||", "GSPconnect.exe is not running. Reset it via GSPRO->Settings->Game->Reset GSPro Connect->Save")
                time.sleep(1)
        
        club_speed = ball_speed_last = total_spin_last = spin_axis_last = hla_last = vla_last = club_speed_last = path_angle_last = face_angle_last = None
        screenshot_attempts = 0
        incomplete_data_displayed = False
        ready_message_displayed = False

        # Create a ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=3)

        print_colored_prefix(Color.GREEN, "GSPro ||", "Connecting to OpenConnect API ({}:{})...".format(HOST, PORT))
 
        last_sound=0            
        while True:

            # send any pending shots from the queue.  Will block while awaiting shot responses
            send_shots()

            if not gsp_stat.Putter:

                         if AUDIBLE_MLM_READY and gsp_stat.RollingOut:
                            now = time.perf_counter()
                            if total_dist != '-':        # MLM is done with current shot
                                gsp_stat.RollingOut = False
                                if now - last_sound < 2: # as long as the last chime was from the current shot
                                    chime.success(sync=True, raise_error=True)
                            else:
                                if now - last_sound > 1:
                                    last_sound = now
                                    chime.info(sync=True, raise_error=True)
                                
                else :
                    if gsp_stat.Ready and (time.perf_counter() - gsp_stat.ReadyTime) > AUTOSHOT_DELAY:
                        d = gsp_stat.DistToPin
                        if d > 300:
                            d = 300
                        if gsp_stat.Putter:
                            result = [1.5*d, 0, 0,random.randint(-2,2),0,4] # fake shot data
                        else:
                            # general shots
                            result = [round(d/1.95+20), round(-26.6*d+10700), random.randint(-3,3),random.randint(-2,2),round(-0.1*d+41),round((d/1.85+20)/1.5)] # fake shot data
                            # driver robot
                            #result = [140+random.randint(-3,3), 2500+100*random.randint(-6,6), 0, 0, 12+random.randint(-3,3), 99+random.randint(-3,3)]
                        ball_speed, total_spin, spin_axis, hla, vla, club_speed = map(str, result)

                path_angle = '-'
                face_angle = '-'
            else: # putter is in use
   
                message = {
                    "DeviceID": "ES16 Tour Plus",
                    "Units": METRIC,
                    "ShotNumber": 999,
                    "APIversion": "1",
                    "BallData": {
                        "Speed": ball_speed,
                        "SpinAxis": spin_axis,
                        "TotalSpin": total_spin,
                        "BackSpin": round(total_spin * math.cos(math.radians(spin_axis))),
                        "SideSpin": round(total_spin * math.sin(math.radians(spin_axis))),
                        "HLA": hla,
                        "VLA": vla
                    },
                    "ClubData": {
                        "Speed": club_speed,
                        "Path": path_angle,
                        "FaceToTarget": face_angle,
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
                ball_speed_last = ball_speed
                total_spin_last = total_spin
                spin_axis_last = spin_axis
                hla_last = hla
                vla_last = vla
                club_speed_last = club_speed
                path_angle_last = path_angle
                face_angle_last = face_angle
            time.sleep(.5)

    except Exception as e:
        print_colored_prefix(Color.RED, "MLM2PRO Connector ||","An error occurred: {}".format(e))
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
                    print_colored_prefix(Color.RED, "MLM2PRO Connector ||", "Closed GSPconnect.exe.")
                    break
        except Exception as e:
            print(f"Exception: Failed to close and relaunch GSPconnect.exe. {path} ({e})")
            
        if send_shots.sock:
            send_shots.sock.close()
            print_colored_prefix(Color.RED, "MLM2PRO Connector ||", "Socket to OpenAPI connection closed...")

        if PUTTING_MODE == 1 or PUTTING_MODE == 3:
            closed = False
            try:
                # there are 2 such processes to kill, so don't break out when we close one
                # Check before doing this that we are the ones in control of the external putting process.  
                if PUTTING_MODE == 1:
                for proc in psutil.process_iter():
                    if 'ball_tracking.exe' == proc.name():
                        proc = psutil.Process(proc.pid)
                        proc.terminate()
                        closed = True
                if closed:
                    print_colored_prefix(Color.RED, "MLM2PRO Connector ||", "Closed ball_tracking app")
                        
            except Exception as e:
                print(f"Exception: Failed to close ball tracking app ({e})")


if __name__ == "__main__":
    time.sleep(1)
    plt.ion()  # Turn interactive mode on.
    main()
