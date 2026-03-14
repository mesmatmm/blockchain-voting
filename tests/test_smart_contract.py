"""
Tests for smart contract (voting rules & eligibility).
Run with:  python -m pytest tests/ -v
"""
import sys
import os
import time
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from smart_contract.voting_rules import VotingContract
from smart_contract.eligibility import is_valid_voter_id, hash_voter_id, check_eligibility


# =====================================================================
# VotingContract tests
# =====================================================================

class TestVotingContract:
    def _make_contract(self, end_offset=3600):
        return VotingContract(
            candidates=["Alice", "Bob", "Charlie"],
            election_id="test_election",
            start_time=time.time() - 1,
            end_time=time.time() + end_offset
        )

    def test_valid_vote(self):
        c = self._make_contract()
        ok, reason = c.validate("voter1", "Alice")
        assert ok is True
        assert reason is None

    def test_invalid_candidate(self):
        c = self._make_contract()
        ok, reason = c.validate("voter1", "Unknown Candidate")
        assert ok is False
        assert "Invalid candidate" in reason

    def test_double_vote_rejected(self):
        c = self._make_contract()
        ok, _ = c.validate("voter1", "Alice")
        assert ok is True
        c.record_vote("voter1")
        ok2, reason2 = c.validate("voter1", "Bob")
        assert ok2 is False
        assert "already voted" in reason2

    def test_election_not_started(self):
        c = VotingContract(
            candidates=["Alice"],
            election_id="future",
            start_time=time.time() + 9999,
            end_time=time.time() + 99999
        )
        ok, reason = c.validate("voter1", "Alice")
        assert ok is False
        assert "not started" in reason

    def test_election_ended(self):
        c = VotingContract(
            candidates=["Alice"],
            election_id="past",
            start_time=time.time() - 1000,
            end_time=time.time() - 1
        )
        ok, reason = c.validate("voter1", "Alice")
        assert ok is False
        assert "ended" in reason

    def test_no_end_time(self):
        c = VotingContract(
            candidates=["Alice"],
            election_id="open",
            start_time=time.time() - 1,
            end_time=None
        )
        ok, _ = c.validate("voter1", "Alice")
        assert ok is True

    def test_is_active(self):
        c = self._make_contract()
        assert c.is_active() is True

    def test_is_active_ended(self):
        c = self._make_contract(end_offset=-1)
        assert c.is_active() is False

    def test_time_remaining(self):
        c = self._make_contract(end_offset=3600)
        remaining = c.time_remaining()
        assert remaining is not None
        assert 3590 < remaining <= 3600

    def test_time_remaining_no_end(self):
        c = VotingContract(["Alice"], "open", end_time=None)
        assert c.time_remaining() is None

    def test_record_vote_prevents_duplicate(self):
        c = self._make_contract()
        c.record_vote("voter1")
        hashed = hashlib.sha256("voter1".encode()).hexdigest()
        assert hashed in c.voted_hashes

    def test_to_dict_and_from_dict(self):
        c = self._make_contract()
        c.record_vote("voter1")
        d = c.to_dict()
        c2 = VotingContract.from_dict(d)
        assert c2.candidates == c.candidates
        assert c2.election_id == c.election_id
        assert c2.voted_hashes == c.voted_hashes

    def test_different_voter_ids_are_independent(self):
        c = self._make_contract()
        c.record_vote("voter1")
        ok, _ = c.validate("voter2", "Alice")
        assert ok is True


# =====================================================================
# Eligibility helper tests
# =====================================================================

class TestEligibility:
    def test_valid_voter_id(self):
        ok, reason = is_valid_voter_id("voter123")
        assert ok is True
        assert reason is None

    def test_empty_voter_id(self):
        ok, reason = is_valid_voter_id("")
        assert ok is False

    def test_short_voter_id(self):
        ok, reason = is_valid_voter_id("abc")
        assert ok is False

    def test_none_voter_id(self):
        ok, reason = is_valid_voter_id(None)
        assert ok is False

    def test_hash_voter_id_is_sha256(self):
        hashed = hash_voter_id("voter1")
        expected = hashlib.sha256("voter1".encode()).hexdigest()
        assert hashed == expected

    def test_hash_strips_whitespace(self):
        assert hash_voter_id("voter1") == hash_voter_id("  voter1  ")

    def test_check_eligibility_ok(self):
        c = VotingContract(["Alice"], "e1", time.time() - 1, time.time() + 3600)
        ok, reason = check_eligibility("voter1", c)
        assert ok is True

    def test_check_eligibility_already_voted(self):
        c = VotingContract(["Alice"], "e1", time.time() - 1, time.time() + 3600)
        c.record_vote("voter1")
        ok, reason = check_eligibility("voter1", c)
        assert ok is False
        assert "already" in reason.lower()

    def test_check_eligibility_inactive_election(self):
        c = VotingContract(["Alice"], "e1", time.time() - 100, time.time() - 1)
        ok, reason = check_eligibility("voter1", c)
        assert ok is False
