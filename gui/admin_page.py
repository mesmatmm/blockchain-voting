import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import json

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


class AdminPage:
    def __init__(self, parent, node_url, root):
        self.parent = parent
        self.node_url = node_url
        self.root = root
        self._election_id_var = tk.StringVar()
        self._candidates_var = tk.StringVar()
        self._duration_var = tk.StringVar(value="24")
        self._node_info_var = tk.StringVar(value="—")
        self._build()

    def _build(self):
        tk.Label(
            self.parent, text="Admin Panel", font=FONT_LARGE,
            bg=BG, fg=HIGHLIGHT
        ).pack(pady=(20, 5))
        tk.Frame(self.parent, bg=HIGHLIGHT, height=2).pack(fill=tk.X, padx=20, pady=5)

        # Scrollable content
        canvas = tk.Canvas(self.parent, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.parent, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        content = tk.Frame(canvas, bg=BG)
        canvas_win = canvas.create_window((0, 0), window=content, anchor="nw")

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_resize(e):
            canvas.itemconfig(canvas_win, width=e.width)

        content.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_canvas_resize)

        padx = 20
        pady_section = 10

        # === Create Election ===
        section = tk.Frame(content, bg=PANEL, padx=20, pady=20)
        section.pack(fill=tk.X, padx=padx, pady=pady_section)

        tk.Label(section, text="Create New Election", font=FONT_TITLE, bg=PANEL, fg=HIGHLIGHT).pack(anchor="w", pady=(0, 15))

        def row(parent, label, var, placeholder=""):
            fr = tk.Frame(parent, bg=PANEL)
            fr.pack(fill=tk.X, pady=5)
            tk.Label(fr, text=label, width=20, anchor="w", font=FONT_MAIN, bg=PANEL, fg=TEXT).pack(side=tk.LEFT)
            e = tk.Entry(fr, textvariable=var, bg=ACCENT, fg=TEXT, insertbackground=TEXT,
                         relief=tk.FLAT, font=FONT_MAIN)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7)
            if placeholder and not var.get():
                e.insert(0, placeholder)
                e.configure(fg="#888888")
                def on_focus_in(ev, entry=e, var=var, ph=placeholder):
                    if entry.get() == ph:
                        entry.delete(0, tk.END)
                        entry.configure(fg=TEXT)
                def on_focus_out(ev, entry=e, var=var, ph=placeholder):
                    if not entry.get():
                        entry.insert(0, ph)
                        entry.configure(fg="#888888")
                e.bind("<FocusIn>", on_focus_in)
                e.bind("<FocusOut>", on_focus_out)
            return e

        row(section, "Election ID:", self._election_id_var, "e.g. election_2027")
        row(section, "Candidates (comma-sep):", self._candidates_var, "e.g. Alice, Bob, Charlie")
        row(section, "Duration (hours):", self._duration_var)

        tk.Button(
            section, text="Create Election",
            command=self._create_election,
            bg=SUCCESS, fg="white", font=FONT_TITLE,
            activebackground="#3d8b40", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", pady=12
        ).pack(fill=tk.X, pady=(15, 0))

        # === Mining ===
        section2 = tk.Frame(content, bg=PANEL, padx=20, pady=20)
        section2.pack(fill=tk.X, padx=padx, pady=pady_section)

        tk.Label(section2, text="Mining", font=FONT_TITLE, bg=PANEL, fg=HIGHLIGHT).pack(anchor="w", pady=(0, 10))

        self._mine_status_lbl = tk.Label(section2, text="", font=FONT_MAIN, bg=PANEL, fg=TEXT)
        self._mine_status_lbl.pack(anchor="w", pady=(0, 10))

        btn_row = tk.Frame(section2, bg=PANEL)
        btn_row.pack(fill=tk.X)

        tk.Button(
            btn_row, text="Mine Now",
            command=self._mine_now,
            bg=WARNING, fg="white", font=FONT_MAIN,
            activebackground="#cc7a00", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=14, pady=10
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btn_row, text="Clear Pending Transactions",
            command=self._clear_pending,
            bg=HIGHLIGHT, fg="white", font=FONT_MAIN,
            activebackground="#c73652", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=14, pady=10
        ).pack(side=tk.LEFT)

        # === Export ===
        section3 = tk.Frame(content, bg=PANEL, padx=20, pady=20)
        section3.pack(fill=tk.X, padx=padx, pady=pady_section)

        tk.Label(section3, text="Export & Backup", font=FONT_TITLE, bg=PANEL, fg=HIGHLIGHT).pack(anchor="w", pady=(0, 10))

        exp_row = tk.Frame(section3, bg=PANEL)
        exp_row.pack(fill=tk.X)

        tk.Button(
            exp_row, text="Export Blockchain JSON",
            command=self._export_blockchain,
            bg=ACCENT, fg=TEXT, font=FONT_MAIN,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=14, pady=10
        ).pack(side=tk.LEFT, padx=(0, 10))

        # === Node Info ===
        section4 = tk.Frame(content, bg=PANEL, padx=20, pady=20)
        section4.pack(fill=tk.X, padx=padx, pady=pady_section)

        tk.Label(section4, text="Node Information", font=FONT_TITLE, bg=PANEL, fg=HIGHLIGHT).pack(anchor="w", pady=(0, 10))

        self._node_info_text = tk.Text(
            section4, bg=BG, fg=TEXT, font=("Consolas", 9),
            relief=tk.FLAT, height=8, state=tk.DISABLED
        )
        self._node_info_text.pack(fill=tk.X)

        tk.Button(
            section4, text="Refresh Node Info",
            command=self._refresh_node_info,
            bg=ACCENT, fg=TEXT, font=FONT_SMALL,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", pady=6
        ).pack(anchor="w", pady=(10, 0))

        self._refresh_node_info()

    def on_show(self):
        self._refresh_node_info()

    def _create_election(self):
        election_id = self._election_id_var.get().strip()
        candidates_raw = self._candidates_var.get().strip()
        duration = self._duration_var.get().strip()

        # Strip placeholder text
        if election_id in ("e.g. election_2027", ""):
            messagebox.showwarning("Input Error", "Please enter an election ID.")
            return
        if candidates_raw in ("e.g. Alice, Bob, Charlie", ""):
            messagebox.showwarning("Input Error", "Please enter at least one candidate.")
            return

        candidates = [c.strip() for c in candidates_raw.split(",") if c.strip()]
        if not candidates:
            messagebox.showwarning("Input Error", "Please enter at least one candidate.")
            return

        try:
            duration_h = float(duration)
        except ValueError:
            messagebox.showwarning("Input Error", "Duration must be a number.")
            return

        if not REQUESTS_OK:
            return

        def post():
            try:
                r = requests.post(
                    f"{self.node_url}/create_election",
                    json={"election_id": election_id, "candidates": candidates, "duration_hours": duration_h},
                    timeout=5
                )
                data = r.json()
                if r.status_code in (200, 201) and data.get("success"):
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Election Created",
                        f"Election '{election_id}' created successfully!\nCandidates: {', '.join(candidates)}"
                    ))
                    self.root.after(0, lambda: self._election_id_var.set(""))
                    self.root.after(0, lambda: self._candidates_var.set(""))
                else:
                    err = data.get("error", "Unknown error")
                    self.root.after(0, lambda: messagebox.showerror("Error", err))
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("Error", str(ex)))

        threading.Thread(target=post, daemon=True).start()

    def _mine_now(self):
        if not REQUESTS_OK:
            return

        self._mine_status_lbl.configure(text="Mining in progress...", fg=WARNING)

        def post():
            try:
                r = requests.post(f"{self.node_url}/mine", timeout=120)
                data = r.json()
                if r.status_code == 200 and data.get("success"):
                    block = data.get("block", {})
                    idx = block.get("index", "?")
                    tx_count = len(block.get("transactions", []))
                    msg = f"Block #{idx} mined with {tx_count} transaction(s)."
                    self.root.after(0, lambda: self._mine_status_lbl.configure(text=msg, fg=SUCCESS))
                    self.root.after(0, lambda: messagebox.showinfo("Mining Complete", msg))
                else:
                    err = data.get("error", "Unknown error")
                    self.root.after(0, lambda: self._mine_status_lbl.configure(text=f"Error: {err}", fg=HIGHLIGHT))
                    self.root.after(0, lambda: messagebox.showerror("Mining Error", err))
            except Exception as ex:
                self.root.after(0, lambda: self._mine_status_lbl.configure(text=f"Error: {ex}", fg=HIGHLIGHT))
                self.root.after(0, lambda: messagebox.showerror("Error", str(ex)))

        threading.Thread(target=post, daemon=True).start()

    def _clear_pending(self):
        if not messagebox.askyesno("Confirm", "Clear all pending (unmined) transactions?"):
            return
        if not REQUESTS_OK:
            return

        def post():
            try:
                r = requests.post(f"{self.node_url}/clear_pending", timeout=3)
                data = r.json()
                cleared = data.get("cleared", 0)
                self.root.after(0, lambda: messagebox.showinfo("Cleared", f"Cleared {cleared} pending transaction(s)."))
                self.root.after(0, self._refresh_node_info)
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("Error", str(ex)))

        threading.Thread(target=post, daemon=True).start()

    def _export_blockchain(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export Blockchain"
        )
        if not path or not REQUESTS_OK:
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/chain", timeout=10)
                if r.status_code == 200:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(r.json(), f, indent=2)
                    self.root.after(0, lambda: messagebox.showinfo("Exported", f"Blockchain saved to:\n{path}"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to fetch chain."))
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("Error", str(ex)))

        threading.Thread(target=fetch, daemon=True).start()

    def _refresh_node_info(self):
        if not REQUESTS_OK:
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/status", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    lines = [
                        f"Node URL:      {self.node_url}",
                        f"Port:          {data.get('port', '?')}",
                        f"Status:        {data.get('status', '?')}",
                        f"Chain Length:  {data.get('chain_length', '?')} blocks",
                        f"Pending Tx:    {data.get('pending_count', '?')}",
                        f"Peers:         {len(data.get('peers', []))}",
                        f"Elections:     {', '.join(data.get('elections', [])) or 'none'}",
                        f"Auto-mine:     {'Enabled' if data.get('auto_mine') else 'Disabled'}",
                        f"Mining:        {'In Progress' if data.get('is_mining') else 'Idle'}",
                    ]
                    text = "\n".join(lines)
                else:
                    text = "Node is offline or unreachable."
            except Exception as ex:
                text = f"Connection error: {ex}"

            def update():
                self._node_info_text.configure(state=tk.NORMAL)
                self._node_info_text.delete("1.0", tk.END)
                self._node_info_text.insert("1.0", text)
                self._node_info_text.configure(state=tk.DISABLED)

            self.root.after(0, update)

        threading.Thread(target=fetch, daemon=True).start()
