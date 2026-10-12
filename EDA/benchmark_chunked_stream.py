import orjson
import requests
import time

url = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/validation.jsonl"
print("Testing 1MB chunked byte stream with orjson...", flush=True)

t0 = time.time()
resp = requests.get(url, stream=True, timeout=60)
resp.raise_for_status()

count = 0
buffer = b""
for chunk in resp.iter_content(chunk_size=1024 * 1024):
    buffer += chunk
    lines = buffer.split(b"\n")
    buffer = lines.pop()
    for line in lines:
        if not line:
            continue
        row = orjson.loads(line)
        count += 1
    if count >= 100000:
        break

t1 = time.time()
print(f"Processed {count:,} rows in {t1 - t0:.2f} seconds ({count/(t1-t0):.1f} rows/sec)!", flush=True)
