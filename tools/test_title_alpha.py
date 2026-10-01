import unittest
import numpy as np
from title_artwork import prefer_opaque_palette_entries


class TitleAlphaTests(unittest.TestCase):
    def test_opaque_white_uses_original_solid_entry(self):
        palette = [bytes((255, 255, 255, a)) for a in (140, 164, 230, 255)]
        indices = np.array([0, 1, 2, 3], dtype=np.uint8)
        target = np.full((4, 4), 255, dtype=np.int32)
        fixed = prefer_opaque_palette_entries(indices, target, palette)
        np.testing.assert_array_equal(fixed, [3, 3, 3, 3])
        np.testing.assert_array_equal(indices, [0, 1, 2, 3])

    def test_partial_alpha_and_distinct_colors_are_preserved(self):
        palette = [bytes((255, 255, 255, 140)), bytes((255, 255, 255, 255)),
                   bytes((254, 255, 255, 140)), bytes((255, 255, 255, 0))]
        indices = np.array([0, 2, 3], dtype=np.uint8)
        target = np.array([[255, 255, 255, 200], [254, 255, 255, 255],
                           [255, 255, 255, 0]], dtype=np.int32)
        np.testing.assert_array_equal(prefer_opaque_palette_entries(indices, target, palette), indices)


if __name__ == '__main__':
    unittest.main()
