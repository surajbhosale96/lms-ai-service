import io
import requests
import pdfplumber


def extract_pdf(url: str) -> str:
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    texts = []
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)

    return "\n\n".join(texts)
