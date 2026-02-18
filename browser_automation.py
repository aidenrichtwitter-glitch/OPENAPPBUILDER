import os
import json
import subprocess
import time
import requests
import ollama
import tempfile
import random
import shutil

try:
    import pyautogui
except Exception:
    pyautogui = None

from config import BROWSER_CMD_TEMPLATE, WINDSCRIBE_DOWNLOAD_URL, WINDSCRIBE_INSTALLER, WINDSCRIBE_CLI, ROTATION_FILE, VISION_MODEL
try:
    from utils import get_offset_pos, human_like_mouse_move, gaussian_delay, optional_human_noise, paste_text
except Exception:
    pass

def is_windscribe_installed():
    import shutil
    return shutil.which(WINDSCRIBE_CLI) is not None

def download_windscribe_installer():
    print("Downloading Windscribe installer...")
    response = requests.get(WINDSCRIBE_DOWNLOAD_URL, stream=True)
    with open(WINDSCRIBE_INSTALLER, 'wb') as f:
        shutil.copyfileobj(response.raw, f)
    print("Installer downloaded to current directory.")

def setup_windscribe_cli(config):
    import sys
    if is_windscribe_installed():
        print("Windscribe already installed.")
    else:
        download_windscribe_installer()
        print("Please run the downloaded Windscribe.exe installer manually as administrator.")
        print("Approve UAC, follow the wizard, and ensure CLI is installed.")
        input("Press Enter once installation is finished and Windscribe is ready...")

        if not is_windscribe_installed():
            print("Windscribe CLI not detected. Re-install or add to PATH manually.")
            sys.exit(1)

    username = input("Enter Windscribe username: ")
    password = input("Enter Windscribe password: ")

    print("Logging into Windscribe CLI...")
    try:
        result = subprocess.run([WINDSCRIBE_CLI, "login", username, password], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Login failed: {result.stderr}")
            input("Press Enter once manual login succeeds...")
    except Exception as e:
        print(f"Error during login: {str(e)}")
        input("Press Enter once manual login succeeds...")

    config['vpn_cmd'] = f"{WINDSCRIBE_CLI} connect"

def load_rotation_state():
    if os.path.exists(ROTATION_FILE):
        with open(ROTATION_FILE, 'r') as f:
            return json.load(f)
    return {'current_index': 0}

def save_rotation_state(state):
    with open(ROTATION_FILE, 'w') as f:
        json.dump(state, f)

def get_grok_response_via_browser(user_prompt, config):
    INPUT_X, INPUT_Y = config['input_field']
    DOWN_X, DOWN_Y = config['down_button']
    COPY_X, COPY_Y = config['copy_button']
    CMD_TEMPLATE = config.get('browser_cmd_template', BROWSER_CMD_TEMPLATE)
    VPN_CMD = config.get('vpn_cmd', '')
    PROFILE_PATHS = config['profile_paths']
    OFFSET_RADIUS = config.get('click_offset_radius', 15)

    num_profiles = len(PROFILE_PATHS)
    print(f"Loaded {num_profiles} profiles")

    if VPN_CMD:
        print("Starting VPN...")
        subprocess.run(VPN_CMD, shell=True)
        input("Press Enter once VPN connected...")

    state = load_rotation_state()
    current_index = state['current_index'] % num_profiles
    profile_path = PROFILE_PATHS[current_index]
    next_index = (current_index + 1) % num_profiles
    state['current_index'] = next_index
    save_rotation_state(state)

    cmd = CMD_TEMPLATE.format(profile_path=profile_path)
    subprocess.run(cmd, shell=True)
    print(f"Using profile: {profile_path}")
    input("Press Enter once loaded/ready...")

    current_x, current_y = pyautogui.position()

    ix, iy = get_offset_pos(INPUT_X, INPUT_Y, OFFSET_RADIUS)
    human_like_mouse_move(current_x, current_y, ix, iy, duration=random.uniform(0.9, 1.6))
    gaussian_delay(0.3, 0.1)
    pyautogui.click()

    paste_text(user_prompt)

    gaussian_delay(0.4, 0.1)
    pyautogui.press('enter')

    print("Waiting for Grok response...")
    while True:
        gaussian_delay(60, 10)
        screenshot = pyautogui.screenshot()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            screenshot.save(tmp.name)
            img_path = tmp.name

        vision_prompt = """Analyze this screenshot of the Grok chat interface. Determine the current stage:
- If Grok is still generating, stage: generating, action: wait
- If response is complete and copy button is visible, stage: complete, action: click_copy
- If response is long and needs expansion (down button visible), stage: needs_expand, action: click_down
Output in JSON format: {"stage": "generating/complete/needs_expand", "action": "wait/click_copy/click_down"}"""

        res = ollama.chat(model=VISION_MODEL, messages=[{'role': 'user', 'content': vision_prompt, 'images': [img_path]}])
        response_content = res['message']['content'].strip()
        os.remove(img_path)

        try:
            analysis = json.loads(response_content)
            stage = analysis.get('stage', '')
            action = analysis.get('action', '')
        except:
            continue

        if action == 'wait':
            print("Grok is still thinking... Waiting...")
            continue
        elif action == 'click_down':
            print("Expanding response...")
            dx, dy = get_offset_pos(DOWN_X, DOWN_Y, OFFSET_RADIUS)
            human_like_mouse_move(current_x, current_y, dx, dy, duration=0.7)
            gaussian_delay(0.3, 0.1)
            pyautogui.click()
            continue
        elif action == 'click_copy':
            print("Response complete. Copying...")
            cx, cy = get_offset_pos(COPY_X, COPY_Y, OFFSET_RADIUS)
            human_like_mouse_move(current_x, current_y, cx, cy, duration=0.7)
            gaussian_delay(0.3, 0.1)
            pyautogui.click()
            break

    response = pyperclip.paste().strip()
    print("\nGrok's output:\n", response[:500], "..." if len(response)>500 else "")
    return response