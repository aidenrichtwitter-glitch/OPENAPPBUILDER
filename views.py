import customtkinter as ctk
import tkinter.messagebox as messagebox

from constants import *
from config import LLM_PROVIDERS, get_available_providers

def create_top_bar(self):
    top = ctk.CTkFrame(self, height=52, fg_color=BG_DARKER, corner_radius=0)
    top.pack(fill="x")
    top.pack_propagate(False)

    hamburger = ctk.CTkButton(top, text="≡", width=50, height=42,
                              font=ctk.CTkFont(size=28, weight="bold"),
                              fg_color="transparent", text_color=ACCENT_CYAN,
                              hover_color=BG_GLASS, corner_radius=8,
                              command=lambda: self.toggle_menu())
    hamburger.pack(side="left", padx=(12, 0))

    badge_frame = ctk.CTkFrame(top, fg_color=BG_GLASS, corner_radius=16,
                               border_width=1, border_color=BORDER_GLOW)
    badge_frame.pack(side="left", padx=(8, 0), pady=6)
    self.title_label = ctk.CTkLabel(badge_frame, text="Python Desktop App Builder",
                                    font=ctk.CTkFont(size=15, weight="bold"),
                                    text_color=TEXT_TITLE)
    self.title_label.pack(padx=20, pady=4)

    self.llm_toggle_frame = ctk.CTkFrame(top, fg_color="transparent")
    self.llm_toggle_frame.pack(side="right", padx=(0, 16), pady=6)
    self._llm_toggle_buttons = {}
    self.selected_provider = self.config.get("selected_llm", "hybrid")
    _build_llm_toggle(self)

def _build_llm_toggle(self):
    for widget in self.llm_toggle_frame.winfo_children():
        widget.destroy()
    self._llm_toggle_buttons = {}

    available = get_available_providers(self.config)
    cloud_providers = [p for p in available if p != "ollama"]
    show_hybrid = len(available) >= 2 and len(cloud_providers) >= 1

    for provider_id in available:
        info = LLM_PROVIDERS[provider_id]
        color = info["color"]
        btn = ctk.CTkButton(
            self.llm_toggle_frame, text=info["name"],
            width=70, height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=15,
            fg_color=BG_GLASS, text_color=TEXT_DIM,
            hover_color=BG_GLASS_LIGHT,
            border_width=2, border_color=BORDER_GLOW,
            command=lambda pid=provider_id: self.select_llm_provider(pid)
        )
        btn.pack(side="left", padx=2)
        self._llm_toggle_buttons[provider_id] = (btn, color)

    if show_hybrid:
        btn = ctk.CTkButton(
            self.llm_toggle_frame, text="Hybrid",
            width=70, height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=15,
            fg_color=BG_GLASS, text_color=TEXT_DIM,
            hover_color=BG_GLASS_LIGHT,
            border_width=2, border_color=BORDER_GLOW,
            command=lambda: self.select_llm_provider("hybrid")
        )
        btn.pack(side="left", padx=2)
        self._llm_toggle_buttons["hybrid"] = (btn, ACCENT_PURPLE)

    if self.selected_provider not in self._llm_toggle_buttons:
        if show_hybrid:
            self.selected_provider = "hybrid"
        elif available:
            self.selected_provider = available[0]
    _highlight_selected(self)

def _highlight_selected(self):
    for pid, (btn, color) in self._llm_toggle_buttons.items():
        if pid == self.selected_provider:
            btn.configure(fg_color=color, text_color=BG_DARK, border_color=color)
        else:
            btn.configure(fg_color=BG_GLASS, text_color=TEXT_DIM, border_color=BORDER_GLOW)

