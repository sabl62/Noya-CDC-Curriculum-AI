import pymupdf  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os

# =========================
# CONFIGURATION
# =========================

PDF_FILE = "textbook.pdf"
OUTPUT_FILE = "textbook_ocr.txt"

# OCR resolution
DPI = 300

# Languages
# Use "eng" for English only
# Use "nep+eng" for Nepali + English
LANGUAGE = "nep+eng"


# =========================
# TESSERACT CONFIG
# =========================

# Uncomment this if Tesseract is not automatically detected.
# Change the path if your installation is elsewhere.

# pytesseract.pytesseract.tesseract_cmd = (
#     r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# )


# =========================
# OPEN PDF
# =========================

if not os.path.exists(PDF_FILE):
    print(f"ERROR: Could not find '{PDF_FILE}'")
    print("Put the PDF in the same folder as this script.")
    exit()

doc = pymupdf.open(PDF_FILE)

total_pages = len(doc)

print("=" * 60)
print("PDF OCR STARTED")
print("=" * 60)
print(f"File: {PDF_FILE}")
print(f"Pages: {total_pages}")
print(f"DPI: {DPI}")
print(f"Language: {LANGUAGE}")
print("=" * 60)


# =========================
# PROCESS PAGES
# =========================

with open(OUTPUT_FILE, "w", encoding="utf-8") as output:

    for page_index, page in enumerate(doc):

        page_number = page_index + 1

        print(f"OCR processing page " f"{page_number}/{total_pages}...")

        try:

            # Render PDF page directly into memory
            pix = page.get_pixmap(dpi=DPI, alpha=False)

            # Convert image bytes → PIL image
            image = Image.open(io.BytesIO(pix.tobytes("png")))

            # Run Tesseract OCR
            text = pytesseract.image_to_string(image, lang=LANGUAGE)

            # Write page separator
            output.write(
                f"\n\n" f"{'=' * 20} " f"PAGE {page_number} " f"{'=' * 20}" f"\n\n"
            )

            # Write OCR text
            output.write(text)

            # Make sure pages don't run together
            output.write("\n")

        except Exception as error:

            print(f"ERROR on page {page_number}: " f"{error}")

            output.write(
                f"\n\n" f"{'=' * 20} " f"PAGE {page_number} " f"{'=' * 20}" f"\n\n"
            )

            output.write("[OCR FAILED FOR THIS PAGE]\n")


# =========================
# FINISHED
# =========================

doc.close()

print("\n" + "=" * 60)
print("OCR COMPLETE")
print("=" * 60)
print(f"Pages processed: {total_pages}")
print(f"Output file: {OUTPUT_FILE}")
print("=" * 60)












