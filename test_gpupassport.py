"""Run with: python test_gpupassport.py"""
import unittest

import gpupassport as gp

REAL_3070 = "NVIDIA GeForce RTX 3070, GPU-aaaa-1111, 0x248410DE, 94.04.3A.00.62, 8192, 560.94"
OTHER_3070 = "NVIDIA GeForce RTX 3070, GPU-bbbb-2222, 0x248410DE, 94.04.3A.00.62, 8192, 560.94"
FAKE_3070 = "NVIDIA GeForce RTX 3070, GPU-cccc-3333, 0x288210DE, 95.07.00.00.01, 8188, 560.94"  # really a 4060
UNKNOWN = "NVIDIA GeForce GTX 1080, GPU-dddd-4444, 0x1B8010DE, 86.04.17.00.01, 8192, 560.94"


def gpu(line):
    return gp.parse_gpus(line)[0]


class GpuPassportTest(unittest.TestCase):
    def test_parse_reads_device_id_from_pci_id(self):
        self.assertEqual(gpu(REAL_3070)["device_id"], "2484")
        self.assertEqual(gpu(REAL_3070)["vram_mib"], 8192)

    def test_parse_rejects_unexpected_output(self):
        with self.assertRaises(ValueError):
            gp.parse_gpus("garbage line")

    def test_spec_check(self):
        self.assertEqual(gp.spec_check(gpu(REAL_3070))[0], "ok")
        self.assertEqual(gp.spec_check(gpu(FAKE_3070))[0], "mismatch")
        self.assertEqual(gp.spec_check(gpu(UNKNOWN))[0], "unknown")

    def test_link_round_trip(self):
        passport = gp.make_passport(gpu(REAL_3070))
        link = gp.SITE + "#" + gp.encode(passport)
        self.assertEqual(gp.decode(link), passport)
        self.assertNotIn("GPU-aaaa-1111", link)  # raw hardware ID never appears in the link

    def test_decode_rejects_bad_links(self):
        for bad in ["https://x/#not-base64!!", "https://x/#" + gp.encode({"v": 1}), "https://x/#" + gp.encode({"v": 99, "model": "", "device_id": "", "vram_mib": 0, "uuid_hash": ""})]:
            with self.assertRaises(ValueError):
                gp.decode(bad)

    def test_verify_same_card_passes(self):
        passport = gp.make_passport(gpu(REAL_3070))
        ok, _ = gp.verify(passport, [gpu(REAL_3070)])
        self.assertTrue(ok)

    def test_verify_swapped_card_fails(self):
        passport = gp.make_passport(gpu(REAL_3070))
        ok, messages = gp.verify(passport, [gpu(OTHER_3070)])
        self.assertFalse(ok)
        self.assertIn("NOT the card", messages[0])

    def test_verify_fails_when_scammer_edits_claims_in_link(self):
        # Seller uses the fake card's real ID but edits the link to claim a real 3070.
        passport = gp.make_passport(gpu(FAKE_3070))
        passport.update(device_id="2484", vram_mib=8192, spec="ok")
        tampered = gp.decode("#" + gp.encode(passport))
        ok, _ = gp.verify(tampered, [gpu(FAKE_3070)])
        self.assertFalse(ok)

    def test_verify_flags_fake_even_if_link_is_honest(self):
        passport = gp.make_passport(gpu(FAKE_3070))
        ok, messages = gp.verify(passport, [gpu(FAKE_3070)])
        self.assertFalse(ok)
        self.assertTrue(any("Possible fake" in m for m in messages))

    def test_verify_picks_matching_card_among_several(self):
        passport = gp.make_passport(gpu(REAL_3070))
        ok, _ = gp.verify(passport, [gpu(OTHER_3070), gpu(REAL_3070)])
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
