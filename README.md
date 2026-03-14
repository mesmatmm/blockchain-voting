# BlockVote — Decentralized Voting System

A blockchain-based voting application built in Python. Votes are stored as permanent, tamper-proof records on a distributed blockchain network, making the results transparent and verifiable by anyone.

---

## What Is This?

Traditional voting systems rely on a central database controlled by one authority — which can be hacked, manipulated, or go offline. **BlockVote** replaces that central authority with a blockchain: a chain of records spread across multiple computers, where every change is visible to everyone and nothing can be altered in secret.

Think of it like this:
- Every vote is written in ink on a page
- Pages are grouped into a book (a block)
- Each book is chained to the previous one using a secret code
- Every participant holds an identical copy of the library
- To cheat, you'd need to rewrite every book in every library at the same time — which is practically impossible

---

## Key Features

| Feature | Description |
|---|---|
| **Blockchain Storage** | Votes are grouped into blocks, each cryptographically linked to the previous one |
| **Proof-of-Work Mining** | New blocks are only added after solving a computational puzzle (prevents fraud) |
| **Smart Contract Rules** | Automatic enforcement: no double voting, valid candidates only, time-restricted elections |
| **Vote Privacy** | Your Voter ID is SHA-256 hashed — it's never stored in plain text |
| **Receipt Verification** | Every voter gets a unique receipt hash to verify their vote was counted |
| **Multi-Node Network** | Run multiple nodes that automatically sync and reach consensus |
| **Live Results** | Real-time bar chart that updates every 10 seconds |
| **Audit Log** | Every system action is logged with timestamps |
| **GUI Interface** | Full desktop application — no command-line needed |

---

## How It Works — Step by Step

