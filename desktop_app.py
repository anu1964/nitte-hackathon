import tkinter as tk
from tkinter import scrolledtext, font
import threading
import requests
import json
import time
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
API_URL = "http://127.0.0.1:8000"

# ── Colors ─────────────────────────────────────────────────────────────────────
BG_DARK       = "#0d0f14"
BG_PANEL      = "#13161e"
BG_CARD       = "#1a1d27"
BG_INPUT      = "#1e2130"
ACCENT_CYAN   = "#00d4ff"
ACCENT_RED    = "#ff3b5c"
ACCENT_GREEN  = "#00e87a"
ACCENT_YELLOW = "#ffd43b"
TEXT_PRIMARY  = "#e8eaf0"
TEXT_MUTED    = "#5a6070"
TEXT_DIM      = "#3a3f50"
BORDER        = "#252836"
USER_BUBBLE   = "#1e3a5f"
BOT_BUBBLE    = "#1a1d27"
BLOCK_BUBBLE  = "#2a0f18"

class SafeGuardianApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Safe Prompt Guardian — AI Assistant")
        self.root.geometry("900x700")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)
        self.root.minsize(700, 500)

        self.stats = {"total": 0, "blocked": 0}
        self.typing = False

        self._build_ui()
        self._check_api_status()

    # ── UI Builder ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Top Header ──────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=BG_PANEL, height=60)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Left — logo + title
        left_header = tk.Frame(header, bg=BG_PANEL)
        left_header.pack(side=tk.LEFT, padx=20, pady=10)

        shield = tk.Label(left_header, text="🛡", font=("Segoe UI Emoji", 22),
                          bg=BG_PANEL, fg=ACCENT_CYAN)
        shield.pack(side=tk.LEFT, padx=(0, 8))

        title_frame = tk.Frame(left_header, bg=BG_PANEL)
        title_frame.pack(side=tk.LEFT)

        tk.Label(title_frame, text="Safe Prompt Guardian",
                 font=("Consolas", 13, "bold"),
                 bg=BG_PANEL, fg=TEXT_PRIMARY).pack(anchor=tk.W)
        tk.Label(title_frame, text="AI Assistant with Prompt Injection Protection",
                 font=("Consolas", 8),
                 bg=BG_PANEL, fg=TEXT_MUTED).pack(anchor=tk.W)

        # Right — status indicator
        right_header = tk.Frame(header, bg=BG_PANEL)
        right_header.pack(side=tk.RIGHT, padx=20)

        self.status_dot = tk.Label(right_header, text="●",
                                    font=("Segoe UI", 10),
                                    bg=BG_PANEL, fg=ACCENT_YELLOW)
        self.status_dot.pack(side=tk.LEFT, padx=(0, 5))

        self.status_label = tk.Label(right_header, text="Connecting...",
                                      font=("Consolas", 9),
                                      bg=BG_PANEL, fg=TEXT_MUTED)
        self.status_label.pack(side=tk.LEFT)

        # Separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        # ── Stats Bar ───────────────────────────────────────────────────────────
        stats_bar = tk.Frame(self.root, bg=BG_CARD, height=38)
        stats_bar.pack(fill=tk.X)
        stats_bar.pack_propagate(False)

        stats_inner = tk.Frame(stats_bar, bg=BG_CARD)
        stats_inner.pack(side=tk.LEFT, padx=20, pady=6)

        self._stat_block(stats_inner, "PROMPTS ANALYZED", "0", "total_val", ACCENT_CYAN)
        self._divider(stats_inner)
        self._stat_block(stats_inner, "ATTACKS BLOCKED", "0", "blocked_val", ACCENT_RED)
        self._divider(stats_inner)
        self._stat_block(stats_inner, "ATTACK RATE", "0%", "rate_val", ACCENT_YELLOW)
        self._divider(stats_inner)
        self._stat_block(stats_inner, "MODEL ACCURACY", "96.88%", "acc_val", ACCENT_GREEN)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        # ── Chat Area ───────────────────────────────────────────────────────────
        self.chat_frame = tk.Frame(self.root, bg=BG_DARK)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Canvas + scrollbar for chat bubbles
        self.canvas = tk.Canvas(self.chat_frame, bg=BG_DARK,
                                 highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self.chat_frame, orient=tk.VERTICAL,
                                       command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.messages_frame = tk.Frame(self.canvas, bg=BG_DARK)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.messages_frame, anchor=tk.NW
        )

        self.messages_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Welcome message
        self._add_system_message(
            "🛡️  Safe Prompt Guardian is active. Every message is scanned "
            "for prompt injection before reaching the AI."
        )

        # ── Input Area ──────────────────────────────────────────────────────────
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        input_area = tk.Frame(self.root, bg=BG_PANEL, pady=14)
        input_area.pack(fill=tk.X, side=tk.BOTTOM)

        input_inner = tk.Frame(input_area, bg=BG_INPUT,
                                highlightthickness=1,
                                highlightbackground=BORDER,
                                highlightcolor=ACCENT_CYAN)
        input_inner.pack(fill=tk.X, padx=16)

        self.input_box = tk.Text(input_inner, height=3,
                                  bg=BG_INPUT, fg=TEXT_PRIMARY,
                                  font=("Consolas", 11),
                                  insertbackground=ACCENT_CYAN,
                                  relief=tk.FLAT, bd=0,
                                  wrap=tk.WORD,
                                  padx=12, pady=10)
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)
        self.input_box.bind("<FocusIn>",
            lambda e: input_inner.config(highlightbackground=ACCENT_CYAN))
        self.input_box.bind("<FocusOut>",
            lambda e: input_inner.config(highlightbackground=BORDER))

        # Placeholder
        self._set_placeholder()

        btn_frame = tk.Frame(input_inner, bg=BG_INPUT, padx=8, pady=8)
        btn_frame.pack(side=tk.RIGHT)

        self.send_btn = tk.Button(
            btn_frame, text="Send  ▶",
            font=("Consolas", 10, "bold"),
            bg=ACCENT_CYAN, fg=BG_DARK,
            activebackground="#00b8e0", activeforeground=BG_DARK,
            relief=tk.FLAT, bd=0, padx=16, pady=8,
            cursor="hand2",
            command=self._send_message
        )
        self.send_btn.pack()

        # Hint
        tk.Label(input_area,
                 text="Enter to send  •  Shift+Enter for new line  •  Powered by LLaMA 3.1",
                 font=("Consolas", 8), bg=BG_PANEL, fg=TEXT_DIM
                 ).pack(pady=(4, 0))

    def _stat_block(self, parent, label, value, attr, color):
        frame = tk.Frame(parent, bg=BG_CARD)
        frame.pack(side=tk.LEFT, padx=16)
        val = tk.Label(frame, text=value,
                       font=("Consolas", 13, "bold"),
                       bg=BG_CARD, fg=color)
        val.pack()
        tk.Label(frame, text=label,
                 font=("Consolas", 7),
                 bg=BG_CARD, fg=TEXT_MUTED).pack()
        setattr(self, attr, val)

    def _divider(self, parent):
        tk.Frame(parent, bg=BORDER, width=1, height=28).pack(
            side=tk.LEFT, padx=4)

    # ── Placeholder ─────────────────────────────────────────────────────────────
    def _set_placeholder(self):
        self.input_box.insert("1.0", "Type your message here...")
        self.input_box.config(fg=TEXT_MUTED)
        self.input_box.bind("<FocusIn>", self._clear_placeholder)
        self.input_box.bind("<FocusOut>", self._restore_placeholder)
        self._placeholder_active = True

    def _clear_placeholder(self, event=None):
        if self._placeholder_active:
            self.input_box.delete("1.0", tk.END)
            self.input_box.config(fg=TEXT_PRIMARY)
            self._placeholder_active = False

    def _restore_placeholder(self, event=None):
        if not self.input_box.get("1.0", tk.END).strip():
            self.input_box.insert("1.0", "Type your message here...")
            self.input_box.config(fg=TEXT_MUTED)
            self._placeholder_active = True

    # ── Canvas Helpers ──────────────────────────────────────────────────────────
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _scroll_to_bottom(self):
        self.root.after(100, lambda: self.canvas.yview_moveto(1.0))

    # ── Message Bubbles ─────────────────────────────────────────────────────────
    def _add_system_message(self, text):
        frame = tk.Frame(self.messages_frame, bg=BG_DARK)
        frame.pack(fill=tk.X, padx=20, pady=(16, 4))

        tk.Label(frame, text=text,
                 font=("Consolas", 9),
                 bg=BG_DARK, fg=TEXT_MUTED,
                 wraplength=700, justify=tk.CENTER).pack()

    def _add_user_bubble(self, text):
        outer = tk.Frame(self.messages_frame, bg=BG_DARK)
        outer.pack(fill=tk.X, padx=20, pady=(8, 2))

        # Timestamp
        ts = datetime.now().strftime("%H:%M")
        tk.Label(outer, text=f"You  {ts}",
                 font=("Consolas", 8), bg=BG_DARK,
                 fg=TEXT_MUTED).pack(anchor=tk.E, padx=4)

        bubble = tk.Frame(outer, bg=USER_BUBBLE,
                           highlightthickness=1,
                           highlightbackground="#1e4a7a")
        bubble.pack(anchor=tk.E)

        tk.Label(bubble, text=text,
                 font=("Consolas", 11),
                 bg=USER_BUBBLE, fg=TEXT_PRIMARY,
                 wraplength=580, justify=tk.LEFT,
                 padx=14, pady=10).pack()

        self._scroll_to_bottom()

    def _add_bot_bubble(self, text):
        outer = tk.Frame(self.messages_frame, bg=BG_DARK)
        outer.pack(fill=tk.X, padx=20, pady=(8, 2))

        ts = datetime.now().strftime("%H:%M")
        tk.Label(outer, text=f"🤖 AI Assistant  {ts}",
                 font=("Consolas", 8), bg=BG_DARK,
                 fg=TEXT_MUTED).pack(anchor=tk.W, padx=4)

        bubble = tk.Frame(outer, bg=BOT_BUBBLE,
                           highlightthickness=1,
                           highlightbackground=BORDER)
        bubble.pack(anchor=tk.W)

        tk.Label(bubble, text=text,
                 font=("Consolas", 11),
                 bg=BOT_BUBBLE, fg=TEXT_PRIMARY,
                 wraplength=580, justify=tk.LEFT,
                 padx=14, pady=10).pack()

        self._scroll_to_bottom()

    def _add_blocked_bubble(self, category, severity, confidence, rephrasing=None):
        outer = tk.Frame(self.messages_frame, bg=BG_DARK)
        outer.pack(fill=tk.X, padx=20, pady=(8, 2))

        ts = datetime.now().strftime("%H:%M")
        tk.Label(outer, text=f"🛡 Guardian  {ts}",
                 font=("Consolas", 8), bg=BG_DARK,
                 fg=ACCENT_RED).pack(anchor=tk.W, padx=4)

        bubble = tk.Frame(outer, bg=BLOCK_BUBBLE,
                           highlightthickness=1,
                           highlightbackground=ACCENT_RED)
        bubble.pack(anchor=tk.W, fill=tk.X)

        # Header
        header = tk.Frame(bubble, bg=BLOCK_BUBBLE)
        header.pack(fill=tk.X, padx=14, pady=(10, 4))

        tk.Label(header, text="🚨  ATTACK BLOCKED",
                 font=("Consolas", 12, "bold"),
                 bg=BLOCK_BUBBLE, fg=ACCENT_RED).pack(side=tk.LEFT)

        # Severity badge
        sev_colors = {
            "Critical": ACCENT_RED,
            "High": "#ff6b35",
            "Medium": ACCENT_YELLOW,
            "Low": ACCENT_GREEN
        }
        sev_color = sev_colors.get(severity, ACCENT_YELLOW)
        tk.Label(header, text=f"  {severity.upper()}  ",
                 font=("Consolas", 8, "bold"),
                 bg=sev_color, fg=BG_DARK,
                 padx=4, pady=2).pack(side=tk.RIGHT)

        # Separator
        tk.Frame(bubble, bg=ACCENT_RED, height=1).pack(fill=tk.X, padx=14)

        # Details
        details = tk.Frame(bubble, bg=BLOCK_BUBBLE)
        details.pack(fill=tk.X, padx=14, pady=8)

        cat_display = (category or "Unknown").replace("_", " ").title()
        conf_display = f"{confidence * 100:.1f}%"

        tk.Label(details,
                 text=f"Category    :  {cat_display}\n"
                      f"Confidence  :  {conf_display}\n"
                      f"Status      :  Prompt never reached the LLM",
                 font=("Consolas", 10),
                 bg=BLOCK_BUBBLE, fg="#ff8fa3",
                 justify=tk.LEFT).pack(anchor=tk.W)

        # Safe rephrasing
        if rephrasing:
            tk.Frame(bubble, bg=BORDER, height=1).pack(fill=tk.X, padx=14)
            rephrase_frame = tk.Frame(bubble, bg=BLOCK_BUBBLE)
            rephrase_frame.pack(fill=tk.X, padx=14, pady=(6, 10))

            tk.Label(rephrase_frame,
                     text="💡 Safe alternative:",
                     font=("Consolas", 9, "bold"),
                     bg=BLOCK_BUBBLE, fg=ACCENT_YELLOW).pack(anchor=tk.W)

            tk.Label(rephrase_frame, text=rephrasing,
                     font=("Consolas", 9),
                     bg=BLOCK_BUBBLE, fg="#ffd43b",
                     wraplength=520, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 0))
        else:
            tk.Frame(bubble, bg=BG_DARK, height=6).pack()

        self._scroll_to_bottom()

    def _add_typing_indicator(self):
        self.typing_frame = tk.Frame(self.messages_frame, bg=BG_DARK)
        self.typing_frame.pack(fill=tk.X, padx=20, pady=(4, 0))

        tk.Label(self.typing_frame, text="🤖 AI Assistant is thinking...",
                 font=("Consolas", 9, "italic"),
                 bg=BG_DARK, fg=TEXT_MUTED).pack(anchor=tk.W)

        self._scroll_to_bottom()

    def _remove_typing_indicator(self):
        if hasattr(self, 'typing_frame'):
            self.typing_frame.destroy()

    # ── Core Logic ──────────────────────────────────────────────────────────────
    def _on_enter(self, event):
        if not event.state & 0x1:  # Shift not held
            self._send_message()
            return "break"

    def _send_message(self):
        if self._placeholder_active:
            return
        text = self.input_box.get("1.0", tk.END).strip()
        if not text:
            return

        self.input_box.delete("1.0", tk.END)
        self._restore_placeholder()
        self.send_btn.config(state=tk.DISABLED, bg=TEXT_DIM)
        self._add_user_bubble(text)
        self._add_typing_indicator()
        threading.Thread(target=self._process_message,
                         args=(text,), daemon=True).start()

    def _process_message(self, text):
        try:
            # Call Guardian API
            response = requests.post(
                f"{API_URL}/chat",
                json={"prompt": text, "system_prompt":
                      "You are a helpful AI assistant. Answer clearly and concisely."},
                timeout=30
            )
            data = response.json()

            self.root.after(0, self._remove_typing_indicator)

            if data["status"] == "blocked":
                # Get full details from /analyze
                analyze_resp = requests.post(
                    f"{API_URL}/analyze",
                    json={"prompt": text, "rephrase": True},
                    timeout=30
                )
                details = analyze_resp.json()

                self.root.after(0, lambda: self._add_blocked_bubble(
                    category=details.get("category"),
                    severity=details.get("severity", "High"),
                    confidence=details.get("confidence", data["confidence"]),
                    rephrasing=details.get("safe_rephrasing")
                ))
                self.root.after(0, self._increment_blocked)
            else:
                msg = data.get("message", "No response.")
                self.root.after(0, lambda: self._add_bot_bubble(msg))

            self.root.after(0, self._increment_total)
            self.root.after(0, self._update_stats_display)

        except requests.exceptions.ConnectionError:
            self.root.after(0, self._remove_typing_indicator)
            self.root.after(0, lambda: self._add_system_message(
                "⚠️  Cannot connect to Guardian API. Make sure api.py is running on port 8000."
            ))
        except Exception as e:
            self.root.after(0, self._remove_typing_indicator)
            self.root.after(0, lambda: self._add_system_message(f"⚠️  Error: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.send_btn.config(
                state=tk.NORMAL, bg=ACCENT_CYAN))

    # ── Stats ───────────────────────────────────────────────────────────────────
    def _increment_total(self):
        self.stats["total"] += 1

    def _increment_blocked(self):
        self.stats["blocked"] += 1

    def _update_stats_display(self):
        t = self.stats["total"]
        b = self.stats["blocked"]
        rate = f"{(b/t*100):.1f}%" if t > 0 else "0%"
        self.total_val.config(text=str(t))
        self.blocked_val.config(text=str(b))
        self.rate_val.config(text=rate)

    # ── API Status Check ────────────────────────────────────────────────────────
    def _check_api_status(self):
        def check():
            try:
                r = requests.get(f"{API_URL}/health", timeout=3)
                if r.status_code == 200:
                    self.root.after(0, lambda: self.status_dot.config(fg=ACCENT_GREEN))
                    self.root.after(0, lambda: self.status_label.config(
                        text="Guardian Active", fg=ACCENT_GREEN))
                else:
                    self._set_offline()
            except:
                self._set_offline()
            # Recheck every 10 seconds
            self.root.after(10000, self._check_api_status)

        threading.Thread(target=check, daemon=True).start()

    def _set_offline(self):
        self.root.after(0, lambda: self.status_dot.config(fg=ACCENT_RED))
        self.root.after(0, lambda: self.status_label.config(
            text="API Offline — run api.py", fg=ACCENT_RED))


# ── Main ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()

    # Try to set window icon
    try:
        root.iconbitmap(default="")
    except:
        pass

    app = SafeGuardianApp(root)
    root.mainloop()