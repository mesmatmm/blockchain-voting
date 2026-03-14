"""
Seed script — generates 142 votes of realistic dummy data for BlockVote demo.
Run once: python seed_data.py
"""
import sys, os, hashlib, time, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blockchain.block import Block
from blockchain.transaction import Transaction
from blockchain.blockchain import Blockchain
from smart_contract.voting_rules import VotingContract

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BC_FILE  = os.path.join(DATA_DIR, "blockchain_5000.json")
CT_FILE  = os.path.join(DATA_DIR, "contracts_5000.json")
LOG_FILE = os.path.join(DATA_DIR, "audit.log")

ELECTION_ID = "election_2026"
CANDIDATES  = ["Mahmoud Esmat", "Heba Mostafa", "Ahmed Sabry", "Ali Mahmoud"]
DIFFICULTY  = 3   # lower difficulty for fast seeding; node re-mines at 4
BLOCK_SIZE  = 8   # votes per block  → 142 / 8 = ~18 blocks

now = time.time()

# ── Generate 142 votes spread over 5 days ─────────────────────────────────────
# Target distribution:
#   Mahmoud Esmat : 48  (33.8%)
#   Heba Mostafa  : 36  (25.4%)
#   Ahmed Sabry   : 35  (24.6%)
#   Ali Mahmoud   : 23  (16.2%)
#   Total         : 142

# Pattern repeated across 5 days — weighted toward Mahmoud Esmat
PATTERN = [
    "Mahmoud Esmat", "Heba Mostafa",   "Ahmed Sabry",  "Mahmoud Esmat",
    "Ali Mahmoud",   "Mahmoud Esmat",  "Heba Mostafa", "Ahmed Sabry",
    "Mahmoud Esmat", "Ahmed Sabry",    "Heba Mostafa", "Ali Mahmoud",
    "Mahmoud Esmat", "Heba Mostafa",   "Ahmed Sabry",  "Mahmoud Esmat",
    "Ali Mahmoud",   "Mahmoud Esmat",  "Heba Mostafa", "Ahmed Sabry",
    "Mahmoud Esmat", "Ali Mahmoud",    "Heba Mostafa", "Mahmoud Esmat",
    "Ahmed Sabry",   "Heba Mostafa",   "Mahmoud Esmat","Ali Mahmoud",
    "Ahmed Sabry",   "Mahmoud Esmat",
]

# Build votes list: spread 142 votes over 5 days with realistic hour spacing
VOTES = []
voter_num = 1
day_slots = [
    # (day_offset_in_seconds, votes_this_day)
    (86400 * 5, 18),   # 5 days ago
    (86400 * 4, 22),   # 4 days ago
    (86400 * 3, 30),   # 3 days ago (peak)
    (86400 * 2, 28),   # 2 days ago
    (86400 * 1, 25),   # yesterday
    (0,         19),   # today
]

pattern_idx = 0
for day_offset, count in day_slots:
    # Spread votes across waking hours: 07:00 to 22:00 (54000 seconds)
    # Add slight randomness by spacing votes evenly then offsetting
    step = 54000 // count
    for i in range(count):
        hour_offset = 7 * 3600 + i * step + (voter_num * 37 % step)
        seconds_ago = day_offset + 54000 - hour_offset
        candidate   = PATTERN[pattern_idx % len(PATTERN)]
        voter_id    = f"voter_{voter_num:03d}"
        VOTES.append((voter_id, candidate, int(seconds_ago)))
        voter_num  += 1
        pattern_idx += 1

assert len(VOTES) == 142, f"Expected 142 votes, got {len(VOTES)}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_tx(plain_id, candidate, seconds_ago):
    t = Transaction.__new__(Transaction)
    t.election_id = ELECTION_ID
    t.candidate   = candidate
    t.timestamp   = now - seconds_ago
    t.voter_id    = hashlib.sha256(plain_id.encode()).hexdigest()
    raw = f"{plain_id}{candidate}{ELECTION_ID}{t.timestamp}"
    t.vote_hash   = hashlib.sha256(raw.encode()).hexdigest()
    return t


def mine_block(index, transactions, previous_hash, timestamp):
    block = Block.__new__(Block)
    block.index         = index
    block.transactions  = transactions
    block.previous_hash = previous_hash
    block.difficulty    = DIFFICULTY
    block.timestamp     = timestamp
    block.merkle_root   = block._compute_merkle()
    block.nonce         = 0
    block.hash          = block.compute_hash()
    block.mine(DIFFICULTY)
    return block