### Casting a Vote
1. You open the app and go to **Cast Vote**
2. Select the active election from the dropdown
3. Enter your **Voter ID** (it's masked and hashed — never revealed)
4. Click on your chosen candidate's card
5. Check the eligibility box and click **Submit Vote**
6. Your vote is sent to the node as a **transaction**
7. You receive a **receipt** containing your vote hash — save it!

### What Happens Behind the Scenes
```
Your Vote
    ↓
Smart Contract validates:
  • Is this voter ID new? (no double voting)
  • Is the candidate valid?
  • Is the election still active?
    ↓
Vote added to the Pending Transaction Pool
    ↓
Mining Process:
  • Transactions are grouped into a Block
  • Node solves a SHA-256 puzzle (Proof-of-Work)
  • Block gets a unique hash starting with "0000..."
    ↓
Block added to the Blockchain
    ↓
Block broadcast to all peer nodes
    ↓
All nodes update their copy — consensus reached
```

### Verifying Your Vote
1. Go to **Verify Vote**
2. Paste your vote hash from your receipt
3. The system searches every block in the chain
4. If found: shows you the block number, timestamp, and candidate
5. If not found: the vote is not yet mined (still pending)

---

## Technical Details

### Blockchain Structure

Each **Block** contains:
```
Block {
    index:          5
    timestamp:      2026-03-14 10:30:00
    transactions:   [ list of vote records ]
    merkle_root:    "7h8i9j..."   ← fingerprint of all transactions
    previous_hash:  "a78bc23..."  ← links to the previous block
    nonce:          23841         ← the mining solution
    hash:           "00004abc..." ← starts with 4 zeros (difficulty)
}
```

### Each Vote (Transaction) contains:
```json
{
  "voter_id":   "<sha256 hash of your ID>",
  "candidate":  "Mahmoud Esmat",
  "election_id": "election_2026",
  "timestamp":  1741947000.0,
  "vote_hash":  "abc123..."
}
```

### Merkle Tree
All vote hashes in a block are combined using a **Merkle Tree** — a binary tree of hashes. This creates a single root hash that acts as a fingerprint for all transactions. If even one vote is tampered with, the root hash changes, making tampering immediately detectable.

### Proof-of-Work (Mining)
To add a block, the node must find a `nonce` (a number) such that:
```
SHA-256(block_data + nonce) starts with "0000"
```
This requires thousands of attempts and takes real computation, making it economically infeasible to rewrite history.

### Consensus (Longest Chain Rule)
When multiple nodes disagree, the network adopts the **longest valid chain**. This ensures all nodes eventually agree on the same blockchain without any central coordinator.

---

## Project Structure

```
blockchain-voting/
│
├── blockchain/
│   ├── block.py           Block class — mining, hashing
│   ├── transaction.py     Vote transaction with SHA-256 privacy
│   ├── merkle.py          Merkle tree root computation
│   └── blockchain.py      Chain management — add, validate, save, query
│
├── smart_contract/
│   ├── voting_rules.py    Double-vote prevention, time windows, candidate checks
│   └── eligibility.py     Voter ID validation helpers
│
├── network/
│   ├── node.py            Flask REST API server (15 routes)
│   └── consensus.py       Longest-chain consensus, peer sync
│
├── audit/
│   ├── receipt.py         Vote receipt generation
│   ├── verification.py    Vote hash lookup
│   └── audit_log.py       Thread-safe event logging
│
├── gui/
│   ├── main_window.py     Main app window, sidebar navigation, status bar
│   ├── vote_page.py       Voting form with candidate cards
│   ├── results_page.py    Live bar chart results
│   ├── verify_page.py     Vote hash verification
│   ├── blockchain_viewer.py   Block explorer
│   ├── network_page.py    Peer management and sync
│   ├── admin_page.py      Create elections, mine, export
│   └── audit_page.py      Event log viewer
│
├── data/
│   └── config.json        Configuration (candidates, port, difficulty)
│
├── tests/                 61 unit tests (run with pytest)
├── requirements.txt
└── main.py                Entry point
```

---

## Getting Started

### Requirements

- Python 3.8 or higher
- pip

### Install Dependencies

```bash
pip install flask requests matplotlib
```

### Run the Application

```bash
# Start a single node (port 5000) + GUI
python main.py

# Start on a different port
python main.py --port 5001

# Start a second node connected to the first (simulates a network)
python main.py --port 5001 --peer http://localhost:5000

# Node only (no GUI) — useful for running multiple headless nodes
python main.py --node-only --port 5002

# GUI only (connect to an existing node)
python main.py --gui-only --port 5000
```

### Run Tests

```bash
python -m pytest tests/ -v
```

---

## Current Election Candidates

| # | Candidate |
|---|-----------|
| 1 | Mahmoud Esmat |
| 2 | Heba Mostafa |
| 3 | Ahmed Sabry |
| 4 | Ali Mahmoud |

To change candidates, edit `data/config.json` or use the **Admin** panel in the GUI.

---

## REST API Endpoints

The node exposes a REST API that the GUI uses internally:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/status` | Node health and stats |
| `GET`  | `/chain` | Full blockchain |
| `GET`  | `/pending` | Pending transactions |
| `POST` | `/vote` | Submit a vote |
| `POST` | `/mine` | Mine pending transactions |
| `GET`  | `/results` | Vote counts per candidate |
| `GET`  | `/elections` | List all elections |
| `POST` | `/create_election` | Create a new election |
| `GET`  | `/find_vote/<hash>` | Verify a vote |
| `GET`  | `/peers` | List connected peers |
| `POST` | `/register_peer` | Add a peer node |
| `POST` | `/sync` | Trigger consensus sync |
| `GET`  | `/audit_log` | Recent audit events |

---

## Security Properties

| Property | How it's achieved |
|---|---|
| **Immutability** | Changing one block invalidates every block after it |
| **Transparency** | The full blockchain is publicly readable |
| **Privacy** | Voter IDs are stored as SHA-256 hashes, not plain text |
| **No double voting** | Smart contract tracks all hashed voter IDs |
| **Tamper detection** | Hash chains and Merkle trees make alteration detectable |
| **Verifiability** | Every voter gets a unique receipt hash to verify their vote |
| **Decentralization** | No single point of failure — any node can serve the chain |

---

## Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.13 | Core language |
| Flask | REST API for each blockchain node |
| hashlib | SHA-256 hashing (blocks, transactions, voter IDs) |
| Tkinter | Desktop GUI |
| matplotlib | Live results bar chart |
| requests | HTTP communication between nodes |
| SQLite (via json) | Blockchain persistence |
| threading | Background tasks (mining, peer sync, UI refresh) |

---

## Educational Value

This project demonstrates:
- How blockchains store data securely using hash chains
- How Proof-of-Work prevents spam and fraud
- How Merkle trees efficiently verify transaction integrity
- How smart contracts enforce rules automatically
- How distributed systems reach consensus without a central server
- How privacy and transparency can coexist (hashed IDs + public ledger)

---

*Built with Python — for learning, research, and demonstration of blockchain principles.*
