import json
import os
import threading
import time

from flask import Flask, request, jsonify

from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from smart_contract.voting_rules import VotingContract
from audit import audit_log
from network.consensus import resolve_conflicts


# ---------------------------------------------------------------------------
# Module-level state (shared between Flask routes and background threads)
# ---------------------------------------------------------------------------
_blockchain = None
_contracts = {}        # election_id -> VotingContract
_peers = set()
_port = 5000
_data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
_chain_file = None
_mining_lock = threading.Lock()
_is_mining = False
_auto_mine_thread = None
_auto_mine_enabled = False
_auto_mine_interval = 60  # seconds


def _chain_path():
    return os.path.join(os.path.abspath(_data_dir), f"blockchain_{_port}.json")


def _contracts_path():
    return os.path.join(os.path.abspath(_data_dir), f"contracts_{_port}.json")


def _save_state():
    """Persist blockchain and contracts to disk."""
    try:
        _blockchain.save(_chain_path())
        contracts_data = {eid: c.to_dict() for eid, c in _contracts.items()}
        with open(_contracts_path(), "w") as f:
            json.dump(contracts_data, f, indent=2)
    except Exception as e:
        audit_log.log_event("ERROR", f"Save state failed: {e}")


def _load_state():
    """Load blockchain and contracts from disk, or initialise defaults."""
    global _blockchain, _contracts

    cp = _chain_path()
    if os.path.exists(cp):
        try:
            _blockchain = Blockchain.load(cp)
            audit_log.log_event("STARTUP", f"Blockchain loaded from {cp} ({len(_blockchain.chain)} blocks)")
        except Exception as e:
            audit_log.log_event("ERROR", f"Failed to load blockchain: {e} — creating fresh chain")
            _blockchain = Blockchain(difficulty=4)
    else:
        _blockchain = Blockchain(difficulty=4)
        audit_log.log_event("STARTUP", "New blockchain created")

    ctp = _contracts_path()
    if os.path.exists(ctp):
        try:
            with open(ctp, "r") as f:
                raw = json.load(f)
            _contracts = {eid: VotingContract.from_dict(d) for eid, d in raw.items()}
            audit_log.log_event("STARTUP", f"Loaded {len(_contracts)} election contract(s)")
        except Exception as e:
            audit_log.log_event("ERROR", f"Failed to load contracts: {e}")
            _contracts = {}
    else:
        _contracts = {}


