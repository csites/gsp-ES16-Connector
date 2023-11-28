import re
import msvcrt
import time
import serial
import pyttsx3
import sys
import timeit

from golf_shot import BallData, ClubHeadData
from gsproconnect import GSProConnect

class Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'

def print_color_prefix(color, prefix, message):
    print(f"{color}{prefix}{Color.RESET}", message)
      
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
Club mapping key-press to Voice and ES16 Club Code
"""
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

gspclub_mapping = {
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
        
