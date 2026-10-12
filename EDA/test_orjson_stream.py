import orjson
import requests
import time
from collections import Counter

url = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/train.jsonl"
print("Benchmarking orjson streaming...")

t0 = time.time()
resp = requests.get(url, stream=True, timeout=60)
resp.raise_for_status()

count = 0
labels = Counter()
for line in resp.iter_lines():
    if not line:
        continue
    row = orjson.loads(line)
    for s in row.get("privacy_mask", []):
        labels[s.get("label", "UNKNOWN")] += 1
    count += 1
    if count >= 100000:
        break

t1 = time.time()
print(f"Processed {count:,} rows in {t1 - t0:.2f} seconds ({count/(t1-t0):.1f} rows/sec).")
print(f"Found {len(labels)} unique labels in 100k rows!")
print("Top 10 labels:", labels.most_common(10))
print("Bottom 10 labels:", labels.most_common()[-10:])
