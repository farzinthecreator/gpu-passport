# GPU Passport

**Prove a used graphics card is real, and that it's the card you were sold.**

Buying a used GPU from a stranger is risky: fake cards with a modified BIOS, hollowed-out cards, worn mining cards, or a good card shown in photos and a different one shipped. Swap forums ask sellers for photo "timestamps", but photos can be faked.

GPU Passport replaces photos with a check the scammer can't fake:

1. **Seller** runs `gpupassport create`. It reads the card's unique hardware ID and real model, and prints a **passport link** for the listing.
2. **Buyer** opens the link to see the card's details before paying.
3. When the card arrives, the **buyer** runs `gpupassport verify "<link>"` on their own PC:
   - **PASS:** same physical card, genuine model
   - **FAIL:** different card, or the model doesn't match its hardware ID

The seller's passport alone is only a claim, since the seller's PC could be tampered with. **The buyer's check is the proof**, because it runs on a machine the seller doesn't control.

No account, no server, no tracking: the passport data lives inside the link, and only a hash of the hardware ID is shared.

## Quick start

Requires an **NVIDIA** card with its driver installed (NVIDIA only for now).

**Windows, no install:** download `gpu-passport.exe` from the [latest release](https://github.com/farzinthecreator/gpu-passport/releases/latest), double-click it, and choose **1** (selling) or **2** (bought). Windows may warn that the app is unrecognized because it isn't code-signed yet: click "More info" → "Run anyway". The .exe is built automatically by GitHub from the code in this repository.

**With Python 3.9+ (Windows or Linux):**

```bash
git clone https://github.com/farzinthecreator/gpu-passport
cd gpu-passport
python gpupassport.py create
```

Buyer, after installing the card:

```bash
python gpupassport.py verify "https://farzinthecreator.github.io/gpu-passport/#..."
```

No NVIDIA card? Try it with a simulated RTX 3070: `python gpupassport.py --mock create`

## What it checks (v0.1)

| Check | How |
|---|---|
| Same physical card | Compares a hash of the GPU's unique ID (`nvidia-smi` UUID) |
| Genuine model | Compares the card's PCI device ID and memory size with known specs (`specs.json`) |
| Claims in the link weren't edited | Re-reads model, device ID and memory on the buyer's PC |
| BIOS changed since the passport | Shows a warning |

## Limits (honest list)

- **NVIDIA only** for now. AMD cards don't expose an easy unique ID; help wanted.
- **No stress or memory test yet.** Still run memtest_vulkan and a benchmark after buying. Built-in tests are planned.
- A very advanced fake that rewrites the hardware ID too would pass the model check. Real benchmark scores catch those, which is planned.
- `specs.json` covers 80 desktop cards: GTX 16 and RTX 20, 30, 40 and 50 series (device IDs checked against the [PCI ID database](https://pci-ids.ucw.cz/read/PC/10de)). Older cards and rare variants show "UNKNOWN". Add cards by pull request.

## Testers wanted

Got an NVIDIA card? Run `python gpupassport.py create` and open an issue with:
- your card model
- whether the model check said OK, MISMATCH or UNKNOWN
- anything confusing

Even 2 minutes helps. Unknown models are the most useful reports.

## Run the tests

```bash
python test_gpupassport.py
```

## License

MIT
