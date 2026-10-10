from pathlib import Path
import tempfile
import ocrmypdf

INPUT_DIR = Path(r"cdc_curriculum/")
STAGING_DIR = Path(tempfile.gettempdir()) / "noya-ocr"
BOOKS = ["math.pdf", "omaths.pdf", "english.pdf"]

STAGING_DIR.mkdir(parents=True, exist_ok=True)

for name in BOOKS:
    source = INPUT_DIR / name
    output = STAGING_DIR / name

    if not source.is_file():
        print(f"Skipping missing file: {source}")
        continue

    print(f"OCR: {source}")
    ocrmypdf.ocr(
        source,
        output,
        redo_ocr=True,
        language=["eng"],
        output_type="pdf",
        jobs=1,
    )
    print(f"Saved: {output}")
