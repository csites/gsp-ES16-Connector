import socket
import json
import msvcrt
import pyttsx3
import traceback

"""
GSP_SERVRT_EMULATOR:  This program can emulate the socket connectivity of the GSPConnector.exe program, which is the 
openAPI connector for the GSPro Golf Simulator.  It does not validate any of the data sent to it, it just prints what
it recieves and sends a CODE 200 reponse back, or it can send a CODE 201 Player data for a club change.   This is use
full if your debugging a connector for the GSPro OpenAPI interface but either don't have the game available or to save
time in debugging.  You can select a club using the keys '1234567890-=\p (see club_mapping below)
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

HOST = 'localhost'  # Change this to your desired host
PORT = 921  # Change this to your desired port
voice=""


def handle_connection(client_socket):
  global voice
  try:  
    print("Enter Handle_connection loop")
    loop=True
    while (loop==True):
        print("In loop")
        # Check for a club selection
        key = msvcrt.getch()
        print(key)
        if (ord(key) == ord('q')):
            loop = False
            break
        skey = str(chr(ord(key)))          
        if skey in club_mapping:
            print("Club Selected,"+club_mapping[skey][0])
            voice.say("Club Selected,"+club_mapping[skey][0])
            voice.runAndWait()
            if voice._inLoop:
                voice.endLoop()
            # Get the corresponding string from the dictionary
            club = club_mapping[skey][2]
            message = {
            	"Code": "201",
            	"Message": "GSPro Player Information",
            	"Player": {
                "DistanceToTarget": 50,
            		"Handed": "RH",
            		"Club": club
            	}
            }
            json_message = json.dumps(message).encode()
            # Construct the message string
            print("|| GSP Pseudo-server Change Clubs ||", message)
            client_socket.sendall(json_message)
            continue
          
        # Receive data from client
        data = client_socket.recv(1024).decode()
        print(f"DATA: {len(data)}")
        if not data:
            continue

        # Print received data
        print(f"Received data: {data}")

        # prepare a standard 200 response
        response_dict = {
            "Code": "200",
            "Message": "OpenAPI simulator OK reply"
        }
        print("Sending 200 message")
        # Send response to client
        response_data = json.dumps(response_dict).encode()
        client_socket.sendall(response_data)
        continue

  except Exception as e:
    print("Error ")
    print(e)
    traceback_obj = traceback.format_exc()  # Get the traceback information
    print(traceback_obj)  # Print the full traceback
    # Access the line number:
    line_number = traceback_obj.splitlines()[-1].split()[-1]  # Extract line number from traceback
    print("Error occurred on line:", line_number)

  return    

def start_server():
  try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection established from {client_address}")
            handle_connection(client_socket)
            print("Returned from handle_connection")
            client_socket.close()
            break
            
  except Exception as e:
    print("Error ")
    print(e)
    traceback_obj = traceback.format_exc()  # Get the traceback information
    print(traceback_obj)  # Print the full traceback
    # Access the line number:
    line_number = traceback_obj.splitlines()[-1].split()[-1]  # Extract line number from traceback
    print("Error occurred on line:", line_number)
           
if __name__ == "__main__":

    voice=pyttsx3.init() # Initialize text to speech
    voice.setProperty('rate',265)
    voice.setProperty('voice', 'Microsoft Mary')
    voice.say("GSPro openAPI connector Simulator is Ready!")
    voice.runAndWait()
    try:
      start_server()
    except Exception as e:
      print(e)
      traceback_obj = traceback.format_exc()  # Get the traceback information
      print(traceback_obj)  # Print the full traceback
      # Access the line number:
      line_number = traceback_obj.splitlines()[-1].split()[-1]  # Extract line number from traceback
      print("Error occurred on line:", line_number)
