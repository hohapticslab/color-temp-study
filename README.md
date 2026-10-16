# Color Temperature Study

This repository contains programs used for experiments investigating the relationship between color and perceived temperature.

The project includes a web-based Visual Analog Scale (VAS) experiment, simple monitoring and manual control tools for the PLC-24V10A temperature controller, and a Peltier-based color-temperature matching experiment.

## Files

### `index.html`

A web-based experiment interface for evaluating temperature impressions evoked by colors.

Participants view color stimuli and rate how cold or hot each color feels using a continuous Visual Analog Scale (VAS).

Main features:

- Displays multiple color stimuli.
- Uses a continuous VAS ranging from "Very cold" to "Very hot".
- Supports Japanese, English, and Traditional Chinese.
- Collects participant information such as age, gender, color vision difficulty, and finger temperature.
- Includes practice trials using physical thermal stimuli.
- Can submit experimental data online or save the data as a CSV file.

Open `index.html` in a web browser to run the experiment.

---

### `temp_display.py`

A simple serial monitoring script for the PLC-24V10A temperature controller.

The script connects to the controller via serial communication and displays:

- Current temperature
- Target temperature
- Timestamp

The temperature information is updated once per second.

Default serial settings:

- Port: `COM6`
- Baud rate: `115200`

Run:

```bash
python temp_display.py
```

Press `Ctrl+C` to stop the program.

> Change `PORT` in the script if the controller is connected to a different COM port.

---

### `set_temp_change.py`

A manual temperature control script for the PLC-24V10A temperature controller.

The script displays the current and target temperatures once per second while allowing the target temperature to be changed from the keyboard.

Controls:

- `↑` : Increase the target temperature by 0.5 °C
- `↓` : Decrease the target temperature by 0.5 °C
- `Q` or `Esc` : Exit
- `Ctrl+C` : Exit

The initial target temperature is 30.0 °C, and the selectable range is 15.0–45.0 °C.

Run:

```bash
python set_temp_change.py
```

> `set_temp_change.py` uses `msvcrt` for keyboard input and is intended for Windows.

---

### `color_temp_exp.py`

The main Peltier-based color-temperature matching experiment.

The program presents two sets of color stimuli:

- 12-color set
- 16-color set

A total of 28 colors are presented. The order of the two sets and the colors within each set are randomized.

For each color, the participant touches the Peltier module and adjusts its temperature until the temperature sensation matches the displayed color.

Controls:

- `↑` : Increase the Peltier target temperature
- `↓` : Decrease the Peltier target temperature
- `Enter` : Confirm the selected temperature and proceed
- `Space` : Continue after the break between color sets
- `Esc` : Abort and exit the experiment

The temperature adjustment starts with a 3 °C step. When the adjustment direction is reversed, the step size is reduced from 3 °C to 2 °C and then to 1 °C for finer adjustment.

Before each trial, the Peltier module returns to 32.0 °C. The next trial starts after the measured temperature remains within ±0.2 °C of the target temperature for 3 seconds.

During the experiment, a separate monitor window displays:

- Current set temperature
- Measured temperature
- Real-time temperature graph
- Trial and experiment status

Auditory cues indicate when the participant should touch and release the Peltier module.

After the experiment, two CSV files are saved:

- Experimental results
- 1-second temperature log

The files are stored in:

```text
Desktop/Peltier Device/ExperimentData
```

Run:

```bash
python color_temp_exp.py
```

---

## Requirements

- Windows
- Python 3
- PLC-24V10A temperature controller
- Peltier module
- Serial connection between the PC and PLC-24V10A

Python packages:

```bash
pip install pyserial matplotlib
```

`color_temp_exp.py` also uses Tkinter for its graphical interface and `winsound` for auditory cues.

## Serial Communication

The Python programs use the following serial settings by default:

```text
Port: COM6
Baud rate: 115200
```

If the PLC-24V10A is assigned to another COM port, change the `PORT` variable in the corresponding Python script.

## Notes

Before running the temperature-control programs, make sure that the PLC-24V10A, Peltier module, temperature sensors, cooling system, and power supply are connected correctly.

The temperature range used by the control programs is limited to 15–45 °C.

## Repository Structure

```text
color-temp-study/
├── index.html
├── temp_display.py
├── set_temp_change.py
├── color_temp_exp.py
└── README.md
```