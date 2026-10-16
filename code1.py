import time
import serial

PORT = "COM6"
BAUD_RATE = 115200

with serial.Serial(
    PORT,
    BAUD_RATE,
    timeout=1,
    write_timeout=1
) as plc:

    plc.reset_input_buffer()
    plc.reset_output_buffer()

    print("Connected to the PLC. Press Ctrl+C to exit.\n")

    try:
        while True:
            plc.reset_input_buffer()
            plc.write(b"RTP\n")
            plc.flush()

            response = plc.readline().decode("ascii").strip()

            if response:
                data = response.split(",")

                if data[0] == "RTP" and len(data) >= 4:
                    target = int(data[1]) / 100
                    current = int(data[2]) / 100

                    print(
                        f"[{time.strftime('%H:%M:%S')}] "
                        f"Current Temperature: {current:.2f} °C "
                        f"/ Target Temperature: {target:.2f} °C"
                    )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nProgram terminated.")