import json
import os
import fitz


RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def extract_text_by_page(pdf_path: str) -> list[dict]:
    """Extract text from each page of a PDF."""
    pages = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        text = clean_text(text)
        if text:
            pages.append({"text": text, "page": page_num + 1})
    doc.close()
    return pages


def clean_text(text: str) -> str:
    """Remove extra spaces and empty lines."""
    lines = text.splitlines()
    lines = [line.strip() for line in lines if line.strip()]
    return " ".join(lines)


def split_into_chunks(pages: list[dict], chunk_size: int = 200, overlap: int = 50, source: str = "") -> list[dict]:
    """Split full document text into overlapping word chunks that cross page boundaries."""
    # Build a flat word list, tracking which page each word came from
    all_words = []
    for page in pages:
        for word in page["text"].split():
            all_words.append({"word": word, "page": page["page"]})

    chunks = []
    start = 0

    while start < len(all_words):
        end = min(start + chunk_size, len(all_words))
        chunk_words = all_words[start:end]

        chunk_text = " ".join(w["word"] for w in chunk_words)

        if len(chunk_text.strip()) < 100:
            start += chunk_size - overlap
            continue

        noisy_keywords = [
            "index", "table of contents", "contents",
            "preface", "isbn", "copyright",
        ]
        if any(word in chunk_text.lower() for word in noisy_keywords):
            start += chunk_size - overlap
            continue

        page_start = chunk_words[0]["page"]
        page_end = chunk_words[-1]["page"]

        chunks.append({
            "content": chunk_text,
            "metadata": {
                "source": source,
                "page_start": page_start,
                "page_end": page_end,
            },
        })

        start += chunk_size - overlap

    return chunks


def process_pdf(pdf_path: str) -> list[dict]:
    """Process a single PDF: extract text, clean, chunk."""
    filename = os.path.basename(pdf_path)
    print(f"Processing: {filename}")

    pages = extract_text_by_page(pdf_path)
    chunks = split_into_chunks(pages, source=filename)

    print(f"  → {len(pages)} pages, {len(chunks)} chunks")
    return chunks


def save_chunks(chunks: list[dict], output_path: str):
    """Save chunks to a JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  → Saved to {output_path}")


def process_all_pdfs():
    """Loop over all PDFs in data/raw/, process each, save JSON to data/processed/."""
    raw_dir = os.path.abspath(RAW_DIR)
    processed_dir = os.path.abspath(PROCESSED_DIR)

    pdf_files = [f for f in os.listdir(raw_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"No PDF files found in {raw_dir}")
        return

    print(f"Found {len(pdf_files)} PDF(s)\n")

    for pdf_file in pdf_files:
        pdf_path = os.path.join(raw_dir, pdf_file)
        chunks = process_pdf(pdf_path)

        json_filename = os.path.splitext(pdf_file)[0] + ".json"
        output_path = os.path.join(processed_dir, json_filename)
        save_chunks(chunks, output_path)
        print()

    print("Done!")


if __name__ == "__main__":
    process_all_pdfs()