def _ensure_default_election():
    """Create the default election from config.json if no elections exist."""
    if _contracts:
        return
    config_path = os.path.join(os.path.abspath(_data_dir), "config.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        de = cfg.get("default_election", {})
        eid = de.get("election_id", "election_2026")
        candidates = de.get("candidates", ["Alice", "Bob"])
        duration_h = de.get("duration_hours", 24)
        end_time = time.time() + duration_h * 3600
        _contracts[eid] = VotingContract(candidates, eid, end_time=end_time)
        _save_state()
        audit_log.log_event("ELECTION", f"Default election '{eid}' created with candidates: {candidates}")
    except Exception as e:
        audit_log.log_event("ERROR", f"Could not create default election: {e}")
        # Fallback
        eid = "election_2026"
        _contracts[eid] = VotingContract(
            ["Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince"],
            eid,
            end_time=time.time() + 24 * 3600
        )
        _save_state()


def _auto_mine_loop(app):
    """Background thread: auto-mine pending transactions every N seconds."""
    global _is_mining, _auto_mine_enabled
    while _auto_mine_enabled:
        time.sleep(_auto_mine_interval)
        if not _auto_mine_enabled:
            break
        if _blockchain.pending_transactions:
            with _mining_lock:
                _is_mining = True
                try:
                    block = _blockchain.mine_pending()
                    if block:
                        _save_state()
                        audit_log.log_event("MINE", f"Auto-mined block #{block.index} with {len(block.transactions)} tx")
                finally:
                    _is_mining = False


# ---------------------------------------------------------------------------
# Flask application factory
# ---------------------------------------------------------------------------

def create_app(port=5000, peer=None):
    global _port, _auto_mine_interval

    _port = port
    os.makedirs(os.path.abspath(_data_dir), exist_ok=True)
    _load_state()
    _ensure_default_election()

    if peer:
        _peers.add(peer)

    app = Flask(__name__)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.route("/chain", methods=["GET"])
    def get_chain():
        return jsonify(_blockchain.to_dict()), 200

    @app.route("/pending", methods=["GET"])
    def get_pending():
        return jsonify({
            "count": len(_blockchain.pending_transactions),
            "transactions": [t.to_dict() for t in _blockchain.pending_transactions]
        }), 200

    @app.route("/vote", methods=["POST"])
    def cast_vote():
        data = request.get_json(force=True) or {}
        voter_id = data.get("voter_id", "").strip()
        candidate = data.get("candidate", "").strip()
        election_id = data.get("election_id", "default").strip()

        if not voter_id or not candidate:
            return jsonify({"success": False, "error": "voter_id and candidate are required"}), 400

        contract = _contracts.get(election_id)
        if not contract:
            return jsonify({"success": False, "error": f"Election '{election_id}' not found"}), 404

        valid, reason = contract.validate(voter_id, candidate)
        if not valid:
            audit_log.log_event("VOTE_REJECTED", f"Election={election_id} Reason={reason}")
            return jsonify({"success": False, "error": reason}), 400

        tx = Transaction(voter_id, candidate, election_id)
        _blockchain.add_transaction(tx)
        contract.record_vote(voter_id)
        _save_state()

        audit_log.log_event("VOTE", f"Election={election_id} Candidate={candidate} Hash={tx.vote_hash[:16]}...")
        return jsonify({
            "success": True,
            "vote_hash": tx.vote_hash,
            "message": "Vote submitted to pending pool. It will be confirmed when mined."
        }), 201

    @app.route("/mine", methods=["POST"])
    def mine():
        global _is_mining
        if _is_mining:
            return jsonify({"success": False, "error": "Mining already in progress"}), 409

        if not _blockchain.pending_transactions:
            return jsonify({"success": False, "error": "No pending transactions to mine"}), 400

        with _mining_lock:
            _is_mining = True
            try:
                block = _blockchain.mine_pending()
            finally:
                _is_mining = False

        if block:
            _save_state()
            audit_log.log_event("MINE", f"Block #{block.index} mined. Hash={block.hash[:16]}... Txs={len(block.transactions)}")
            return jsonify({
                "success": True,
                "block": block.to_dict()
            }), 200
        return jsonify({"success": False, "error": "Mining failed"}), 500

    @app.route("/results", methods=["GET"])
    def get_results():
        election_id = request.args.get("election_id", "default")
        results = _blockchain.get_results(election_id)
        contract = _contracts.get(election_id)
        candidates = contract.candidates if contract else list(results.keys())

        # Ensure all candidates appear (even with 0 votes)
        full_results = {c: results.get(c, 0) for c in candidates}
        total = sum(full_results.values())
        return jsonify({
            "election_id": election_id,
            "results": full_results,
            "total_votes": total,
            "chain_length": len(_blockchain.chain)
        }), 200

    @app.route("/peers", methods=["GET"])
    def get_peers():
        return jsonify({"peers": list(_peers)}), 200

    @app.route("/register_peer", methods=["POST"])
    def register_peer():
        data = request.get_json(force=True) or {}
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"success": False, "error": "url is required"}), 400
        _peers.add(url)
        audit_log.log_event("PEER", f"Registered peer: {url}")
        return jsonify({"success": True, "peers": list(_peers)}), 200

    @app.route("/sync", methods=["POST"])
    def sync():
        """Receive a chain from a peer and adopt it if it's longer and valid."""
        replaced = resolve_conflicts(_blockchain, list(_peers))
        if replaced:
            _save_state()
            audit_log.log_event("SYNC", "Chain replaced by longer peer chain")
            return jsonify({"message": "Chain was replaced by a longer valid chain"}), 200
        return jsonify({"message": "Our chain is authoritative — no replacement needed"}), 200

    @app.route("/status", methods=["GET"])
    def status():
        return jsonify({
            "status": "online",
            "port": _port,
            "chain_length": len(_blockchain.chain),
            "pending_count": len(_blockchain.pending_transactions),
            "peers": list(_peers),
            "is_mining": _is_mining,
            "elections": list(_contracts.keys()),
            "auto_mine": _auto_mine_enabled
        }), 200

    @app.route("/find_vote/<vote_hash>", methods=["GET"])
    def find_vote(vote_hash):
        result = _blockchain.find_vote(vote_hash)
        return jsonify(result), 200

    @app.route("/elections", methods=["GET"])
    def list_elections():
        elections = []
        for eid, c in _contracts.items():
            elections.append({
                "election_id": eid,
                "candidates": c.candidates,
                "is_active": c.is_active(),
                "start_time": c.start_time,
                "end_time": c.end_time,
                "voted_count": len(c.voted_hashes),
                "time_remaining": c.time_remaining()
            })
        return jsonify({"elections": elections}), 200

    @app.route("/create_election", methods=["POST"])
    def create_election():
        data = request.get_json(force=True) or {}
        election_id = data.get("election_id", "").strip()
        candidates = data.get("candidates", [])
        duration_hours = float(data.get("duration_hours", 24))

        if not election_id:
            return jsonify({"success": False, "error": "election_id is required"}), 400
        if not candidates or not isinstance(candidates, list):
            return jsonify({"success": False, "error": "candidates must be a non-empty list"}), 400
        if election_id in _contracts:
            return jsonify({"success": False, "error": f"Election '{election_id}' already exists"}), 409

        end_time = time.time() + duration_hours * 3600 if duration_hours > 0 else None
        contract = VotingContract(candidates, election_id, end_time=end_time)
        _contracts[election_id] = contract
        _save_state()
        audit_log.log_event("ELECTION", f"Created election '{election_id}' candidates={candidates} duration={duration_hours}h")
        return jsonify({"success": True, "election_id": election_id, "contract": contract.to_dict()}), 201

    @app.route("/clear_pending", methods=["POST"])
    def clear_pending():
        count = len(_blockchain.pending_transactions)
        _blockchain.pending_transactions = []
        audit_log.log_event("ADMIN", f"Cleared {count} pending transactions")
        return jsonify({"success": True, "cleared": count}), 200

    @app.route("/auto_mine", methods=["POST"])
    def toggle_auto_mine():
        global _auto_mine_enabled, _auto_mine_thread, _auto_mine_interval
        data = request.get_json(force=True) or {}
        enable = data.get("enable", True)
        interval = int(data.get("interval", _auto_mine_interval))
        _auto_mine_interval = interval

        if enable and not _auto_mine_enabled:
            _auto_mine_enabled = True
            _auto_mine_thread = threading.Thread(
                target=_auto_mine_loop, args=(app,), daemon=True
            )
            _auto_mine_thread.start()
            audit_log.log_event("ADMIN", f"Auto-mine enabled (interval={interval}s)")
            return jsonify({"success": True, "auto_mine": True, "interval": interval}), 200
        elif not enable and _auto_mine_enabled:
            _auto_mine_enabled = False
            audit_log.log_event("ADMIN", "Auto-mine disabled")
            return jsonify({"success": True, "auto_mine": False}), 200

        return jsonify({"success": True, "auto_mine": _auto_mine_enabled}), 200

    @app.route("/audit_log", methods=["GET"])
    def get_audit_log():
        n = int(request.args.get("n", 100))
        entries = audit_log.get_recent(n)
        return jsonify({"entries": entries, "count": len(entries)}), 200

    return app
