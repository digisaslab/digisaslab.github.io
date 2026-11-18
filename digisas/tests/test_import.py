import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from scripts import migrate


class MediaImportTests(unittest.TestCase):
    def test_srcset_keeps_unicode_spacing_in_filenames(self):
        source = "https://example.org/Screenshot-9.34.00\u202fam.png"
        self.assertEqual(migrate.srcset_sources(f"{source} 900w, {source}?small=1 300w"),
                         [source, source + "?small=1"])

    def test_image_metadata_is_removed_after_orientation_is_applied(self):
        source = Image.new("RGB", (2, 3))
        exif = Image.Exif()
        exif[274] = 6
        data = io.BytesIO()
        source.save(data, format="JPEG", exif=exif)
        with tempfile.TemporaryDirectory() as temporary, patch.object(migrate, "ROOT", Path(temporary)), patch.object(migrate, "fetch", return_value=(data.getvalue(), {})):
            result = migrate.download_media("https://www.digisaslab.org/wp-content/uploads/portrait.jpg")
            with Image.open(Path(temporary) / result["path"].lstrip("/")) as image:
                self.assertEqual(image.size, (3, 2))
                self.assertFalse(image.getexif())

    def test_tiff_conversion_uses_real_jpeg_bytes(self):
        data = io.BytesIO()
        Image.new("RGB", (2, 3)).save(data, format="TIFF")
        with tempfile.TemporaryDirectory() as temporary, patch.object(migrate, "ROOT", Path(temporary)), patch.object(migrate, "fetch", return_value=(data.getvalue(), {})):
            result = migrate.download_media("https://www.digisaslab.org/wp-content/uploads/portrait.tif")
            self.assertTrue(result["path"].endswith(".tif.jpg"))
            with Image.open(Path(temporary) / result["path"].lstrip("/")) as image:
                self.assertEqual(image.format, "JPEG")


if __name__ == "__main__":
    unittest.main()
