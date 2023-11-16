import msvcrt
import pyttsx3

class Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'

def print_color_prefix(color, prefix, message):
    print(f"{color}{prefix}{Color.RESET}", message)

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

voice=pyttsx3.init() # Initialize text to speech
voice.setProperty('rate',265)
voice.setProperty('voice', 'Microsoft Mary')

loop = True
while (loop == True):

  # Check if a key is pressed
  if msvcrt.kbhit():
      # Read the key and print its value
      key = msvcrt.getch()
      if (key == 'q'):
        loop = false
        continue
      skey = str(chr(ord(key)))  
      if skey in club_mapping:
        # Get the corresponding string from the dictionary
        string = club_mapping[skey][1]
        voice.say("Club selected: "+club_mapping[skey][0])
        # Construct the message string
        club_change_string = "CLUB" + string + "LOFT000\r"
        msg = club_change_string.encode('ascii') 
        print_color_prefix(Color.RED, "|| ES16 Change Clubs ||", msg)
        voice.runAndWait()
        continue
      else:
        print("You pressed key: ",key)
