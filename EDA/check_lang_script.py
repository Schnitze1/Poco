import pandas as pd

df = pd.read_csv(r"d:\Repos\Poco\EDA\eda_refined_100k.csv")
print("Languages in 100k sample:")
print(df["language"].value_counts())

print("\nScripts in 100k sample:")
print(df["script"].value_counts())
