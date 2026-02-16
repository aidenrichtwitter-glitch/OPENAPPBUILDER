import os
import re
import subprocess
import time
import sys
import ollama
import warnings
from crewai import Agent, Task, Crew, Process, LLM
from openai import OpenAI

# =====================================================================
# MANIFEST - FULL SYSTEM FLOW
# =====================================================================
# 1. Show numbered list of existing projects + 'new' option
# 2. If 'new':
#       - Ollama expands the user idea into a detailed spec
#       - Expanded spec is sent to Grok using your exact code
# 3. Write files to project folder
# 4. Enter continuous ping-pong loop
# 5. After 5 syntax errors → ask user if they want Grok one-shot fix
# 6. Restart Ollama before every call
# =====================================================================

# ================== TOTAL SILENCE ==================
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="Impersonate")
warnings.filterwarnings("ignore", message="UserWarning")

# ================== CONFIG ==================
llm = LLM(model="ollama/llama3.2", base_url="http://localhost:11434")
EXPAND_MODEL = "llama3.2"
FIX_MODEL = "qwen2.5-coder:14b"
XAI_API_KEY = ""
GROK_MODEL = "grok-4"  # Centralized model name for consistency

print("🚀 Python Desktop App Builder + Ping-Pong Auto-Fixer")
print("=" * 110)

# ================== PROJECT SELECTOR ==================
print("\nExisting projects:")
projects = [d for d in os.listdir(r"C:\Users\Aiden\Desktop\Gemini\gemini_apps") if os.path.isdir(os.path.join(r"C:\Users\Aiden\Desktop\Gemini\gemini_apps", d))]
for i, p in enumerate(projects, 1):
    print(f"  {i}. {p}")

choice = input("\nEnter number to load existing project, or type 'new' for new app: ").strip()

if choice.lower() == 'new':
    app_idea = input("\nWhat Python desktop app do you want to build?\n> ").strip()
    app_name = re.sub(r'[^a-zA-Z0-9]', '-', app_idea.lower()).strip('-')[:60] or "my-app"
else:
    try:
        app_name = projects[int(choice)-1]
        print(f"   → Loading existing project: {app_name}")
    except:
        print("Invalid selection. Starting new project.")
        app_idea = choice
        app_name = re.sub(r'[^a-zA-Z0-9]', '-', app_idea.lower()).strip('-')[:60] or "my-app"

gemini_folder = r"C:\Users\Aiden\Desktop\Gemini\gemini_apps"
app_folder = os.path.join(gemini_folder, app_name)
os.makedirs(app_folder, exist_ok=True)

print(f"\n✅ Working in: {app_folder}\n")

