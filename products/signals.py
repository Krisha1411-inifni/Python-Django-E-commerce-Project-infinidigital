import zipfile
from io import BytesIO
from pathlib import Path
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .models import Product


@receiver(post_save, sender=Product)
def handle_product_file(sender, instance, created, **kwargs):

    if not instance.ProductFile:
        return

    # ❗ Skip extraction for SourceCode / Projects category
    if instance.CategoryId.CategoryName.lower() in ["source code", "projects", "source code / projects"]:
        return

    file_path = Path(instance.ProductFile.path)

    # =============================
    # 📦 ZIP DEMO EXTRACTION
    # =============================
    if file_path.suffix.lower() == ".zip" and not instance.DemoFolder:

        demo_folder_name = f"product_{instance.id}"
        demo_path = Path(settings.MEDIA_ROOT) / "products" / "template_demo" / demo_folder_name
        demo_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(file_path, "r") as zip_ref:
            for member in zip_ref.infolist():

                if member.filename.endswith("/"):
                    continue

                parts = member.filename.split("/", 1)
                relative_path = parts[1] if len(parts) > 1 else parts[0]

                target_path = demo_path / relative_path

                # Prevent Zip Slip
                if not str(target_path.resolve()).startswith(str(demo_path.resolve())):
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)

                with zip_ref.open(member) as source, open(target_path, "wb") as target:
                    target.write(source.read())

        Product.objects.filter(pk=instance.pk).update(
            DemoFolder=demo_folder_name
        )

    elif file_path.suffix.lower() == ".pdf" and not instance.PreviewFile:

        try:
            reader = PdfReader(str(file_path))
            writer = PdfWriter()

            start_page = 0
            total_pages = 5

            end_page = min(start_page + total_pages, len(reader.pages))

            for i in range(start_page, end_page):
                page = reader.pages[i]

                # Get actual page size
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))

                logo_path = Path(
                    settings.BASE_DIR).parent / "infinidigital" / "products" / "static" / "images" / "logo.png"
                logo = ImageReader(str(logo_path))

                # Logo size
                logo_width = 200
                logo_height = 100

                # Center position
                center_x = page_width / 2
                center_y = page_height / 2

                can.saveState()

                # Move origin to center of page
                can.translate(center_x, center_y)

                # Optional rotation
                can.rotate(45)

                can.setFillAlpha(0.2)

                # Draw image centered on origin
                can.drawImage(
                    logo,
                    -logo_width / 2,
                    -logo_height / 2,
                    width=logo_width,
                    height=logo_height,
                    mask='auto'
                )

                can.restoreState()
                can.save()

                packet.seek(0)

                watermark_pdf = PdfReader(packet)
                watermark_page = watermark_pdf.pages[0]

                page.merge_page(watermark_page)
                writer.add_page(page)

            preview_folder = Path(settings.MEDIA_ROOT) / "products/preview"
            preview_folder.mkdir(parents=True, exist_ok=True)

            preview_filename = f"preview_{instance.id}.pdf"
            preview_path = preview_folder / preview_filename

            with open(preview_path, "wb") as f:
                writer.write(f)

            Product.objects.filter(pk=instance.pk).update(
                PreviewFile=f"products/preview/{preview_filename}"
            )

        except Exception as e:
            print("Watermark preview generation failed:", e)
