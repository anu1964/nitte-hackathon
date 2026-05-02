# scan_prompts.py
# Scans all .txt and .py files in repo for prompt injection attacks
# Runs automatically on every push to GitHub

import os
import requests
import sys

API_URL = os.environ.get("GUARDIAN_API", "http://localhost:8000")

# ── Find all prompt-like strings in the repo ──────────────────────────────────
SCAN_EXTENSIONS = [".txt", ".py", ".json", ".md"]
SKIP_FOLDERS = [".git", ".venv", "venv", "__pycache__", ".github"]

def find_prompts(root="."):
    prompts = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip unwanted folders
        dirnames[:] = [d for d in dirnames if d not in SKIP_FOLDERS]
        for filename in filenames:
            if any(filename.endswith(ext) for ext in SCAN_EXTENSIONS):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    for i, line in enumerate(lines):
                        line = line.strip()
                        # Only scan lines that look like prompts (strings/comments)
                        if len(line) > 20 and any(
                            kw in line.lower() for kw in 
                            ["ignore", "forget", "pretend", "you are", 
                             "disregard", "override", "bypass", "jailbreak",
                             "system prompt", "instructions"]
                        ):
                            prompts.append({
                                "file": filepath,
                                "line": i + 1,
                                "text": line[:200]
                            })
                except Exception:
                    pass
    return prompts

# ── Scan each prompt ──────────────────────────────────────────────────────────
def scan_prompts(prompts):
    attacks_found = []
    
    for p in prompts:
        try:
            response = requests.post(
                f"{API_URL}/analyze",
                json={"prompt": p["text"], "rephrase": False},
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if result["blocked"]:
                    attacks_found.append({
                        "file":       p["file"],
                        "line":       p["line"],
                        "text":       p["text"][:80],
                        "category":   result["category"],
                        "severity":   result["severity"],
                        "confidence": result["confidence"]
                    })
        except Exception as e:
            print(f"  Warning: Could not scan line {p['line']} in {p['file']}: {e}")
    
    return attacks_found

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🛡️  Safe Prompt Guardian — Scanning repository...\n")
    
    prompts = find_prompts(".")
    print(f"   Found {len(prompts)} prompt-like strings to scan.")
    
    if not prompts:
        print("   ✅ Nothing to scan. All clear!")
        sys.exit(0)
    
    attacks = scan_prompts(prompts)
    
    print(f"\n   Results:")
    print(f"   Scanned:  {len(prompts)} strings")
    print(f"   Blocked:  {len(attacks)} potential attacks\n")
    
    if attacks:
        print("🚨 POTENTIAL PROMPT INJECTION FOUND:\n")
        for a in attacks:
            print(f"   File:       {a['file']}:{a['line']}")
            print(f"   Text:       {a['text']}")
            print(f"   Category:   {a['category']}")
            print(f"   Severity:   {a['severity']}")
            print(f"   Confidence: {a['confidence']*100:.1f}%")
            print()
        # Don't fail the build — just warn
        # Change to sys.exit(1) if you want to BLOCK the push
        print("⚠️  Warning: Prompt injection patterns detected in codebase.")
        print("   Review the above findings before deploying to production.")
        sys.exit(0)
    else:
        print("✅ No prompt injection attacks detected. Safe to deploy!")
        sys.exit(0)