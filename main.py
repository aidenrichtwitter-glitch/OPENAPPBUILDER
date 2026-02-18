import os
import re
import shutil
import difflib
import threading
import customtkinter as ctk
import tkinter.messagebox as messagebox
import importlib.util
import time
import datetime
import ollama
from openai import OpenAI
import subprocess
import sys

from config import gemini_folder, EXPAND_MODEL, XAI_API_KEY, GROK_MODEL, load_config, save_config, validate_config
from browser_automation import get_grok_response_via_browser
from ai_functions import ping_pong_fix, grok_syntax_rescue
from constants import *
from views import (create_top_bar, create_sliding_menu, create_main_view, create_idea_chat_view,
                   create_logs_view, create_config_view, create_build_view)
from utils import redirect_print_to_log, log, project_log, restart_ollama
from handlers import (generate_app, write_files, ping_pong_fix_gui, start_launch_thread,
                      launch_app_gui, prepare_pending, commit_pending, undo_changes, start_generate_thread)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class AppBuilderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Python Desktop App Builder")
        self.geometry("1050x630")
        self.minsize(900, 540)
        self.configure(fg_color=BG_DEEP)

        self.config = load_config()
        self.app_folder = None
        self.app_name = None
        self.is_new_project = False
        self.syntax_fail_count = 0
        self.use_browser_for_grok = False
        self.raw_text = None
        self.error_log = ""
        self.pending_folder = None
        self.menu_open = False
        self.preview_instance = None
        self.preview_success = False
        self.chat_history = []
        self.generating = False
        self.generating_done = False
        self._loading_preview = False
        self._fixing_in_progress = False
        self._thinking_label = None

        create_top_bar(self)
        create_sliding_menu(self)
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        create_main_view(self)
        create_idea_chat_view(self)
        create_logs_view(self)
        create_config_view(self)
        create_build_view(self)

        self.show_main_view()
        self.load_projects()

        self.after(200, lambda: redirect_print_to_log(self))

        threading.Thread(target=self.warmup_ollama, daemon=True).start()
        threading.Thread(target=self.load_suggestion_bubbles, daemon=True).start()

        self.start_generate_thread = start_generate_thread.__get__(self, AppBuilderGUI)
        self.generate_app = generate_app.__get__(self, AppBuilderGUI)
        self.write_files = write_files.__get__(self, AppBuilderGUI)
        self.ping_pong_fix_gui = ping_pong_fix_gui.__get__(self, AppBuilderGUI)
        self.start_launch_thread = start_launch_thread.__get__(self, AppBuilderGUI)
        self.launch_app_gui = launch_app_gui.__get__(self, AppBuilderGUI)
        self.prepare_pending = prepare_pending.__get__(self, AppBuilderGUI)
        self.commit_pending = commit_pending.__get__(self, AppBuilderGUI)
        self.undo_changes = undo_changes.__get__(self, AppBuilderGUI)
        self.build_from_ideate = self.build_from_ideate
        self.deploy_app = self.deploy_app

    def warmup_ollama(self):
        try:
            time.sleep(0.3)
            self.after(0, lambda: log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [STARTUP] Warming up Ollama with Qwen..."))
            restart_ollama()
            time.sleep(5)
            ollama.chat(model=EXPAND_MODEL, messages=[{"role": "user", "content": "warmup"}])
            self.after(0, lambda: log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [STARTUP] Qwen model ready."))
        except Exception as e:
            err_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [STARTUP] Qwen warmup failed: {str(e)}"
            self.after(0, lambda msg=err_msg: log(self, msg))

    def _scan_imports(self, folder):
        import_to_pip = {
            'cv2': 'opencv-python', 'PIL': 'pillow', 'skimage': 'scikit-image',
            'sklearn': 'scikit-learn', 'yaml': 'pyyaml', 'bs4': 'beautifulsoup4',
            'gi': 'PyGObject', 'wx': 'wxPython', 'attr': 'attrs',
            'serial': 'pyserial', 'usb': 'pyusb', 'Crypto': 'pycryptodome',
            'dateutil': 'python-dateutil', 'dotenv': 'python-dotenv',
            'websocket': 'websocket-client', 'google.protobuf': 'protobuf',
        }
        stdlib = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else {
            'os', 'sys', 'io', 're', 'math', 'json', 'time', 'datetime', 'random',
            'collections', 'itertools', 'functools', 'pathlib', 'shutil', 'subprocess',
            'threading', 'multiprocessing', 'socket', 'http', 'urllib', 'email',
            'logging', 'unittest', 'typing', 'abc', 'copy', 'string', 'textwrap',
            'struct', 'hashlib', 'hmac', 'secrets', 'tempfile', 'glob', 'fnmatch',
            'csv', 'configparser', 'argparse', 'gettext', 'locale', 'calendar',
            'pprint', 'enum', 'dataclasses', 'contextlib', 'decimal', 'fractions',
            'statistics', 'array', 'queue', 'heapq', 'bisect', 'weakref',
            'types', 'operator', 'pickle', 'shelve', 'sqlite3', 'zlib', 'gzip',
            'zipfile', 'tarfile', 'xml', 'html', 'webbrowser', 'uuid', 'platform',
            'ctypes', 'traceback', 'warnings', 'signal', 'mmap', 'codecs',
            'importlib', 'pkgutil', 'inspect', 'dis', 'ast', 'token', 'tokenize',
            'tkinter', '_tkinter', 'idlelib',
        }
        found = set()
        for root, dirs, files in os.walk(folder):
            for fname in files:
                if not fname.endswith('.py'):
                    continue
                try:
                    with open(os.path.join(root, fname), 'r', errors='ignore') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('import ') or line.startswith('from '):
                                parts = line.replace('from ', '').replace('import ', '').split()[0]
                                top = parts.split('.')[0]
                                if top and top not in stdlib and not top.startswith('_'):
                                    pip_name = import_to_pip.get(top, top)
                                    found.add(pip_name)
                except Exception:
                    pass
        found.add('customtkinter')
        return sorted(found)

    def _get_pip_cmd(self):
        import shutil
        pip_path = shutil.which("pip") or shutil.which("pip3")
        if pip_path:
            return [pip_path]
        return [sys.executable, "-m", "pip"]

    def _get_deps_dir(self, folder):
        deps_dir = os.path.join(folder, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        return deps_dir

    def _add_deps_to_path(self, folder):
        deps_dir = self._get_deps_dir(folder)
        if deps_dir not in sys.path:
            sys.path.insert(0, deps_dir)

    def ensure_dependencies(self, folder, callback=None):
        def install_thread():
            try:
                self.after(0, lambda: project_log(self, "🔧 Detecting missing modules..."))
                scanned = self._scan_imports(folder)
                pkg_list = ", ".join(scanned)
                self.after(0, lambda msg=pkg_list: project_log(self, f"📋 Detected packages: {msg}"))

                req_path = os.path.join(folder, "requirements.txt")
                existing = set()
                if os.path.exists(req_path):
                    with open(req_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                existing.add(line.split('>=')[0].split('==')[0].split('<')[0].strip().lower())
                for p in scanned:
                    if p.lower() not in existing:
                        with open(req_path, "a") as f:
                            f.write(f"{p}\n")

                pip_cmd = self._get_pip_cmd()
                deps_dir = self._get_deps_dir(folder)
                self.after(0, lambda: project_log(self, "📦 Installing packages to project deps folder..."))
                result = subprocess.run(
                    pip_cmd + ["install", "--upgrade", "--target", deps_dir, "-r", "requirements.txt", "--quiet"],
                    cwd=folder, timeout=300, capture_output=True, text=True
                )

                self._add_deps_to_path(folder)

                if result.returncode == 0:
                    self.after(0, lambda: project_log(self, "✅ All dependencies installed & up to date"))
                    if callback:
                        self.after(500, callback)
                    return

                stderr_msg = result.stderr[:800] if result.stderr else "Unknown install error"
                self.after(0, lambda msg=stderr_msg: project_log(self, f"❌ Batch install failed: {msg}"))

                self.after(0, lambda: project_log(self, "🔄 Retrying packages individually..."))
                all_ok = True
                with open(req_path, "r") as f:
                    pkgs = [l.strip() for l in f if l.strip() and not l.startswith('#')]
                for pkg in pkgs:
                    r = subprocess.run(
                        pip_cmd + ["install", "--upgrade", "--target", deps_dir, pkg, "--quiet"],
                        timeout=120, capture_output=True, text=True
                    )
                    if r.returncode != 0:
                        fail_msg = f"⚠️ Failed: {pkg}"
                        self.after(0, lambda msg=fail_msg: project_log(self, msg))
                        all_ok = False
                    else:
                        ok_msg = f"  ✓ {pkg}"
                        self.after(0, lambda msg=ok_msg: project_log(self, msg))

                if all_ok:
                    self.after(0, lambda: project_log(self, "✅ All dependencies installed (individual mode)"))
                    if callback:
                        self.after(500, callback)
                    return

                if not self._fixing_in_progress:
                    self._fixing_in_progress = True
                    self.after(0, lambda err=stderr_msg: self.smart_fix_loop(err))

            except Exception as e:
                err_msg = f"⚠️ Dependency error: {e}"
                self.after(0, lambda msg=err_msg: project_log(self, msg))
                if not self._fixing_in_progress:
                    self._fixing_in_progress = True
                    self.after(0, lambda err=str(e): self.smart_fix_loop(err))

        threading.Thread(target=install_thread, daemon=True).start()

    def create_snapshot(self):
        if not self.app_folder or not os.path.isdir(self.app_folder):
            return
        backup_dir = os.path.join(self.app_folder, ".backup")
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        os.makedirs(backup_dir)
        for f in os.listdir(self.app_folder):
            if f.endswith('.py') or f == 'requirements.txt':
                src = os.path.join(self.app_folder, f)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(backup_dir, f))
        self.after(0, lambda: project_log(self, "📸 Snapshot saved (pre-fix backup)"))
        self._update_undo_button_state()

    def restore_snapshot(self):
        if not self.app_folder:
            return
        backup_dir = os.path.join(self.app_folder, ".backup")
        if not os.path.exists(backup_dir):
            self.after(0, lambda: project_log(self, "⚠️ No snapshot to restore"))
            return
        restored = []
        for f in os.listdir(backup_dir):
            src = os.path.join(backup_dir, f)
            dst = os.path.join(self.app_folder, f)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                restored.append(f)
        names = ", ".join(restored)
        self.after(0, lambda n=names: project_log(self, f"⏪ Restored from snapshot: {n}"))
        self._fixing_in_progress = False
        self.after(0, self._try_load_module)

    def has_snapshot(self):
        if not self.app_folder:
            return False
        backup_dir = os.path.join(self.app_folder, ".backup")
        return os.path.exists(backup_dir) and len(os.listdir(backup_dir)) > 0

    def _update_undo_button_state(self):
        if hasattr(self, 'undo_btn') and self.undo_btn.winfo_exists():
            if self.has_snapshot():
                self.undo_btn.configure(state="normal", fg_color=ACCENT_PURPLE)
            else:
                self.undo_btn.configure(state="disabled", fg_color=BG_GLASS)

    def _validate_fix(self, folder):
        main_path = os.path.join(folder, "main.py")
        if not os.path.exists(main_path):
            return False, "No main.py found"
        try:
            with open(main_path, 'r', errors='ignore') as f:
                code = f.read()
            compile(code, main_path, 'exec')
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        return True, "OK"

    def _check_diff_size(self, original_folder, fixed_folder):
        for fname in os.listdir(fixed_folder):
            if not fname.endswith('.py'):
                continue
            orig_path = os.path.join(original_folder, fname)
            fixed_path = os.path.join(fixed_folder, fname)
            if not os.path.exists(orig_path):
                continue
            try:
                with open(orig_path, 'r', errors='ignore') as f:
                    orig_lines = f.readlines()
                with open(fixed_path, 'r', errors='ignore') as f:
                    fixed_lines = f.readlines()
                if not orig_lines:
                    continue
                diff = list(difflib.unified_diff(orig_lines, fixed_lines))
                changed = sum(1 for line in diff if line.startswith('+') or line.startswith('-'))
                ratio = changed / max(len(orig_lines), 1)
                if ratio > 0.6:
                    return False, f"{fname}: {ratio:.0%} changed (too destructive)"
            except Exception:
                pass
        return True, "OK"

    def smart_fix_loop(self, error):
        def _run():
            try:
                self.create_snapshot()

                for attempt in range(2):
                    self.after(0, lambda a=attempt+1: project_log(self, f"🔄 Qwen smart fix attempt {a}/2..."))
                    self.after(0, lambda a=attempt+1: self._show_thinking_indicator(f"Qwen is analyzing & fixing (attempt {a}/2)..."))

                    snapshot_dir = os.path.join(self.app_folder, ".backup")
                    self.ping_pong_fix_gui(f"Preview failed with error: {error}. This is Qwen attempt {attempt+1}/2. Fix the code so the AppFrame runs perfectly with current CustomTkinter (remove CTkProgressbar if not available). Output full main.py and requirements.txt.", fixer_choice='1', auto_preview=False)

                    if self.pending_folder and os.path.exists(self.pending_folder):
                        valid, reason = self._validate_fix(self.pending_folder)
                        if not valid:
                            self.after(0, lambda r=reason: project_log(self, f"❌ Fix rejected (invalid): {r}"))
                            continue

                        safe, reason = self._check_diff_size(snapshot_dir, self.pending_folder)
                        if not safe:
                            self.after(0, lambda r=reason: project_log(self, f"❌ Fix rejected (too destructive): {r}"))
                            continue

                    self.after(0, self.commit_pending)
                    time.sleep(1)
                    self.after(0, self._try_load_module)
                    time.sleep(2)
                    if self.preview_success:
                        self.after(0, lambda: project_log(self, "✅ Preview succeeded after Qwen fix!"))
                        self.after(0, self._update_undo_button_state)
                        return

                self.after(0, lambda: project_log(self, "Qwen couldn't fix in 2 rounds → Grok taking over"))
                self.ping_pong_fix_gui(f"Preview failed with error: {error}. Grok, fix the code so the AppFrame runs perfectly with current CustomTkinter. Output full main.py and requirements.txt.", fixer_choice='2', auto_preview=False)

                if self.pending_folder and os.path.exists(self.pending_folder):
                    valid, reason = self._validate_fix(self.pending_folder)
                    if not valid:
                        self.after(0, lambda r=reason: project_log(self, f"❌ Grok fix rejected (invalid): {r}"))
                        self.after(0, lambda: project_log(self, "⏪ Restoring snapshot..."))
                        self.restore_snapshot()
                        return

                    safe, reason = self._check_diff_size(snapshot_dir, self.pending_folder)
                    if not safe:
                        self.after(0, lambda r=reason: project_log(self, f"❌ Grok fix rejected (too destructive): {r}"))
                        self.after(0, lambda: project_log(self, "⏪ Restoring snapshot..."))
                        self.restore_snapshot()
                        return

                self.after(0, self.commit_pending)
                time.sleep(1)
                self.after(0, self._try_load_module)
                self.after(0, self._update_undo_button_state)
            finally:
                self._fixing_in_progress = False
                self.after(0, self._hide_thinking_indicator)
        threading.Thread(target=_run, daemon=True).start()

    def _show_thinking_indicator(self, msg="AI is thinking..."):
        if hasattr(self, '_thinking_label') and self._thinking_label and self._thinking_label.winfo_exists():
            self._thinking_label.configure(text=f"💭 {msg}")
            return
        self._thinking_label = ctk.CTkLabel(
            self.main_content, text=f"💭 {msg}",
            font=ctk.CTkFont(size=16, slant="italic"),
            text_color="#facc15"
        )
        self._thinking_label.pack(pady=10)

    def _hide_thinking_indicator(self):
        if hasattr(self, '_thinking_label') and self._thinking_label and self._thinking_label.winfo_exists():
            self._thinking_label.destroy()
            self._thinking_label = None

    def toggle_menu(self):
        if self.menu_open:
            self.menu_frame.pack_forget()
            self.menu_open = False
        else:
            self.menu_frame.pack(side="left", fill="y", before=self.content_container)
            self.menu_open = True
            self.load_projects()

    def _create_bubble_widgets(self):
        self._bubble_frames = []
        self._bubble_titles = []
        self._bubble_descs = []
        self._bubble_ideas = ["", "", "", ""]
        for i in range(4):
            colors = CARD_COLORS[i % len(CARD_COLORS)]
            row = i // 2
            col = i % 2

            bubble = ctk.CTkFrame(self.ideas_frame, fg_color=colors["bg"], corner_radius=16,
                                  border_width=2, border_color=colors["border"])
            bubble.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

            t_label = ctk.CTkLabel(bubble, text="",
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   text_color=colors["title_color"], anchor="w")
            t_label.pack(pady=(10, 2), padx=12, anchor="w")

            d_label = ctk.CTkLabel(bubble, text="",
                                   font=ctk.CTkFont(size=11),
                                   wraplength=220, justify="left",
                                   text_color=TEXT_DIM, anchor="w")
            d_label.pack(pady=(0, 10), padx=12, anchor="w", fill="x")

            rest_bg = colors["bg"]
            rest_border = colors["border"]
            def enter(e, b=bubble, bc=rest_border):
                b.configure(fg_color=BG_GLASS_LIGHT)
            def leave(e, b=bubble, rbg=rest_bg):
                b.configure(fg_color=rbg)
            bubble.bind("<Enter>", enter)
            bubble.bind("<Leave>", leave)
            idx = i
            for widget in [bubble, t_label, d_label]:
                widget.bind("<Button-1>", lambda e, ii=idx: self.use_suggestion(self._bubble_ideas[ii]))

            self._bubble_frames.append(bubble)
            self._bubble_titles.append(t_label)
            self._bubble_descs.append(d_label)

    def populate_bubbles(self, ideas):
        if not hasattr(self, '_bubble_frames') or not self._bubble_frames:
            self._create_bubble_widgets()
        for i in range(4):
            if i < len(ideas):
                idea = ideas[i]
                self._bubble_ideas[i] = idea
                if ":" in idea:
                    title_part, desc_part = idea.split(":", 1)
                    title_part = title_part.strip()
                    desc_part = desc_part.strip()
                else:
                    title_part = idea[:20]
                    desc_part = idea
                self._bubble_titles[i].configure(text=title_part)
                self._bubble_descs[i].configure(text=desc_part)

    def load_suggestion_bubbles(self):
        fallback = [
            "GlassShelf: Sort and organize files with neon-lit panels and smooth drag-and-drop.",
            "NeonDive: Explore data with glowing interactive charts and real-time filtering.",
            "GlowZone: Dynamic wallpaper creator with gradient blending and light effects.",
            "CodeFlow: Smart code formatter with syntax highlighting and neon color palettes."
        ]
        self.after(0, self.populate_bubbles, fallback)

        prompt = """Generate exactly 4 exciting modern Python desktop app ideas that MUST use CustomTkinter for the UI.
Format each as: AppName: One-sentence description (60-100 characters) highlighting a sleek dark glassmorphism UI with neon glow effects.
Do not mention 'CustomTkinter' in the description text.
Do not add any introductory text, numbering, or extra lines.
Output ONLY the 4 formatted lines."""
        for attempt in range(3):
            try:
                restart_ollama()
                time.sleep(5)
                resp = ollama.chat(model=EXPAND_MODEL, messages=[{"role": "user", "content": prompt}])
                ideas = [line.strip() for line in resp['message']['content'].strip().split('\n') if line.strip() and ':' in line][:4]
                if len(ideas) >= 4:
                    self.after(0, self.populate_bubbles, ideas[:4])
                    return
            except Exception as e:
                err_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Suggestion attempt {attempt+1} failed: {e}"
                self.after(0, lambda msg=err_msg: log(self, msg))

    def use_suggestion(self, text):
        if self.generating: return
        self.generating = True
        self.idea_entry.delete(0, "end")
        self.idea_entry.insert(0, text)
        self.show_build_view()
        self.start_generate_thread()

    def build_from_ideate(self):
        if self.generating: return
        if not self.chat_history:
            messagebox.showinfo("Info", "No LLM response yet to build from.")
            return
        last_llm_response = None
        for role, content in reversed(self.chat_history):
            if role != "You":
                last_llm_response = content
                break
        if not last_llm_response:
            messagebox.showinfo("Info", "No LLM response found.")
            return
        self.generating = True
        self.idea_entry.delete(0, "end")
        self.idea_entry.insert(0, last_llm_response[:300])
        self.show_build_view()
        self.start_generate_thread()

    def create_and_generate(self):
        if self.generating: return
        self.generating = True
        self.create_btn.configure(state="disabled")
        self.show_build_view()
        self.start_generate_thread()

    def deploy_app(self):
        if not self.app_folder:
            messagebox.showinfo("Info", "Create or select a project first.")
            return
        self.after(0, lambda: project_log(self, "🚀 Deploying — launching app in new window..."))
        threading.Thread(target=launch_app_gui, args=(self,), daemon=True).start()

    def select_project_from_menu(self, name):
        if name == "Select project...": return
        self.select_project(name)
        self.toggle_menu()
        self.show_build_view()

    def select_project(self, name):
        self.app_name = name
        self.load_project()

    def load_project(self):
        if not self.app_name: return
        self.app_folder = os.path.join(gemini_folder, self.app_name)
        self.is_new_project = False
        self._fixing_in_progress = False
        self._loading_preview = False
        self.after(0, lambda: self.generate_output.delete("0.0", "end") if hasattr(self, 'generate_output') else None)
        self.syntax_fail_count = 0
        self.after(0, lambda: log(self, f"✓ Loaded: {self.app_name}"))
        title_text = f"{self.app_name[:30].capitalize()}... - Python Desktop App Builder" if len(self.app_name) > 30 else f"{self.app_name.capitalize()} - Python Desktop App Builder"
        self.title_label.configure(text=title_text)
        self.title(title_text)
        self.show_build_view()
        self.load_preview()

    def load_projects(self):
        projects = sorted([d for d in os.listdir(gemini_folder) if os.path.isdir(os.path.join(gemini_folder, d))])
        self.project_menu.configure(values=["Select project..."] + projects)

    def _try_load_module(self):
        for w in self.main_content.winfo_children():
            w.destroy()
        if self.preview_instance:
            self.preview_instance.destroy()
            self.preview_instance = None
        self.preview_success = False

        try:
            self._add_deps_to_path(self.app_folder)
            main_path = os.path.join(self.app_folder, "main.py")
            if not os.path.exists(main_path):
                raise FileNotFoundError(f"No main.py in {self.app_folder}")
            spec = importlib.util.spec_from_file_location("main", main_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'AppFrame'):
                self.preview_instance = module.AppFrame(self.main_content)
                self.preview_instance.pack(fill="both", expand=True)
                self.preview_success = True
                project_log(self, "App preview loaded.")
            else:
                raise AttributeError("No AppFrame")
        except Exception as e:
            project_log(self, f"Preview failed: {e}")
            error_label = ctk.CTkLabel(self.main_content, text="Preview not available (auto-fixing...)", font=ctk.CTkFont(size=20), text_color=TEXT_DIM)
            error_label.pack(pady=20)

    def load_preview(self):
        if self._loading_preview:
            return
        self._loading_preview = True

        self._try_load_module()

        if not self.preview_success:
            self.ensure_dependencies(self.app_folder, callback=self._on_deps_installed)
        else:
            self._loading_preview = False

    def _on_deps_installed(self):
        self._try_load_module()
        self._loading_preview = False

        if not self.preview_success and not self._fixing_in_progress:
            self._fixing_in_progress = True
            e_str = "Preview failed after dependency install"
            self.after(1000, lambda: self.smart_fix_loop(e_str))

    def toggle_browser(self):
        self.use_browser_for_grok = self.use_browser_var.get()

    def save_config_gui(self):
        self.config['vpn_cmd'] = self.vpn_entry.get()
        save_config(self.config)
        messagebox.showinfo("Saved", "Config updated!")

    def setup_calibration(self):
        pass

    def show_main_view(self):
        self.hide_all_views()
        self.main_view.pack(fill="both", expand=True)
        self.current_view = "main"
        if self.menu_open:
            self.toggle_menu()

    def show_idea_chat(self):
        self.hide_all_views()
        self.idea_chat_view.pack(fill="both", expand=True)
        self.current_view = "idea"
        self.chat_box.delete("0.0", "end")
        self.chat_box.insert("end", "Ideate mode ready. Ask anything.\n\n")
        for role, content in self.chat_history:
            self.chat_box.insert("end", f"{role}: {content}\n\n")
        self.chat_box.see("end")

    def show_logs(self):
        self.hide_all_views()
        self.logs_view.pack(fill="both", expand=True)
        self.current_view = "logs"
        if self.menu_open:
            self.toggle_menu()

    def show_config(self):
        self.hide_all_views()
        self.config_view.pack(fill="both", expand=True)
        self.current_view = "config"
        if self.menu_open:
            self.toggle_menu()

    def show_build_view(self):
        self.hide_all_views()
        self.build_view.pack(fill="both", expand=True)
        self.current_view = "build"
        self._update_undo_button_state()

    def show_project_editor(self):
        self.toggle_menu()
        self.show_build_view()

    def hide_all_views(self):
        for view in [self.main_view, self.idea_chat_view, self.logs_view, self.config_view, self.build_view]:
            view.pack_forget()

    def send_idea_message(self):
        if self.generating: return
        prompt = self.chat_entry.get().strip()
        if not prompt: return
        self.generating = True
        self.chat_history.append(("You", prompt))
        self.chat_entry.delete(0, "end")
        self.chat_box.insert("end", f"You: {prompt}\n\n")
        self.chat_box.insert("end", "Generating response...\n\n")
        self.chat_box.see("end")
        threading.Thread(target=self._get_llm_response, args=(prompt,), daemon=True).start()

    def _get_llm_response(self, prompt):
        try:
            llm = self.llm_selector.get()
            if llm == "Ollama":
                resp = ollama.chat(model=EXPAND_MODEL, messages=[{"role": "user", "content": prompt}])
                answer = resp['message']['content']
            else:
                if self.use_browser_for_grok:
                    answer = get_grok_response_via_browser(prompt, self.config)
                else:
                    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
                    response = client.chat.completions.create(model=GROK_MODEL, messages=[{"role": "user", "content": prompt}])
                    answer = response.choices[0].message.content
            self.chat_history.append((llm, answer))
            self.after(0, lambda: self.chat_box.insert("end", f"{llm}: {answer}\n\n"))
            self.after(0, lambda: self.chat_box.see("end"))
        except Exception as e:
            error_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ERROR] {str(e)}"
            self.after(0, lambda: log(self, error_msg))
            self.after(0, lambda: self.chat_box.insert("end", f"{error_msg}\n\n"))
        finally:
            self.generating = False
            self.after(0, lambda: self.send_btn.configure(state="normal"))

    def apply_fix(self):
        user_feedback = self.fix_entry.get().strip()
        if not user_feedback:
            messagebox.showinfo("Info", "Enter a fix or upgrade description")
            return
        self.create_snapshot()
        self.after(0, lambda: log(self, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Applying fix: {user_feedback}"))
        threading.Thread(target=self.ping_pong_fix_gui, args=(user_feedback,), daemon=True).start()
        self.fix_entry.delete(0, "end")

if __name__ == "__main__":
    import traceback

    if getattr(sys, 'frozen', False):
        import io
        log_path = os.path.join(os.path.dirname(sys.executable), "appbuilder.log")
        try:
            _log_file = open(log_path, "w", encoding="utf-8")
        except Exception:
            _log_file = io.StringIO()
        if sys.stdout is None:
            sys.stdout = _log_file
        if sys.stderr is None:
            sys.stderr = _log_file

    def handle_exception(exc_type, exc_value, exc_traceback):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        try:
            sys.stderr.write(f"\n[UNHANDLED EXCEPTION]\n{msg}\n")
            sys.stderr.flush()
        except Exception:
            pass
    sys.excepthook = handle_exception

    print("[STARTUP] Python Desktop App Builder starting...")
    print(f"[STARTUP] Python: {sys.executable}")
    print(f"[STARTUP] Working dir: {os.getcwd()}")
    print(f"[STARTUP] Projects dir: {gemini_folder}")
    sys.stdout.flush()

    ctk.set_widget_scaling(1.0)
    app = AppBuilderGUI()
    print("[STARTUP] App window created, entering mainloop")
    sys.stdout.flush()
    app.mainloop()
