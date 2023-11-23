"""
ES16 VOCALIZER.  An Ernest Sports Vocalizer of Swing Data
CSITES 2023.  MIT License.

This program reads the Ernest Sports ES16, ES16 Tour Plus, and ES2020
Untested on the ES2020 or original ES16.  
Launch monitors (a bluetooth serial device) and parses the data and uses
the pyttsx3 voice library to say the ball speed and club speed for each 
suscessfull swing.  Kind of like the Speech Caddy LM.  It reads the keyboard 
for club selection and will send that to the ES16.  The keys are 
`1234567890-=\p and corrispond to driver to putter.  Lob wedge places the 
unit into CHP mode (and all optical mode).  Putter is also pur optical.

The ES16 and Tour Plus will miss read if you hit a fat shot and not provide
data other than ball speed and club speed (pure radar only data). On those
shots the ES16 Vocalizer will simply say "Misread shot sequence"

ES16 funk. On a misread shot, it returns a single 168 byte string beginning
with ESTP Club Speed and Ball Speed.  On a good shot, it returns that string 
followed by a line that begins with ES16. To be able to distingquish a misread
shot vs a good shot, I use a timer to wait for the second set of data.  if it 
doesn't appear in 1.5s I report it as a misread.  

Note:  I'm using the Windows library msvcrt library for the kbhit() function.
For linux, the library getch may work.
 
"""  
import re
import msvcrt
import time
import serial
import pyttsx3
import sys
import timeit

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
    "`": ("Driver", "Drv"),
    "1": ("3 Wood", "3Wd"),
    "2": ("5 Wood", "5Wd"),
    "3": ("4 Hybrid", "4Hy"),
    "4": ("4 Iron", "4Ir"),
    "5": ("5 Iron", "5Ir"),
    "6": ("6 Iron", "6Ir"),
    "7": ("7 Iron", "7Ir"),
    "8": ("8 Iron", "8Ir"),
    "9": ("9 Iron", "9Ir"),
    "0": ("Pitch Wedge", "Ptw"),
    "-": ("Gap Wedge", "Gpw"),
    "=": ("Sand Wedge", "Swd"),
    "\\": ("Lob Wedge Chip", "Chp"),
    "p": ("Putter", "Ptt"),
}

# Example usage:
#input_string = "ESTPPtr001CS091.08BS108.50000000000123456"  # Replace this with your input string
#processed_string = process_input_string(input_string)
#if (processed_string != None):
#  print(processed_string)
#input_string = "ES16Prt001CS081.0BS108.6CD000.0TD000.0LA20.1SP04736SF1.34CLDrvSPA+21.1DIR+01.1LDA00.0AA+5.4DL23.3MH000.0SC+000.0ST+000.0CPTH-04.5CFAC+02.3SPL17.9HT00.00BV8.38VER179End"
#parsed_data = process_input_string(input_string)
#print(processed_string)
#print(parsed_data['CL'])
#print(parsed_data['LA'])
#print(parsed_data['CS'])
#print(parsed_data['SPA'])
#print(parsed_data['CPTH'])
#print(parsed_data['CFAC'])
#print("end")


print_color_prefix(Color.GREEN,"||  ES16 SERIAL LINE READ/PARSE  ||","Opening serial port COM7")
print_color_prefix(Color.GREEN,"||  Press a key to change clubs  ||","` 1 2 3 4 5 6 7 8 9 0 - = \ p")

 # Open the COM port at 115200 baud
try: 
  ser = serial.Serial('COM7', baudrate=115200,timeout=1.5)
except:
  print_color_prefix(Color.RED, "||  ES16 SERIAL LINE No COM port ||","Data Not recieved. Exiting. Check unit and bluetooth connection")
  sys.exit(1)

# Initialize the pyttsx3 Voice library
voice=pyttsx3.init() # Initialize text to speech
voice.setProperty('rate',265)
voice.setProperty('voice', 'Microsoft Mary')
  
# Check if there is any data to read.  If a keyboard character is pressed see if it's a club selection.
# If it is a club selection, set the club string and send club change to the ES16.
pass_cnt=0
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

  ES16string_data = ES16data.decode('utf-8')   
  parsed_ES16data =  process_input_string(ES16string_data) 
  if (parsed_ES16data != None):
      print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","Data recieved in pass2")
      print("Parsed data2: ",parsed_ES16data)
      voice.say("Club Speed, "+parsed_ES16data["CS"]+".  Ball Speed, "+parsed_ES16data["BS"])
      voice.runAndWait()
      ser.flush()
  else:
      # If we are here, then the 2nd read pass returned something unexpected.
      print(ES16data)  
      voice.say("Timeout pass 2. Misread shot sequence")
      voice.runAndWait()
      ser.flush()
      continue
  continue    
        
  # End of pass1 
# End While (loop)

voice.stop()    
ser.close()
print("Quit!")
sys.exit(0)
        
