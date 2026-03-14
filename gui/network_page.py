import tkinter as tk
from tkinter import messagebox
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


class NetworkPage:
    def __init__(self, parent, node_url, root):
        self.parent = parent
        self.node_url = node_url
        self.root = root
        self._peer_url_var = tk.StringVar()
        self._auto_mine_var = tk.BooleanVar(value=False)
        self._mining_status_var = tk.StringVar(value="Idle")
        self._build()

    def _build(self):
        tk.Label(
            self.parent, text="Network & Peers", font=FONT_LARGE,
            bg=BG, fg=HIGHLIGHT
        ).pack(pady=(20, 5))
        tk.Frame(self.parent, bg=HIGHLIGHT, height=2).pack(fill=tk.X, padx=20, pady=5)

        container = tk.Frame(self.parent, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Left column
        left = tk.Frame(container, bg=PANEL, padx=20, pady=20)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Add peer
        tk.Label(left, text="Add Peer", font=FONT_TITLE, bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 8))

        peer_row = tk.Frame(left, bg=PANEL)
        peer_row.pack(fill=tk.X, pady=(0, 15))

        self._peer_entry = tk.Entry(
            peer_row, textvariable=self._peer_url_var, width=35,
            bg=ACCENT, fg=TEXT, insertbackground=TEXT,
            relief=tk.FLAT, font=FONT_MAIN
        )
        self._peer_entry.insert(0, "http://localhost:5001")
        self._peer_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))

        tk.Button(
            peer_row, text="Add Peer",
            command=self._add_peer,
            bg=HIGHLIGHT, fg="white", font=FONT_MAIN,
            activebackground="#c73652", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=12, pady=8
        ).pack(side=tk.LEFT)

        # Peer list
        tk.Label(left, text="Connected Peers", font=FONT_TITLE, bg=PANEL, fg=TEXT).pack(anchor="w", pady=(5, 8))

        list_frame = tk.Frame(left, bg=PANEL)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL, bg=PANEL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._peer_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scroll.set,
            bg=ACCENT, fg=TEXT, font=FONT_MAIN,
            relief=tk.FLAT, selectbackground=HIGHLIGHT,
            selectforeground="white", activestyle="none",
            highlightthickness=0, height=8
        )
        self._peer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.configure(command=self._peer_listbox.yview)

        # Sync button
        tk.Button(
            left, text="Sync Blockchain (Consensus)",
            command=self._sync,
            bg=SUCCESS, fg="white", font=FONT_MAIN,
            activebackground="#3d8b40", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", pady=10
        ).pack(fill=tk.X, pady=(10, 0))

        # Right column
        right = tk.Frame(container, bg=PANEL, padx=20, pady=20, width=280)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        # Node status
        tk.Label(right, text="Node Status", font=FONT_TITLE, bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 10))

        self._status_text = tk.Text(
            right, bg=BG, fg=TEXT, font=FONT_SMALL,
            relief=tk.FLAT, height=8, state=tk.DISABLED
        )
        self._status_text.pack(fill=tk.X, pady=(0, 15))

        # Auto-mine toggle
        tk.Label(right, text="Auto-Mining", font=FONT_TITLE, bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 8))

        toggle_row = tk.Frame(right, bg=PANEL)
        toggle_row.pack(fill=tk.X)

        self._auto_mine_check = tk.Checkbutton(
            toggle_row, text="Enable auto-mine (every 30s)",
            variable=self._auto_mine_var,
            command=self._toggle_auto_mine,
            bg=PANEL, fg=TEXT, selectcolor=ACCENT,
            activebackground=PANEL, activeforeground=TEXT,
            font=FONT_MAIN
        )
        self._auto_mine_check.pack(anchor="w")

        tk.Label(right, text="Mining Status:", font=FONT_SMALL, bg=PANEL, fg=WARNING).pack(anchor="w", pady=(10, 3))
        self._mining_lbl = tk.Label(
            right, textvariable=self._mining_status_var,
            font=FONT_MAIN, bg=PANEL, fg=SUCCESS
        )
        self._mining_lbl.pack(anchor="w")

        # Refresh button
        tk.Button(
            right, text="Refresh Status",
            command=self._refresh_status,
            bg=ACCENT, fg=TEXT, font=FONT_SMALL,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", pady=6
        ).pack(fill=tk.X, pady=(20, 0))

        self._refresh_status()

    def on_show(self):
        self._refresh_status()

    def _refresh_status(self):
        if not REQUESTS_OK:
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/status", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    self.root.after(0, lambda: self._update_status_display(data))
                    # Update peer list
                    peers = data.get("peers", [])
                    self.root.after(0, lambda: self._update_peer_list(peers))
                    is_mining = data.get("is_mining", False)
                    self.root.after(0, lambda: self._mining_status_var.set("Mining..." if is_mining else "Idle"))
            except Exception:
                self.root.after(0, lambda: self._update_status_display(None))

        threading.Thread(target=fetch, daemon=True).start()

    def _update_status_display(self, data):
        self._status_text.configure(state=tk.NORMAL)
        self._status_text.delete("1.0", tk.END)
        if data:
            lines = [
                f"Status:        {data.get('status', '?')}",
                f"Port:          {data.get('port', '?')}",
                f"Chain Length:  {data.get('chain_length', '?')} blocks",
                f"Pending Tx:    {data.get('pending_count', '?')}",
                f"Peers:         {len(data.get('peers', []))}",
                f"Auto-mine:     {'On' if data.get('auto_mine') else 'Off'}",
                f"Elections:     {len(data.get('elections', []))}",
            ]
            self._status_text.insert("1.0", "\n".join(lines))
        else:
            self._status_text.insert("1.0", "Node is offline or unreachable.")
        self._status_text.configure(state=tk.DISABLED)

    def _update_peer_list(self, peers):
        self._peer_listbox.delete(0, tk.END)
        if not peers:
            self._peer_listbox.insert(tk.END, "  (no peers connected)")
            return
        for peer in peers:
            # Check if peer is online
            def check_and_insert(p):
                try:
                    r2 = requests.get(f"{p}/status", timeout=2)
                    status = "ONLINE" if r2.status_code == 200 else "OFFLINE"
                except Exception:
                    status = "OFFLINE"
                entry = f"  {'[+]' if status == 'ONLINE' else '[-]'}  {p}"
                self.root.after(0, lambda e=entry: self._peer_listbox.insert(tk.END, e))

            threading.Thread(target=check_and_insert, args=(peer,), daemon=True).start()

    def _add_peer(self):
        url = self._peer_url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a peer URL.")
            return
        if not REQUESTS_OK:
            return

        def post():
            try:
                r = requests.post(
                    f"{self.node_url}/register_peer",
                    json={"url": url}, timeout=3
                )
                if r.status_code == 200:
                    self.root.after(0, lambda: self._refresh_status())
                    self.root.after(0, lambda: messagebox.showinfo("Peer Added", f"Peer registered:\n{url}"))
                else:
                    err = r.json().get("error", "Unknown error")
                    self.root.after(0, lambda: messagebox.showerror("Error", err))
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("Error", str(ex)))

        threading.Thread(target=post, daemon=True).start()

    def _sync(self):
        if not REQUESTS_OK:
            return

        def post():
            try:
                r = requests.post(f"{self.node_url}/sync", timeout=10)
                msg = r.json().get("message", "Sync completed.")
                self.root.after(0, lambda: messagebox.showinfo("Sync Complete", msg))
                self.root.after(0, self._refresh_status)
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("Sync Error", str(ex)))

        threading.Thread(target=post, daemon=True).start()

    def _toggle_auto_mine(self):
        enabled = self._auto_mine_var.get()
        if not REQUESTS_OK:
            return

        def post():
            try:
                requests.post(
                    f"{self.node_url}/auto_mine",
                    json={"enable": enabled, "interval": 30},
                    timeout=3
                )
                self.root.after(0, self._refresh_status)
            except Exception:
                pass

        threading.Thread(target=post, daemon=True).start()
