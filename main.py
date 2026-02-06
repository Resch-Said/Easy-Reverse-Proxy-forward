import sys

from app import create_app
from app.services.persistence import restore_persistent_rules


def main():
    if not sys.platform.startswith("linux"):
        print("Only runs on Linux.")
        sys.exit(1)

    # Restore rules at startup, not just at the first request
    restore_persistent_rules()

    app = create_app()
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
