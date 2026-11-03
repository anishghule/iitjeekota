import unittest

from dsapkit.images.png import Pixels, decode_png, encode_png
from dsapkit.images.raster import Image


def solid(width: int, height: int, rgba: tuple[int, int, int, int]) -> Pixels:
    return Pixels(width, height, 4, [bytes(rgba) * width for _ in range(height)])


class PngTest(unittest.TestCase):
    def test_encode_then_decode_round_trips(self):
        px = Pixels(3, 2, 4, [bytes([10, 20, 30, 255, 40, 50, 60, 128, 0, 0, 0, 0]),
                              bytes([255, 255, 255, 255, 1, 2, 3, 4, 200, 100, 50, 255])])
        back = decode_png(encode_png(px))
        self.assertEqual((back.width, back.height, back.rows), (3, 2, px.rows))


class ImageTest(unittest.TestCase):
    def test_resize_gives_exact_sizes(self):
        image = Image.from_pixels(solid(97, 97, (200, 150, 100, 255)))
        for size in (48, 32, 16, 7):
            small = image.resize(size)
            self.assertEqual((small.width, small.height), (size, size))

    def test_flat_colour_survives_downscale_and_sharpening(self):
        image = Image.from_pixels(solid(64, 64, (230, 194, 150, 255))).resize(16).sharpen(0.55, 0.9)
        pixel = image.to_pixels().rows[8][32:36]
        self.assertEqual(tuple(pixel), (230, 194, 150, 255))

    def test_downscale_averages_in_linear_light(self):
        # Half black, half white stripes average to mid grey in light (sRGB 188), not to sRGB 128.
        rows = [bytes([0, 0, 0, 255, 255, 255, 255, 255] * 8) for _ in range(16)]
        grey = Image.from_pixels(Pixels(16, 16, 4, rows)).resize(1).to_pixels().rows[0]
        self.assertAlmostEqual(grey[0], 188, delta=2)

    def test_crop_outside_the_source_is_transparent(self):
        image = Image.from_pixels(solid(4, 4, (255, 0, 0, 255)), -2, -2, 4, 4).to_pixels()
        self.assertEqual(image.rows[0][3], 0)
        self.assertEqual(image.rows[3][3 * 4 + 3], 255)

    def test_plate_is_opaque_with_the_background_at_the_edges(self):
        plate = Image.from_pixels(solid(32, 32, (255, 255, 255, 0))).on_background("#0f1c1f", 20, 0.5).to_pixels()
        self.assertEqual(tuple(plate.rows[0][0:4]), (15, 28, 31, 255))
        self.assertTrue(all(row[3::4] == bytes([255]) * 20 for row in plate.rows))


if __name__ == "__main__":
    unittest.main()
