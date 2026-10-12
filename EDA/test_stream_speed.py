import time
from datasets import load_dataset

print("Testing streaming speed for 1,000 rows...")
t0 = time.time()
ds = load_dataset("woojin1069/pii-masking-openpii-1.5m", split="train", streaming=True)

rows = []
for i, r in enumerate(ds):
    rows.append(r)
    if i + 1 >= 1000:
        break
t1 = time.time()
print(f"Loaded 1,000 rows in {t1 - t0:.2f} seconds. ({1000/(t1-t0):.1f} rows/sec)")
