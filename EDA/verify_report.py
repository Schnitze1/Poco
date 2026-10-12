import re

for path, name in [
    (r"d:\Repos\Poco\EDA\EDA_REPORT.md", "EDA_REPORT.md"),
    (r"C:\Users\Shadd\.gemini\antigravity-ide\brain\0f1bd67a-e6ce-4dc6-b535-b908b888cb0b\eda_openpii_report.md", "eda_openpii_report.md")
]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"=== {name} ===")
    imgs = re.findall(r'!\[.*?\]\((.*?)\)', text)
    print(f"Total embedded images: {len(imgs)}")
    bad_imgs = [img for img in imgs if not img.startswith("./")]
    print(f"Non-relative images: {bad_imgs}")
    
    m61 = re.findall(r'.*?GIVENNAME and SURNAME.*', text)
    print(f"Sec 6.1: {m61}")
    
    m_exec = re.findall(r'.*?viable training labels.*', text)
    print(f"Exec summary: {m_exec}")
    
    has_cyrl = "Cyrl" in text
    has_grek = "Grek" in text
    print(f"Has Cyrl: {has_cyrl}, Has Grek: {has_grek}")
    
    m20 = re.findall(r'.*?Figure 20:.*', text)
    print(f"Fig 20: {m20}")
    print()
