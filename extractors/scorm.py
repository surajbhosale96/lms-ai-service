import zipfile
import io
import requests
from bs4 import BeautifulSoup


def extract_scorm(url: str) -> str:
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    texts = []

    for name in zip_file.namelist():
        if name.endswith(".html") or name.endswith(".htm"):
            content = zip_file.read(name).decode("utf-8", errors="ignore")
            soup = BeautifulSoup(content, "lxml")
            # Remove script and style tags
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            if text:
                texts.append(text)

    return "\n\n".join(texts)
