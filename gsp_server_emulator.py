import socket
import json

HOST = 'localhost'  # Change this to your desired host
PORT = 921  # Change this to your desired port

def handle_connection(client_socket):
    while True:
        # Receive data from client
        data = client_socket.recv(1024).decode()
        if not data:
            break

        # Print received data
        print(f"Received data: {data}")

        # Parse JSON data
        try:
            data_dict = json.loads(data)
        except json.JSONDecodeError:
            print("Error decoding JSON data")
            break

        # Respond with message based on received code
        if data_dict.get("Code") == 200:
            response_dict = {"code": 200}
        elif data_dict.get("Code") == 201:
            response_dict = {
                "code": 201,
                "Player": {
                    "DistanceToTarget": 100,
                    "Club": "Driver",
                },
            }
        else:
            print(f"Unknown code: {data_dict.get('Code')}")
            break

        # Send response to client
        response_data = json.dumps(response_dict).encode()
        client_socket.sendall(response_data)

    # Close client socket
    client_socket.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection established from {client_address}")
            handle_connection(client_socket)

if __name__ == "__main__":
    start_server()
