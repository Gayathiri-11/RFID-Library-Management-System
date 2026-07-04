import serial
import time
import os

arduino = None

if os.environ.get("RENDER"):
    arduino = None
else:
    try:
        arduino = serial.Serial("COM5", 9600, timeout=1)
        time.sleep(2)
        print("Arduino Connected")
    except Exception as e:
        print(e)
        arduino = None


def scan_uid():

    if arduino is None:
        return "RFID_NOT_CONNECTED"

    arduino.reset_input_buffer()

    start = time.time()

    while time.time() - start < 5:   # Wait only 5 seconds

        if arduino.in_waiting > 0:

            uid = arduino.readline().decode().strip()

            if uid:
                print("Scanned UID:", uid)
                return uid

        time.sleep(0.1)

    return ""