import sys
import unittest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))

from document_exporter import calculate_image_size


class DocumentExporterTableTest(unittest.TestCase):
    def test_calculate_image_size_falls_back_for_missing_image(self):
        width, height = calculate_image_size("missing.png")
        self.assertEqual(width, 14.0)
        self.assertIsNone(height)


if __name__ == "__main__":
    unittest.main()
