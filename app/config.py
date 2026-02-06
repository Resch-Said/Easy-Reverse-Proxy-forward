import os

# Path to persistence file
# Use /app/data for Docker volume persistence, fallback to script directory
DATA_DIR = (
    os.environ.get("DATA_DIR", "/app/data")
    if os.path.exists("/app/data")
    else os.path.dirname(os.path.realpath(__file__))
)
RULES_FILE = os.path.join(DATA_DIR, "rules.json")


def ensure_data_dir():
    # Ensure DATA_DIR exists and is writable
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        # Test if we can write to the directory
        test_file = os.path.join(DATA_DIR, ".write_test")
        with open(test_file, "w") as handle:
            handle.write("test")
        os.remove(test_file)
        print(f"✓ DATA_DIR is writable: {DATA_DIR}")
    except Exception as exc:
        print(f"✗ WARNING: DATA_DIR may not be writable: {DATA_DIR}")
        print(f"  Error: {exc}")
