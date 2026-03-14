import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import csv
import time

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MPL_OK = True
except ImportError:
    MPL_OK = False

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

BAR_COLORS = ["#e94560", "#4CAF50", "#ff9800", "#2196F3", "#9C27B0", "#00BCD4"]


class ResultsPage:
    def __init__(self, parent, node_url, root):
        self.parent = parent
        self.node_url = node_url
        self.root = root

        self._election_var = tk.StringVar()
        self._elections = []
        self._last_results = {}
        self._canvas_widget = None
        self._fig = None
        self._canvas = None

        self._build()
        self._start_auto_refresh()

    def _build(self):
        # Header
        header = tk.Frame(self.parent, bg=BG)
        header.pack(fill=tk.X, padx=20, pady=(20, 5))

        tk.Label(header, text="Live Election Results", font=FONT_LARGE, bg=BG, fg=HIGHLIGHT).pack(side=tk.LEFT)

        btn_frame = tk.Frame(header, bg=BG)
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(
            btn_frame, text="Refresh Now",
            command=self._refresh_results,
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

        # Election selector row
        sel_frame = tk.Frame(self.parent, bg=BG)
        sel_frame.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(sel_frame, text="Election:", font=FONT_MAIN, bg=BG, fg=TEXT).pack(side=tk.LEFT, padx=(0, 10))
        self._election_menu = tk.OptionMenu(sel_frame, self._election_var, "Loading...")
        self._election_menu.configure(
            bg=ACCENT, fg=TEXT, font=FONT_MAIN,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, highlightthickness=0
        )
        self._election_menu["menu"].configure(bg=ACCENT, fg=TEXT)
        self._election_menu.pack(side=tk.LEFT)
        self._election_var.trace("w", lambda *a: self._refresh_results())

        self._total_label = tk.Label(sel_frame, text="Total Votes: —", font=FONT_TITLE, bg=BG, fg=TEXT)
        self._total_label.pack(side=tk.RIGHT)

        # Chart area
        self._chart_frame = tk.Frame(self.parent, bg=PANEL)
        self._chart_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        if MPL_OK:
            self._init_chart()
        else:
            tk.Label(
                self._chart_frame,
                text="matplotlib not available.\nInstall with: pip install matplotlib",
                font=FONT_MAIN, bg=PANEL, fg=WARNING
            ).pack(expand=True)

        # Info bar
        self._info_bar = tk.Label(
            self.parent,
            text="Auto-refreshes every 10 seconds",
            font=FONT_SMALL, bg=BG, fg=WARNING
        )
        self._info_bar.pack(pady=(0, 10))

        # Fetch elections
        self._fetch_elections()

    def _init_chart(self):
        self._fig = Figure(figsize=(8, 5), facecolor=PANEL)
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor(PANEL)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._chart_frame)
        self._canvas_widget = self._canvas.get_tk_widget()
        self._canvas_widget.configure(bg=PANEL)
        self._canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _fetch_elections(self):
        if not REQUESTS_OK:
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/elections", timeout=3)
                if r.status_code == 200:
                    elections = r.json().get("elections", [])
                    self.root.after(0, lambda: self._populate_elections(elections))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_elections(self, elections):
        self._elections = elections
        menu = self._election_menu["menu"]
        menu.delete(0, "end")
        if not elections:
            self._election_var.set("No elections")
            return
        for e in elections:
            eid = e["election_id"]
            menu.add_command(label=eid, command=lambda v=eid: self._election_var.set(v))
        if not self._election_var.get() or self._election_var.get() not in [e["election_id"] for e in elections]:
            self._election_var.set(elections[0]["election_id"])
        else:
            self._refresh_results()

    def _refresh_results(self):
        eid = self._election_var.get()
        if not eid or not REQUESTS_OK:
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/results", params={"election_id": eid}, timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    self.root.after(0, lambda: self._update_chart(data))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()

    def _update_chart(self, data):
        results = data.get("results", {})
        total = data.get("total_votes", 0)
        self._last_results = results
        self._total_label.configure(text=f"Total Votes: {total}")

        if not MPL_OK or not self._ax:
            return

        self._ax.clear()

        if not results:
            self._ax.text(0.5, 0.5, "No votes yet", ha="center", va="center",
                          color=TEXT, fontsize=14, transform=self._ax.transAxes)
            self._canvas.draw()
            return

        candidates = list(results.keys())
        counts = [results[c] for c in candidates]
        colors = [BAR_COLORS[i % len(BAR_COLORS)] for i in range(len(candidates))]

        bars = self._ax.barh(candidates, counts, color=colors, height=0.5)

        # Labels
        for bar, count in zip(bars, counts):
            pct = (count / total * 100) if total > 0 else 0
            self._ax.text(
                bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                f"  {count} ({pct:.1f}%)",
                va="center", ha="left", color=TEXT, fontsize=10
            )

        self._ax.set_facecolor(PANEL)
        self._ax.set_xlabel("Votes", color=TEXT, fontsize=11)
        self._ax.set_title(f"Results: {self._election_var.get()}", color=HIGHLIGHT, fontsize=13, fontweight="bold")
        self._ax.tick_params(colors=TEXT, labelsize=10)
        self._ax.spines["bottom"].set_color(ACCENT)
        self._ax.spines["left"].set_color(ACCENT)
        self._ax.spines["top"].set_visible(False)
        self._ax.spines["right"].set_visible(False)
        self._fig.patch.set_facecolor(PANEL)

        if total > 0:
            max_count = max(counts)
            self._ax.set_xlim(0, max_count * 1.25)

        self._fig.tight_layout()
        self._canvas.draw()

        self._info_bar.configure(
            text=f"Last updated: {__import__('time').strftime('%H:%M:%S')}  |  Auto-refresh in 10s"
        )

    def _start_auto_refresh(self):
        def auto():
            self._refresh_results()
            self.root.after(10000, auto)

        self.root.after(10000, auto)

    def on_show(self):
        self._fetch_elections()
        self._refresh_results()

    def _export_csv(self):
        if not self._last_results:
            messagebox.showinfo("No Data", "No results to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Results"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Candidate", "Votes", "Percentage"])
                total = sum(self._last_results.values())
                for cand, count in self._last_results.items():
                    pct = (count / total * 100) if total > 0 else 0
                    writer.writerow([cand, count, f"{pct:.2f}%"])
            messagebox.showinfo("Exported", f"Results exported to:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))
