import os
import time
import csv
import threading

_lock = threading.Lock()
_log_path = os.path.join(os.path.dirname(__file__), "..", "data", "audit.log")


def _get_log_path():
    return os.path.abspath(_log_path)


def log_event(event_type, details):
    """Append a timestamped event to the audit log."""
    path = _get_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    entry = f"[{timestamp}] [{event_type}] {details}\n"
    with _lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)


def get_recent(n=50):
    """Return the last n log entries as a list of strings."""
    path = _get_log_path()
    if not os.path.exists(path):
        return []
    with _lock:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    return [line.rstrip("\n") for line in lines[-n:]]


def get_all():
    """Return all log entries."""
    path = _get_log_path()
    if not os.path.exists(path):
        return []
    with _lock:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    return [line.rstrip("\n") for line in lines]


def filter_events(event_type):
    """Return entries matching a specific event_type."""
    all_entries = get_all()
    tag = f"[{event_type}]"
    return [e for e in all_entries if tag in e]


def export_csv(path):
    """Export the audit log to a CSV file."""
    entries = get_all()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Event Type", "Details"])
        for entry in entries:
            # Parse: [timestamp] [event_type] details
            # e.g. "[2026-03-14 07:00:00] [VOTE] Candidate=Alice"
            try:
                ts_end = entry.index("]")
                timestamp = entry[1:ts_end]
                # After ts_end: "] [event_type] details"
                # Skip past "] [" → ts_end + 2 lands on first char of event_type bracket "[..."
                bracket_start = ts_end + 2  # points at '['
                et_end = entry.index("]", bracket_start)
                event_type = entry[bracket_start + 1:et_end]
                details = entry[et_end + 2:]  # skip '] '
                writer.writerow([timestamp, event_type, details])
            except (ValueError, IndexError):
                writer.writerow(["", "", entry])
