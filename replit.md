# Python Desktop App Builder

## Overview
A Python desktop application built with CustomTkinter that helps users create, manage, and deploy Python desktop apps. It uses Ollama (Qwen) for idea expansion and Grok (via xAI API) for code generation.

## Recent Changes
- **2026-02-18**: Fixed module installation failures for generated projects
  - Switched from `pip install --user` to `pip install --target deps/` (project-local)
  - System packages (e.g. old dateutil 2.1 from Nix) no longer override fresh installs
  - Preview loads with deps/ on sys.path; launch sets PYTHONPATH to deps/ folder
  - Both ensure_dependencies (main.py) and launch_app_gui (handlers.py) updated
- **2026-02-18**: Added AI fix safety system and Undo button
  - Snapshot system: saves all .py files to `.backup/` folder before any AI fix attempt
  - Fix validation: test-compiles fixed code before committing (rejects syntax errors)
  - Diff size guard: rejects fixes that change >60% of the file (prevents destructive rewrites)
  - Reduced Qwen fix attempts from 5 to 2, then escalates to Grok
  - Added Undo button in build view that restores from last snapshot
  - `apply_fix()` also creates a snapshot before running AI fixes
- **2026-02-18**: UI redesign to match cosmic glassmorphism concept
  - Deeper cosmic color palette (BG_DEEP #060610, refined glass/entry colors)
  - Centered title badge in top bar
  - Pill-shaped neon-bordered buttons (Ideate=purple, Create=green, Deploy=cyan)
  - 4 suggestion cards with title + description, color-coded borders
  - Refined spacing, corner radii, and typography throughout
- **2026-02-18**: Fixed critical double-project creation bug
  - Added `_loading_preview` flag to prevent re-entrant `load_preview` calls
  - Added `_fixing_in_progress` flag to prevent multiple concurrent fix loops
  - Broke circular dependency: `load_preview` -> `ensure_dependencies` -> `load_preview` (infinite loop)
  - Moved `generating` flag reset into `_finish_generation` callback so it only resets AFTER `load_project` completes

## Project Architecture
- `main.py` - Main application class (AppBuilderGUI), view management, project loading, snapshot/undo system
- `views.py` - UI view creation functions (top bar, sliding menu, main view, build view with Undo button)
- `handlers.py` - Background thread handlers for generation, launching, fixing
- `ai_functions.py` - AI integration (Ollama, Grok API) for code generation and fixing
- `browser_automation.py` - Browser-based Grok interaction (optional)
- `config.py` - Configuration constants and file management
- `constants.py` - UI color palette constants (cosmic glassmorphism theme)
- `utils.py` - Utility functions (logging, mouse automation, code helpers)

## Key Dependencies
- customtkinter (UI framework)
- ollama (local LLM)
- openai (xAI/Grok API client)
- pyautogui, pyperclip (browser automation)
- numpy, scipy, bezier (mouse movement simulation)

## User Preferences
- Desktop app targeting Windows
- Dark cyberpunk/glassmorphism theme with deeper cosmic colors
- Uses Qwen models via Ollama and Grok via xAI API
- Concerned about AI fixes destroying code — safety system implemented
