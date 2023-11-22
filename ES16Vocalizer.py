"""
ES16 VOCALIZER.  An Ernest Sports Vocalizer of Swing Data
CSITES 2023.

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

def timed_serial_read(ser, length, seconds):
""" 
  Timed serial read function
  This fumction reads a serial port upto 168 characters under a specified number of milliseconds.
  It returns the buffer and the time required to get the buffer.   If it does not reach the 
  length.
"""   
    ccnt = 0
    stime = timeit.default_timer()

    # timer loop
    while (timeit_default_timer() - stime < seconds):
      if ser.inWaiting():
          c = b""
          while True:
              try:
                while(ser.inWaiting() > 0):
                  val = ser.read(1)
                  break
              except serial.SerialException as e:
                print(f"Serial port error: {e}")
                break
              finally:  
                if val == b"\r" or (timeit_default_time() - stime >= seconds) or ccnt > length:
                    break
                else:
                    c += val
                    ccnt = ccnt + 1
          buffer.append(c.decode('utf-8'))  # Decode the bytes to a string
          ser.timeout = None
    timecnt = timeit.default_timer() - stime
    if (ccnt >= length):
        return buffer, timecnt, ccnt 
    else:
        return None, timecnt, ccnt
"""
Club_mapping is for keyboard keypress to voice string of club and ES16 Club change code
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
  ser = serial.Serial('COM7', baudrate=115200)
except:
  print_color_prefix(Color.RED, "||  ES16 SERIAL LINE No COM port ||","Data Not recieved. Exiting. Check unit and bluetooth connection")
  sys.exit(1)

# Initialize the pyttsx3 Voice library
voice=pyttsx3.init() # Initialize text to speech
voice.setProperty('rate',265)
voice.setProperty('voice', 'Microsoft Mary')
  
# Check if there is any data to read
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
# how it handles a fat shot vs a good shot.  So in pass == 1, it only 
# received the ESTP string and not the ES16 string.  In pass2 it may 
# or may not have another string of 168 bytes of data.  The only way 
# to tell is if # the pass2 serial read times out, or you have data.
# (the timeout is unknown (but it feels like 1.5 secs).

  if (ser.inWaiting() > 0):
     # pass 1.   Read data + carriage return First data should be the ESTP line.
     timeout = 300 # milliseconds.
     pass_cnt = 1
     data, retime, rcnt = timed_serial_read(ser, timeout, 168)
     if (data == None):
        print("Pass1: String was None, Returned_time: {retime}, Return_Lenght: {rcnt}.  Check")
        continue  # Loop again
#       string_data = data.decode('utf-8')
     print(f"Pass1 data read: {len(data)}")
     parsed_data = process_input_string(data)
     print(data)

     # force a 1/2 slee       # Check to see if we have real data in pass 1.  Indicates that the sleep wasn't long enough.
     if (parsed_data != None):
        # You should not be here.  This should not happen.
        print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","Data recieved in pass2")
        print("Parsed data2: ",parsed_data)
        voice.say("Club Speed, "+parsed_data["CS"]+".  Ball Speed, "+parsed_data["BS"])
        voice.runAndWait()
        pass_cnt=2
        ser.flush()
        # Continue to the while loop. 
        continue

     # pass 2.  Setup a timed serial reader.  
     print("Pass1 complete.   Now entering pass2")
     timeout = 1500 # millisecs. 1.5 secs.
     data2, retime. rcnt = timed_serial_read(ser, timeout, 168) 
     if (data2 == None):
        print("Pass2: String was None, Returned_time: {retime}, Return_Lenght: {rcnt}.  Check")
        voice.say("Misread shot sequence")
        voice.runAndWait()
        ser.flush()
        continue  # Loop again

     string_data2 = data2   
     # string_data2 = data2.decode('utf-8')   
     parsed_data2 = process_input_string(string_data2) 
     if (parsed_data2 != None):
          # This should be a normal well struck ball with all the data.
          print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","Data recieved in pass2")
          print("Parsed data2: ",parsed_data2)
          voice.say("Club Speed, "+parsed_data2["CS"]+".  Ball Speed, "+parsed_data2["BS"])
          voice.runAndWait()
          pass_cnt=2
          ser.flush()
          break
     else:
          pass_cnt = 1
          voice.say("Misread shot sequence")
          voice.runAndWait()
          ser.flush()
          continue
                   
     ser.timeout=0
     ser.flush()
     print("serial read1 timeout")
     voice.say("Serial read1 timeout!")
     voice.runAndWait()
     continue
        
    # End of pass1 
# End While (loop)

voice.stop()    
ser.close()
print("Quit!")
sys.exit(0)
        
