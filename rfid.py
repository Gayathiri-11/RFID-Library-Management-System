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

    while True:
        if arduino.in_waiting:

            uid = arduino.readline().decode().strip()

            if uid:
                return uid