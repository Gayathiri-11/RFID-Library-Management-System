import serial
import time
import requests

arduino = serial.Serial("COM7", 9600, timeout=1)

time.sleep(2)

RENDER_URL = "https://rfid-library-management-system-1.onrender.com/api/rfid/update"

print("Arduino connected on COM7")
print("Waiting for RFID cards/tags...")

while True:
    try:
        if arduino.in_waiting:
            data = arduino.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if data:
                print("ARDUINO:", data)

                if data.startswith("UID:"):
                    uid = data.replace("UID:", "").strip()

                    print("Detected UID:", uid)

                    try:
                        response = requests.post(
                            RENDER_URL,
                            json={"uid": uid},
                            timeout=10
                        )

                        print("Server response:", response.status_code)

                    except requests.RequestException as e:
                        print("Error sending UID:", e)

        time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nRFID bridge stopped.")
        break

    except Exception as e:
        print("Bridge error:", e)