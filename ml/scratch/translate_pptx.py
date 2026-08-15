import os
# pyrefly: ignore [missing-import]
from pptx import Presentation

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PPTX_PATH = os.path.join(PROJECT_ROOT, "PredictaGuard_Presentation.pptx")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "PredictaGuard_Presentation.pptx")  # Overwrite same file

TRANSLATIONS = {
    "Struktur Database PostgreSQL": "PostgreSQL Database Structure",
    "Raw sensor data — tanpa cleaning": "Raw sensor data — without cleaning",
    "Raw sensor data — tanpa cleaning": "Raw sensor data — without cleaning",
    "(jika akumulasi salah)": "(if errors accumulate)",
    "Downtime Minim": "Minimal Downtime",
    "Menghubungkan API PredictaGuard ke sistem logistik gudang agar pemesanan spare part otomatis saat RUL kritis.": "Connect the PredictaGuard API to the warehouse logistics system to automate spare parts ordering when RUL is critical."
}

def translate_presentation():
    if not os.path.exists(PPTX_PATH):
        print(f"Presentation file not found at: {PPTX_PATH}")
        return
        
    prs = Presentation(PPTX_PATH)
    print(f"Loaded presentation for translation: {PPTX_PATH}")
    
    replaced_count = 0
    
    for i, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            # 1. Handle shapes with text frames (including textboxes, groups, smartart shapes, etc.)
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    for old_text, new_text in TRANSLATIONS.items():
                        if old_text in paragraph.text:
                            # If it's a direct match or contains the old text
                            print(f"Slide {i+1}: Found in paragraph: '{paragraph.text}'")
                            # If there are runs, we try to replace within runs first to preserve formatting
                            if len(paragraph.runs) > 0:
                                for run in paragraph.runs:
                                    if old_text in run.text:
                                        run.text = run.text.replace(old_text, new_text)
                                        replaced_count += 1
                                    elif old_text == paragraph.text and run == paragraph.runs[0]:
                                        # If the text is split but matches paragraph, set it in the first run and clear others
                                        run.text = new_text
                                        for r in paragraph.runs[1:]:
                                            r.text = ""
                                        replaced_count += 1
                            else:
                                paragraph.text = paragraph.text.replace(old_text, new_text)
                                replaced_count += 1
                                
            # 2. Handle tables
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        for old_text, new_text in TRANSLATIONS.items():
                            if old_text in cell.text:
                                print(f"Slide {i+1}: Found in table cell: '{cell.text}'")
                                cell.text = cell.text.replace(old_text, new_text)
                                replaced_count += 1
                                
    # Save the updated presentation
    prs.save(OUTPUT_PATH)
    print(f"Successfully translated {replaced_count} items and saved presentation to: {OUTPUT_PATH}")

if __name__ == "__main__":
    translate_presentation()
