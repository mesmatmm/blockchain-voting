"""
Tests for core blockchain logic.
Run with:  python -m pytest tests/ -v
"""
import sys
import os
import time
import hashlib

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blockchain.transaction import Transaction
from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.merkle import compute_merkle_root, hash_pair


# =====================================================================
# Transaction tests
# =====================================================================

class TestTransaction:
    def test_hash_is_computed(self):
        tx = Transaction("voter1", "Alice", "test_election")
        assert tx.vote_hash is not None
        assert len(tx.vote_hash) == 64  # SHA-256 hex

    def test_to_dict_hides_voter_id(self):
        tx = Transaction("voter1", "Alice", "test_election")
        d = tx.to_dict()
        assert d["voter_id"] != "voter1"
        # Should be the SHA-256 of "voter1"
        expected = hashlib.sha256("voter1".encode()).hexdigest()
        assert d["voter_id"] == expected

    def test_to_dict_contains_required_fields(self):
        tx = Transaction("voter1", "Alice", "test_election")
        d = tx.to_dict()
        for field in ("voter_id", "candidate", "election_id", "timestamp", "vote_hash"):
            assert field in d

    def test_from_dict_roundtrip(self):
        tx = Transaction("voter2", "Bob", "election_x")
        d = tx.to_dict()
        tx2 = Transaction.from_dict(d)
        assert tx2.candidate == tx.candidate
        assert tx2.election_id == tx.election_id
        assert tx2.vote_hash == tx.vote_hash

    def test_unique_hashes_for_different_voters(self):
        tx1 = Transaction("voter_a", "Alice", "e1")
        time.sleep(0.001)
        tx2 = Transaction("voter_b", "Alice", "e1")
        assert tx1.vote_hash != tx2.vote_hash


# =====================================================================
# Merkle tree tests
# =====================================================================

class TestMerkle:
    def test_empty_list(self):
        root = compute_merkle_root([])
        assert root == hashlib.sha256(b"empty").hexdigest()

    def test_single_element(self):
        h = "abc123"
        root = compute_merkle_root([h])
        assert root == h

    def test_two_elements(self):
        a = "a" * 64
        b = "b" * 64
        expected = hash_pair(a, b)
        assert compute_merkle_root([a, b]) == expected

    def test_odd_number_of_elements(self):
        # Should not raise — duplicates last element
        hashes = ["a" * 64, "b" * 64, "c" * 64]
        root = compute_merkle_root(hashes)
        assert len(root) == 64

    def test_deterministic(self):
        hashes = ["a" * 64, "b" * 64, "c" * 64, "d" * 64]
        assert compute_merkle_root(hashes) == compute_merkle_root(hashes)


# =====================================================================
# Block tests
# =====================================================================

class TestBlock:
    def _make_tx(self, voter, candidate):
        return Transaction(voter, candidate, "test")

    def test_genesis_block_hash(self):
        b = Block(0, [], "0" * 64, difficulty=1)
        h = b.compute_hash()
        assert len(h) == 64

    def test_mine_satisfies_difficulty(self):
        tx = self._make_tx("v1", "Alice")
        b = Block(1, [tx], "0" * 64, difficulty=2)
        b.mine()
        assert b.hash.startswith("00")

    def test_to_dict_and_from_dict(self):
        tx = self._make_tx("v1", "Alice")
        b = Block(1, [tx], "0" * 64, difficulty=2)
        b.mine()
        d = b.to_dict()
        b2 = Block.from_dict(d)
        assert b2.index == b.index
        assert b2.hash == b.hash
        assert b2.nonce == b.nonce
        assert len(b2.transactions) == 1
        assert b2.transactions[0].candidate == "Alice"

    def test_merkle_root_changes_with_transactions(self):
        tx1 = self._make_tx("v1", "Alice")
        tx2 = self._make_tx("v2", "Bob")
        b1 = Block(1, [tx1], "0" * 64, difficulty=1)
        b2 = Block(1, [tx1, tx2], "0" * 64, difficulty=1)
        assert b1.merkle_root != b2.merkle_root


# =====================================================================
# Blockchain tests
# =====================================================================

class TestBlockchain:
    def _fresh_chain(self, difficulty=2):
        return Blockchain(difficulty=difficulty)

    def test_genesis_block_exists(self):
        bc = self._fresh_chain()
        assert len(bc.chain) == 1
        assert bc.chain[0].index == 0

    def test_add_transaction(self):
        bc = self._fresh_chain()
        tx = Transaction("voter1", "Alice", "e1")
        bc.add_transaction(tx)
        assert len(bc.pending_transactions) == 1

    def test_mine_pending_creates_block(self):
        bc = self._fresh_chain()
        tx = Transaction("voter1", "Alice", "e1")
        bc.add_transaction(tx)
        block = bc.mine_pending()
        assert block is not None
        assert len(bc.chain) == 2
        assert len(bc.pending_transactions) == 0

    def test_mine_empty_pending_returns_none(self):
        bc = self._fresh_chain()
        result = bc.mine_pending()
        assert result is None

    def test_chain_is_valid_after_mining(self):
        bc = self._fresh_chain()
        tx = Transaction("voter1", "Alice", "e1")
        bc.add_transaction(tx)
        bc.mine_pending()
        assert bc.is_valid_chain()

    def test_tamper_invalidates_chain(self):
        bc = self._fresh_chain()
        tx = Transaction("voter1", "Alice", "e1")
        bc.add_transaction(tx)
        bc.mine_pending()
        # Tamper with the stored hash directly — simulates an attacker
        # who modifies a block's hash without re-mining
        bc.chain[1].hash = "00" + "a" * 62  # plausible looking but wrong
        assert not bc.is_valid_chain()

    def test_get_results(self):
        bc = self._fresh_chain()
        for voter in ("v1", "v2", "v3"):
            bc.add_transaction(Transaction(voter, "Alice", "e1"))
        bc.add_transaction(Transaction("v4", "Bob", "e1"))
        bc.mine_pending()
        results = bc.get_results("e1")
        assert results.get("Alice") == 3
        assert results.get("Bob") == 1

    def test_find_vote(self):
        bc = self._fresh_chain()
        tx = Transaction("voter1", "Alice", "e1")
        bc.add_transaction(tx)
        bc.mine_pending()
        found = bc.find_vote(tx.vote_hash)
        assert found["found"] is True
        assert found["candidate"] == "Alice"

    def test_find_vote_not_found(self):
        bc = self._fresh_chain()
        result = bc.find_vote("a" * 64)
        assert result["found"] is False

    def test_save_and_load(self, tmp_path):
        bc = self._fresh_chain()
        tx = Transaction("voter1", "Alice", "e1")
        bc.add_transaction(tx)
        bc.mine_pending()
        path = str(tmp_path / "chain.json")
        bc.save(path)
        bc2 = Blockchain.load(path)
        assert len(bc2.chain) == len(bc.chain)
        assert bc2.chain[-1].hash == bc.chain[-1].hash
        assert bc2.is_valid_chain()

    def test_multiple_elections(self):
        bc = self._fresh_chain()
        bc.add_transaction(Transaction("v1", "Alice", "election_a"))
        bc.add_transaction(Transaction("v2", "Bob", "election_b"))
        bc.mine_pending()
        assert bc.get_results("election_a") == {"Alice": 1}
        assert bc.get_results("election_b") == {"Bob": 1}
