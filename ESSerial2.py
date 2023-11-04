import serial
import cv2

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

try:
    ser = serial.Serial("COM7", 115200)
    while True:
      data = read_serial_data(ser)
      print(data)
      key = cv2.waitKey(1) & 0xFF
      # if the 'q' key is pressed, stop the loop
      if key == ord("q"):
        break

except serial.SerialException as e:
    print(f"Serial port error: {e}")
finally:
    ser.close()
