import json
import os
import time
from blockchain.block import Block
from blockchain.transaction import Transaction


class Blockchain:
    def __init__(self, difficulty=4):
        self.difficulty = difficulty
        self.chain = []
        self.pending_transactions = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(
            index=0,
            transactions=[],
            previous_hash="0" * 64,
            difficulty=self.difficulty
        )
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_transaction(self, tx):
        """Add a Transaction object to the pending pool."""
        self.pending_transactions.append(tx)
        return True

    def mine_pending(self, miner_id="system"):
        """Mine a block with all pending transactions. Returns the new block or None."""
        if not self.pending_transactions:
            return None

        block = Block(
            index=len(self.chain),
            transactions=list(self.pending_transactions),
            previous_hash=self.last_block.hash,
            difficulty=self.difficulty
        )
        block.mine()
        self.chain.append(block)
        self.pending_transactions = []
        return block

    def is_valid_chain(self):
        """Validate the entire chain."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Check hash integrity
            if current.hash != current.compute_hash():
                return False

            # Check chain linkage
            if current.previous_hash != previous.hash:
                return False

            # Check proof of work
            if not current.hash.startswith("0" * current.difficulty):
                return False

        return True

    def get_results(self, election_id="default"):
        """Count votes per candidate for a given election."""
        counts = {}
        for block in self.chain:
            for tx in block.transactions:
                if tx.election_id == election_id:
                    counts[tx.candidate] = counts.get(tx.candidate, 0) + 1
        return counts

    def find_vote(self, vote_hash):
        """Locate a vote by its hash. Returns block info or None."""
        for block in self.chain:
            for tx in block.transactions:
                if tx.vote_hash == vote_hash:
                    return {
                        "found": True,
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "candidate": tx.candidate,
                        "election_id": tx.election_id,
                        "timestamp": tx.timestamp
                    }
        return {"found": False}

    def get_all_elections(self):
        """Return a set of all election IDs in the chain and pending."""
        elections = set()
        for block in self.chain:
            for tx in block.transactions:
                elections.add(tx.election_id)
        for tx in self.pending_transactions:
            elections.add(tx.election_id)
        return list(elections)

    def to_dict(self):
        return {
            "length": len(self.chain),
            "difficulty": self.difficulty,
            "chain": [b.to_dict() for b in self.chain]
        }

    @classmethod
    def from_dict(cls, d):
        bc = cls.__new__(cls)
        bc.difficulty = d.get("difficulty", 4)
        bc.pending_transactions = []
        bc.chain = [Block.from_dict(b) for b in d["chain"]]
        return bc

    def save(self, path):
        """Save blockchain to a JSON file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path):
        """Load blockchain from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
