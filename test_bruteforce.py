"""Brute-force tests: throw thousands of random and malicious inputs at GPU Passport.

Run with: python test_bruteforce.py
More rounds: set ROUNDS=100000 (PowerShell: $env:ROUNDS=100000)
"""
import base64
import json
import os
import random
import string
import unittest

import gpupassport as gp

ROUNDS = int(os.environ.get("ROUNDS", "3000"))
REAL = gp.parse_gpus("NVIDIA GeForce RTX 3070, GPU-aaaa-1111, 0x248410DE, 94.04.3A.00.62, 8192, 560.94")[0]
JUNK_VALUES = [None, True, 0, -1, 2**64, 3.5, "", "x" * 5000, [], {}, "RTX 4090", "2684", 24576, "<script>", "ok", "mismatch"]


def random_text(rng, max_len=200):
    alphabet = string.printable + "äöü€😀\x00"
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, max_len)))


def b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


class BruteForceTest(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(1234)  # fixed seed: a failure can be reproduced exactly

    def test_garbage_links_never_crash(self):
        """Random text, random base64 and random JSON must give a clean ValueError or a valid passport."""
        for _ in range(ROUNDS):
            kind = self.rng.randint(0, 2)
            if kind == 0:
                link = random_text(self.rng)
            elif kind == 1:
                link = "#" + base64.urlsafe_b64encode(os.urandom(self.rng.randint(0, 300))).decode()
            else:
                link = "#" + b64(self.rng.choice([[], 5, "s", None, {"v": 1}, {k: self.rng.choice(JUNK_VALUES) for k in ("v", "model", "device_id", "vram_mib", "uuid_hash")}]))
            try:
                passport = gp.decode(link)
            except ValueError:
                continue
            gp.verify(passport, [REAL])  # must not raise

    def test_tampered_passport_never_passes(self):
        """Change any claim in a real passport: the buyer's check must not say PASS for a lie."""
        honest = gp.make_passport(REAL)
        claims = ["model", "device_id", "vram_mib", "uuid_hash"]
        for _ in range(ROUNDS):
            fake = dict(honest)
            field = self.rng.choice(claims)
            fake[field] = self.rng.choice(JUNK_VALUES + [random_text(self.rng, 30), self.rng.randint(0, 50000)])
            if fake[field] == honest[field] or (field == "model" and gp.model_name(str(fake[field])) == gp.model_name(honest["model"])):
                continue  # not actually a lie
            ok, _ = gp.verify(gp.decode("#" + b64(fake)), [REAL])
            self.assertFalse(ok, f"PASS for a passport with tampered {field}={fake[field]!r}")

    def test_swapped_cards_always_fail(self):
        """Thousands of other cards (random unique IDs) against one passport: all must FAIL."""
        passport = gp.make_passport(REAL)
        for _ in range(ROUNDS):
            other = dict(REAL, uuid="GPU-" + "".join(self.rng.choice("0123456789abcdef") for _ in range(32)))
            ok, _ = gp.verify(passport, [other])
            self.assertFalse(ok)

    def test_honest_passport_passes_every_time(self):
        """The opposite check: an honest passport for the same card must always PASS."""
        ok, messages = gp.verify(gp.decode("#" + gp.encode(gp.make_passport(REAL))), [REAL])
        self.assertTrue(ok, messages)


if __name__ == "__main__":
    unittest.main()
