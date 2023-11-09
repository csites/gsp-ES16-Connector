import re
import keyboard
import timer
import serial

class Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'

def print_color_prefix(color, prefix, message):
    print(f"{color}{prefix}{Color.RESET}", message)

def check_for_key():
    key = keyboard.read_key()
    return key

def process_input_string(input_string):
    """
    Process_input_string takes a serialized data retrieved from an ES16 Lauch monitor.
    The ES16 data string is read from a wifi USB to serial port and shows up as COM7
    or a COM port higher than COM3.  This function converts it to a single string 
    of comma seperated Key Value,  It also filters off the Tour Plus extra line.
    """
    # Check for Tour Pluse if the input string begins with 'ESTP' and ignore it
    if input_string.startswith('ESTP'):
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

key_mapping = {
    "`": "Drv",
    "1": "3Wd",
    "2": "5Wd",
    "3": "4Hy",
    "4": "4Ir",
    "5": "5Ir",
    "6": "6Ir",
    "7": "7Ir",
    "8": "8Ir",
    "9": "9Ir",
    "0": "Ptw",
    "-": "Gpw",
    "=": "Swd",
    "\\": "Chp",
    "p": "Ptt",
}

print_color_prefix(Color.GREEN,"||  ES16 SERIAL LINE READ/PARSE  ||","Opening serial port COM7")

print_color_prefix(Color.GREEN,"||  Press keys: `1234567890-=\p to change clubs.  ||","Opening serial port COM7")

 # Open the COM port at 115200 baud
try: 
  ser = serial.Serial('COM7', baudrate=115200)
except:
  print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE No COM port ||","Data Not recieved")
  
# Check if there is any data to read
while True:
  if (ser.inWaiting() > 0):
      # Read the data from the port
      data = ser.read(ser.inWaiting())
      parsed_data = process_input_string(data)
      if (parsed_data == Nono):
        continue
      print_color_prefix(Color.YELLOW, "||  ES16 SERIAL LINE READ/PARSE  ||","Data recieved")
      print(parsed_data)
  else:
      print("No data available to read")

      # Check if a key has been pressed
      key = check_for_key()
      if key:
        # Get the corresponding string from the dictionary
        string = key_mapping[key]
        # Construct the message string
        club_change_string = "CLUB" + string + "LOFT000\r"
        msg = club_change_string.encode('ascii') 
        msg = s.encode('ascii')
        print_color_prefix(Color.RED, "|| ES16 Change Clubs ||", msg)
        ser.write(msg)
        
        while (ser.inWaiting() <= 0):  
          timer.sleep(0.1)
              # Read the data from the port
        data = ser.read(ser.inWaiting())
        print(data)
        