import os
import re
import subprocess
import threading
import shutil
import importlib.util
import sys
import ollama
from openai import OpenAI
import tkinter.messagebox as messagebox
import datetime
import time

from config import gemini_folder, EXPAND_MODEL, XAI_API_KEY, GROK_MODEL, load_config, save_config, validate_config
from utils import restart_ollama, log, project_log
from browser_automation import get_grok_response_via_browser
from ai_functions import ping_pong_fix, grok_syntax_rescue

def start_generate_thread(self):
    threading.Thread(target=generate_app, args=(self,), daemon=True).start()

def generate_app(self):
    if not self.generating:
        return
    self.after(0, lambda: self.create_btn.configure(state="disabled"))
    self.after(0, lambda: self.build_log.delete("0.0", "end"))
    try:
        app_idea = self.idea_entry.get().strip()
        if not app_idea:
            def _no_idea_cleanup():
                messagebox.showerror("Error", "Enter an app idea")
                self.create_btn.configure(state="normal")
                self.generating = False
            self.after(0, _no_idea_cleanup)
            return
        self.is_new_project = True
        self.app_name = re.sub(r'[^a-zA-Z0-9]', '-', app_idea.lower()).strip('-')[:60] or "my-app"
        self.app_folder = os.path.join(gemini_folder, self.app_name)
        os.makedirs(self.app_folder, exist_ok=True)
        self.after(0, lambda: project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Creating new project: {self.app_name}"))
        expand_prompt = f"""You are an expert software architect specializing in modern Python desktop apps using CustomTkinter.
Use only CustomTkinter. Apply sleek glassmorphism dark theme with neon accents, gradients, glow borders, high corner radii.
Expand this user request into a hyper-detailed specification.
User request: {app_idea}"""
        self.after(0, lambda: log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Expanding idea with {EXPAND_MODEL}..."))
        start_time = time.time()
        self.generating_done = False
        def show_progress():
            elapsed = 0
            while not self.generating_done:
                time.sleep(10)
                elapsed += 10
                if not self.generating_done:
                    self.after(0, lambda: project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [PROGRESS] Qwen still generating... ({elapsed}s)"))
        progress_thread = threading.Thread(target=show_progress, daemon=True)
        progress_thread.start()
        resp = ollama.chat(model=EXPAND_MODEL, messages=[{"role": "user", "content": expand_prompt}])
        expanded_idea = resp['message']['content'].strip()
        self.after(0, lambda: log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Expansion complete in {time.time()-start_time:.1f}s"))
        self.generating_done = True
        progress_thread.join(timeout=1.0)

        self.after(0, lambda: project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Generating code with Grok..."))
        user_prompt = f"""You are Grok, an expert Python coder. Generate complete code using ONLY CustomTkinter.
Use EXACTLY this skeleton—fill in the # UI code comment with ALL widgets/logic:
import customtkinter as ctk
class AppFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        # UI code here using self as master
Output ONLY the Python code for main.py, no explanations, no markdown.
Use glassmorphism dark theme with neon accents.
{expanded_idea}"""
        if self.use_browser_for_grok:
            self.raw_text = get_grok_response_via_browser(user_prompt, self.config)
        else:
            client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
            response = client.chat.completions.create(model=GROK_MODEL, messages=[{"role": "user", "content": user_prompt}])
            self.raw_text = response.choices[0].message.content
        write_files(self)
        def _finish_generation():
            self.load_project()
            project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] New project generated.")
            self.create_btn.configure(state="normal")
            self.is_generating = False
            self.generating = False
        self.after(0, _finish_generation)
    except Exception as e:
        def _error_cleanup():
            project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ERROR] Generation failed: {str(e)}")
            self.create_btn.configure(state="normal")
            self.is_generating = False
            self.generating = False
        self.after(0, _error_cleanup)

def write_files(self):
    if not self.raw_text: return
    self.after(0, lambda: project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Parsing output..."))
    cleaned_raw = re.sub(r'^(?:.*\n)*?```(?:python)?\s*\n?', '', self.raw_text)
    cleaned_raw = re.sub(r'\n?```(?:\s*python)?$', '', cleaned_raw)
    cleaned_raw = cleaned_raw.strip()
    files = re.split(r'===\s*(.+?)\s*===', cleaned_raw)
    written = []
    if len(files) > 1:
        for i in range(1, len(files), 2):
            filename = files[i].strip()
            content = files[i+1].strip()
            content = re.sub(r'^```(?:python)?\s*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
            content = content.strip()
            full_path = os.path.join(self.app_folder, filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.after(0, lambda f=filename: project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✓ {f}"))
            written.append(filename)
    else:
        with open(os.path.join(self.app_folder, "main.py"), "w", encoding="utf-8") as f:
            f.write(cleaned_raw)
        written.append("main.py")
    self.after(0, lambda: project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {len(written)} file(s) written!"))
    self.after(0, self.load_projects)

def ping_pong_fix_gui(self, user_feedback="", fixer_choice='1', auto_preview=True):
    if not self.app_folder:
        self.after(0, lambda: messagebox.showerror("Error", "Select or create a project"))
        return

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            if not self.pending_folder or not os.path.exists(self.pending_folder):
                self.after(0, self.prepare_pending)
                time.sleep(0.5)

            fixer_name = "Grok" if fixer_choice == '2' else "Qwen"
            self.after(0, lambda a=attempt, fn=fixer_name: project_log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Fix attempt {a}/{max_attempts} ({fn}) → {user_feedback[:80]}"))
            self.after(0, lambda fn=fixer_name, a=attempt: self._show_thinking_indicator(f"{fn} is thinking (attempt {a}/{max_attempts})..."))

            success = ping_pong_fix(self.pending_folder, self.error_log, user_feedback,
                                    use_browser_for_grok=self.use_browser_for_grok, browser_config=self.config, fixer_choice=fixer_choice)

            self.after(0, self._hide_thinking_indicator)

            if success:
                if self.pending_folder and os.path.exists(self.pending_folder):
                    valid, reason = self._validate_fix(self.pending_folder)
                    if not valid:
                        self.after(0, lambda r=reason: project_log(self, f"❌ Fix rejected (invalid): {r}"))
                        continue

                    if hasattr(self, 'app_folder') and self.app_folder:
                        backup_dir = os.path.join(self.app_folder, ".backup")
                        if os.path.exists(backup_dir):
                            safe, reason = self._check_diff_size(backup_dir, self.pending_folder)
                            if not safe:
                                self.after(0, lambda r=reason: project_log(self, f"❌ Fix rejected (too destructive): {r}"))
                                continue

                self.after(0, lambda a=attempt: project_log(self, f"✅ Fix succeeded on attempt {a}!"))
                if auto_preview:
                    self.after(0, self.commit_pending)
                    time.sleep(0.5)
                    self.after(0, self.load_preview)
                return
            else:
                self.after(0, lambda a=attempt: project_log(self, f"Fix attempt {a} failed. Retrying..."))
                time.sleep(1.5)

        except Exception as e:
            self.after(0, self._hide_thinking_indicator)
            err_str = str(e)
            self.after(0, lambda a=attempt, err=err_str: project_log(self, f"Fix attempt {a} error: {err}"))
            if attempt == max_attempts:
                self.after(0, lambda err=err_str: project_log(self, f"❌ All retry attempts failed: {err}"))
            else:
                time.sleep(2.0)

def start_launch_thread(self):
    threading.Thread(target=launch_app_gui, args=(self,), daemon=True).start()

def launch_app_gui(self):
    try:
        if not self.app_folder:
            self.after(0, lambda: messagebox.showerror("Error", "Select or create a project"))
            return

        self.pending_folder = os.path.join(self.app_folder, ".pending")
        launch_folder = self.pending_folder if os.path.exists(self.pending_folder) else self.app_folder

        self.ensure_dependencies(launch_folder)

        main_file = "main.py"
        if not os.path.exists(os.path.join(launch_folder, main_file)):
            self.after(0, lambda: project_log(self, f"No {main_file} found—skipping launch."))
            return

        self.after(0, lambda: project_log(self, f"LAUNCHING from {'pending' if os.path.exists(self.pending_folder) else 'main'}"))

        req_path = os.path.join(launch_folder, "requirements.txt")
        if not os.path.exists(req_path):
            self.after(0, lambda: project_log(self, "No requirements.txt found → creating safe default"))
            with open(req_path, "w", encoding="utf-8") as f:
                f.write("customtkinter\n")

        deps_dir = os.path.join(launch_folder, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        import shutil as _shutil
        pip_path = _shutil.which("pip") or _shutil.which("pip3")
        pip_cmd = [pip_path] if pip_path else [sys.executable, "-m", "pip"]
        subprocess.run(pip_cmd + ["install", "--upgrade", "--target", deps_dir, "-r", "requirements.txt", "--quiet"], 
                       cwd=launch_folder, timeout=120, check=False)

        launch_env = os.environ.copy()
        existing_pp = launch_env.get("PYTHONPATH", "")
        launch_env["PYTHONPATH"] = deps_dir + (os.pathsep + existing_pp if existing_pp else "")

        proc = subprocess.Popen([sys.executable, main_file], cwd=launch_folder, 
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                text=True, bufsize=1, env=launch_env)
        output, _ = proc.communicate()
        return_code = proc.returncode
        self.error_log = output

        if return_code == 0:
            self.after(0, lambda: project_log(self, "APP RAN SUCCESSFULLY!"))
            self.after(0, lambda: messagebox.showinfo("Success", "App ran successfully."))
        else:
            self.after(0, lambda: project_log(self, "Crashed — auto-fixing now..."))
            self.after(0, lambda: project_log(self, output[-2000:] if len(output) > 2000 else output))
            if "SyntaxError" in output:
                self.syntax_fail_count += 1
                if self.syntax_fail_count >= 3:
                    if messagebox.askyesno("Syntax Rescue", "Call Grok for syntax fix?"):
                        grok_syntax_rescue(launch_folder, output, self.use_browser_for_grok, self.config)
                        self.syntax_fail_count = 0
            else:
                self.after(0, lambda: self.ping_pong_fix_gui("Fix the crash/error shown above"))

    except Exception as e:
        self.after(0, lambda err=e: project_log(self, f"Launch failed: {err}"))

def prepare_pending(self):
    self.pending_folder = os.path.join(self.app_folder, ".pending")
    if os.path.exists(self.pending_folder):
        shutil.rmtree(self.pending_folder)
    os.makedirs(self.pending_folder)
    for f in [f for f in os.listdir(self.app_folder) if f.endswith('.py') or f == 'requirements.txt']:
        shutil.copy(os.path.join(self.app_folder, f), os.path.join(self.pending_folder, f))
    req_path = os.path.join(self.pending_folder, "requirements.txt")
    if not os.path.exists(req_path):
        with open(req_path, "w", encoding="utf-8") as f:
            f.write("customtkinter\n")
    self.after(0, lambda: project_log(self, "Prepared pending folder (with safe requirements.txt)"))

def commit_pending(self):
    if not self.pending_folder: return
    for f in [f for f in os.listdir(self.pending_folder) if f.endswith('.py') or f == 'requirements.txt']:
        shutil.copy(os.path.join(self.pending_folder, f), os.path.join(self.app_folder, f))
    shutil.rmtree(self.pending_folder)
    self.pending_folder = None
    self.after(0, lambda: project_log(self, "Committed changes."))

def undo_changes(self):
    if self.pending_folder and os.path.exists(self.pending_folder):
        shutil.rmtree(self.pending_folder)
        self.pending_folder = None
        self.after(0, lambda: project_log(self, "Undid changes."))
        self.syntax_fail_count = 0