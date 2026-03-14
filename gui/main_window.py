import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
BG      = "#0d1117"
PANEL   = "#161b22"
CARD    = "#1f2937"
ACCENT  = "#1d4ed8"
ACCENT2 = "#2563eb"
HIGHLIGHT = "#e94560"
TEXT    = "#f0f6fc"
TEXT2   = "#8b949e"
SUCCESS = "#3fb950"
WARNING = "#d29922"
BORDER  = "#30363d"

FONT_MAIN  = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_LARGE = ("Segoe UI", 17, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO  = ("Consolas", 9)


# ---------------------------------------------------------------------------
# Reusable styled widgets
# ---------------------------------------------------------------------------

def make_label(parent, text, font=FONT_MAIN, fg=TEXT, bg=BG, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)


def make_button(parent, text, command, bg=ACCENT, fg=TEXT, font=FONT_MAIN, **kw):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, font=font,
        activebackground=HIGHLIGHT, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", padx=16, pady=8,
        **kw
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=ACCENT2))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


def make_entry(parent, textvariable=None, width=30, **kw):
    return tk.Entry(
        parent, textvariable=textvariable, width=width,
        bg=CARD, fg=TEXT, insertbackground=TEXT,
        relief=tk.FLAT, font=FONT_MAIN, **kw
    )


def separator(parent, color=BORDER, pady=6):
    f = tk.Frame(parent, bg=color, height=1)
    f.pack(fill=tk.X, pady=pady)
    return f


# ---------------------------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------------------------

