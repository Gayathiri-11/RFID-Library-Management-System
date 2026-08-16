import serial
import time
import os

arduino = None

# RFID reader works only when Flask is running on your local PC.
# Render cannot access your PC's COM port.
if not os.environ.get("RENDER"):
    try:
        arduino = serial.Serial("COM7", 9600, timeout=1)
        time.sleep(2)
        print("Arduino Connected on COM7")
    except Exception as e:
        print("Arduino connection error:", e)
        arduino = None


def scan_uid():

    if arduino is None:
        return "RFID_NOT_CONNECTED"

    try:
        arduino.reset_input_buffer()

        while True:
            if arduino.in_waiting:

                data = arduino.readline().decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if data.startswith("UID:"):
                    uid = data.replace("UID:", "").strip()

                    if uid:
                        print("RFID UID:", uid)
                        return uid

    except Exception as e:
        print("RFID scan error:", e)
        return "RFID_NOT_CONNECTED"
