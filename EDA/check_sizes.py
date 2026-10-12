from huggingface_hub import HfApi

api = HfApi()
info = api.model_info if hasattr(api, "dataset_info") else api.dataset_info
d_info = api.dataset_info("woojin1069/pii-masking-openpii-1.5m", files_metadata=True)
for s in d_info.siblings:
    if "jsonl" in s.rfilename:
        print(s.rfilename, "size:", getattr(s, "size", "unknown"))