def ts_fmt(offset_secs):
    return datetime.datetime.fromtimestamp(now - offset_secs).strftime("%Y-%m-%d %H:%M:%S")


# ── Build blockchain ──────────────────────────────────────────────────────────
print(f"Building blockchain: {len(VOTES)} votes, block size {BLOCK_SIZE}...")

genesis = Block(0, [], "0" * 64, DIFFICULTY)
genesis.timestamp = now - 86400 * 6
genesis.hash = genesis.compute_hash()
chain = [genesis]

groups = [VOTES[i:i+BLOCK_SIZE] for i in range(0, len(VOTES), BLOCK_SIZE)]
vote_hashes = []

for g_idx, group in enumerate(groups):
    txs = [make_tx(pid, cand, secs) for pid, cand, secs in group]
    for tx in txs:
        vote_hashes.append(tx.vote_hash)

    # Block timestamp = right after the earliest vote in this group
    earliest_secs = max(s for _, _, s in group)
    block_ts = now - earliest_secs + 180   # ~3 min after first vote

    print(f"  Block #{len(chain):>2}  ({len(txs)} votes)...", end=" ", flush=True)
    blk = mine_block(len(chain), txs, chain[-1].hash, block_ts)
    chain.append(blk)
    print(f"nonce={blk.nonce:<6}  {blk.hash[:20]}...")

# Validate
bc = Blockchain.__new__(Blockchain)
bc.difficulty = DIFFICULTY
bc.pending_transactions = []
bc.chain = chain

assert bc.is_valid_chain(), "ERROR: chain validation failed!"
bc.save(BC_FILE)
print(f"\nChain valid: True  |  {len(chain)} blocks  |  {len(VOTES)} votes")

# ── Smart contract ────────────────────────────────────────────────────────────
contract = VotingContract(
    candidates=CANDIDATES,
    election_id=ELECTION_ID,
    start_time=now - 86400 * 6,
    end_time=None,
    min_age=18
)
for plain_id, _, _ in VOTES:
    contract.voted_hashes.add(hashlib.sha256(plain_id.encode()).hexdigest())

with open(CT_FILE, "w") as f:
    json.dump({ELECTION_ID: contract.to_dict()}, f, indent=2)
print(f"Contract saved: {len(VOTES)} registered voters")

# ── Audit log ─────────────────────────────────────────────────────────────────
log_lines = [
    f"[{ts_fmt(86400*6+300)}] [STARTUP] New blockchain created",
    f"[{ts_fmt(86400*6+290)}] [ELECTION] Election '{ELECTION_ID}' created | candidates: {CANDIDATES}",
    f"[{ts_fmt(86400*6+200)}] [PEER] Node registered: http://localhost:5001",
    f"[{ts_fmt(86400*6+190)}] [PEER] Node registered: http://localhost:5002",
    f"[{ts_fmt(86400*6+180)}] [ADMIN] Auto-mine enabled (interval=60s)",
]

# Add vote + mine entries for each block
for g_idx, (blk, group) in enumerate(zip(chain[1:], groups)):
    earliest = max(s for _, _, s in group)
    for p_idx, (pid, cand, secs) in enumerate(group):
        vh = vote_hashes[g_idx * BLOCK_SIZE + p_idx]
        log_lines.append(
            f"[{ts_fmt(secs)}] [VOTE] Election={ELECTION_ID} | Candidate={cand} | Hash={vh[:32]}..."
        )
    log_lines.append(
        f"[{ts_fmt(earliest - 200)}] [MINE] Block #{blk.index} mined | "
        f"Hash={blk.hash[:28]}... | Txs={len(group)} | Nonce={blk.nonce}"
    )
    log_lines.append(
        f"[{ts_fmt(earliest - 190)}] [CONSENSUS] Chain synced with peers"
    )

log_lines.append(f"[{ts_fmt(60)}] [CONSENSUS] All nodes in agreement — chain length {len(chain)}")

# Sort chronologically
log_lines.sort()

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines) + "\n")
print(f"Audit log: {len(log_lines)} entries")

# ── Tally ─────────────────────────────────────────────────────────────────────
results = bc.get_results(ELECTION_ID)
total = sum(results.values())
print(f"\nFinal Vote Tally ({total} total):")
for name, count in sorted(results.items(), key=lambda x: -x[1]):
    pct = count / total * 100
    bar = "#" * (count // 2)
    print(f"  {name:<22} {count:>3} votes  ({pct:.1f}%)  {bar}")

print(f"\nSample vote hash (use in Verify page):")
print(f"  {vote_hashes[0]}")
print("\nDone! Run: python main.py")
