import serial
""" 
  Timed serial read function
  This fumction reads a serial port upto 168 characters under a specified number of milliseconds.
  It returns the buffer and the time required to get the buffer.   If it does not reach the 
  length
"""   
def timed_serial_read(ser, length, seconds):
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
