import os
import re
import ollama
from openai import OpenAI
import sys

from config import EXPAND_MODEL, FIX_MODEL, XAI_API_KEY, GROK_MODEL
from utils import restart_ollama, get_all_code
from browser_automation import get_grok_response_via_browser

def ping_pong_fix(folder, error_log="", user_feedback="", use_browser_for_grok=False, browser_config=None, is_new_project=False, fixer_choice='2'):
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
        print(" → Feedback expanded.\n")
    else:
        expanded_feedback = user_feedback or "None"

    code_summary = "\n\n".join([f"=== {fname} ===\n{code[:1000]}..." for fname, code in get_all_code(folder).items()])

    print(f"\n🧠 Using fixer: {'Grok' if fixer_choice == '2' else 'Ollama'}")

    if fixer_choice == '2':
        print("\n🧠 Using Grok for fix...")
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

        if use_browser_for_grok:
            fixed = get_grok_response_via_browser(user_prompt, browser_config)
        else:
            client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
            messages = [
                {"role": "system", "content": "You are Grok, built by xAI. Be helpful, truthful, and a little witty."},
                {"role": "user", "content": user_prompt}
            ]
            try:
                response = client.chat.completions.create(model=GROK_MODEL, messages=messages, temperature=0.7, max_tokens=8000)
                fixed = response.choices[0].message.content
                print(" → Grok provided the fix.")
            except Exception as e:
                print(f"Error calling Grok API: {str(e)}")
                return False
    else:
        print(f"\n🔄 PING → Ollama fixer ({FIX_MODEL})")
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
            err_str = str(e)
            print(f"Fixer error: {err_str}")
            if "not found" in err_str or "404" in err_str:
                print(f"⚠️ Model '{FIX_MODEL}' not installed. Run: ollama pull {FIX_MODEL}")
            return False

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

def grok_syntax_rescue(folder, error, use_browser_for_grok=False, browser_config=None):
    print("\n🛠️ Calling Grok for syntax rescue...")
    code_summary = "\n\n".join([f"=== {f} ===\n{c}" for f, c in get_all_code(folder).items()])
   
    user_prompt = f"""Fix ONLY the syntax errors in this Python code. Do not change logic, just make it valid Python.
Error:
{error}
Code:
{code_summary}
Return ONLY the corrected files in === filename.py === format. No explanations, no markdown."""

    if use_browser_for_grok:
        fixed = get_grok_response_via_browser(user_prompt, browser_config)
    else:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
        try:
            response = client.chat.completions.create(model=GROK_MODEL, messages=[{"role": "user", "content": user_prompt}])
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