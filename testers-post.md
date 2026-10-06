# Posts to copy and paste

Check each subreddit's rules before posting. Some don't allow self-promotion or meta posts. r/buildapc and r/nvidia are usually fine with "help me test my free open-source tool" when it's clearly non-commercial.

---

## Reddit (r/buildapc, r/nvidia, r/hardware)

**Title:** I built a free open-source tool to replace GPU "timestamps" when buying used. Looking for testers with NVIDIA cards

**Body:**

Buying used GPUs is a minefield right now: fake cards with flashed BIOS, hollow cards, and timestamps that get photoshopped or AI-generated.

So I made **GPU Passport**, a small free tool (Python, MIT license):

1. The **seller** runs it, and it creates a link with the card's real model and a hash of its unique hardware ID.
2. The **buyer** runs it when the card arrives, and it says **PASS** (same physical card, genuine model) or **FAIL** (swapped or fake).

The seller's link alone is just a claim. The buyer's check is the proof, because it runs on the buyer's own PC. No account, no server, nothing uploaded.

**I don't own an NVIDIA card myself**, so I need testers. If you have 2 minutes:

```
git clone https://github.com/farzinthecreator/gpu-passport
cd gpu-passport
python gpupassport.py create
```

Then tell me your card model and whether the model check said OK / MISMATCH / UNKNOWN. Unknown cards help the most, since I'm building the model database.

Repo: https://github.com/farzinthecreator/gpu-passport

Honest limits: NVIDIA only for now, and no built-in stress test yet (still run memtest_vulkan).

Would you actually use this when buying or selling? Brutal feedback welcome.

---

## Discord (short version)

Made a free open-source tool that replaces GPU timestamps: seller creates a passport link, buyer runs a check when the card arrives (PASS = same card + genuine model). I have no NVIDIA card, so I need testers. 2 minutes: https://github.com/farzinthecreator/gpu-passport
