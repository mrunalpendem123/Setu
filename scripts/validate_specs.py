import json
import os
import sys

SCHEMA_DIR = "spec/2026-02-24/json-schema"


def main() -> int:
    if not os.path.isdir(SCHEMA_DIR):
        print(f"Missing schema dir: {SCHEMA_DIR}")
        return 1

    for name in os.listdir(SCHEMA_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(SCHEMA_DIR, name)
        with open(path, "r", encoding="utf-8") as handle:
            try:
                json.load(handle)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON schema {name}: {exc}")
                return 1

    print("Specs validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
