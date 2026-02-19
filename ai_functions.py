import os
import re
import json
import ollama
from openai import OpenAI
import sys

from config import EXPAND_MODEL, FIX_MODEL, XAI_API_KEY, GROK_MODEL, LLM_PROVIDERS, get_provider_key, load_config
from utils import restart_ollama, get_all_code
from browser_automation import get_grok_response_via_browser


def call_cloud_llm(provider_id, prompt, system_prompt="", config=None):
    if config is None:
        config = load_config()
    api_key = get_provider_key(config, provider_id)
    if not api_key:
        print(f"No API key for {provider_id}")
        return None

    provider = LLM_PROVIDERS.get(provider_id)
    if not provider:
        print(f"Unknown provider: {provider_id}")
        return None

    if provider_id == "anthropic":
        return _call_anthropic(api_key, provider["model"], prompt, system_prompt)

    client = OpenAI(api_key=api_key, base_url=provider["base_url"])
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=provider["model"],
            messages=messages,
            temperature=0.7,
            max_tokens=8000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling {provider_id}: {e}")
        return None


def _call_anthropic(api_key, model, prompt, system_prompt=""):
    try:
        import httpx
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": 8000,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt
        resp = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as e:
        print(f"Error calling Anthropic: {e}")
        return None


def get_generation_provider(selected_provider, config=None):
    if config is None:
        config = load_config()
    if selected_provider == "hybrid":
        for pid in ["xai", "openai", "anthropic", "google"]:
            key = get_provider_key(config, pid)
            if key:
                return pid
        return "ollama"
    if selected_provider == "ollama":
        return "ollama"
    return selected_provider


def get_fix_provider(selected_provider, config=None):
    return get_generation_provider(selected_provider, config)


def generate_code_with_provider(provider_id, prompt, config=None, use_browser_for_grok=False, browser_config=None):
    if provider_id == "ollama":
        try:
            resp = ollama.chat(model=FIX_MODEL, messages=[{"role": "user", "content": prompt}])
            return resp['message']['content']
        except Exception as e:
            print(f"Ollama error: {e}")
            return None

    if provider_id == "xai" and use_browser_for_grok:
        return get_grok_response_via_browser(prompt, browser_config)

    system_prompts = {
        "xai": "You are Grok, built by xAI. Be helpful, truthful, and a little witty.",
        "openai": "You are a senior Python developer. Output only clean, runnable code.",
        "anthropic": "You are a senior Python developer. Output only clean, runnable code.",
        "google": "You are a senior Python developer. Output only clean, runnable code.",
    }
    return call_cloud_llm(provider_id, prompt, system_prompts.get(provider_id, ""), config)


def ping_pong_fix(folder, error_log="", user_feedback="", use_browser_for_grok=False, browser_config=None, is_new_project=False, fixer_choice='2', selected_provider=None, config=None):
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

    actual_provider = None
    if fixer_choice == '2' and selected_provider and selected_provider != "ollama":
        actual_provider = get_fix_provider(selected_provider, config)
    elif fixer_choice == '2':
        actual_provider = "xai"

    if actual_provider and actual_provider != "ollama":
        provider_name = LLM_PROVIDERS.get(actual_provider, {}).get("name", actual_provider)
        print(f"\n🧠 Using {provider_name} for fix...")
        user_prompt = f"""You are an expert Python coder. Update/fix this Python desktop app based on the current code, error log, and expanded feedback/spec update:

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

        if actual_provider == "xai" and use_browser_for_grok:
            fixed = get_grok_response_via_browser(user_prompt, browser_config)
        else:
            fixed = generate_code_with_provider(actual_provider, user_prompt, config, use_browser_for_grok, browser_config)

        if not fixed:
            print(f"Error: {provider_name} returned no response")
            return False
        print(f" → {provider_name} provided the fix.")
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

def grok_syntax_rescue(folder, error, use_browser_for_grok=False, browser_config=None, selected_provider=None, config=None):
    actual_provider = None
    if selected_provider and selected_provider not in ("ollama", "hybrid"):
        actual_provider = selected_provider
    elif selected_provider == "hybrid":
        actual_provider = get_fix_provider("hybrid", config)
    else:
        actual_provider = "xai"

    if actual_provider == "ollama":
        actual_provider = "xai"

    provider_name = LLM_PROVIDERS.get(actual_provider, {}).get("name", actual_provider)
    print(f"\n🛠️ Calling {provider_name} for syntax rescue...")
    code_summary = "\n\n".join([f"=== {f} ===\n{c}" for f, c in get_all_code(folder).items()])

    user_prompt = f"""Fix ONLY the syntax errors in this Python code. Do not change logic, just make it valid Python.
Error:
{error}
Code:
{code_summary}
Return ONLY the corrected files in === filename.py === format. No explanations, no markdown."""

    if actual_provider == "xai" and use_browser_for_grok:
        fixed = get_grok_response_via_browser(user_prompt, browser_config)
    else:
        fixed = generate_code_with_provider(actual_provider, user_prompt, config, use_browser_for_grok, browser_config)

    if not fixed:
        print(f"Error: {provider_name} returned no response for syntax rescue")
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
            print(f" ✓ {provider_name} fixed {fname}")
    else:
        content = blocks[0].strip() if blocks else fixed
        with open(os.path.join(folder, "main.py"), "w", encoding="utf-8") as f:
            f.write(content)
        print(f" ✓ {provider_name} overwrote main.py")

    print(f"✅ {provider_name} syntax rescue complete.")
