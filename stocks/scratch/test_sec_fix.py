import re
from bs4 import BeautifulSoup
from html import unescape

def extract_section_improved(html: str, section: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    text = unescape(text)

    # Normalize whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    section_pattern = re.compile(
        rf"(?:^|\n)\s*ITEM\s+{re.escape(section.upper())}[\s\.:\-]+",
        re.IGNORECASE | re.MULTILINE,
    )
    next_item_pattern = re.compile(
        r"(?:^|\n)\s*ITEM\s+\d+[A-Z]?[\s\.:\-]+",
        re.IGNORECASE | re.MULTILINE,
    )

    matches = list(section_pattern.finditer(text))
    if not matches:
        return f"Section Item {section} not found."

    best_extracted = ""
    max_len = -1

    for match in matches:
        start = match.start()
        next_match = next_item_pattern.search(text, match.end())
        end = next_match.start() if next_match else len(text)
        extracted = text[start:end].strip()
        
        if len(extracted) > max_len:
            max_len = len(extracted)
            best_extracted = extracted

    if len(best_extracted) > 15000:
        best_extracted = best_extracted[:15000] + "\n\n[... truncated ...]"

    return best_extracted

# Test with the META URL
import requests
SEC_HEADERS = {"User-Agent": "StockAnalysis test@example.com"}
url = "https://www.sec.gov/Archives/edgar/data/1326801/000162828026003942/meta-20251231.htm"
resp = requests.get(url, headers=SEC_HEADERS)
html = resp.text

for s in ["1", "1A", "7"]:
    print(f"\n--- Testing Section {s} ---")
    ext = extract_section_improved(html, s)
    print(f"Length: {len(ext)}")
    print(ext[:500])
