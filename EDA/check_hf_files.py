from huggingface_hub import HfApi

api = HfApi()
files = api.list_repo_files("woojin1069/pii-masking-openpii-1.5m", repo_type="dataset")
print("Files in repo:")
for f in files[:20]:
    print(" ", f)
print(f"Total files: {len(files)}")
