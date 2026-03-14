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


class VotePage:
    def __init__(self, parent, node_url, root):
        self.parent = parent
        self.node_url = node_url
        self.root = root

        self._election_var = tk.StringVar()
        self._candidate_var = tk.StringVar()
        self._voter_id_var = tk.StringVar()
        self._eligible_var = tk.BooleanVar()
        self._status_var = tk.StringVar(value="")
        self._timer_var = tk.StringVar(value="")
        self._total_votes_var = tk.StringVar(value="Total votes: —")
        self._elections = []
        self._current_contract = None

        self._build()
        self._refresh_elections()

    def _build(self):
        # Page title
        tk.Label(
            self.parent, text="Cast Your Vote", font=FONT_LARGE,
            bg=BG, fg=HIGHLIGHT
        ).pack(pady=(20, 5))

        tk.Frame(self.parent, bg=HIGHLIGHT, height=2).pack(fill=tk.X, padx=20, pady=5)

        # Main container
        container = tk.Frame(self.parent, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)

        # Left panel — form
        left = tk.Frame(container, bg=PANEL, padx=20, pady=20)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Election selector
        tk.Label(left, text="Select Election", font=FONT_TITLE, bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 5))
        self._election_menu = tk.OptionMenu(left, self._election_var, "Loading...")
        self._election_menu.configure(
            bg=ACCENT, fg=TEXT, font=FONT_MAIN,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, highlightthickness=0, width=30
        )
        self._election_menu["menu"].configure(bg=ACCENT, fg=TEXT, font=FONT_MAIN)
        self._election_menu.pack(fill=tk.X, pady=(0, 15))
        self._election_var.trace("w", self._on_election_change)

        # Voter ID
        tk.Label(left, text="Your Voter ID (kept private)", font=FONT_TITLE, bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 5))
        self._voter_entry = tk.Entry(
            left, textvariable=self._voter_id_var, width=40,
            bg=ACCENT, fg=TEXT, insertbackground=TEXT,
            relief=tk.FLAT, font=FONT_MAIN, show=""
        )
        self._voter_entry.pack(fill=tk.X, pady=(0, 5), ipady=8)
        tk.Label(
            left, text="Your Voter ID will be hashed before submission — never stored in plain text.",
            font=FONT_SMALL, bg=PANEL, fg=WARNING, wraplength=400, justify="left"
        ).pack(anchor="w", pady=(0, 15))

        # Candidate selection
        self._candidates_frame_label = tk.Label(left, text="Select Candidate", font=FONT_TITLE, bg=PANEL, fg=TEXT)
        self._candidates_frame_label.pack(anchor="w", pady=(0, 5))
        self._candidates_frame = tk.Frame(left, bg=PANEL)
        self._candidates_frame.pack(fill=tk.X, pady=(0, 15))

        # Eligibility checkbox
        self._eligible_check = tk.Checkbutton(
            left,
            text="I confirm I am eligible to vote in this election",
            variable=self._eligible_var,
            bg=PANEL, fg=TEXT, selectcolor=ACCENT,
            activebackground=PANEL, activeforeground=TEXT,
            font=FONT_MAIN
        )
        self._eligible_check.pack(anchor="w", pady=(0, 15))

        # Submit button
        self._submit_btn = tk.Button(
            left, text="SUBMIT VOTE",
            command=self._submit_vote,
            bg=HIGHLIGHT, fg="white", font=FONT_LARGE,
            activebackground="#c73652", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", pady=14
        )
        self._submit_btn.pack(fill=tk.X, pady=(0, 10))

        # Status message
        self._status_label = tk.Label(
            left, textvariable=self._status_var,
            font=FONT_MAIN, bg=PANEL, fg=SUCCESS, wraplength=400
        )
        self._status_label.pack(anchor="w")

        # Right panel — info
        right = tk.Frame(container, bg=PANEL, padx=20, pady=20, width=250)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        tk.Label(right, text="Election Info", font=FONT_TITLE, bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0, 10))

        tk.Label(right, text="Time Remaining:", font=FONT_SMALL, bg=PANEL, fg=WARNING).pack(anchor="w")
        tk.Label(right, textvariable=self._timer_var, font=FONT_TITLE, bg=PANEL, fg=HIGHLIGHT).pack(anchor="w", pady=(0, 15))

        tk.Label(right, textvariable=self._total_votes_var, font=FONT_MAIN, bg=PANEL, fg=TEXT).pack(anchor="w")

        tk.Button(
            right, text="Refresh Elections",
            command=self._refresh_elections,
            bg=ACCENT, fg=TEXT, font=FONT_SMALL,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", pady=6
        ).pack(fill=tk.X, pady=(20, 0))

        # Start timers
        self._update_timer()
        self._update_total_votes()

    def on_show(self):
        self._refresh_elections()

    def _refresh_elections(self):
        if not REQUESTS_OK:
            return

        def fetch():
            try:
                r = requests.get(f"{self.node_url}/elections", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    elections = data.get("elections", [])
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
            label = f"{eid} ({'Active' if e.get('is_active') else 'Inactive'})"
            menu.add_command(label=label, command=lambda v=eid: self._election_var.set(v))
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
        self._candidate_var.set("")
        for i, c in enumerate(candidates):
            rb = tk.Radiobutton(
                self._candidates_frame,
                text=c,
                value=c,
                variable=self._candidate_var,
                bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                activebackground=PANEL, activeforeground=TEXT,
                font=("Segoe UI", 12),
                indicatoron=True
            )
            rb.pack(anchor="w", pady=4)

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
        elif contract and not contract.get("end_time"):
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
                r = requests.get(f"{self.node_url}/results", params={"election_id": eid}, timeout=2)
                if r.status_code == 200:
                    total = r.json().get("total_votes", 0)
                    self.root.after(0, lambda: self._total_votes_var.set(f"Total votes cast: {total}"))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()
        self.root.after(5000, self._update_total_votes)

    def _submit_vote(self):
        voter_id = self._voter_id_var.get().strip()
        candidate = self._candidate_var.get().strip()
        election_id = self._election_var.get().strip()

        if not voter_id:
            self._show_status("Please enter your Voter ID.", error=True)
            return
        if not candidate:
            self._show_status("Please select a candidate.", error=True)
            return
        if not self._eligible_var.get():
            self._show_status("Please confirm your eligibility.", error=True)
            return
        if not REQUESTS_OK:
            self._show_status("requests library not available.", error=True)
            return

        self._submit_btn.configure(state=tk.DISABLED, text="Submitting...")
        self._show_status("Submitting vote...", error=False)

        def post():
            try:
                r = requests.post(
                    f"{self.node_url}/vote",
                    json={"voter_id": voter_id, "candidate": candidate, "election_id": election_id},
                    timeout=5
                )
                data = r.json()
                if r.status_code in (200, 201) and data.get("success"):
                    vote_hash = data.get("vote_hash", "")
                    self.root.after(0, lambda: self._on_vote_success(candidate, election_id, voter_id, vote_hash))
                else:
                    err = data.get("error", "Unknown error")
                    self.root.after(0, lambda: self._on_vote_fail(err))
            except Exception as ex:
                self.root.after(0, lambda: self._on_vote_fail(str(ex)))

        threading.Thread(target=post, daemon=True).start()

    def _on_vote_success(self, candidate, election_id, voter_id, vote_hash):
        self._submit_btn.configure(state=tk.NORMAL, text="SUBMIT VOTE")
        self._show_status(f"Vote submitted successfully!", error=False)
        self._voter_id_var.set("")
        self._eligible_var.set(False)
        self._show_receipt_dialog(candidate, election_id, voter_id, vote_hash)

    def _on_vote_fail(self, error):
        self._submit_btn.configure(state=tk.NORMAL, text="SUBMIT VOTE")
        self._show_status(f"Error: {error}", error=True)

    def _show_status(self, msg, error=False):
        self._status_var.set(msg)
        self._status_label.configure(fg=HIGHLIGHT if error else SUCCESS)

    def _show_receipt_dialog(self, candidate, election_id, voter_id, vote_hash):
        from audit.receipt import generate_receipt, format_receipt
        receipt = generate_receipt(voter_id, candidate, election_id, vote_hash)
        receipt_text = format_receipt(receipt)

        dlg = tk.Toplevel(self.root)
        dlg.title("Your Vote Receipt")
        dlg.configure(bg=BG)
        dlg.geometry("540x400")
        dlg.grab_set()

        tk.Label(dlg, text="Vote Submitted Successfully!", font=FONT_LARGE, bg=BG, fg=SUCCESS).pack(pady=(20, 5))
        tk.Label(dlg, text="Save your receipt — use the Vote Hash to verify later.", font=FONT_SMALL, bg=BG, fg=WARNING).pack(pady=(0, 10))

        text_box = tk.Text(dlg, bg=PANEL, fg=TEXT, font=("Consolas", 10), relief=tk.FLAT, height=12, padx=10, pady=10)
        text_box.pack(fill=tk.BOTH, expand=True, padx=20)
        text_box.insert("1.0", receipt_text)
        text_box.configure(state=tk.DISABLED)

        btn_frame = tk.Frame(dlg, bg=BG)
        btn_frame.pack(pady=15)

        def copy_hash():
            dlg.clipboard_clear()
            dlg.clipboard_append(vote_hash)
            copy_btn.configure(text="Copied!")

        copy_btn = tk.Button(
            btn_frame, text="Copy Vote Hash", command=copy_hash,
            bg=ACCENT, fg=TEXT, font=FONT_MAIN,
            activebackground=HIGHLIGHT, activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=14, pady=8
        )
        copy_btn.pack(side=tk.LEFT, padx=10)

        tk.Button(
            btn_frame, text="Close", command=dlg.destroy,
            bg=HIGHLIGHT, fg="white", font=FONT_MAIN,
            activebackground="#c73652", activeforeground="white",
            relief=tk.FLAT, cursor="hand2", padx=14, pady=8
        ).pack(side=tk.LEFT, padx=10)
