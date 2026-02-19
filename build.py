import subprocess
import sys
import os

def build():
    print("=" * 60)
    print("  Python Desktop App Builder - EXE Build Script")
    print("=" * 60)

    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("[!] PyInstaller not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller installed")

    app_name = "AppBuilder"
    icon_flag = []
    if os.path.exists("app_icon.ico"):
        icon_flag = ["--icon=app_icon.ico"]
        print(f"[OK] Using icon: app_icon.ico")
    elif os.path.exists("icon.ico"):
        icon_flag = ["--icon=icon.ico"]
        print(f"[OK] Using icon: icon.ico")
    else:
        print("[!] No icon file found - using default icon")

    hidden_imports = [
        "customtkinter",
        "ollama",
        "openai",
        "pyautogui",
        "pyperclip",
        "numpy",
        "scipy",
        "bezier",
        "PIL",
        "PIL._tkinter_finder",
        "tkinter",
        "tkinter.messagebox",
        "json",
        "importlib",
        "importlib.util",
        "difflib",
        "shutil",
        "httpx",
        "httpcore",
        "anyio",
        "certifi",
        "charset_normalizer",
        "idna",
        "sniffio",
        "h11",
        "pydantic",
        "tqdm",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={app_name}",
        "--clean",
    ]

    cmd += icon_flag

    for imp in hidden_imports:
        cmd += ["--hidden-import", imp]

    cmd += ["--collect-all", "customtkinter"]
    cmd += ["--collect-all", "ollama"]

    cmd.append("main.py")

    print(f"\n[BUILD] Running PyInstaller...")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        dist_path = os.path.join("dist", app_name)
        print()
        print("=" * 60)
        print(f"  BUILD SUCCESSFUL!")
        print(f"  Output: {os.path.abspath(dist_path)}")
        print(f"  Run: {os.path.join(dist_path, app_name + '.exe')}")
        print("=" * 60)

        projects_dir = os.path.join(dist_path, "projects")
        os.makedirs(projects_dir, exist_ok=True)
        print(f"  Created projects folder: {projects_dir}")
    else:
        print()
        print("=" * 60)
        print("  BUILD FAILED - check errors above")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    build()
