import tkinter as tk
from tkinter import ttk, messagebox
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
FONT_MONO = ("Consolas", 9)


class BlockchainViewer:
    def __init__(self, parent, node_url, root):
        self.parent = parent
        self.node_url = node_url
        self.root = root
        self._chain_data = []
        self._selected_block = None
        self._build()

    def _build(self):
        # Header
        header = tk.Frame(self.parent, bg=BG)
        header.pack(fill=tk.X, padx=20, pady=(20, 5))

        tk.Label(header, text="Blockchain Explorer", font=FONT_LARGE, bg=BG, fg=HIGHLIGHT).pack(side=tk.LEFT)

        btn_frame = tk.Frame(header, bg=BG)
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(
            btn_frame, text="Refresh",
            command=self._refresh_chain,
            bg=ACCENT, fg=TEXT, font=FONT_SMALL,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=10, pady=6
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="Validate Chain",
            command=self._validate_chain,
            bg=SUCCESS, fg="white", font=FONT_SMALL,
            activebackground="#3d8b40", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=10, pady=6
        ).pack(side=tk.LEFT, padx=5)

        tk.Frame(self.parent, bg=HIGHLIGHT, height=2).pack(fill=tk.X, padx=20, pady=5)

        # Main area: block list + details side by side
        main = tk.Frame(self.parent, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Left: block list
        left = tk.Frame(main, bg=PANEL, width=360)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(left, text="Blocks", font=FONT_TITLE, bg=PANEL, fg=TEXT, pady=10).pack(fill=tk.X)

        # Scrollable listbox with scrollbar
        list_frame = tk.Frame(left, bg=PANEL)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, bg=PANEL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._block_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            bg=ACCENT, fg=TEXT, font=FONT_MONO,
            relief=tk.FLAT, selectbackground=HIGHLIGHT,
            selectforeground="white", activestyle="none",
            highlightthickness=0
        )
        self._block_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.configure(command=self._block_listbox.yview)
        self._block_listbox.bind("<<ListboxSelect>>", self._on_block_select)

        # Right: block details
        right = tk.Frame(main, bg=PANEL)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(right, text="Block Details", font=FONT_TITLE, bg=PANEL, fg=TEXT, pady=10).pack(fill=tk.X)

        # Scrollable details text
        details_frame = tk.Frame(right, bg=PANEL)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        d_scroll = tk.Scrollbar(details_frame, orient=tk.VERTICAL, bg=PANEL)
        d_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._details_text = tk.Text(
            details_frame,
            yscrollcommand=d_scroll.set,
            bg=BG, fg=TEXT, font=FONT_MONO,
            relief=tk.FLAT, wrap=tk.WORD,
            padx=10, pady=10,
            state=tk.DISABLED
        )
        self._details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        d_scroll.configure(command=self._details_text.yview)

        # Configure text tags
        self._details_text.tag_configure("key", foreground=WARNING, font=("Consolas", 9, "bold"))
        self._details_text.tag_configure("value", foreground=TEXT)
        self._details_text.tag_configure("section", foreground=HIGHLIGHT, font=("Consolas", 10, "bold"))
        self._details_text.tag_configure("hash", foreground=SUCCESS, font=FONT_MONO)

        self._show_placeholder()

    def _show_placeholder(self):
        self._set_details_text([("section", "Select a block from the list to view details.\n")])

    def on_show(self):
        self._refresh_chain()

    def _refresh_chain(self):
        if not REQUESTS_OK:
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/chain", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    chain = data.get("chain", [])
                    self.root.after(0, lambda: self._populate_list(chain))
            except Exception as ex:
                self.root.after(0, lambda: self._show_error(str(ex)))

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_list(self, chain):
        self._chain_data = chain
        self._block_listbox.delete(0, tk.END)
        for block in reversed(chain):
            idx = block.get("index", "?")
            h = block.get("hash", "")[:12] + "..."
            tx_count = len(block.get("transactions", []))
            ts = time.strftime("%m/%d %H:%M", time.localtime(block.get("timestamp", 0)))
            entry = f"#{idx:>4}  {h}  Tx:{tx_count:<3}  {ts}"
            self._block_listbox.insert(tk.END, entry)

    def _on_block_select(self, event):
        sel = self._block_listbox.curselection()
        if not sel:
            return
        list_index = sel[0]
        # We inserted in reverse, so map back
        chain_index = len(self._chain_data) - 1 - list_index
        if 0 <= chain_index < len(self._chain_data):
            self._display_block(self._chain_data[chain_index])

    def _display_block(self, block):
        parts = []
        parts.append(("section", f"=== Block #{block.get('index', '?')} ===\n\n"))

        fields = [
            ("Index", str(block.get("index", "?"))),
            ("Timestamp", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(block.get("timestamp", 0)))),
            ("Difficulty", str(block.get("difficulty", "?"))),
            ("Nonce", str(block.get("nonce", "?"))),
        ]
        for k, v in fields:
            parts.append(("key", f"{k + ':':<18}"))
            parts.append(("value", f"{v}\n"))

        parts.append(("key", f"{'Hash:':<18}"))
        parts.append(("hash", f"{block.get('hash', '?')}\n"))
        parts.append(("key", f"{'Previous Hash:':<18}"))
        parts.append(("hash", f"{block.get('previous_hash', '?')}\n"))
        parts.append(("key", f"{'Merkle Root:':<18}"))
        parts.append(("hash", f"{block.get('merkle_root', '?')}\n"))

        transactions = block.get("transactions", [])
        parts.append(("section", f"\n--- Transactions ({len(transactions)}) ---\n"))

        if not transactions:
            parts.append(("value", "  (no transactions — genesis block)\n"))
        else:
            for i, tx in enumerate(transactions):
                parts.append(("key", f"\n  Tx #{i + 1}\n"))
                parts.append(("value", f"    Candidate:   {tx.get('candidate', '?')}\n"))
                parts.append(("value", f"    Election:    {tx.get('election_id', '?')}\n"))
                ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tx.get("timestamp", 0)))
                parts.append(("value", f"    Timestamp:   {ts_str}\n"))
                parts.append(("key",   f"    Vote Hash:   "))
                parts.append(("hash",  f"{tx.get('vote_hash', '?')}\n"))
                voter_hash = tx.get("voter_id", "?")
                parts.append(("value", f"    Voter (hashed): {voter_hash[:24]}...\n"))

        self._set_details_text(parts)

    def _set_details_text(self, parts):
        self._details_text.configure(state=tk.NORMAL)
        self._details_text.delete("1.0", tk.END)
        for tag, content in parts:
            self._details_text.insert(tk.END, content, tag)
        self._details_text.configure(state=tk.DISABLED)

    def _show_error(self, msg):
        self._set_details_text([("section", f"Error: {msg}\n")])

    def _validate_chain(self):
        if not REQUESTS_OK:
            messagebox.showerror("Error", "requests library not available.")
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/chain", timeout=5)
                if r.status_code != 200:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Could not fetch chain."))
                    return
                from audit.verification import verify_chain_integrity
                from blockchain.blockchain import Blockchain
                data = r.json()
                bc = Blockchain.from_dict(data)
                result = verify_chain_integrity(bc)
                self.root.after(0, lambda: self._show_validation(result))
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("Error", str(ex)))

        threading.Thread(target=fetch, daemon=True).start()

    def _show_validation(self, result):
        valid = result.get("valid", False)
        errors = result.get("errors", [])
        chain_length = result.get("chain_length", 0)

        if valid:
            messagebox.showinfo(
                "Chain Valid",
                f"The blockchain is VALID.\n\nChain length: {chain_length} blocks\nAll hashes and links verified."
            )
        else:
            error_text = "\n".join(f"  - {e}" for e in errors)
            messagebox.showerror(
                "Chain INVALID",
                f"The blockchain has integrity issues!\n\nErrors found:\n{error_text}"
            )
