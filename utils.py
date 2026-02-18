import sys
import subprocess
import time
import random
import os

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    import pyperclip
except Exception:
    pyperclip = None

import numpy as np
from scipy.stats import norm
import bezier

import customtkinter as ctk
from constants import *

def restart_ollama():
    print(" → Restarting Ollama for clean state...")
    try:
        subprocess.run(["ollama", "kill"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.8)
    except:
        pass

def capture_position(prompt):
    print(prompt)
    print("Move mouse to spot and press Enter...")
    input()
    x, y = pyautogui.position()
    print(f"Captured: ({x}, {y})")
    return x, y

def get_offset_pos(base_x, base_y, radius):
    return base_x + random.uniform(-radius, radius), base_y + random.uniform(-radius, radius)

def human_like_mouse_move(start_x, start_y, end_x, end_y, duration=1.0):
    control_x = (start_x + end_x) / 2 + random.uniform(-50, 50)
    control_y = (start_y + end_y) / 2 + random.uniform(-50, 50)
    nodes = np.asfortranarray([[start_x, control_x, end_x], [start_y, control_y, end_y]])
    curve = bezier.Curve(nodes, degree=2)
    points = curve.evaluate_multi(np.linspace(0.0, 1.0, num=25))
    for i in range(1, len(points[0])):
        pyautogui.moveTo(points[0][i] + random.uniform(-2, 2), points[1][i] + random.uniform(-2, 2), duration=duration / 25)
        time.sleep(random.uniform(0.01, 0.05))

def gaussian_delay(mean=1.0, std=0.3, min_sec=0.5):
    delay = max(min_sec, norm.rvs(loc=mean, scale=std))
    time.sleep(delay)

def optional_human_noise():
    if random.random() < 0.4:
        pyautogui.scroll(random.randint(-150, 150))
        gaussian_delay(0.6, 0.2)
    if random.random() < 0.3:
        hover_x, hover_y = random.randint(100, 400), random.randint(200, 900)
        cx, cy = pyautogui.position()
        human_like_mouse_move(cx, cy, hover_x, hover_y, duration=0.6)
        gaussian_delay(1.2, 0.5)
        human_like_mouse_move(hover_x, hover_y, cx, cy, duration=0.6)

def paste_text(text):
    pyperclip.copy(text)
    gaussian_delay(0.4, 0.1)
    pyautogui.hotkey('ctrl', 'v')
    gaussian_delay(0.6, 0.2)
    optional_human_noise()

def get_all_code(folder):
    code_map = {}
    for root, _, fs in os.walk(folder):
        for f in fs:
            if f.endswith('.py'):
                with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as fh:
                    code_map[f] = fh.read()
    return code_map

class _NullStream:
    def write(self, msg):
        pass
    def flush(self):
        pass

_real_stdout = sys.stdout if sys.stdout is not None else _NullStream()
_real_stderr = sys.stderr if sys.stderr is not None else _NullStream()

def redirect_print_to_log(app):
    class Redirect:
        def __init__(self, app, original):
            self.app = app
            self.original = original
        def write(self, msg):
            if msg and msg.strip():
                try:
                    self.original.write(msg)
                    self.original.flush()
                except Exception:
                    pass
            if hasattr(self.app, 'after'):
                self.app.after(0, self._safe_write, msg)
        def _safe_write(self, msg):
            for name in ('mini_log', 'log_text', 'build_log'):
                widget = getattr(self.app, name, None)
                if widget:
                    widget.insert("end", msg)
                    widget.see("end")
        def flush(self):
            try:
                self.original.flush()
            except Exception:
                pass

    sys.stdout = Redirect(app, _real_stdout)
    sys.stderr = Redirect(app, _real_stderr)

def log(app, msg):
    try:
        _real_stdout.write(f"[LOG] {msg}\n")
        _real_stdout.flush()
    except Exception:
        pass
    if hasattr(app, 'after'):
        app.after(0, _safe_log, app, msg)

def _safe_log(app, msg):
    for name in ('mini_log', 'log_text', 'build_log'):
        widget = getattr(app, name, None)
        if widget:
            widget.insert("end", msg + "\n")
            widget.see("end")

def project_log(app, msg):
    _real_stdout.write(f"[PROJECT] {msg}\n")
    _real_stdout.flush()
    if hasattr(app, 'after'):
        app.after(0, _safe_project_log, app, msg)
        app.after(0, _safe_log, app, msg)

def _safe_project_log(app, msg):
    widget = getattr(app, 'generate_output', None)
    if widget:
        widget.insert("end", msg + "\n")
        widget.see("end")