import os
import shutil

src_dir = r"d:\Repos\Poco\EDA"
dst_dir = r"C:\Users\Shadd\.gemini\antigravity-ide\brain\0f1bd67a-e6ce-4dc6-b535-b908b888cb0b"

os.makedirs(dst_dir, exist_ok=True)

copied = 0
for f in os.listdir(src_dir):
    if f.endswith(".png"):
        shutil.copy2(os.path.join(src_dir, f), os.path.join(dst_dir, f))
        copied += 1

print(f"Copied {copied} figures to artifact directory {dst_dir}!")
