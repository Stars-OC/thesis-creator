import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from references.verified_reference_pool import VerifiedReferencePool  # noqa: E402


class VerifiedReferencePoolTestCase(unittest.TestCase):
    def test_print_stats_handles_empty_pool(self):
        pool = VerifiedReferencePool(pool_file="__nonexistent_reference_pool__.yaml")

        output = io.StringIO()
        with redirect_stdout(output):
            pool.print_stats()

        self.assertIn("文献总数: 0", output.getvalue())
        self.assertIn("已验证: 0 (0.0%)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
