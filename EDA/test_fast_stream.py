import requests
import json
import time

url = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/train.jsonl"
print("Testing direct streaming from URL:", url)

t0 = time.time()
resp = requests.get(url, stream=True, timeout=30)
resp.raise_for_status()

count = 0
sample_rows = []
for line in resp.iter_lines():
    if not line:
        continue
    row = json.loads(line)
    sample_rows.append(row)
    count += 1
    if count % 10000 == 0:
        print(f"Read {count} rows in {time.time() - t0:.2f}s...")
    if count >= 50000:
        break

t1 = time.time()
print(f"DONE! Read {count} rows in {t1 - t0:.2f} seconds! ({count/(t1-t0):.1f} rows/sec)")
print("Keys:", list(sample_rows[0].keys()))