def create_sliding_menu(self):
    self.menu_frame = ctk.CTkFrame(self, width=280, fg_color=BG_DARKER, corner_radius=0,
                                   border_width=1, border_color=BORDER_GLOW)
    self.menu_frame.pack_forget()

    menu_title = ctk.CTkLabel(self.menu_frame, text="Navigation",
                              font=ctk.CTkFont(size=18, weight="bold"),
                              text_color=ACCENT_CYAN)
    menu_title.pack(pady=(20, 12), padx=24, anchor="w")

    for label, cmd in [("Main", lambda: self.show_main_view()),
                       ("Project Editor", lambda: self.show_project_editor()),
                       ("View Logs", lambda: self.show_logs()),
                       ("Config", lambda: self.show_config())]:
        ctk.CTkButton(self.menu_frame, text=label, height=44,
                      fg_color=BG_GLASS, hover_color=BG_GLASS_LIGHT,
                      text_color=TEXT_MAIN, font=ctk.CTkFont(size=14, weight="bold"),
                      corner_radius=10, anchor="w",
                      command=cmd).pack(pady=4, padx=20, fill="x")

    sep = ctk.CTkFrame(self.menu_frame, height=1, fg_color=BORDER_GLOW)
    sep.pack(fill="x", padx=20, pady=12)

    ctk.CTkLabel(self.menu_frame, text="Projects",
                 font=ctk.CTkFont(size=16, weight="bold"),
                 text_color=ACCENT_PURPLE).pack(pady=(4, 8), padx=24, anchor="w")

    self.project_var = ctk.StringVar(value="Select project...")
    self.project_menu = ctk.CTkOptionMenu(self.menu_frame, variable=self.project_var,
                                          values=[],
                                          command=lambda val: self.select_project_from_menu(val),
                                          fg_color=BG_GLASS, button_color=ACCENT_PURPLE,
                                          button_hover_color=GLOW_PURPLE,
                                          text_color=TEXT_MAIN, height=38,
                                          font=ctk.CTkFont(size=13),
                                          corner_radius=10)
    self.project_menu.pack(pady=4, padx=20, fill="x")

def create_main_view(self):
    self.main_view = ctk.CTkFrame(self.content_container, fg_color=BG_CARD,
                                  corner_radius=28, border_width=2,
                                  border_color=BORDER_GLOW)
    self.main_view.pack(fill="both", expand=True, padx=20, pady=10)

    title = ctk.CTkLabel(self.main_view, text="What do you want to do?",
                         font=ctk.CTkFont(size=38, weight="bold"),
                         text_color=TEXT_BRIGHT)
    title.pack(pady=(30, 20))

    btn_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
    btn_frame.pack(pady=10, padx=80, fill="x")
    btn_frame.grid_columnconfigure((0, 1), weight=1)

    self.ideate_btn = ctk.CTkButton(btn_frame, text="Ideate",
                                    font=ctk.CTkFont(size=22, weight="bold"),
                                    fg_color=BTN_PURPLE_BG, text_color=TEXT_BRIGHT,
                                    height=64, corner_radius=999,
                                    border_width=3, border_color=ACCENT_PURPLE,
                                    hover_color=BTN_PURPLE_HOVER,
                                    command=lambda: self.show_idea_chat())
    self.ideate_btn.grid(row=0, column=0, padx=10, sticky="ew")

    self.create_btn = ctk.CTkButton(btn_frame, text="Create",
                                    font=ctk.CTkFont(size=22, weight="bold"),
                                    fg_color=BTN_GREEN_BG, text_color=TEXT_BRIGHT,
                                    height=64, corner_radius=999,
                                    border_width=3, border_color=ACCENT_GREEN,
                                    hover_color=BTN_GREEN_HOVER,
                                    command=self.create_and_generate)
    self.create_btn.grid(row=0, column=1, padx=10, sticky="ew")

    self.idea_entry = ctk.CTkEntry(self.main_view,
                                   placeholder_text="Describe your app idea here...",
                                   font=ctk.CTkFont(size=16),
                                   fg_color=BG_ENTRY, text_color=TEXT_MAIN,
                                   placeholder_text_color=TEXT_DIM,
                                   height=52, corner_radius=26,
                                   border_width=2, border_color=BORDER_NEON)
    self.idea_entry.pack(pady=(12, 14), padx=60, fill="x")

    self.ideas_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
    self.ideas_frame.pack(pady=(4, 16), padx=30, fill="both", expand=True)
    self.ideas_frame.grid_columnconfigure((0, 1), weight=1)
    self.ideas_frame.grid_rowconfigure((0, 1), weight=1)

