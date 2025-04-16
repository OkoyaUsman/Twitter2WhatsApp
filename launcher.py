import os
import subprocess

PORT = 9222

profile_path = os.path.join(r"C:\browser_t2w")
command = [
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    f"--remote-debugging-port={PORT}",
    f"--user-data-dir={profile_path}",
]
process = subprocess.Popen(command, start_new_session=True)
print(f"Started Chrome with PID: {process.pid}")