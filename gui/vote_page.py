import tkinter as tk
from tkinter import messagebox
import threading
import time

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

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
FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_LARGE = ("Segoe UI", 16, "bold")
FONT_SMALL = ("Segoe UI", 9)

# One distinct color per candidate slot
CANDIDATE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6",
                    "#ef4444", "#06b6d4", "#84cc16", "#f97316"]


class VotePage:
    def __init__(self, parent, node_url, root):
        self.parent   = parent
        self.node_url = node_url
        self.root     = root

        self._election_var    = tk.StringVar()
        self._candidate_var   = tk.StringVar()
        self._voter_id_var    = tk.StringVar()
        self._eligible_var    = tk.BooleanVar()
        self._status_var      = tk.StringVar(value="")
        self._timer_var       = tk.StringVar(value="—")
        self._total_votes_var = tk.StringVar(value="Total votes: —")
        self._elections       = []
        self._current_contract = None
        self._candidate_cards  = []   # list of (frame, color) for hover effects

        self._build()
        self._refresh_elections()

    # -----------------------------------------------------------------------
    def _build(self):
        # ── Scrollable outer wrapper ─────────────────────────────────────
        outer = tk.Frame(self.parent, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # ── Two-column layout ────────────────────────────────────────────
        columns = tk.Frame(outer, bg=BG)
        columns.pack(fill=tk.BOTH, expand=True)

        # LEFT — voting form
        left = tk.Frame(columns, bg=PANEL, padx=28, pady=24)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        tk.Frame(left, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 16))  # top border

        # Section: Election
        self._section_label(left, "1  •  Select Election")
        self._election_menu = tk.OptionMenu(left, self._election_var, "Loading...")
        self._election_menu.configure(
            bg=CARD, fg=TEXT, font=FONT_MAIN,
            activebackground=ACCENT, activeforeground="white",
            relief=tk.FLAT, highlightthickness=0, width=36,
            indicatoron=True
        )
        self._election_menu["menu"].configure(bg=CARD, fg=TEXT, font=FONT_MAIN,
                                               activebackground=ACCENT,
                                               activeforeground="white")
        self._election_menu.pack(fill=tk.X, pady=(0, 20), ipady=4)
        self._election_var.trace("w", self._on_election_change)

        # Section: Voter ID
        self._section_label(left, "2  •  Your Voter ID")
        id_wrap = tk.Frame(left, bg=CARD, pady=0)
        id_wrap.pack(fill=tk.X, pady=(0, 4))
        tk.Frame(id_wrap, bg=ACCENT, width=4).pack(side=tk.LEFT, fill=tk.Y)
        self._voter_entry = tk.Entry(
            id_wrap, textvariable=self._voter_id_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            relief=tk.FLAT, font=("Segoe UI", 11), show="•"
        )
        self._voter_entry.pack(fill=tk.X, padx=10, pady=10)

        # Show/hide toggle
        show_frame = tk.Frame(left, bg=PANEL)
        show_frame.pack(fill=tk.X, pady=(0, 4))
        self._show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            show_frame, text="Show Voter ID", variable=self._show_var,
            bg=PANEL, fg=TEXT2, selectcolor=CARD,
            activebackground=PANEL, activeforeground=TEXT2,
            font=FONT_SMALL, command=self._toggle_show_id
        ).pack(anchor="w")

        tk.Label(
            left,
            text="🔒  Your ID is SHA-256 hashed before submission — never stored in plain text.",
            font=FONT_SMALL, bg=PANEL, fg=TEXT2, wraplength=420, justify="left"
        ).pack(anchor="w", pady=(0, 20))

        # Section: Candidates
        self._section_label(left, "3  •  Select Candidate")
        self._candidates_frame = tk.Frame(left, bg=PANEL)
        self._candidates_frame.pack(fill=tk.X, pady=(0, 20))

        # Eligibility
        self._section_label(left, "4  •  Confirm Eligibility")
        elig_frame = tk.Frame(left, bg=CARD, padx=14, pady=10)
        elig_frame.pack(fill=tk.X, pady=(0, 20))
        self._eligible_check = tk.Checkbutton(
            elig_frame,
            text="I confirm that I am eligible to vote in this election",
            variable=self._eligible_var,
            bg=CARD, fg=TEXT, selectcolor=ACCENT,
            activebackground=CARD, activeforeground=TEXT,
            font=("Segoe UI", 10)
        )
        self._eligible_check.pack(anchor="w")

        # Submit button
        self._submit_btn = tk.Button(
            left, text="   🗳️   SUBMIT VOTE",
            command=self._submit_vote,
            bg=HIGHLIGHT, fg="white", font=("Segoe UI", 13, "bold"),
            activebackground="#c73652", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", pady=14
        )
        self._submit_btn.pack(fill=tk.X, pady=(0, 10))
        self._submit_btn.bind("<Enter>", lambda e: self._submit_btn.configure(bg="#c73652"))
        self._submit_btn.bind("<Leave>", lambda e: self._submit_btn.configure(bg=HIGHLIGHT))

        # Status message
        self._status_label = tk.Label(
            left, textvariable=self._status_var,
            font=FONT_MAIN, bg=PANEL, fg=SUCCESS, wraplength=420
        )
        self._status_label.pack(anchor="w")

        # RIGHT — info panel
        right = tk.Frame(columns, bg=PANEL, padx=20, pady=24, width=240)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        # Election status card
        self._build_info_card(right, "⏱  Time Remaining", self._timer_var, HIGHLIGHT)
        self._build_info_card(right, "🗳  Votes Cast", self._total_votes_var, SUCCESS)

        tk.Frame(right, bg=BORDER, height=1).pack(fill=tk.X, pady=12)

        tk.Label(right, text="HOW IT WORKS", font=("Segoe UI", 8, "bold"),
                 bg=PANEL, fg=TEXT2).pack(anchor="w", pady=(0, 8))

        steps = [
            ("1", "Choose the active election"),
            ("2", "Enter your private Voter ID"),
            ("3", "Select your candidate"),
            ("4", "Confirm eligibility"),
            ("5", "Submit — your vote is\nrecorded on the blockchain"),
        ]
        for num, desc in steps:
            row = tk.Frame(right, bg=PANEL)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=num, font=("Segoe UI", 9, "bold"),
                     bg=ACCENT, fg="white", width=2, pady=2).pack(side=tk.LEFT)
            tk.Label(row, text=f"  {desc}", font=FONT_SMALL,
                     bg=PANEL, fg=TEXT2, justify="left", wraplength=180).pack(side=tk.LEFT)

        tk.Frame(right, bg=BORDER, height=1).pack(fill=tk.X, pady=12)

        tk.Button(
            right, text="↻  Refresh Elections",
            command=self._refresh_elections,
            bg=CARD, fg=TEXT2, font=FONT_SMALL,
            activebackground=ACCENT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", pady=7
        ).pack(fill=tk.X)

        # Start timers
        self._update_timer()
        self._update_total_votes()

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 10, "bold"),
                 bg=PANEL, fg=TEXT2).pack(anchor="w", pady=(0, 6))

    def _build_info_card(self, parent, label, textvar, value_fg):
        card = tk.Frame(parent, bg=CARD, padx=14, pady=12)
        card.pack(fill=tk.X, pady=(0, 10))
        tk.Label(card, text=label, font=FONT_SMALL, bg=CARD, fg=TEXT2).pack(anchor="w")
        tk.Label(card, textvariable=textvar, font=("Segoe UI", 14, "bold"),
                 bg=CARD, fg=value_fg).pack(anchor="w", pady=(4, 0))

    def _toggle_show_id(self):
        show = self._show_var.get()
        self._voter_entry.configure(show="" if show else "•")

    # -----------------------------------------------------------------------
    def on_show(self):
        self._refresh_elections()

    def _refresh_elections(self):
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
            self._election_var.set("No elections available")
            return
        for e in elections:
            eid = e["election_id"]
            status = "Active ✓" if e.get("is_active") else "Inactive"
            menu.add_command(
                label=f"{eid}  [{status}]",
                command=lambda v=eid: self._election_var.set(v)
            )
        current = self._election_var.get()
        if not current or current not in [e["election_id"] for e in elections]:
            self._election_var.set(elections[0]["election_id"])
        else:
            self._on_election_change()

    def _on_election_change(self, *args):
        eid = self._election_var.get()
        for e in self._elections:
            if e["election_id"] == eid:
                self._current_contract = e
                self._populate_candidates(e.get("candidates", []))
                break

    def _populate_candidates(self, candidates):
        for widget in self._candidates_frame.winfo_children():
            widget.destroy()
        self._candidate_cards.clear()
        self._candidate_var.set("")

        for i, name in enumerate(candidates):
            color = CANDIDATE_COLORS[i % len(CANDIDATE_COLORS)]
            self._make_candidate_card(name, color, i)

    def _make_candidate_card(self, name, color, idx):
        """Styled card radio button for each candidate."""
        card = tk.Frame(self._candidates_frame, bg=CARD, cursor="hand2",
                        pady=0, padx=0)
        card.pack(fill=tk.X, pady=4)

        # Color accent bar on left
        accent_bar = tk.Frame(card, bg=color, width=5)
        accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(card, bg=CARD, padx=14, pady=10)
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Candidate number badge
        badge = tk.Label(inner, text=f"#{idx + 1}", font=("Segoe UI", 8, "bold"),
                         bg=color, fg="white", padx=5, pady=2)
        badge.pack(side=tk.LEFT, padx=(0, 10))

        name_lbl = tk.Label(inner, text=name, font=("Segoe UI", 11, "bold"),
                            bg=CARD, fg=TEXT, anchor="w")
        name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Radio indicator on right
        radio_var = self._candidate_var
        rb = tk.Radiobutton(
            inner, variable=radio_var, value=name,
            bg=CARD, activebackground=CARD, selectcolor=color,
            cursor="hand2", command=lambda n=name: self._select_candidate(n)
        )
        rb.pack(side=tk.RIGHT)

        self._candidate_cards.append((card, accent_bar, inner, name_lbl, badge, rb, color, name))

        # Click anywhere on card to select
        for widget in (card, accent_bar, inner, name_lbl, badge):
            widget.bind("<Button-1>", lambda e, n=name: self._select_candidate(n))
            widget.bind("<Enter>",    lambda e, c=card, ab=accent_bar, i=inner, nl=name_lbl, bg2=CARD:
                        self._hover_card(c, ab, i, nl, True))
            widget.bind("<Leave>",    lambda e, c=card, ab=accent_bar, i=inner, nl=name_lbl, bg2=CARD:
                        self._hover_card(c, ab, i, nl, False))

    def _hover_card(self, card, accent_bar, inner, name_lbl, entering):
        hover_bg = "#263146" if entering else CARD
        card.configure(bg=hover_bg)
        inner.configure(bg=hover_bg)
        name_lbl.configure(bg=hover_bg)

    def _select_candidate(self, name):
        self._candidate_var.set(name)
        # Highlight selected card, dim others
        for (card, accent_bar, inner, name_lbl, badge, rb, color, cname) in self._candidate_cards:
            if cname == name:
                card.configure(bg="#0f2847", relief=tk.SOLID)
                inner.configure(bg="#0f2847")
                name_lbl.configure(bg="#0f2847", fg="white")
                badge.configure(bg=color)
            else:
                card.configure(bg=CARD, relief=tk.FLAT)
                inner.configure(bg=CARD)
                name_lbl.configure(bg=CARD, fg=TEXT)

    # -----------------------------------------------------------------------
    def _update_timer(self):
        contract = self._current_contract
        if contract and contract.get("end_time"):
            remaining = contract["end_time"] - time.time()
            if remaining > 0:
                h = int(remaining // 3600)
                m = int((remaining % 3600) // 60)
                s = int(remaining % 60)
                self._timer_var.set(f"{h:02d}:{m:02d}:{s:02d}")
            else:
                self._timer_var.set("ENDED")
        elif contract:
            self._timer_var.set("No time limit")
        else:
            self._timer_var.set("—")
        self.root.after(1000, self._update_timer)

    def _update_total_votes(self):
        eid = self._election_var.get()
        if not eid or not REQUESTS_OK:
            self.root.after(5000, self._update_total_votes)
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/results",
                                 params={"election_id": eid}, timeout=2)
                if r.status_code == 200:
                    total = r.json().get("total_votes", 0)
                    self.root.after(0, lambda: self._total_votes_var.set(str(total)))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()
        self.root.after(5000, self._update_total_votes)

    # -----------------------------------------------------------------------
    def _submit_vote(self):
        voter_id    = self._voter_id_var.get().strip()
        candidate   = self._candidate_var.get().strip()
        election_id = self._election_var.get().strip()

        if not voter_id:
            self._show_status("⚠  Please enter your Voter ID.", error=True); return
        if not candidate:
            self._show_status("⚠  Please select a candidate.", error=True); return
        if not self._eligible_var.get():
            self._show_status("⚠  Please confirm your eligibility.", error=True); return
        if not REQUESTS_OK:
            self._show_status("requests library not available.", error=True); return

        self._submit_btn.configure(state=tk.DISABLED, text="  ⏳  Submitting...")
        self._show_status("Submitting your vote to the blockchain...", error=False)

        def post():
            try:
                r = requests.post(
                    f"{self.node_url}/vote",
                    json={"voter_id": voter_id, "candidate": candidate,
                          "election_id": election_id},
                    timeout=5
                )
                data = r.json()
                if r.status_code in (200, 201) and data.get("success"):
                    vh = data.get("vote_hash", "")
                    self.root.after(0, lambda: self._on_vote_success(
                        candidate, election_id, voter_id, vh))
                else:
                    err = data.get("error", "Unknown error")
                    self.root.after(0, lambda: self._on_vote_fail(err))
            except Exception as ex:
                self.root.after(0, lambda: self._on_vote_fail(str(ex)))

        threading.Thread(target=post, daemon=True).start()

    def _on_vote_success(self, candidate, election_id, voter_id, vote_hash):
        self._submit_btn.configure(state=tk.NORMAL, text="   🗳️   SUBMIT VOTE")
        self._show_status("✓  Vote submitted successfully!", error=False)
        self._voter_id_var.set("")
        self._eligible_var.set(False)
        self._show_receipt_dialog(candidate, election_id, voter_id, vote_hash)

    def _on_vote_fail(self, error):
        self._submit_btn.configure(state=tk.NORMAL, text="   🗳️   SUBMIT VOTE")
        self._show_status(f"✕  {error}", error=True)

    def _show_status(self, msg, error=False):
        self._status_var.set(msg)
        self._status_label.configure(fg=HIGHLIGHT if error else SUCCESS)

    def _show_receipt_dialog(self, candidate, election_id, voter_id, vote_hash):
        from audit.receipt import generate_receipt, format_receipt
        receipt = generate_receipt(voter_id, candidate, election_id, vote_hash)
        receipt_text = format_receipt(receipt)

        dlg = tk.Toplevel(self.root)
        dlg.title("Vote Receipt")
        dlg.configure(bg=BG)
        dlg.geometry("580x460")
        dlg.resizable(False, False)
        dlg.grab_set()

        # Header
        hdr = tk.Frame(dlg, bg=SUCCESS, pady=14)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="✓  Vote Submitted Successfully!",
                 font=("Segoe UI", 14, "bold"), bg=SUCCESS, fg="white").pack()
        tk.Label(hdr, text=f"Candidate: {candidate}",
                 font=FONT_MAIN, bg=SUCCESS, fg="white").pack()

        tk.Label(dlg, text="Save your receipt — paste the Vote Hash in the Verify page anytime.",
                 font=FONT_SMALL, bg=BG, fg=TEXT2).pack(pady=(10, 4))

        # Receipt text box
        text_box = tk.Text(dlg, bg=PANEL, fg=TEXT, font=("Consolas", 9),
                           relief=tk.FLAT, height=14, padx=14, pady=12,
                           borderwidth=0)
        text_box.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 4))
        text_box.insert("1.0", receipt_text)
        text_box.configure(state=tk.DISABLED)

        # Buttons
        btn_frame = tk.Frame(dlg, bg=BG)
        btn_frame.pack(pady=14)

        def copy_hash():
            dlg.clipboard_clear()
            dlg.clipboard_append(vote_hash)
            copy_btn.configure(text="✓ Copied!", bg=SUCCESS)

        copy_btn = tk.Button(
            btn_frame, text="Copy Vote Hash", command=copy_hash,
            bg=ACCENT, fg="white", font=FONT_MAIN,
            activebackground=ACCENT2, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=18, pady=9
        )
        copy_btn.pack(side=tk.LEFT, padx=8)

        tk.Button(
            btn_frame, text="Close", command=dlg.destroy,
            bg=CARD, fg=TEXT, font=FONT_MAIN,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=18, pady=9
        ).pack(side=tk.LEFT, padx=8)
