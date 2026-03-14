"""
Tests for network/consensus and audit utilities.
Run with:  python -m pytest tests/ -v
"""
import sys
import os
import time
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from audit.receipt import generate_receipt, format_receipt
from audit.verification import verify_vote, verify_chain_integrity
from audit import audit_log


# =====================================================================
# Consensus / resolve_conflicts tests (mocked network)
# =====================================================================

class TestConsensus:
    """
    Test resolve_conflicts using a mock requests module so tests don't
    need a live Flask server.
    """

    def _build_chain(self, block_count, difficulty=2):
        """Build a chain with `block_count` mined blocks (plus genesis)."""
        bc = Blockchain(difficulty=difficulty)
        for i in range(block_count):
            bc.add_transaction(Transaction(f"voter_{i}", "Alice", "e1"))
            bc.mine_pending()
        return bc

    def test_resolve_no_peers(self):
        from network.consensus import resolve_conflicts
        bc = self._build_chain(2)
        replaced = resolve_conflicts(bc, [])
        assert replaced is False

    def test_resolve_peer_has_shorter_chain(self, monkeypatch):
        """If peer has a shorter chain, ours should be kept."""
        from network import consensus
        local_bc = self._build_chain(3)  # genesis + 3 blocks = 4 total

        shorter_bc = self._build_chain(1)  # genesis + 1 block = 2 total

        class FakeResponse:
            status_code = 200
            def json(self):
                d = shorter_bc.to_dict()
                return d

        monkeypatch.setattr(consensus.requests, "get", lambda url, timeout: FakeResponse())

        replaced = consensus.resolve_conflicts(local_bc, ["http://fake-peer:5001"])
        assert replaced is False
        assert len(local_bc.chain) == 4  # unchanged

    def test_resolve_peer_has_longer_valid_chain(self, monkeypatch):
        """If peer has a longer valid chain, ours should be replaced."""
        from network import consensus
        local_bc = self._build_chain(1)   # 2 blocks total

        longer_bc = self._build_chain(3)  # 4 blocks total

        class FakeResponse:
            status_code = 200
            def json(self):
                return longer_bc.to_dict()

        monkeypatch.setattr(consensus.requests, "get", lambda url, timeout: FakeResponse())

        replaced = consensus.resolve_conflicts(local_bc, ["http://fake-peer:5001"])
        assert replaced is True
        assert len(local_bc.chain) == len(longer_bc.chain)

    def test_ping_peer_connection_error(self, monkeypatch):
        """ping_peer returns False when the peer is unreachable."""
        from network import consensus

        def raise_exc(*a, **kw):
            raise ConnectionError("unreachable")

        monkeypatch.setattr(consensus.requests, "get", raise_exc)
        result = consensus.ping_peer("http://dead-peer:9999")
        assert result is False


# =====================================================================
# Audit receipt tests
# =====================================================================

class TestReceipt:
    def test_generate_receipt_fields(self):
        r = generate_receipt("voter1", "Alice", "e1", "a" * 64)
        assert "vote_hash" in r
        assert "election_id" in r
        assert "receipt_code" in r
        assert "timestamp" in r
        assert r["election_id"] == "e1"
        assert r["vote_hash"] == "a" * 64

    def test_receipt_code_is_16_uppercase_chars(self):
        r = generate_receipt("voter1", "Alice", "e1", "b" * 64)
        code = r["receipt_code"]
        assert len(code) == 16
        assert code == code.upper()

    def test_format_receipt_contains_election(self):
        r = generate_receipt("voter1", "Alice", "my_election", "c" * 64)
        text = format_receipt(r)
        assert "my_election" in text
        assert "Alice" in text
        assert r["receipt_code"] in text


# =====================================================================
# Audit verification tests
# =====================================================================

class TestVerification:
    def _make_bc_with_vote(self):
        bc = Blockchain(difficulty=2)
        tx = Transaction("voter1", "Alice", "e1")
        bc.add_transaction(tx)
        bc.mine_pending()
        return bc, tx

    def test_verify_vote_found(self):
        bc, tx = self._make_bc_with_vote()
        result = verify_vote(bc, tx.vote_hash)
        assert result["found"] is True
        assert result["candidate"] == "Alice"
        assert result["block_index"] == 1

    def test_verify_vote_not_found(self):
        bc, _ = self._make_bc_with_vote()
        result = verify_vote(bc, "x" * 64)
        assert result["found"] is False

    def test_verify_chain_integrity_valid(self):
        bc = Blockchain(difficulty=2)
        tx = Transaction("v1", "Alice", "e1")
        bc.add_transaction(tx)
        bc.mine_pending()
        result = verify_chain_integrity(bc)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_verify_chain_integrity_tampered(self):
        bc = Blockchain(difficulty=2)
        tx = Transaction("v1", "Alice", "e1")
        bc.add_transaction(tx)
        bc.mine_pending()
        # Tamper with the hash directly
        bc.chain[1].hash = "0" * 64
        result = verify_chain_integrity(bc)
        assert result["valid"] is False
        assert len(result["errors"]) > 0


# =====================================================================
# Audit log tests
# =====================================================================

class TestAuditLog:
    def test_log_and_retrieve(self, tmp_path, monkeypatch):
        """Test that log_event writes and get_recent reads correctly."""
        log_file = str(tmp_path / "test_audit.log")
        # Patch the log path
        monkeypatch.setattr(audit_log, "_log_path", log_file)

        audit_log.log_event("VOTE", "Test vote recorded")
        audit_log.log_event("MINE", "Block mined")

        entries = audit_log.get_recent(10)
        assert len(entries) == 2
        assert "[VOTE]" in entries[0]
        assert "[MINE]" in entries[1]

    def test_get_recent_limit(self, tmp_path, monkeypatch):
        log_file = str(tmp_path / "test_audit2.log")
        monkeypatch.setattr(audit_log, "_log_path", log_file)

        for i in range(20):
            audit_log.log_event("TEST", f"Entry {i}")

        entries = audit_log.get_recent(5)
        assert len(entries) == 5

    def test_export_csv(self, tmp_path, monkeypatch):
        log_file = str(tmp_path / "test_audit3.log")
        csv_file = str(tmp_path / "output.csv")
        monkeypatch.setattr(audit_log, "_log_path", log_file)

        audit_log.log_event("VOTE", "Candidate=Alice")
        audit_log.export_csv(csv_file)

        assert os.path.exists(csv_file)
        with open(csv_file) as f:
            content = f.read()
        assert "VOTE" in content
        assert "Candidate=Alice" in content
