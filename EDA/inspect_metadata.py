import json
from datasets import load_dataset_builder, get_dataset_config_names

print("Getting configs...")
try:
    configs = get_dataset_config_names("woojin1069/pii-masking-openpii-1.5m")
    print("Configs:", configs)
except Exception as e:
    print("Error getting configs:", e)

builder = load_dataset_builder("woojin1069/pii-masking-openpii-1.5m")
print("Splits info:", builder.info.splits)
print("Features:", builder.info.features)
print("Description:", builder.info.description)
print("Dataset size:", builder.info.dataset_size)
print("Download size:", builder.info.download_size)
