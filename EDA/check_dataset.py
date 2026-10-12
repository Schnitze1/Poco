import sys
from datasets import load_dataset

print("Checking woojin1069/pii-masking-openpii-1.5m...")
try:
    ds1 = load_dataset("woojin1069/pii-masking-openpii-1.5m", split="train", streaming=True)
    first1 = next(iter(ds1))
    print("woojin1069 loaded successfully! Keys:", list(first1.keys()))
    print("Sample row:", {k: str(v)[:100] for k, v in first1.items()})
except Exception as e:
    print("Error loading woojin1069:", e)

print("\nChecking ai4privacy/pii-masking-openpii-1.5m...")
try:
    ds2 = load_dataset("ai4privacy/pii-masking-openpii-1.5m", split="train", streaming=True)
    first2 = next(iter(ds2))
    print("ai4privacy loaded successfully! Keys:", list(first2.keys()))
    print("Sample row:", {k: str(v)[:100] for k, v in first2.items()})
except Exception as e:
    print("Error loading ai4privacy:", e)