def create_idea_chat_view(self):
    self.idea_chat_view = ctk.CTkFrame(self.content_container, fg_color=BG_CARD,
                                       corner_radius=28, border_width=2,
                                       border_color=BORDER_GLOW)

    self.llm_selector = ctk.CTkSegmentedButton(self.idea_chat_view,
                                               values=["Ollama", "Grok"],
                                               fg_color=BG_GLASS,
                                               selected_color=ACCENT_PURPLE,
                                               selected_hover_color=GLOW_PURPLE,
                                               text_color=TEXT_MAIN,
                                               font=ctk.CTkFont(size=14))
    self.llm_selector.grid(row=0, column=0, pady=(20, 10), padx=40, sticky="ew")
    self.llm_selector.set("Ollama")

    self.chat_box = ctk.CTkTextbox(self.idea_chat_view,
                                   font=ctk.CTkFont(family="Consolas", size=13),
                                   fg_color=BG_GLASS, text_color=TEXT_MAIN,
                                   border_width=1, border_color=BORDER_GLOW,
                                   corner_radius=12)
    self.chat_box.grid(row=1, column=0, padx=40, pady=(0, 10), sticky="nsew")
    self.idea_chat_view.grid_rowconfigure(1, weight=1)
    self.idea_chat_view.grid_columnconfigure(0, weight=1)

    input_frame = ctk.CTkFrame(self.idea_chat_view, fg_color="transparent")
    input_frame.grid(row=2, column=0, sticky="ew", padx=40, pady=(0, 10))
    input_frame.grid_columnconfigure(0, weight=1)

    self.chat_entry = ctk.CTkEntry(input_frame,
                                   placeholder_text="Ask the LLM anything...",
                                   font=ctk.CTkFont(size=15), height=48,
                                   fg_color=BG_ENTRY, text_color=TEXT_MAIN,
                                   placeholder_text_color=TEXT_DIM,
                                   border_width=2, border_color=BORDER_NEON,
                                   corner_radius=14)
    self.chat_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

    self.send_btn = ctk.CTkButton(input_frame, text="Send", width=100, height=48,
                                  fg_color=ACCENT_CYAN, hover_color=GLOW_CYAN,
                                  text_color=BG_DARK, font=ctk.CTkFont(size=15, weight="bold"),
                                  corner_radius=14,
                                  command=lambda: self.send_idea_message())
    self.send_btn.grid(row=0, column=1, padx=(0, 8))

    self.build_btn = ctk.CTkButton(input_frame, text="Build App", width=100, height=48,
                                   fg_color=ACCENT_GREEN, hover_color=GLOW_GREEN,
                                   text_color=BG_DARK, font=ctk.CTkFont(size=15, weight="bold"),
                                   corner_radius=14,
                                   command=lambda: self.build_from_ideate())
    self.build_btn.grid(row=0, column=2)

    ctk.CTkButton(self.idea_chat_view, text="← Back to Main", height=40,
                  fg_color=BG_GLASS, hover_color=BG_GLASS_LIGHT,
                  text_color=TEXT_MAIN, font=ctk.CTkFont(size=14),
                  corner_radius=12,
                  command=lambda: self.show_main_view()).grid(row=3, column=0, pady=(4, 16))

def create_logs_view(self):
    self.logs_view = ctk.CTkFrame(self.content_container, fg_color=BG_CARD,
                                  corner_radius=28, border_width=2,
                                  border_color=BORDER_GLOW)
    self.log_text = ctk.CTkTextbox(self.logs_view,
                                   font=ctk.CTkFont(family="Consolas", size=12),
                                   fg_color=BG_GLASS, text_color=GLOW_CYAN,
                                   border_width=1, border_color=BORDER_GLOW,
                                   corner_radius=12)
    self.log_text.pack(fill="both", expand=True, padx=30, pady=30)

