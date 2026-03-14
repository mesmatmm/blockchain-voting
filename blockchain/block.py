import hashlib
import json
import time
from blockchain.merkle import compute_merkle_root


class Block:
    def __init__(self, index, transactions, previous_hash, difficulty=4):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions  # list of Transaction objects
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.nonce = 0
        self.merkle_root = self._compute_merkle()
        self.hash = self.compute_hash()

    def _compute_merkle(self):
        hashes = [t.vote_hash for t in self.transactions]
        return compute_merkle_root(hashes)

    def compute_hash(self):
        block_str = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [t.vote_hash for t in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root
        }, sort_keys=True)
        return hashlib.sha256(block_str.encode()).hexdigest()

    def mine(self, difficulty=None):
        d = difficulty or self.difficulty
        target = "0" * d
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()
        return self.hash

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [t.to_dict() for t in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root,
            "hash": self.hash,
            "difficulty": self.difficulty
        }

    @classmethod
    def from_dict(cls, d):
        from blockchain.transaction import Transaction
        b = cls.__new__(cls)
        b.index = d["index"]
        b.timestamp = d["timestamp"]
        b.transactions = [Transaction.from_dict(t) for t in d["transactions"]]
        b.previous_hash = d["previous_hash"]
        b.nonce = d["nonce"]
        b.merkle_root = d["merkle_root"]
        b.hash = d["hash"]
        b.difficulty = d.get("difficulty", 4)
        return b
