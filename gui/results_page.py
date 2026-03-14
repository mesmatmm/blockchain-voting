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
    import matplotlib.patches as mpatches
    MPL_OK = True
except ImportError:
    MPL_OK = False

BG        = "#0d1117"
PANEL     = "#161b22"
CARD      = "#1f2937"
ACCENT    = "#1d4ed8"
ACCENT2   = "#2563eb"
HIGHLIGHT = "#e94560"
TEXT      = "#f0f6fc"
TEXT2     = "#8b949e"
SUCCESS   = "#3fb950"
WARNING   = "#d29922"
BORDER    = "#30363d"

FONT_MAIN  = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_LARGE = ("Segoe UI", 16, "bold")
FONT_SMALL = ("Segoe UI", 9)

BAR_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6",
               "#ef4444", "#06b6d4", "#84cc16", "#f97316"]


class ResultsPage:
    def __init__(self, parent, node_url, root):
        self.parent   = parent
        self.node_url = node_url
        self.root     = root

        self._election_var  = tk.StringVar()
        self._elections     = []
        self._last_results  = {}
        self._canvas_widget = None
        self._fig = None
        self._ax  = None
        self._canvas = None

        self._build()
        self._start_auto_refresh()

    def _build(self):
        # ── Header ───────────────────────────────────────────────────────
        header = tk.Frame(self.parent, bg=BG)
        header.pack(fill=tk.X, padx=24, pady=(20, 6))

        btn_frame = tk.Frame(header, bg=BG)
        btn_frame.pack(side=tk.RIGHT)

        self._mk_btn(btn_frame, "↻  Refresh", self._refresh_results, ACCENT).pack(
            side=tk.LEFT, padx=4)
        self._mk_btn(btn_frame, "⬇  Export CSV", self._export_csv, SUCCESS, "white").pack(
            side=tk.LEFT, padx=4)

        tk.Frame(self.parent, bg=BORDER, height=1).pack(fill=tk.X, padx=24, pady=(0, 10))

        # ── Election + stats row ──────────────────────────────────────────
        row = tk.Frame(self.parent, bg=BG)
        row.pack(fill=tk.X, padx=24, pady=(0, 10))

        tk.Label(row, text="Election:", font=FONT_MAIN, bg=BG, fg=TEXT2).pack(
            side=tk.LEFT, padx=(0, 8))
        self._election_menu = tk.OptionMenu(row, self._election_var, "Loading...")
        self._election_menu.configure(
            bg=CARD, fg=TEXT, font=FONT_MAIN,
            activebackground=ACCENT, activeforeground="white",
            relief=tk.FLAT, highlightthickness=0
        )
        self._election_menu["menu"].configure(bg=CARD, fg=TEXT, font=FONT_MAIN,
                                               activebackground=ACCENT,
                                               activeforeground="white")
        self._election_menu.pack(side=tk.LEFT)
        self._election_var.trace("w", lambda *a: self._refresh_results())

        # Stat cards row (right side)
        self._total_var  = tk.StringVar(value="—")
        self._leader_var = tk.StringVar(value="—")

        self._stat_card(row, "Total Votes", self._total_var, SUCCESS)
        self._stat_card(row, "Current Leader", self._leader_var, "#f59e0b")

        # ── Chart area ────────────────────────────────────────────────────
        self._chart_frame = tk.Frame(self.parent, bg=PANEL)
        self._chart_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 6))

        if MPL_OK:
            self._init_chart()
        else:
            tk.Label(
                self._chart_frame,
                text="matplotlib not available.\nInstall with: pip install matplotlib",
                font=FONT_MAIN, bg=PANEL, fg=WARNING
            ).pack(expand=True)

        # ── Footer info ───────────────────────────────────────────────────
        footer = tk.Frame(self.parent, bg=BG)
        footer.pack(fill=tk.X, padx=24, pady=(0, 12))

        self._info_lbl = tk.Label(
            footer, text="Auto-refreshes every 10 seconds",
            font=FONT_SMALL, bg=BG, fg=TEXT2
        )
        self._info_lbl.pack(side=tk.LEFT)

        self._status_dot = tk.Label(footer, text="●", font=FONT_SMALL, bg=BG, fg=SUCCESS)
        self._status_dot.pack(side=tk.RIGHT, padx=(0, 4))
        tk.Label(footer, text="Live", font=FONT_SMALL, bg=BG, fg=TEXT2).pack(side=tk.RIGHT)

        self._fetch_elections()

    def _stat_card(self, parent, label, textvar, value_fg):
        card = tk.Frame(parent, bg=CARD, padx=14, pady=8)
        card.pack(side=tk.RIGHT, padx=6)
        tk.Label(card, text=label, font=FONT_SMALL, bg=CARD, fg=TEXT2).pack(anchor="w")
        tk.Label(card, textvariable=textvar, font=("Segoe UI", 12, "bold"),
                 bg=CARD, fg=value_fg).pack(anchor="w")

    def _mk_btn(self, parent, text, cmd, bg=ACCENT, fg="white"):
        btn = tk.Button(
            parent, text=text, command=cmd,
            bg=bg, fg=fg, font=FONT_SMALL,
            activebackground=ACCENT2, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=12, pady=7
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=ACCENT2))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
        return btn

    def _init_chart(self):
        self._fig = Figure(figsize=(9, 5), facecolor=PANEL)
        self._ax  = self._fig.add_subplot(111)
        self._ax.set_facecolor(PANEL)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._chart_frame)
        self._canvas_widget = self._canvas.get_tk_widget()
        self._canvas_widget.configure(bg=PANEL, highlightthickness=0)
        self._canvas_widget.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

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
        if not self._election_var.get() or \
                self._election_var.get() not in [e["election_id"] for e in elections]:
            self._election_var.set(elections[0]["election_id"])
        else:
            self._refresh_results()

    def _refresh_results(self):
        eid = self._election_var.get()
        if not eid or not REQUESTS_OK:
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/results",
                                 params={"election_id": eid}, timeout=3)
                if r.status_code == 200:
                    self.root.after(0, lambda: self._update_chart(r.json()))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()

    def _update_chart(self, data):
        results = data.get("results", {})
        total   = data.get("total_votes", 0)
        self._last_results = results
        self._total_var.set(str(total))

        # Update leader stat
        if results:
            leader = max(results, key=results.get)
            self._leader_var.set(leader)
        else:
            self._leader_var.set("—")

        if not MPL_OK or not self._ax:
            return

        self._ax.clear()
        self._fig.patch.set_facecolor(PANEL)
        self._ax.set_facecolor(PANEL)

        if not results:
            self._ax.text(0.5, 0.5, "No votes recorded yet",
                          ha="center", va="center", color=TEXT2,
                          fontsize=14, transform=self._ax.transAxes)
            self._canvas.draw()
            return

        candidates = list(results.keys())
        counts     = [results[c] for c in candidates]
        colors     = [BAR_COLORS[i % len(BAR_COLORS)] for i in range(len(candidates))]

        y_pos = range(len(candidates))
        bars  = self._ax.barh(y_pos, counts, color=colors, height=0.55,
                               edgecolor="none", zorder=2)

        # Background grid
        self._ax.xaxis.grid(True, color=BORDER, linestyle="--", alpha=0.5, zorder=0)
        self._ax.set_axisbelow(True)

        # Labels on bars
        max_count = max(counts) if counts else 1
        for bar, count, cand in zip(bars, counts, candidates):
            pct = (count / total * 100) if total > 0 else 0
            # Vote count label on bar
            self._ax.text(
                bar.get_width() + max_count * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"  {count:,}  ({pct:.1f}%)",
                va="center", ha="left", color=TEXT, fontsize=10,
                fontfamily="Segoe UI"
            )

        self._ax.set_yticks(list(y_pos))
        self._ax.set_yticklabels(candidates, color=TEXT, fontsize=11,
                                  fontfamily="Segoe UI")
        self._ax.set_xlabel("Number of Votes", color=TEXT2, fontsize=10)
        self._ax.set_title(
            f"Election Results  —  {self._election_var.get()}",
            color=TEXT, fontsize=13, fontweight="bold", pad=14
        )
        self._ax.tick_params(axis="x", colors=TEXT2, labelsize=9)
        self._ax.tick_params(axis="y", colors=TEXT, labelsize=10, length=0)
        for spine in self._ax.spines.values():
            spine.set_visible(False)

        if total > 0:
            self._ax.set_xlim(0, max_count * 1.30)

        self._fig.tight_layout(pad=1.5)
        self._canvas.draw()

        ts = time.strftime("%H:%M:%S")
        self._info_lbl.configure(text=f"Last updated: {ts}  •  Auto-refresh every 10 s")

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
                writer.writerow(["Rank", "Candidate", "Votes", "Percentage"])
                total = sum(self._last_results.values())
                sorted_results = sorted(self._last_results.items(),
                                        key=lambda x: x[1], reverse=True)
                for rank, (cand, count) in enumerate(sorted_results, 1):
                    pct = (count / total * 100) if total > 0 else 0
                    writer.writerow([rank, cand, count, f"{pct:.2f}%"])
            messagebox.showinfo("Exported", f"Results exported to:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))