def create_config_view(self):
    self.config_view = ctk.CTkFrame(self.content_container, fg_color=BG_CARD,
                                    corner_radius=28, border_width=2,
                                    border_color=BORDER_GLOW)

    scroll = ctk.CTkScrollableFrame(self.config_view, fg_color="transparent")
    scroll.pack(fill="both", expand=True, padx=20, pady=20)
    scroll.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(scroll, text="LLM API Keys",
                 font=ctk.CTkFont(size=20, weight="bold"),
                 text_color=ACCENT_PURPLE).grid(row=0, column=0, pady=(0, 4), padx=20, sticky="w")
    ctk.CTkLabel(scroll, text="Add your API keys below. Only providers with keys will appear in the model toggle.",
                 font=ctk.CTkFont(size=12),
                 text_color=TEXT_DIM, wraplength=500, justify="left").grid(row=1, column=0, pady=(0, 12), padx=20, sticky="w")

    self._api_key_entries = {}
    llm_keys = self.config.get("llm_keys", {})
    row = 2
    key_providers = [
        ("xai", "Grok (xAI)", "xai-...", ACCENT_PURPLE),
        ("openai", "OpenAI (GPT)", "sk-...", ACCENT_GREEN),
        ("anthropic", "Anthropic (Claude)", "sk-ant-...", "#f97316"),
        ("google", "Google (Gemini)", "AIza...", ACCENT_BLUE),
    ]
    for pid, label, placeholder, color in key_providers:
        ctk.CTkLabel(scroll, text=f"{label}:",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=color).grid(row=row, column=0, pady=(8, 2), padx=20, sticky="w")
        row += 1
        entry = ctk.CTkEntry(scroll, height=40,
                             font=ctk.CTkFont(size=13), fg_color=BG_ENTRY,
                             text_color=TEXT_MAIN, placeholder_text=placeholder,
                             placeholder_text_color=TEXT_DIM,
                             border_width=2, border_color=BORDER_NEON,
                             corner_radius=12, show="•")
        entry.grid(row=row, column=0, pady=(0, 4), padx=20, sticky="ew")
        existing_key = llm_keys.get(pid, "")
        if pid == "xai" and not existing_key:
            existing_key = self.config.get("xai_api_key", "")
        if existing_key:
            entry.insert(0, existing_key)
        self._api_key_entries[pid] = entry
        row += 1

    sep = ctk.CTkFrame(scroll, height=2, fg_color=BORDER_GLOW)
    sep.grid(row=row, column=0, sticky="ew", padx=20, pady=16)
    row += 1

    ctk.CTkLabel(scroll, text="Other Settings",
                 font=ctk.CTkFont(size=20, weight="bold"),
                 text_color=ACCENT_CYAN).grid(row=row, column=0, pady=(0, 8), padx=20, sticky="w")
    row += 1

    self.use_browser_var = ctk.BooleanVar(value=self.use_browser_for_grok)
    ctk.CTkCheckBox(scroll, text="Use Browser Automation for Grok",
                    variable=self.use_browser_var, command=lambda: self.toggle_browser(),
                    font=ctk.CTkFont(size=14), text_color=TEXT_MAIN,
                    fg_color=BG_GLASS, border_color=BORDER_NEON,
                    corner_radius=6).grid(row=row, column=0, pady=(0, 8), padx=20, sticky="w")
    row += 1

    ctk.CTkButton(scroll, text="Setup/Calibrate Browser", height=40,
                  fg_color=ACCENT_PURPLE, hover_color=GLOW_PURPLE,
                  font=ctk.CTkFont(size=14), corner_radius=12,
                  command=lambda: self.setup_calibration()).grid(row=row, column=0, pady=4, padx=20, sticky="w")
    row += 1

    ctk.CTkLabel(scroll, text="VPN Command:",
                 font=ctk.CTkFont(size=14, weight="bold"),
                 text_color=TEXT_MAIN).grid(row=row, column=0, pady=(12, 2), padx=20, sticky="w")
    row += 1

    self.vpn_entry = ctk.CTkEntry(scroll, height=40,
                                  font=ctk.CTkFont(size=13), fg_color=BG_ENTRY,
                                  text_color=TEXT_MAIN,
                                  border_width=2, border_color=BORDER_NEON,
                                  corner_radius=12)
    self.vpn_entry.grid(row=row, column=0, pady=4, padx=20, sticky="ew")
    self.vpn_entry.insert(0, self.config.get('vpn_cmd', ''))
    row += 1

    ctk.CTkButton(scroll, text="Save Config", height=46,
                  fg_color=ACCENT_GREEN, hover_color=GLOW_GREEN,
                  text_color=BG_DARK,
                  font=ctk.CTkFont(size=16, weight="bold"),
                  corner_radius=14,
                  command=lambda: self.save_config_gui()).grid(row=row, column=0, pady=(16, 8), padx=20, sticky="w")

