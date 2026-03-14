import time
import hashlib


class VotingContract:
    def __init__(self, candidates, election_id, start_time=None, end_time=None, min_age=18):
        self.candidates = candidates
        self.election_id = election_id
        self.start_time = start_time or time.time()
        self.end_time = end_time  # None = no end
        self.min_age = min_age
        self.voted_hashes = set()  # hashed voter IDs who voted

    def validate(self, voter_id, candidate):
        """Returns (True, None) or (False, reason_string)"""
        hashed = hashlib.sha256(voter_id.encode()).hexdigest()

        if hashed in self.voted_hashes:
            return False, "You have already voted in this election."

        if candidate not in self.candidates:
            return False, f"Invalid candidate. Choose from: {', '.join(self.candidates)}"

        now = time.time()
        if now < self.start_time:
            return False, "Election has not started yet."

        if self.end_time and now > self.end_time:
            return False, "Election has ended."

        return True, None

    def record_vote(self, voter_id):
        hashed = hashlib.sha256(voter_id.encode()).hexdigest()
        self.voted_hashes.add(hashed)

    def is_active(self):
        now = time.time()
        if now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True

    def time_remaining(self):
        if not self.end_time:
            return None
        remaining = self.end_time - time.time()
        return max(0, remaining)

    def to_dict(self):
        return {
            "candidates": self.candidates,
            "election_id": self.election_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "min_age": self.min_age,
            "voted_count": len(self.voted_hashes),
            "voted_hashes": list(self.voted_hashes)
        }

    @classmethod
    def from_dict(cls, d):
        c = cls(
            d["candidates"],
            d["election_id"],
            d["start_time"],
            d.get("end_time"),
            d.get("min_age", 18)
        )
        c.voted_hashes = set(d.get("voted_hashes", []))
        return c
