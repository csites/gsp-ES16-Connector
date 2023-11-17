import re
import msvcrt
import time
import serial
import pyttsx3
import sys

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

# Example usage:
input_string = "ESTPPtr001CS091.08BS108.50000000000123456"  # Replace this with your input string
processed_string = process_input_string(input_string)
if (processed_string != None):
  print(processed_string)
input_string = "ES16Prt001CS081.0BS108.6CD000.0TD000.0LA20.1SP04736SF1.34CLDrvSPA+21.1DIR+01.1LDA00.0AA+5.4DL23.3MH000.0SC+000.0ST+000.0CPTH-04.5CFAC+02.3SPL17.9HT00.00BV8.38VER179End"
parsed_data = process_input_string(input_string)
print(processed_string)
print(parsed_data['CL'])
print(parsed_data['LA'])
print(parsed_data['CS'])
print(parsed_data['SPA'])
print(parsed_data['CPTH'])
print(parsed_data['CFAC'])
print("end")

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

print_color_prefix(Color.GREEN,"||  ES16 SERIAL LINE READ/PARSE  ||","Opening serial port COM7")
print_color_prefix(Color.GREEN,"||  Press a key to change clubs  ||","` 1 2 3 4 5 6 7 8 9 0 - = \ p")

 # Open the COM port at 115200 baud
try: 
  ser = serial.Serial('COM7', baudrate=115200)
except:
  print_color_prefix(Color.RED, "||  ES16 SERIAL LINE No COM port ||","Data Not recieved. Exiting.")
  sys.exit(1)

voice=pyttsx3.init() # Initialize text to speech
voice.setProperty('rate',265)
voice.setProperty('voice', 'Microsoft Mary')
  
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
                  
  # Read the data from the port
  string_data = string_data2 = ""
  if (ser.inWaiting() == 3):
      print(ser.read(3))
  if (ser.inWaiting() > 0): 
    ser.timeout = 0.3
    try: 
      data = ser.read(168)
      ser.timeout=0
      string_data = data.decode('utf-8')
      print("string_data: ",string_data)
    except serial.SerialTimeoutException:
      ser.timeout=0
      ser.flush()
      continue
    # The ESTP send 1 line of radar only data (BS, and CS) on mis-read (ie: fat shots). 
    # It sends a 2nd line of radar and optical or none at all on a misread.  Maybe have 
    # our program say "Misread swing again."
    if (ser.inWaiting() > 0):
      ser.timeout = 0.3
      try: 
        data2 = ser.read(168)
        ser.timeout=0
        string_data2 = data2.decode('utf-8')
        print("string data2: ",string_data2)
      except serial.SerialTimeoutException:
        ser.timeout=0
        ser.flush()
        continue
  ser.timeout = 0
  if (len(string_data) == 0 and len(string_data2) == 0):
      continue
        
  parsed_data = process_input_string(string_data)
  if (parsed_data == None):
    print("ESTP data: ",string_data[:29])
    ser.flush()
    continue
  if (len(parsed_data) == 3):
    print("ESTP data: ",parsed_data)
    ser.flush()
    continue
  parsed_data2 = process_input_string(string_data2)
  if (parsed_data2 != None):
    print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","Data recieved")
    print("Parsed data2: ",parsed_data2)
    voice.say("Club Speed, "+parsed_data2["CS"]+".  Ball Speed, "+parsed_data2["BS"])
    voice.runAndWait()
  else:
    voice.say("Misread shot")
    voice.runAndWait()
    
voice.stop()    
ser.close()
print("Quit!")
sys.exit(0)
        