def create_build_view(self):
    self.build_view = ctk.CTkFrame(self.content_container, fg_color=BG_CARD,
                                   corner_radius=28, border_width=2,
                                   border_color=BORDER_GLOW)
    self.build_view.grid_columnconfigure(1, weight=1)
    self.build_view.grid_rowconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(self.build_view, fg_color=BG_GLASS, corner_radius=16,
                              border_width=1, border_color=BORDER_GLOW, width=200)
    left_panel.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(16, 8), pady=16)

    ctk.CTkLabel(left_panel, text="Build Log",
                 font=ctk.CTkFont(size=13, weight="bold"),
                 text_color=ACCENT_CYAN).pack(pady=(10, 4), padx=10)

    self.build_log = ctk.CTkTextbox(left_panel, width=180,
                                    font=ctk.CTkFont(family="Consolas", size=11),
                                    fg_color=BG_ENTRY, text_color=GLOW_CYAN,
                                    border_width=0, corner_radius=10)
    self.build_log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    ctk.CTkButton(left_panel, text="← Main", height=36,
                  fg_color=BG_GLASS_LIGHT, hover_color=BORDER_GLOW,
                  text_color=TEXT_MAIN, font=ctk.CTkFont(size=13),
                  corner_radius=10,
                  command=lambda: self.show_main_view()).pack(pady=(0, 10), padx=8, fill="x")

    right_column = ctk.CTkFrame(self.build_view, fg_color="transparent")
    right_column.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(0, 16), pady=16)
    right_column.grid_columnconfigure(0, weight=1)
    right_column.grid_rowconfigure(0, weight=1)

    self.main_content = ctk.CTkFrame(right_column, fg_color=BG_GLASS,
                                     corner_radius=16, border_width=1,
                                     border_color=BORDER_GLOW)
    self.main_content.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))

    bottom_frame = ctk.CTkFrame(right_column, fg_color="transparent")
    bottom_frame.grid(row=1, column=0, sticky="ew", pady=0)
    bottom_frame.grid_columnconfigure(0, weight=1)

    self.fix_entry = ctk.CTkEntry(bottom_frame,
                                  placeholder_text="Enter fixes or upgrades...",
                                  font=ctk.CTkFont(size=15), height=46,
                                  fg_color=BG_ENTRY, text_color=TEXT_MAIN,
                                  placeholder_text_color=TEXT_DIM,
                                  border_width=2, border_color=BORDER_NEON,
                                  corner_radius=14)
    self.fix_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

    self.apply_fix_btn = ctk.CTkButton(bottom_frame, text="Apply", width=100, height=46,
                                       fg_color=ACCENT_PURPLE, hover_color=GLOW_PURPLE,
                                       text_color=TEXT_BRIGHT,
                                       font=ctk.CTkFont(size=15, weight="bold"),
                                       corner_radius=14,
                                       command=lambda: self.apply_fix())
    self.apply_fix_btn.grid(row=0, column=1, padx=(0, 8))

    self.undo_btn = ctk.CTkButton(bottom_frame, text="⏪ Undo", width=100, height=46,
                                   fg_color=BG_GLASS, hover_color=BG_GLASS_LIGHT,
                                   text_color=TEXT_MAIN,
                                   font=ctk.CTkFont(size=15, weight="bold"),
                                   corner_radius=14, state="disabled",
                                   command=lambda: self.restore_snapshot())
    self.undo_btn.grid(row=0, column=2, padx=(0, 8))

    self.deploy_btn = ctk.CTkButton(bottom_frame, text="Deploy", width=100, height=46,
                                    fg_color=ACCENT_CYAN, hover_color=GLOW_CYAN,
                                    text_color=BG_DARK,
                                    font=ctk.CTkFont(size=15, weight="bold"),
                                    corner_radius=14,
                                    command=lambda: self.deploy_app())
    self.deploy_btn.grid(row=0, column=3)
