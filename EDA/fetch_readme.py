from huggingface_hub import hf_hub_download

path = hf_hub_download(repo_id="woojin1069/pii-masking-openpii-1.5m", filename="README.md", repo_type="dataset")
with open(path, "r", encoding="utf-8") as f:
    readme_content = f.read()

print("README size:", len(readme_content))
print("First 1500 chars:")
print(readme_content[:1500])
