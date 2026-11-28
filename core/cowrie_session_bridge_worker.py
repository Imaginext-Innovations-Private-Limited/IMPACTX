import time
import traceback

from core.cowrie_session_bridge import process_closed_sessions

POLL_INTERVAL = 2

def main():
    print("Universal AI Honeypot - SSH Session Bridge Worker")
    print("Monitoring Cowrie sessions...")

    while True:
        try:
            count = process_closed_sessions()

            if count:
                print(f"[BRIDGE] Evaluated {count} closed SSH session(s).")

        except Exception as error:
            print(f"[BRIDGE ERROR] {error}")
            traceback.print_exc()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSSH Session Bridge Worker stopped.")
