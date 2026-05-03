import subprocess, sys, os, time

procs = []

def start(script, port=None):
    cmd = [sys.executable, script]
    p = subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    procs.append(p)
    print(f"  Started {script}" + (f" on port {port}" if port else ""))
    time.sleep(2)

print("\n Starting Safe Prompt Guardian...\n")

start("api.py",            port=8000)
start("vulnerable_bot.py", port=7861)
start("protected_bot.py",  port=7862)
start("app.py",            port=7860)

print("""
 All services running:
   Main dashboard   → http://localhost:7860
   Vulnerable bot   → http://localhost:7861
   Protected bot    → http://localhost:7862

 Press Ctrl+C to stop everything.
""")

try:
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    print("\n Shutting down...")
    for p in procs:
        p.terminate()