"""
SIMS Phase 1 — Environment Validator
Run this script to verify your local setup before proceeding to Phase 2.

Usage:
  python scripts/validate_env.py
"""

import sys
import os
import platform

def main():
    print("=" * 50)
    print("🛡️  SIMS Environment Validator (Phase 1) 🛡️")
    print("=" * 50)

    # 1. Check Python version
    py_version = platform.python_version()
    print(f"[1] Python Version: {py_version}")
    if not py_version.startswith("3.11"):
        print("    ⚠️  Warning: Blueprint recommends Python 3.11")
    else:
        print("    ✅  Python 3.11 detected.")

    # 2. Check critical imports
    print("\n[2] Checking ML/Backend Dependencies...")
    imports_to_test = [
        "fastapi",
        "uvicorn",
        "tensorflow",
        "transformers",
        "pandas",
        "motor",
        "loguru"
    ]
    all_imports_passed = True
    for mod in imports_to_test:
        try:
            __import__(mod)
            print(f"    ✅  {mod} installed.")
        except ImportError:
            print(f"    ❌  Missing dependency: {mod}")
            all_imports_passed = False

    if not all_imports_passed:
        print("\n❌  Some dependencies failed. Run: pip install -r requirements.txt")
        sys.exit(1)

    # 3. Check Data Directories
    print("\n[3] Checking Directory Structure...")
    dirs_to_check = [
        "data/raw",
        "data/processed",
        "data/models",
    ]
    for d in dirs_to_check:
        path = os.path.join(os.path.dirname(__file__), "..", d)
        if os.path.exists(path):
            print(f"    ✅  Found {d}")
        else:
            print(f"    ❌  Missing directory: {d}")

    # 4. Check Environment File
    print("\n[4] Checking Environment Variables...")
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        print("    ✅  Found .env file")
        # Quick parse to check VT key
        with open(env_path, "r") as f:
            content = f.read()
            if "your_virustotal_api_key_here" in content:
                print("    ⚠️  Warning: VirusTotal API key not configured in .env")
    else:
        print("    ⚠️  Warning: .env file missing. Copy .env.example to .env")

    print("\n" + "=" * 50)
    print("🎉 Environment Validation Complete.")
    print("=" * 50)

if __name__ == "__main__":
    main()
