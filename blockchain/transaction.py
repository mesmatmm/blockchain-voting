import hashlib
import json
import time


class Transaction:
    def __init__(self, voter_id, candidate, election_id="default"):
        self.voter_id = voter_id
        self.candidate = candidate
        self.election_id = election_id
        self.timestamp = time.time()
        self.vote_hash = self._compute_hash()

    def _compute_hash(self):
        data = f"{self.voter_id}{self.candidate}{self.election_id}{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        return {
            "voter_id": hashlib.sha256(self.voter_id.encode()).hexdigest(),  # privacy: hash voter_id
            "candidate": self.candidate,
            "election_id": self.election_id,
            "timestamp": self.timestamp,
            "vote_hash": self.vote_hash
        }

    @classmethod
    def from_dict(cls, d):
        t = cls.__new__(cls)
        t.voter_id = d["voter_id"]
        t.candidate = d["candidate"]
        t.election_id = d["election_id"]
        t.timestamp = d["timestamp"]
        t.vote_hash = d["vote_hash"]
        return t
