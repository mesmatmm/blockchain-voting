import tkinter as tk
from tkinter import filedialog, messagebox
import threading

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
FONT_MONO = ("Consolas", 9)

EVENT_TYPES = ["ALL", "VOTE", "VOTE_REJECTED", "MINE", "ELECTION", "PEER", "SYNC", "STARTUP", "ERROR", "ADMIN"]


class AuditPage:
    def __init__(self, parent, node_url, root):
        self.parent = parent
        self.node_url = node_url
        self.root = root
        self._filter_var = tk.StringVar(value="ALL")
        self._all_entries = []
        self._auto_refresh = True
        self._build()
        self._start_auto_refresh()

    def _build(self):
        # Header
        header = tk.Frame(self.parent, bg=BG)
        header.pack(fill=tk.X, padx=20, pady=(20, 5))

        tk.Label(header, text="Audit Log", font=FONT_LARGE, bg=BG, fg=HIGHLIGHT).pack(side=tk.LEFT)

        btn_frame = tk.Frame(header, bg=BG)
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(
            btn_frame, text="Refresh",
            command=self._fetch_log,
            bg=ACCENT, fg=TEXT, font=FONT_SMALL,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=10, pady=6
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="Export CSV",
            command=self._export_csv,
            bg=SUCCESS, fg="white", font=FONT_SMALL,
            activebackground="#3d8b40", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=10, pady=6
        ).pack(side=tk.LEFT, padx=5)

        tk.Frame(self.parent, bg=HIGHLIGHT, height=2).pack(fill=tk.X, padx=20, pady=5)

        # Filter bar
        filter_bar = tk.Frame(self.parent, bg=BG)
        filter_bar.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(filter_bar, text="Filter by type:", font=FONT_MAIN, bg=BG, fg=TEXT).pack(side=tk.LEFT, padx=(0, 8))

        for et in EVENT_TYPES:
            rb = tk.Radiobutton(
                filter_bar, text=et, value=et,
                variable=self._filter_var,
                command=self._apply_filter,
                bg=BG, fg=TEXT, selectcolor=ACCENT,
                activebackground=BG, activeforeground=TEXT,
                font=FONT_SMALL
            )
            rb.pack(side=tk.LEFT, padx=3)

        # Log text area
        log_frame = tk.Frame(self.parent, bg=PANEL)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        v_scroll = tk.Scrollbar(log_frame, orient=tk.VERTICAL, bg=PANEL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        h_scroll = tk.Scrollbar(log_frame, orient=tk.HORIZONTAL, bg=PANEL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self._log_text = tk.Text(
            log_frame,
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            bg=BG, fg=TEXT, font=FONT_MONO,
            relief=tk.FLAT, wrap=tk.NONE,
            padx=10, pady=10,
            state=tk.DISABLED
        )
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.configure(command=self._log_text.yview)
        h_scroll.configure(command=self._log_text.xview)

        # Colour tags
        self._log_text.tag_configure("VOTE", foreground=SUCCESS)
        self._log_text.tag_configure("VOTE_REJECTED", foreground=HIGHLIGHT)
        self._log_text.tag_configure("MINE", foreground=WARNING)
        self._log_text.tag_configure("ELECTION", foreground="#2196F3")
        self._log_text.tag_configure("PEER", foreground="#9C27B0")
        self._log_text.tag_configure("SYNC", foreground="#00BCD4")
        self._log_text.tag_configure("STARTUP", foreground="#607D8B")
        self._log_text.tag_configure("ERROR", foreground=HIGHLIGHT)
        self._log_text.tag_configure("ADMIN", foreground=WARNING)
        self._log_text.tag_configure("DEFAULT", foreground=TEXT)

        # Status bar
        self._count_lbl = tk.Label(
            self.parent, text="0 entries",
            font=FONT_SMALL, bg=BG, fg=WARNING
        )
        self._count_lbl.pack(pady=(0, 5))

    def on_show(self):
        self._fetch_log()

    def _start_auto_refresh(self):
        def auto():
            if self._auto_refresh:
                self._fetch_log()
            self.root.after(15000, auto)

        self.root.after(15000, auto)

    def _fetch_log(self):
        if not REQUESTS_OK:
            # Fallback: read from file directly
            from audit.audit_log import get_all
            entries = get_all()
            self.root.after(0, lambda: self._populate_log(entries))
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/audit_log", params={"n": 500}, timeout=5)
                if r.status_code == 200:
                    entries = r.json().get("entries", [])
                    self.root.after(0, lambda: self._populate_log(entries))
                else:
                    # Fallback
                    from audit.audit_log import get_all
                    entries = get_all()
                    self.root.after(0, lambda: self._populate_log(entries))
            except Exception:
                from audit.audit_log import get_all
                entries = get_all()
                self.root.after(0, lambda: self._populate_log(entries))

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_log(self, entries):
        self._all_entries = entries
        self._apply_filter()

    def _apply_filter(self):
        filter_type = self._filter_var.get()
        if filter_type == "ALL":
            filtered = self._all_entries
        else:
            tag = f"[{filter_type}]"
            filtered = [e for e in self._all_entries if tag in e]

        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)

        for entry in filtered:
            # Determine colour tag
            tag = "DEFAULT"
            for et in EVENT_TYPES[1:]:  # skip "ALL"
                if f"[{et}]" in entry:
                    tag = et
                    break
            self._log_text.insert(tk.END, entry + "\n", tag)

        # Scroll to end
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)
        self._count_lbl.configure(text=f"{len(filtered)} entries shown ({len(self._all_entries)} total)")

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Audit Log"
        )
        if not path:
            return
        try:
            from audit.audit_log import export_csv
            export_csv(path)
            messagebox.showinfo("Exported", f"Audit log exported to:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))