# ================== FORCE OLLAMA RESTART ==================
def restart_ollama():
    print("   → Restarting Ollama for clean state...")
    try:
        subprocess.run(["ollama", "kill"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.8)
    except:
        pass

# ================== INITIAL SCRIPT: OLLAMA EXPAND → GROK ==================
raw_text = None
if choice.lower() == 'new':
    print("🔍 Step 1: Expanding idea with Ollama...")
    expand_prompt = f"""You are an expert software architect specializing in Python desktop apps with Tkinter.
Expand this user request into a hyper-detailed, unambiguous specification for a standalone Python desktop app. The goal is to enable one-shot code generation: the spec must be so complete that an AI can produce fully functional, bug-free code without revisions.

User request: {app_idea}

Structure your output as plain text paragraphs, but make it exhaustive. Include:
- Main purpose and high-level architecture (e.g., MVC pattern if applicable).
- Key features/screens in sequence (e.g., user flow from launch to exit).
- Detailed UI elements: exact widgets (buttons, labels, entries, etc.), layouts (grid/pack/place), styling (fonts, colors, themes via ttk), event bindings, and accessibility considerations.
- Functionality breakdown: step-by-step logic for each feature, including input validation, error handling (e.g., try-except for file I/O, network errors), edge cases (e.g., empty inputs, invalid data, window resizing), and performance optimizations.
- Data storage/online needs: specify file formats (JSON, CSV), paths (use os.path for cross-platform), or APIs (with mock data if needed).
- Dependencies: list required imports and pip-installable packages (e.g., tkinter, pillow for images), and include a requirements.txt snippet.
- Testing directives: outline unit test scenarios (e.g., 'Test loading invalid file throws user-friendly error') to guide implicit testing.
- Critical constraints: Python 3.x compatibility, no external servers, runnable via 'python main.py', modern look (use ttk), and graceful shutdown.

Output ONLY the spec. No code, no markdown, no intros/outros. Ensure it's concise yet detailed enough for zero-iteration coding."""

    restart_ollama()
    resp = ollama.chat(model=EXPAND_MODEL, messages=[{"role": "user", "content": expand_prompt}])
    expanded_idea = resp['message']['content'].strip()
    print("   → Idea expanded.\n")

    # Ask for model choice with numbers
    model_choice = input("\nChoose model for code generation: 1. Ollama (default) 2. Grok > ").strip() or '1'

    if model_choice == '2':
        print("🧠 Step 2: Sending to Grok as if in a command-line chat...")

        # Simulate user sending the prompt in CMD
        user_prompt = f"""You are Grok, an expert Python coder. Your task is to generate a complete, clean, well-commented, and fully functional Python desktop app using Tkinter based on this detailed specification:

{expanded_idea}

Before outputting code, think step-by-step:
1. Analyze the spec for completeness: identify any ambiguities and resolve them logically (e.g., assume standard error handling if not specified).
2. Plan the structure: main.py as entry point, separate utils.py for helpers if needed, import all dependencies.
3. Mentally simulate execution: walk through user flows, test edge cases (e.g., invalid inputs, no file selected), and ensure no runtime errors like NameError, TypeError, or unhandled exceptions.
4. Verify functionality: imagine running 'python main.py'—does it launch without crashes? Handle window close gracefully? Look modern with ttk themes?
5. Optimize: Use best practices (e.g., PEP8 style, no global variables unless necessary, efficient code).

If the spec is insufficient for one-shot functionality, add minimal logical assumptions (e.g., default values) but note them in comments.

Output ONLY the code in this exact format:
=== requirements.txt ===
package1
package2
=== main.py ===
full code here
=== utils.py ===
full code here (if needed)

Make it fully runnable out-of-the-box, modern-looking, and error-free."""

        print("\n> User: " + user_prompt.replace("\n", "\n       "))

        # === YOUR EXACT WORKING GROK CODE ===
        client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1"
        )

        messages = [
            {"role": "system", "content": "You are Grok, built by xAI. Be helpful, truthful, and a little witty."},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = client.chat.completions.create(
                model=GROK_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=4000
            )

            raw_text = response.choices[0].message.content

            # Simulate receiving the response in CMD
            print("\nGrok: " + raw_text.replace("\n", "\n      "))
            print("\n   → Grok generated the initial script.")
        except Exception as e:
            print(f"Error calling Grok API: {str(e)}")
            sys.exit(1)
    else:
        print("🧠 Step 2: Sending to Ollama as if in a command-line chat...")

        # Simulate user sending the prompt in CMD
        user_prompt = f"""You are an expert Python coder. Your task is to generate a complete, clean, well-commented, and fully functional Python desktop app using Tkinter based on this detailed specification:

{expanded_idea}

Before outputting code, think step-by-step:
1. Analyze the spec for completeness: identify any ambiguities and resolve them logically (e.g., assume standard error handling if not specified).
2. Plan the structure: main.py as entry point, separate utils.py for helpers if needed, import all dependencies.
3. Mentally simulate execution: walk through user flows, test edge cases (e.g., invalid inputs, no file selected), and ensure no runtime errors like NameError, TypeError, or unhandled exceptions.
4. Verify functionality: imagine running 'python main.py'—does it launch without crashes? Handle window close gracefully? Look modern with ttk themes?
5. Optimize: Use best practices (e.g., PEP8 style, no global variables unless necessary, efficient code).

If the spec is insufficient for one-shot functionality, add minimal logical assumptions (e.g., default values) but note them in comments.

Output ONLY the code in this exact format:
=== requirements.txt ===
package1
package2
=== main.py ===
full code here
=== utils.py ===
full code here (if needed)

Make it fully runnable out-of-the-box, modern-looking, and error-free."""

        print("\n> User: " + user_prompt.replace("\n", "\n       "))

        try:
            resp = ollama.chat(model=FIX_MODEL, messages=[{"role": "user", "content": user_prompt}])
            raw_text = resp['message']['content']

            # Simulate receiving the response in CMD
            print("\nOllama: " + raw_text.replace("\n", "\n      "))
            print("\n   → Ollama generated the initial script.")
        except Exception as e:
            print(f"Error calling Ollama: {str(e)}")
            sys.exit(1)

else:
    print("   → Loading existing project. Skipping generation.")

# ================== FILE WRITING ==================
if raw_text:
    print("\n📥 Parsing output...")
    files = re.split(r'===\s*(.+?)\s*===', raw_text)
    written = []
    if len(files) > 1:
        for i in range(1, len(files), 2):
            filename = files[i].strip()
            content = files[i+1].strip()
            content = re.sub(r'^```(?:python)?\s*\n', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\n```$', '', content)
            full_path = os.path.join(app_folder, filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f" ✓ {filename}")
            written.append(filename)
    else:
        with open(os.path.join(app_folder, "main.py"), "w", encoding="utf-8") as f:
            f.write(raw_text)
        written.append("main.py")

    print(f"\n🎉 {len(written)} file(s) written!")

# ================== PING-PONG + USER FEEDBACK ==================
def get_all_code(folder):
    code_map = {}
    for root, _, fs in os.walk(folder):
        for f in fs:
            if f.endswith('.py'):
                with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as fh:
                    code_map[f] = fh.read()
    return code_map

def ping_pong_fix(folder, error_log="", user_feedback=""):
    restart_ollama()
    if user_feedback and user_feedback != "Make it perfect":
        print("🔍 Expanding user feedback with Ollama...")
        expand_feedback_prompt = f"""You are an expert app planner.
Expand this user improvement request into a clear, detailed specification update for the existing Python desktop app.

User improvement request: {user_feedback}

Output ONLY a concise but detailed description including:
- What needs to change or be added
- Key features / UI elements affected
- Important behavior or edge cases
- Integration with existing functionality

No code. No markdown. Plain text paragraphs."""

        resp = ollama.chat(model=EXPAND_MODEL, messages=[{"role": "user", "content": expand_feedback_prompt}])
        expanded_feedback = resp['message']['content'].strip()
        print("   → Feedback expanded.\n")
    else:
        expanded_feedback = user_feedback or "None"

    code_summary = "\n\n".join([f"=== {fname} ===\n{code[:1000]}..." for fname, code in get_all_code(folder).items()])  # Reduced truncation to avoid token limits

    # Ask for fixer choice with numbers
    fixer_choice = input("\nChoose model for this fix: 1. Ollama (default) 2. Grok > ").strip() or '1'

    if fixer_choice == '2':
        print("\n🧠 Using Grok for fix...")

        # Grok fix prompt, similar to initial generation but for fixes
        user_prompt = f"""You are Grok, an expert Python coder. Update/fix this Python desktop app based on the current code, error log, and expanded feedback/spec update:

Current code:
{code_summary}

Error log:
{error_log or "None"}

Expanded feedback/spec update:
{expanded_feedback}

Before outputting code, think step-by-step:
1. Analyze the current code and issues for completeness: identify bugs, mismatches with feedback, and resolve them logically.
2. Plan the updates: modify existing structure, add new features, import dependencies as needed.
3. Mentally simulate execution: walk through user flows, test edge cases, and ensure no runtime errors.
4. Verify functionality: imagine running 'python main.py'—does it launch without crashes? Incorporate fixes seamlessly?
5. Optimize: Use best practices, keep changes minimal where possible.

If info is insufficient, add minimal logical assumptions but note in comments.

Output ONLY the updated code in this exact format:
=== requirements.txt ===
updated packages (if changed)
=== main.py ===
full updated code
=== utils.py ===
full updated code (if needed)

Make it fully runnable out-of-the-box, modern-looking, and error-free."""

        # Simulate user sending the prompt in CMD (added for consistency)
        print("\n> User: " + user_prompt.replace("\n", "\n       "))

        # Call Grok API
        client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1"
        )

        messages = [
            {"role": "system", "content": "You are Grok, built by xAI. Be helpful, truthful, and a little witty."},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = client.chat.completions.create(
                model=GROK_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=4000
            )

            fixed = response.choices[0].message.content

            # Simulate receiving the response in CMD (added for consistency)
            print("\nGrok: " + fixed.replace("\n", "\n      "))
            print("   → Grok provided the fix.")
        except Exception as e:
            print(f"Error calling Grok API: {str(e)}")
            return False

    else:
        print(f"\n🔄 PING → Ollama fixer (qwen2.5-coder:14b)")

        prompt = f"""You are the second half of the Gemini ping-pong system.
Return ONLY clean Python code. NO markdown, NO ```, NO explanations.

Current files:
{code_summary}

Last run:
{error_log or "None"}

User feedback (expanded):
{expanded_feedback}

Output ONLY in this exact format:
=== filename.py ===
full clean code here
=== another.py ===
full clean code here"""

        try:
            resp = ollama.chat(model=FIX_MODEL, messages=[{"role": "user", "content": prompt}])
            fixed = resp['message']['content']
        except Exception as e:
            print(f"Fixer error: {e}")
            return False

    # Parse and write files (common for both Ollama and Grok)
    blocks = re.split(r'===\s*(.+?)\s*===', fixed)
    if len(blocks) > 1:
        for i in range(1, len(blocks), 2):
            fname = blocks[i].strip()
            content = blocks[i+1].strip()
            content = re.sub(r'^```(?:python)?\s*\n', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\n```$', '', content)
            with open(os.path.join(folder, fname), "w", encoding="utf-8") as f:
                f.write(content)
            print(f" ✓ Rewrote {fname}")
    else:
        with open(os.path.join(folder, "main.py"), "w", encoding="utf-8") as f:
            f.write(fixed)
        print(" ✓ Overwrote main.py")
    return True

def grok_syntax_rescue(folder, error):
    print("\n🛠️  Calling Grok for syntax rescue...")
    code_summary = "\n\n".join([f"=== {f} ===\n{c}" for f, c in get_all_code(folder).items()])
    
    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    
    try:
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[{
                "role": "user",
                "content": f"""Fix ONLY the syntax errors in this Python code. Do not change logic, just make it valid Python.

Error:
{error}

Code:
{code_summary}

Return ONLY the corrected files in === filename.py === format. No explanations, no markdown."""
            }]
        )
    
        fixed = response.choices[0].message.content
    except Exception as e:
        print(f"Error in Grok syntax rescue: {str(e)}")
        return

    blocks = re.split(r'===\s*(.+?)\s*===', fixed)
    if len(blocks) > 1:
        for i in range(1, len(blocks), 2):
            fname = blocks[i].strip()
            content = blocks[i+1].strip()
            content = re.sub(r'^```(?:python)?\s*\n', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\n```$', '', content)
            with open(os.path.join(folder, fname), "w", encoding="utf-8") as f:
                f.write(content)
            print(f" ✓ Grok fixed {fname}")
    else:
        content = blocks[0].strip() if blocks else fixed
        with open(os.path.join(folder, "main.py"), "w", encoding="utf-8") as f:
            f.write(content)
        print(" ✓ Grok overwrote main.py")
    
    print("✅ Grok syntax rescue complete.")

def launch_and_ping_pong(folder):
    main_file = "main.py" if os.path.exists(os.path.join(folder, "main.py")) else "app.py"
    syntax_fail_count = 0
   
    while True:
        print(f"\n{'═' * 90}")
        print(f"ROUND → LAUNCHING {main_file}")
        print(f"{'═' * 90}")
       
        req = os.path.join(folder, "requirements.txt")
        if os.path.exists(req):
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"], cwd=folder)
      
        try:
            proc = subprocess.Popen(
                [sys.executable, main_file],
                cwd=folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
          
            output = proc.communicate()[0]
            return_code = proc.returncode
          
            if return_code == 0:
                print("✅ APP RAN SUCCESSFULLY! 🎉 (No errors detected)")
                print("\nTested the app? Tell me what isn't working or needs improvement:")
                print("(Type 'new app' for new project, 'exit' to stop, or press Enter if it's perfect)")
                user_feedback = input("> ").strip()
               
                if user_feedback.lower() in ["exit", "quit"]:
                    print("Builder session ended.")
                    sys.exit(0)
               
                if user_feedback.lower() in ["new app", "new"]:
                    print("\nStarting new project...")
                    os.execv(sys.executable, ['python'] + sys.argv)
               
                if user_feedback:
                    ping_pong_fix(folder, output or "App ran successfully", user_feedback)
                else:
                    print("✅ No changes needed. Relaunching...")
                syntax_fail_count = 0
               
            else:
                print("❌ Crashed")
                print("-" * 80)
                print(output[-2000:] if len(output) > 2000 else output)
                print("-" * 80)
                
                if "SyntaxError" in output:
                    syntax_fail_count += 1
                    print(f"Syntax error count: {syntax_fail_count}/5")
                    
                    if syntax_fail_count >= 5:
                        choice = input("\nSyntax errors keep happening. Want to call Grok (xAI) for a one-shot fix? (y/n) > ").strip().lower()
                        if choice == 'y':
                            grok_syntax_rescue(folder, output)
                            syntax_fail_count = 0
                        else:
                            ping_pong_fix(folder, output)
                    else:
                        ping_pong_fix(folder, output)
                else:
                    ping_pong_fix(folder, output)
                    syntax_fail_count = 0
               
            time.sleep(1.5)
           
        except Exception as e:
            print(f"Launch failed: {e}")
            time.sleep(2)

# ================== GO ==================
print("\nStarting full flow: Ollama expand → Grok generate...\n")
launch_and_ping_pong(app_folder)