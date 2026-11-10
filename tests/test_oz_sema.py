"""Səma xəbərləri (oz_sema.py). Şəbəkə yoxdur."""
import unittest

import oz_sema


class ContractTest(unittest.TestCase):
    def test_module_has_items_and_sinaq(self):
        self.assertTrue(callable(oz_sema.items))
        self.assertTrue(callable(oz_sema.sinaq))


if __name__ == "__main__":
    unittest.main()
