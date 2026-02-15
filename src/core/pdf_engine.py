import os
import img2pdf
from . import log

async def create_pdf(source_folder, output_filename):
    images = sorted([os.path.join(source_folder, f) for f in os.listdir(source_folder) if f.endswith(".jpg")])
    
    if not images:
        log("Image not found.", "warn")
        return

    log(f"Packing {len(images)} pages...", "info")

    try:
        with open(output_filename, "wb") as f:
            f.write(img2pdf.convert(images))
        log(f"PDF created: {output_filename}", "success")
    except Exception as e:
        log(f"Failed to create PDF: {e}", "error")
