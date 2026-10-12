import orjson
import requests
import time
from collections import Counter

val_url = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/validation.jsonl"
print("Testing streaming from validation.jsonl...")

t0 = time.time()
resp = requests.get(val_url, stream=True, timeout=60)
resp.raise_for_status()

count = 0
val_labels = Counter()
for line in resp.iter_lines():
    if not line:
        continue
    row = orjson.loads(line)
    for s in row.get("privacy_mask", []):
        val_labels[s.get("label", "UNKNOWN")] += 1
    count += 1
    if count % 50000 == 0:
        print(f"Processed {count:,} validation rows in {time.time() - t0:.2f}s...")

t1 = time.time()
print(f"COMPLETE! Processed all {count:,} validation rows in {t1 - t0:.2f} seconds ({count/(t1-t0):.1f} rows/sec)!")
print(f"Found {len(val_labels)} unique labels in validation split.")
print("Top 10 labels in validation:", val_labels.most_common(10))
print("Bottom 10 labels in validation:", val_labels.most_common()[-10:])
