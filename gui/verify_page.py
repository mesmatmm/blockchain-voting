import tkinter as tk
import threading
import time

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

BG = "#1a1a2e"
PANEL = "#16213e"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
TEXT = "#eaeaea"
SUCCESS = "#4CAF50"
WARNING = "#ff9800"
FONT_MAIN = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_LARGE = ("Segoe UI", 16, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 10)


class VerifyPage:
    def __init__(self, parent, node_url, root):
        self.parent = parent
        self.node_url = node_url
        self.root = root
        self._hash_var = tk.StringVar()
        self._build()

    def _build(self):
        tk.Label(
            self.parent, text="Verify Your Vote", font=FONT_LARGE,
            bg=BG, fg=HIGHLIGHT
        ).pack(pady=(20, 5))
        tk.Frame(self.parent, bg=HIGHLIGHT, height=2).pack(fill=tk.X, padx=20, pady=5)

        container = tk.Frame(self.parent, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=60, pady=20)

        # Input panel
        input_panel = tk.Frame(container, bg=PANEL, padx=30, pady=25)
        input_panel.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            input_panel,
            text="Enter your Vote Hash to verify it was recorded on the blockchain.",
            font=FONT_MAIN, bg=PANEL, fg=TEXT, wraplength=600
        ).pack(anchor="w", pady=(0, 15))

        entry_row = tk.Frame(input_panel, bg=PANEL)
        entry_row.pack(fill=tk.X)

        self._hash_entry = tk.Entry(
            entry_row, textvariable=self._hash_var, width=60,
            bg=ACCENT, fg=TEXT, insertbackground=TEXT,
            relief=tk.FLAT, font=FONT_MONO
        )
        self._hash_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 10))

        self._verify_btn = tk.Button(
            entry_row, text="VERIFY",
            command=self._do_verify,
            bg=HIGHLIGHT, fg="white", font=FONT_TITLE,
            activebackground="#c73652", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=20, pady=10
        )
        self._verify_btn.pack(side=tk.LEFT)

        tk.Button(
            entry_row, text="Clear",
            command=self._clear,
            bg=ACCENT, fg=TEXT, font=FONT_MAIN,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=14, pady=10
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Result panel
        self._result_panel = tk.Frame(container, bg=PANEL, padx=30, pady=25)
        self._result_panel.pack(fill=tk.BOTH, expand=True)

        self._result_icon = tk.Label(
            self._result_panel, text="", font=("Segoe UI", 48, "bold"),
            bg=PANEL
        )
        self._result_icon.pack(pady=(0, 10))

        self._result_title = tk.Label(
            self._result_panel, text="Enter a vote hash above and click VERIFY",
            font=FONT_TITLE, bg=PANEL, fg=TEXT
        )
        self._result_title.pack()

        self._result_details = tk.Frame(self._result_panel, bg=PANEL)
        self._result_details.pack(fill=tk.X, pady=20)

        self._bind_enter()

    def _bind_enter(self):
        self._hash_entry.bind("<Return>", lambda e: self._do_verify())

    def _do_verify(self):
        vote_hash = self._hash_var.get().strip()
        if not vote_hash:
            self._show_result(None, error="Please enter a vote hash.")
            return
        if len(vote_hash) != 64:
            self._show_result(None, error="Invalid hash format (expected 64 hex characters).")
            return
        if not REQUESTS_OK:
            self._show_result(None, error="requests library not available.")
            return

        self._verify_btn.configure(state=tk.DISABLED, text="Verifying...")
        self._result_icon.configure(text="", fg=TEXT)
        self._result_title.configure(text="Searching blockchain...", fg=WARNING)

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/find_vote/{vote_hash}", timeout=5)
                data = r.json()
                self.root.after(0, lambda: self._show_result(data))
            except Exception as ex:
                self.root.after(0, lambda: self._show_result(None, error=str(ex)))

        threading.Thread(target=fetch, daemon=True).start()

    def _show_result(self, data, error=None):
        self._verify_btn.configure(state=tk.NORMAL, text="VERIFY")

        # Clear old details
        for w in self._result_details.winfo_children():
            w.destroy()

        if error:
            self._result_icon.configure(text="!", fg=WARNING)
            self._result_title.configure(text=f"Error: {error}", fg=WARNING)
            return

        if not data:
            return

        if data.get("found"):
            self._result_icon.configure(text="CONFIRMED", fg=SUCCESS)
            self._result_title.configure(
                text="Your vote is recorded on the blockchain!", fg=SUCCESS
            )
            fields = [
                ("Block Number", str(data.get("block_index", "?"))),
                ("Block Hash", data.get("block_hash", "?")[:32] + "..."),
                ("Candidate", data.get("candidate", "?")),
                ("Election ID", data.get("election_id", "?")),
                ("Timestamp", time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(data.get("timestamp", 0))
                )),
            ]
            for label, value in fields:
                row = tk.Frame(self._result_details, bg=PANEL)
                row.pack(fill=tk.X, pady=3)
                tk.Label(
                    row, text=f"{label}:", width=18, anchor="w",
                    font=("Segoe UI", 10, "bold"), bg=PANEL, fg=WARNING
                ).pack(side=tk.LEFT)
                tk.Label(
                    row, text=value, anchor="w",
                    font=FONT_MONO, bg=PANEL, fg=TEXT
                ).pack(side=tk.LEFT)
        else:
            self._result_icon.configure(text="NOT FOUND", fg=HIGHLIGHT)
            self._result_title.configure(
                text="Vote not found in the blockchain.", fg=HIGHLIGHT
            )
            tk.Label(
                self._result_details,
                text=(
                    "This could mean:\n"
                    "  - The vote is still pending (not yet mined into a block)\n"
                    "  - The hash is incorrect\n"
                    "  - The vote was not submitted to this node"
                ),
                font=FONT_MAIN, bg=PANEL, fg=TEXT, justify="left"
            ).pack(anchor="w", pady=10)

    def _clear(self):
        self._hash_var.set("")
        for w in self._result_details.winfo_children():
            w.destroy()
        self._result_icon.configure(text="", fg=TEXT)
        self._result_title.configure(
            text="Enter a vote hash above and click VERIFY", fg=TEXT
        )

    def on_show(self):
        pass
