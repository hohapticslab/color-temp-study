import csv
import random
import time
import tkinter as tk
import threading
import queue
try:
    import winsound
except ImportError:
    winsound = None
from datetime import datetime
from pathlib import Path
import serial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
PORT = "COM6"
BAUD = 115200
MIN_TEMP, MAX_TEMP, DEFAULT_TEMP = 15.0, 45.0, 32.0
SAMPLE_MS = 200
KEY_RELEASE_MS = 80
TOLERANCE = 0.2
STABLE_REQUIRED_SECONDS = 3.0
LOG_INTERVAL = 1.0
TOUCH_SECONDS = 5
INITIAL_STEP = 3.0
WAIT_SECONDS_BY_STEP = {3.0: 12, 2.0: 10, 1.0: 6}
COLORS_12 = [
    ("12_01", (255,255,0)), ("12_02", (255,190,0)), ("12_03", (255,128,0)),
    ("12_04", (255,64,0)), ("12_05", (255,0,0)), ("12_06", (185,3,126)),
    ("12_07", (130,2,126)), ("12_08", (74,1,125)), ("12_09", (19,1,124)),
    ("12_10", (5,74,94)), ("12_11", (1,136,55)), ("12_12", (128,196,28)),
]
COLORS_16 = [
    ("16_01", (255,3,110)), ("16_02", (255,0,0)), ("16_03", (255,156,0)),
    ("16_04", (212,203,0)), ("16_05", (100,225,0)), ("16_06", (0,226,154)),
    ("16_07", (0,221,212)), ("16_08", (0,217,249)), ("16_09", (0,187,254)),
    ("16_10", (4,140,255)), ("16_11", (107,1,255)), ("16_12", (254,0,197)),
    ("16_13", (55,130,0)), ("16_14", (0,131,87)), ("16_15", (0,128,122)),
    ("16_16", (198,149,255)),
]
def rgb_hex(rgb):
    return "#%02x%02x%02x" % rgb
def output_folder():
    home = Path.home()
    for desktop in (home / "Desktop", home / "OneDrive" / "Desktop",
                    home / "OneDrive" / "デスクトップ"):
        if desktop.exists():
            break
    folder = desktop / "Peltier Device" / "ExperimentData"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