class VotingApp:
    def __init__(self, node_url="http://localhost:5000"):
        self.node_url = node_url
        self.root = tk.Tk()
        self.root.title("BlockVote — Decentralized Voting System")
        self.root.geometry("1280x820")
        self.root.minsize(1000, 680)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        # Try to set a window icon (silently skip if unavailable)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._current_page = None
        self._pages = {}
        self._active_nav = None

        self._build_layout()
        self._start_status_refresh()

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_layout(self):
        # ── Sidebar ──────────────────────────────────────────────────────
        self.sidebar = tk.Frame(self.root, bg=PANEL, width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Logo area
        logo_frame = tk.Frame(self.sidebar, bg=PANEL, pady=18)
        logo_frame.pack(fill=tk.X)

        logo_icon = tk.Label(logo_frame, text="⛓", font=("Segoe UI", 26),
                             bg=PANEL, fg=ACCENT2)
        logo_icon.pack()

        logo_text = tk.Label(logo_frame, text="BlockVote",
                             font=("Segoe UI", 15, "bold"), bg=PANEL, fg=TEXT)
        logo_text.pack()

        sub_text = tk.Label(logo_frame, text="Blockchain Voting",
                            font=FONT_SMALL, bg=PANEL, fg=TEXT2)
        sub_text.pack()

        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(4, 12))

        # Navigation section label
        tk.Label(self.sidebar, text="  NAVIGATION",
                 font=("Segoe UI", 8, "bold"), bg=PANEL, fg=TEXT2,
                 anchor="w").pack(fill=tk.X, padx=10, pady=(0, 6))

        nav_items = [
            ("🗳️  Cast Vote",      "vote"),
            ("📊  Results",        "results"),
            ("🔍  Verify Vote",    "verify"),
            ("⛓️  Blockchain",     "blockchain"),
            ("🌐  Network",        "network"),
            ("📋  Audit Log",      "audit"),
            ("⚙️  Admin",          "admin"),
        ]

        self._nav_buttons = {}
        for label, page_id in nav_items:
            btn = self._make_nav_btn(label, page_id)
            self._nav_buttons[page_id] = btn

        # Bottom of sidebar — version tag
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(12, 8))
        tk.Label(self.sidebar, text="v1.0  •  Python + Flask",
                 font=("Segoe UI", 8), bg=PANEL, fg=TEXT2).pack(pady=(0, 12))

        # ── Content area ─────────────────────────────────────────────────
        right_side = tk.Frame(self.root, bg=BG)
        right_side.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Top header bar
        self._build_header(right_side)

        # Page container
        self.content_area = tk.Frame(right_side, bg=BG)
        self.content_area.pack(fill=tk.BOTH, expand=True)

        # ── Status bar ───────────────────────────────────────────────────
        self.status_bar = tk.Frame(right_side, bg=PANEL, height=30)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        tk.Frame(self.status_bar, bg=BORDER, height=1).pack(fill=tk.X)

        self.status_lbl = tk.Label(
            self.status_bar, text="  Connecting to node...",
            font=FONT_MONO, bg=PANEL, fg=TEXT2, anchor="w"
        )
        self.status_lbl.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        self.node_indicator = tk.Label(
            self.status_bar, text=" ● OFFLINE ",
            font=("Segoe UI", 9, "bold"), bg=PANEL, fg=HIGHLIGHT
        )
        self.node_indicator.pack(side=tk.RIGHT, padx=10)

        # Load pages and show default
        self._load_pages()
        self._show_page("vote")

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=PANEL, height=52)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Frame(header, bg=BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)

        self._header_title = tk.Label(
            header, text="Cast Vote",
            font=("Segoe UI", 14, "bold"), bg=PANEL, fg=TEXT
        )
        self._header_title.pack(side=tk.LEFT, padx=24, pady=14)

        # Right side of header — clock
        self._clock_lbl = tk.Label(
            header, text="", font=FONT_SMALL, bg=PANEL, fg=TEXT2
        )
        self._clock_lbl.pack(side=tk.RIGHT, padx=20)
        self._update_clock()

    def _update_clock(self):
        t = time.strftime("%A, %d %b %Y  •  %H:%M:%S")
        self._clock_lbl.configure(text=t)
        self.root.after(1000, self._update_clock)

    def _make_nav_btn(self, label, page_id):
        frame = tk.Frame(self.sidebar, bg=PANEL)
        frame.pack(fill=tk.X, padx=8, pady=2)

        btn = tk.Label(
            frame, text=f"  {label}",
            font=("Segoe UI", 10), bg=PANEL, fg=TEXT2,
            anchor="w", cursor="hand2", pady=9
        )
        btn.pack(fill=tk.X)

        def on_click(pid=page_id):
            self._show_page(pid)

        btn.bind("<Button-1>", lambda e, pid=page_id: on_click(pid))
        frame.bind("<Button-1>", lambda e, pid=page_id: on_click(pid))

        def on_enter(e, f=frame, b=btn):
            if self._active_nav != page_id:
                f.configure(bg=CARD)
                b.configure(bg=CARD)

        def on_leave(e, f=frame, b=btn):
            if self._active_nav != page_id:
                f.configure(bg=PANEL)
                b.configure(bg=PANEL, fg=TEXT2)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)

        # Store frame reference too
        btn._nav_frame = frame
        btn._page_id = page_id
        return btn

    def _load_pages(self):
        from gui.vote_page import VotePage
        from gui.results_page import ResultsPage
        from gui.verify_page import VerifyPage
        from gui.blockchain_viewer import BlockchainViewer
        from gui.network_page import NetworkPage
        from gui.audit_page import AuditPage
        from gui.admin_page import AdminPage

        page_classes = {
            "vote":       (VotePage,          "🗳️  Cast Vote"),
            "results":    (ResultsPage,        "📊  Live Results"),
            "verify":     (VerifyPage,         "🔍  Verify Your Vote"),
            "blockchain": (BlockchainViewer,   "⛓️  Blockchain Explorer"),
            "network":    (NetworkPage,        "🌐  Network & Peers"),
            "audit":      (AuditPage,          "📋  Audit Log"),
            "admin":      (AdminPage,          "⚙️  Admin Panel"),
        }
        for pid, (cls, title) in page_classes.items():
            frame = tk.Frame(self.content_area, bg=BG)
            page = cls(frame, self.node_url, self.root)
            frame.place(relwidth=1, relheight=1)
            self._pages[pid] = (frame, page, title)

    def _show_page(self, page_id):
        self._active_nav = page_id

        # Reset all nav buttons
        for pid, btn in self._nav_buttons.items():
            is_active = pid == page_id
            bg_col  = ACCENT  if is_active else PANEL
            fg_col  = "white" if is_active else TEXT2
            btn.configure(bg=bg_col, fg=fg_col)
            btn._nav_frame.configure(bg=bg_col)

        if page_id in self._pages:
            frame, page, title = self._pages[page_id]
            frame.lift()
            self._current_page = page
            self._header_title.configure(text=title)
            if hasattr(page, "on_show"):
                page.on_show()

    # -----------------------------------------------------------------------
    # Status bar
    # -----------------------------------------------------------------------

    def _start_status_refresh(self):
        self._refresh_status()

    def _refresh_status(self):
        if not REQUESTS_OK:
            self.status_lbl.configure(text="  requests library not available")
            self.root.after(10000, self._refresh_status)
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/status", timeout=2)
                if r.status_code == 200:
                    self.root.after(0, lambda: self._update_status(r.json(), True))
                else:
                    self.root.after(0, lambda: self._update_status(None, False))
            except Exception:
                self.root.after(0, lambda: self._update_status(None, False))

        threading.Thread(target=fetch, daemon=True).start()
        self.root.after(5000, self._refresh_status)

    def _update_status(self, data, online):
        if online and data:
            chain = data.get("chain_length", "?")
            pending = data.get("pending_count", "?")
            peers = len(data.get("peers", []))
            mining = "  ⛏ Mining..." if data.get("is_mining") else ""
            self.status_lbl.configure(
                text=f"  Node: {self.node_url}   |   Chain: {chain} blocks"
                     f"   |   Pending: {pending} tx   |   Peers: {peers}{mining}"
            )
            self.node_indicator.configure(text=" ● ONLINE ", fg=SUCCESS)
        else:
            self.status_lbl.configure(text=f"  Node offline — {self.node_url}")
            self.node_indicator.configure(text=" ● OFFLINE ", fg=HIGHLIGHT)

    def run(self):
        self.root.mainloop()
