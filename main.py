#!/usr/bin/env python3
"""
Decentralized Voting System — Main Entry Point
Usage:
  python main.py               # Start node on port 5000 + GUI
  python main.py --port 5001   # Start node on different port
  python main.py --node-only   # Start node without GUI
  python main.py --gui-only    # Start GUI only (connect to existing node)
"""
import argparse
import sys
import threading
import time


def main():
    parser = argparse.ArgumentParser(
        description="Decentralized Blockchain Voting System"
    )
    parser.add_argument("--port", type=int, default=5000, help="Node port (default: 5000)")
    parser.add_argument("--peer", type=str, default=None, help="Known peer URL to connect to")
    parser.add_argument("--node-only", action="store_true", help="Start the node without launching the GUI")
    parser.add_argument("--gui-only", action="store_true", help="Launch GUI only (connect to an existing node)")
    args = parser.parse_args()

    if args.node_only and args.gui_only:
        print("Error: --node-only and --gui-only are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    node_thread = None

    # ------------------------------------------------------------------ #
    # Start the Flask node in a background daemon thread
    # ------------------------------------------------------------------ #
    if not args.gui_only:
        try:
            from network.node import create_app
            flask_app = create_app(port=args.port, peer=args.peer)

            def run_flask():
                flask_app.run(
                    host="0.0.0.0",
                    port=args.port,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )

            node_thread = threading.Thread(target=run_flask, daemon=True, name="flask-node")
            node_thread.start()
            print(f"[BlockVote] Node started on http://0.0.0.0:{args.port}")
            # Give Flask a moment to bind its socket before the GUI tries to connect
            time.sleep(1.2)
        except Exception as exc:
            print(f"[BlockVote] Failed to start node: {exc}", file=sys.stderr)
            if args.node_only:
                sys.exit(1)
            # In combined mode, carry on — GUI will show "offline" banner

    # ------------------------------------------------------------------ #
    # Launch the Tkinter GUI (main thread)
    # ------------------------------------------------------------------ #
    if not args.node_only:
        try:
            from gui.main_window import VotingApp
            app = VotingApp(node_url=f"http://localhost:{args.port}")
            print(f"[BlockVote] GUI connecting to http://localhost:{args.port}")
            app.run()
        except ImportError as exc:
            print(f"[BlockVote] GUI import error: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        # Node-only mode: keep the main thread alive
        print("[BlockVote] Running in node-only mode. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[BlockVote] Shutting down.")


if __name__ == "__main__":
    main()