class Experiment:
    def __init__(self):
        self.plc = serial.Serial(PORT, BAUD, timeout=1, write_timeout=1)
        self.plc.reset_input_buffer(); self.plc.reset_output_buffer()
        c12, c16 = COLORS_12.copy(), COLORS_16.copy()
        random.shuffle(c12); random.shuffle(c16)
        self.color_sets = [("12-color", c12), ("16-color", c16)]
        random.shuffle(self.color_sets)
        self.set_index = 0; self.color_index = 0; self.global_trial = 0
        self.temp = DEFAULT_TEMP; self.measured = None
        self.results = []; self.temperature_log = []
        self.start_time = time.monotonic(); self.trial_start = None
        self.last_log_time = None
        self.waiting = True; self.finished = False; self.initializing = True
        self.break_screen = False; self.touch_active = False
        self.closing = False
        self.adjust_step = INITIAL_STEP; self.previous_direction = None
        self.temp_history = [DEFAULT_TEMP]; self.one_degree_move_count = 0
        self.wait_end_time = None
        self.stable_since = None
        self.pending_new_trial = True
        self.serial_queue = queue.Queue(); self.serial_stop = threading.Event()
        self.serial_thread = None; self.last_poll = 0.0
        self.key_held = {"Up": False, "Down": False}
        self.key_release_job = {"Up": None, "Down": None}
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = output_folder()
        self.csv_path = folder / f"color_temperature_results_{stamp}.csv"
        self.log_csv_path = folder / f"color_temperature_1s_log_{stamp}.csv"
        self.root = tk.Tk(); self.root.title("Color Presentation"); self.root.resizable(False, False)
        self.canvas = tk.Canvas(self.root, width=800, height=800, highlightthickness=0, background="#808080")
        self.canvas.pack()
        self.countdown = self.canvas.create_text(400, 400, text="", fill="white", font=("Arial", 48, "bold"), justify="center")
        self.monitor = tk.Toplevel(self.root); self.monitor.title("Temperature Monitor"); self.monitor.geometry("800x690")
        self.trial_label = tk.Label(self.monitor, font=("Arial", 15, "bold")); self.trial_label.pack(pady=8)
        self.set_label = tk.Label(self.monitor, font=("Arial", 26, "bold")); self.set_label.pack()
        self.measured_label = tk.Label(self.monitor, font=("Arial", 26, "bold")); self.measured_label.pack()
        self.status_label = tk.Label(self.monitor, font=("Arial", 12), wraplength=760, justify="center"); self.status_label.pack(pady=8)
        self.fig = Figure(figsize=(7.4, 4.6), dpi=100); self.ax = self.fig.add_subplot(111)
        self.set_line, = self.ax.plot([], [], label="Set temperature")
        self.measured_line, = self.ax.plot([], [], label="Measured temperature")
        self.ax.set(title="Real-time Temperature", xlabel="Elapsed time (s)", ylabel="Temperature (°C)")
        self.ax.set_ylim(MIN_TEMP - 1, MAX_TEMP + 1); self.ax.grid(True); self.ax.legend()
        self.graph = FigureCanvasTkAgg(self.fig, master=self.monitor); self.graph.get_tk_widget().pack(fill="both", expand=True)
        self.times, self.sets, self.measures = [], [], []
        for w in (self.root, self.monitor):
            w.bind("<KeyPress-Up>", self.on_temp_key_press); w.bind("<KeyRelease-Up>", self.on_temp_key_release)
            w.bind("<KeyPress-Down>", self.on_temp_key_press); w.bind("<KeyRelease-Down>", self.on_temp_key_release)
            w.bind("<Return>", self.confirm); w.bind("<KP_Enter>", self.confirm)
            w.bind("<space>", self.continue_after_break); w.bind("<Escape>", self.abort)
            w.protocol("WM_DELETE_WINDOW", self.abort)
    def play_beeps(self, count=1):
        """Play a louder, more noticeable Windows system cue."""
        def play_once():
            # Windows does not provide a per-sound volume control through winsound.
            # To make the cue more noticeable, play two short system alerts in quick succession.
            try:
                winsound.PlaySound(
                    "SystemHand",
                    winsound.SND_ALIAS | winsound.SND_SYNC
                )
            except Exception:
                winsound.MessageBeep(winsound.MB_ICONHAND)

            time.sleep(0.06)

            try:
                winsound.PlaySound(
                    "SystemExclamation",
                    winsound.SND_ALIAS | winsound.SND_SYNC
                )
            except Exception:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

        def worker():
            if winsound is None:
                print("[WARN] winsound is unavailable; no cue sound was played.")
                return

            try:
                for i in range(count):
                    play_once()
                    if i < count - 1:
                        time.sleep(0.18)
            except Exception as e:
                print(f"[WARN] Cue sound failed: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _direct_command(self, cmd):
        self.plc.reset_input_buffer(); self.plc.write((cmd + "\r\n").encode("ascii")); self.plc.flush()
        return self.plc.readline().decode("ascii", errors="replace").strip()
    def serial_worker(self):
        while not self.serial_stop.is_set():
            try: item = self.serial_queue.get(timeout=0.1)
            except queue.Empty: continue
            if item is None: self.serial_queue.task_done(); break
            cmd, done, result = item
            try: result["response"] = self._direct_command(cmd)
            except Exception as e: result["error"] = e
            finally: done.set(); self.serial_queue.task_done()
    def command(self, cmd, timeout=2.5):
        if self.serial_stop.is_set(): raise RuntimeError("Serial communication has stopped.")
        done=threading.Event(); result={}; self.serial_queue.put((cmd,done,result))
        if not done.wait(timeout): raise RuntimeError(f"Timeout waiting for response to {cmd}")
        if "error" in result: raise result["error"]
        return result.get("response", "")
    def set_temp(self, value):
        value=max(MIN_TEMP,min(MAX_TEMP,round(value)))
        r=self.command(f"STE,{int(value*100)}")
        if r!="STE,OK": raise RuntimeError(f"Failed to change the set temperature: {r}")
        self.temp=float(value)
    def read_temp(self):
        r=self.command("RTP").split(",")
        if len(r)<3 or r[0]!="RTP": raise RuntimeError("Invalid RTP response")
        return int(r[1])/100, int(r[2])/100
    def start(self):
        self.serial_thread=threading.Thread(target=self.serial_worker,daemon=True); self.serial_thread.start()
        self.set_temp(DEFAULT_TEMP)
        st=self.command("RST").split(",")
        if len(st)<2 or st[1]!="RUN":
            if self.command("STA")!="STA,OK": raise RuntimeError("Failed to start operation.")
        self.canvas.itemconfigure(self.countdown,text="Please wait until\nthe temperature stabilizes\nat 32.0 °C")
        self.status_label.config(text="The first color will be displayed after the measured temperature remains within 32.0 ± 0.2 °C for 3 seconds.")
        self.sample(); self.root.mainloop()
    def current_color(self):
        set_name, colors=self.color_sets[self.set_index]
        return set_name, colors[self.color_index]
    def show_color(self, new_trial=True):
        self.initializing=False; self.break_screen=False; self.waiting=False
        self.touch_active=False; self.stable_since=None
        if new_trial:
            self.adjust_step=INITIAL_STEP; self.previous_direction=None
            self.temp_history=[self.temp]; self.one_degree_move_count=0
            self.global_trial+=1; self.trial_start=time.monotonic()
        set_name,(cid,rgb)=self.current_color()
        self.canvas.configure(background=rgb_hex(rgb))
        self.canvas.itemconfigure(self.countdown,text="")
        self.trial_label.config(
            text=f"Trial {self.global_trial}/28   Set {self.set_index+1}/2 "
                 f"({set_name})   {cid} RGB{rgb}"
        )
        self.status_label.config(text="Temperature stabilized. The touch-start cue will sound shortly.")
        self.update_text()
        self.root.after(250, self.start_touch_signal)
    def start_touch_signal(self):
        if self.finished or self.waiting or self.break_screen or self.initializing:
            return
        self.touch_active=True
        self.status_label.config(text="Beep: Touch the Peltier module with your finger for 5 seconds.")
        self.play_beeps(1)
        self.root.after(TOUCH_SECONDS*1000,self.touch_end_signal)
    def touch_end_signal(self):
        if self.finished or self.waiting or self.break_screen or self.initializing:
            return
        self.touch_active=False
        self.play_beeps(2)
        self.status_label.config(
            text=f"Beep-beep: Remove your finger. ↑ = warmer / ↓ = colder / Enter = matches"
                 f" (Step size: {self.adjust_step:.1f} °C)"
        )
    def update_text(self):
        self.set_label.config(text=f"Set Temperature  {self.temp:.1f} °C")
        self.measured_label.config(text=f"Measured Temperature  {'--.--' if self.measured is None else f'{self.measured:.2f}'} °C")
    def sample(self):
        if self.finished: return
        now=time.monotonic()
        if now-self.last_poll>=SAMPLE_MS/1000:
            self.last_poll=now
            try:
                _,self.measured=self.read_temp(); elapsed=now-self.start_time
                self.times.append(elapsed); self.sets.append(self.temp); self.measures.append(self.measured)
                self.set_line.set_data(self.times,self.sets); self.measured_line.set_data(self.times,self.measures)
                self.ax.set_xlim(0,max(10,elapsed)); self.graph.draw_idle(); self.update_text()
                if self.last_log_time is None or now-self.last_log_time>=LOG_INTERVAL:
                    self.last_log_time=now
                    phase="initial_stabilization" if self.initializing else "set_break" if self.break_screen else "temperature_wait" if self.waiting else "touch" if self.touch_active else "response"
                    sn=cid=""
                    if not self.initializing and not self.break_screen:
                        try: sn,(cid,_)=self.current_color()
                        except Exception: pass
                    self.temperature_log.append({"elapsed_time_s":round(elapsed,3),"set_number":self.set_index+1 if not self.initializing else "","set_name":sn,"trial_number":self.global_trial if not self.initializing else "","color_id":cid,"phase":phase,"set_temperature_c":self.temp,"measured_temperature_c":self.measured})
                if self.initializing:
                    if abs(self.measured-self.temp) <= TOLERANCE:
                        if self.stable_since is None:
                            self.stable_since = now
                        stable_elapsed = now - self.stable_since
                        remaining = max(0.0, STABLE_REQUIRED_SECONDS - stable_elapsed)
                        self.status_label.config(
                            text=f"Checking temperature stability: {remaining:.1f} s remaining "
                                 f"({self.temp:.1f} ± {TOLERANCE:.1f} °C)"
                        )
                        if stable_elapsed >= STABLE_REQUIRED_SECONDS:
                            self.show_color(new_trial=self.pending_new_trial)
                    else:
                        self.stable_since = None
                        self.status_label.config(
                            text=f"Waiting for temperature stability: stay within {self.temp:.1f} ± {TOLERANCE:.1f} °C for "
                                 f"{STABLE_REQUIRED_SECONDS:.0f} seconds to start."
                        )
            except Exception as e: self.measured_label.config(text=f"Read error: {e}")
        self.root.after(SAMPLE_MS,self.sample)
    def key_input_allowed(self):
        return self.measured is not None and abs(self.measured-self.temp)<=TOLERANCE
    def on_temp_key_press(self,event):
        if self.waiting or self.finished or self.break_screen or self.initializing: return
        if self.touch_active:
            self.status_label.config(text="Please wait until the 5-second touch period is complete."); return
        if not self.key_input_allowed():
            self.status_label.config(
                text=f"Input disabled: keys are accepted only when the measured temperature is within {self.temp:.1f} ± {TOLERANCE:.1f} °C."
            )
            return
        key=event.keysym
        if key not in ("Up","Down"): return
        if self.key_held[key]:
            job=self.key_release_job[key]
            if job is not None:
                try: self.root.after_cancel(job)
                except Exception: pass
                self.key_release_job[key]=None
            return
        self.key_held[key]=True
        direction=1 if key=="Up" else -1
        if self.previous_direction is not None and direction!=self.previous_direction:
            if self.adjust_step==3.0: self.adjust_step=2.0
            elif self.adjust_step==2.0: self.adjust_step=1.0
        self.previous_direction=direction
        new_temp=max(MIN_TEMP,min(MAX_TEMP,round(self.temp+direction*self.adjust_step)))
        if new_temp==self.temp: return
        if self.adjust_step==1.0 and self.one_degree_move_count>=4:
            self.set_temp(new_temp); self.temp_history.append(self.temp); self.one_degree_move_count+=1
            last4=self.temp_history[-4:]; perceived=sum(last4)/4.0
            self.complete_trial(perceived,True,last4); return
        self.change_temperature(new_temp)
    def on_temp_key_release(self,event):
        key=event.keysym
        if key not in ("Up","Down"): return
        old=self.key_release_job[key]
        if old is not None:
            try: self.root.after_cancel(old)
            except Exception: pass
        self.key_release_job[key]=self.root.after(KEY_RELEASE_MS,lambda k=key:self._confirm_key_release(k))
    def _confirm_key_release(self,key): self.key_held[key]=False; self.key_release_job[key]=None
    def change_temperature(self,new_temp):
        try:
            step=self.adjust_step
            self.set_temp(new_temp)
            self.stable_since=None
            self.temp_history.append(self.temp)
            if step==1.0:
                self.one_degree_move_count+=1
            self.waiting=True
            self.touch_active=False
            self.wait_end_time=time.monotonic()+WAIT_SECONDS_BY_STEP[step]
            self.canvas.configure(background="#808080")
            self.status_label.config(
                text="Temperature is changing. Remove your finger from the Peltier module."
            )
            self.tick_temperature_wait()
        except Exception as e:
            self.error(e)
    def tick_temperature_wait(self):
        if self.finished or not self.waiting:
            return
        now=time.monotonic()
        if self.measured is not None and abs(self.measured-self.temp)<=TOLERANCE:
            if self.stable_since is None:
                self.stable_since=now
        else:
            self.stable_since=None
        rem=max(0,int(self.wait_end_time-now+0.999))
        stable_elapsed=0.0 if self.stable_since is None else now-self.stable_since
        if rem>0:
            self.canvas.itemconfigure(
                self.countdown,
                text=(
                    f"Remove your finger\nTemperature changing\n{rem}\n\n"
                    f"Stable time {stable_elapsed:.1f}/{STABLE_REQUIRED_SECONDS:.0f} s"
                )
            )
            self.root.after(200,self.tick_temperature_wait)
        else:
            self.waiting=False
            self.wait_end_time=None
            if stable_elapsed>=STABLE_REQUIRED_SECONDS:
                self.initializing=False
                self.pending_new_trial=False
                self.show_color(new_trial=False)
            else:
                self.initializing=True
                self.pending_new_trial=False
                self.canvas.configure(background="#808080")
                self.canvas.itemconfigure(
                    self.countdown,
                    text="Please wait until\nthe temperature stabilizes"
                )
                self.status_label.config(
                    text=(
                        f"The measured temperature must remain within {self.temp:.1f} ± {TOLERANCE:.1f} °C for "
                        f"{STABLE_REQUIRED_SECONDS:.0f} continuous seconds before starting."
                    )
                )
    def confirm(self,event=None):
        if self.waiting or self.finished or self.break_screen or self.initializing or self.touch_active:
            return
        if not self.key_input_allowed():
            self.status_label.config(
                text=f"Enter disabled: confirmation is allowed only when the measured temperature is within {self.temp:.1f} ± {TOLERANCE:.1f} °C."
            )
            return
        self.complete_trial(self.temp,False,self.temp_history[-4:])
    def complete_trial(self,perceived_temp,forced,final4):
        try:
            sn,(cid,rgb)=self.current_color(); st=self.command("RST").split(","); now=datetime.now()
            self.results.append({"trial_order":self.global_trial,"set_order":self.set_index+1,"set_name":sn,"color_order_in_set":self.color_index+1,"color_id":cid,"red":rgb[0],"green":rgb[1],"blue":rgb[2],"rgb":f"{rgb[0]},{rgb[1]},{rgb[2]}","perceived_temperature_c":round(perceived_temp,3),"selected_set_temperature_c":self.temp,"forced_confirmation":forced,"final_four_set_temperatures_c":" -> ".join(f"{v:.1f}" for v in final4),"full_temperature_history_c":" -> ".join(f"{v:.1f}" for v in self.temp_history),"response_time_seconds":round(time.monotonic()-self.trial_start,3),"confirmed_datetime":now.isoformat(timespec="milliseconds"),"operation_status":st[1] if len(st)>1 else "","thermal_mode":st[2] if len(st)>2 else "","control_mode":st[3] if len(st)>3 else ""})
            self.advance_trial()
        except Exception as e: self.error(e)
    def advance_trial(self):
        _,colors=self.color_sets[self.set_index]; self.color_index+=1
        if self.color_index<len(colors): self.prepare_next_color(); return
        if self.set_index==0:
            self.set_index=1; self.color_index=0; self.show_set_break()
        else: self.finish()
    def prepare_next_color(self):
        try:
            self.initializing=True; self.waiting=False; self.touch_active=False
            self.pending_new_trial=True; self.stable_since=None
            self.canvas.configure(background="#808080"); self.canvas.itemconfigure(self.countdown,text="Returning to 32.0 °C\nPlease wait")
            self.status_label.config(text="The next color will be displayed after the measured temperature reaches 32.0 ± 0.2 °C.")
            self.set_temp(DEFAULT_TEMP)
        except Exception as e: self.error(e)
    def show_set_break(self):
        try:
            self.break_screen=True; self.initializing=False; self.waiting=True; self.touch_active=False
            self.canvas.configure(background="#808080"); self.canvas.itemconfigure(self.countdown,text="Set 1 complete\n\nPlease take a break\n\nWhen ready,\npress SPACE")
            next_name,_=self.color_sets[self.set_index]; self.trial_label.config(text=f"Break / Next set: {next_name}")
            self.status_label.config(text="This is the break between sets. Press SPACE when you are ready.")
            self.set_temp(DEFAULT_TEMP)
        except Exception as e: self.error(e)
    def continue_after_break(self,event=None):
        if not self.break_screen or self.finished: return
        self.break_screen=False; self.initializing=True; self.waiting=False
        self.pending_new_trial=True; self.stable_since=None
        self.canvas.itemconfigure(self.countdown,text="Please wait until\nthe temperature stabilizes\nat 32.0 °C")
        self.status_label.config(text="The next set will start when the measured temperature reaches 32.0 ± 0.2 °C.")
    def save(self):
        if self.results:
            with self.csv_path.open("w",newline="",encoding="utf-8-sig") as f:
                w=csv.DictWriter(f,fieldnames=list(self.results[0])); w.writeheader(); w.writerows(self.results)
            print(f"Results CSV saved: {self.csv_path}")
        if self.temperature_log:
            with self.log_csv_path.open("w",newline="",encoding="utf-8-sig") as f:
                w=csv.DictWriter(f,fieldnames=list(self.temperature_log[0])); w.writeheader(); w.writerows(self.temperature_log)
            print(f"1-second temperature log CSV saved: {self.log_csv_path}")
    def stop(self):
        try:
            if self.plc.is_open and not self.serial_stop.is_set():
                try: self.command("STO")
                except Exception as e: print(f"[WARN] Failed to send STO: {e}")
        finally:
            self.serial_stop.set()
            try: self.serial_queue.put_nowait(None)
            except Exception: pass
            if self.serial_thread is not None and self.serial_thread.is_alive(): self.serial_thread.join(timeout=1.0)
            if self.plc.is_open: self.plc.close()
    def finish(self):
        self.finished=True; self.save(); self.stop(); self.canvas.configure(background="#808080"); self.canvas.itemconfigure(self.countdown,text="Experiment complete")
        self.trial_label.config(text="Experiment complete"); self.set_label.config(text="Stopped"); self.measured_label.config(text="Stopped")
        self.status_label.config(text="CSV files have been saved and the Peltier module has been stopped. Press Esc to exit.")
    def abort(self,event=None):
        if self.closing:
            return "break"
        self.closing = True

        # Hide both windows first so Esc never looks like it closes and reopens.
        try:
            self.monitor.withdraw()
            self.root.withdraw()
        except Exception:
            pass

        try:
            if not self.finished:
                self.finished = True
                self.save()
                self.stop()
        finally:
            try:
                self.root.quit()
            except Exception:
                pass
            try:
                self.root.destroy()
            except Exception:
                pass

        return "break"
    def error(self,e):
        print(f"[ERROR] {e}"); self.finished=True; self.save(); self.stop(); self.status_label.config(text="An error occurred. Check the console for details.")
try:
    Experiment().start()
except KeyboardInterrupt:
    pass
