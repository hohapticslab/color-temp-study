import time
import serial
import msvcrt


PORT = "COM6"
BAUD_RATE = 115200
temperature = 30.0


def command(plc, cmd):
    plc.reset_input_buffer()
    plc.write((cmd + "\r\n").encode("ascii"))
    plc.flush()
    return plc.readline().decode("ascii").strip()


with serial.Serial(PORT, BAUD_RATE, timeout=1, write_timeout=1) as plc:
    plc.reset_input_buffer()
    plc.reset_output_buffer()

    command(plc, f"STE,{int(temperature * 100)}")
    command(plc, "STA")

    print("↑↓: ±0.5°C    Ctrl+C: Exit\n")

    try:
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getwch()

                if key in ("\x00", "\xe0"):
                    key = msvcrt.getwch()

                    if key == "H":
                        temperature = min(45.0, temperature + 0.5)
                    elif key == "P":
                        temperature = max(15.0, temperature - 0.5)

                    command(plc, f"STE,{int(temperature * 100)}")
                    print(f"Target Temperature → {temperature:.1f} °C")

                elif key.lower() == "q" or key == "\x1b":
                    break

            response = command(plc, "RTP")

            if response.startswith("RTP,"):
                data = response.split(",")
                target = int(data[1]) / 100
                current = int(data[2]) / 100

                print(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"Current Temperature: {current:.2f} °C "
                    f"/ Target Temperature: {target:.2f} °C"
                )

            time.sleep(1)

    except KeyboardInterrupt:
        pass

    finally:
        command(plc, "STO")
        print("\nPeltier module stopped.")