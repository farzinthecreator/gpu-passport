"""GPU Passport v0.1: create and verify a shareable identity passport for an NVIDIA GPU.

Seller:  python gpupassport.py create          -> prints a passport link for the listing
Buyer:   python gpupassport.py verify "<link>"  -> checks the card in this PC is the card in the link

The passport data lives in the link itself (after the #), so no server is needed.
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FORMAT_VERSION = 1
SITE = "https://farzinthecreator.github.io/gpu-passport/"
FIELDS = "name,uuid,pci.device_id,vbios_version,memory.total,driver_version"
VRAM_TOLERANCE = 0.03  # nvidia-smi reports slightly less than the marketing size (e.g. 24564 MiB on a 24 GB card)
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # _MEIPASS: where the .exe unpacks bundled files
SPECS = {k: v for k, v in json.loads((APP_DIR / "specs.json").read_text()).items() if not k.startswith("_")}
DOWNLOAD = "https://github.com/farzinthecreator/gpu-passport/releases/latest"
MOCK_OUTPUT = "NVIDIA GeForce RTX 3070, GPU-11111111-2222-3333-4444-555555555555, 0x248410DE, 94.04.3A.00.62, 8192, 560.94"


def parse_gpus(csv_text):
    """Parse `nvidia-smi --query-gpu=FIELDS --format=csv,noheader,nounits` output."""
    gpus = []
    for line in csv_text.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 6:
            raise ValueError(f"Unexpected nvidia-smi line: {line!r}")
        name, uuid, pci_id, vbios, vram, driver = parts
        gpus.append({
            "name": name,
            "uuid": uuid,
            "device_id": pci_id[2:6].lower(),  # 0x1F8310DE -> 1f83 (device), 10DE is NVIDIA's vendor id
            "vbios": vbios,
            "vram_mib": int(vram),
            "driver": driver,
        })
    return gpus


def read_gpus(mock=False):
    if mock:
        return parse_gpus(MOCK_OUTPUT)
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={FIELDS}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True, timeout=30,
        ).stdout
    except FileNotFoundError:
        sys.exit("nvidia-smi not found. GPU Passport v0.1 supports NVIDIA cards only (install the NVIDIA driver).")
    except subprocess.CalledProcessError as e:
        sys.exit(f"nvidia-smi failed: {(e.stderr or '').strip() or e}")
    except subprocess.TimeoutExpired:
        sys.exit("nvidia-smi did not answer within 30 seconds. Is the driver working?")
    gpus = parse_gpus(out)
    if not gpus:
        sys.exit("No NVIDIA GPU found.")
    return gpus


def uuid_hash(uuid):
    # Only the hash is shared, so the link doesn't expose the raw hardware ID.
    return hashlib.sha256(f"gpu-passport:v1:{uuid.strip().lower()}".encode()).hexdigest()


def model_name(name):
    """'NVIDIA GeForce RTX 3060 12GB' -> 'rtx 3060'. Drops brand words and variant tags that don't change the model."""
    words = [w for w in name.lower().split() if w not in ("nvidia", "geforce", "lhr", "oem") and not re.fullmatch(r"\d+gb", w)]
    return " ".join(words)


def spec_check(gpu):
    """Compare what the card says it is with the known specs for its hardware device ID."""
    spec = SPECS.get(gpu["device_id"])
    if spec is None:
        return "unknown", f"Device ID {gpu['device_id']} is not in the database yet, so the model can't be checked."
    problems = []
    # Exact match, so a 3070 renamed to "3070 Ti" is caught.
    if model_name(gpu["name"]) != model_name(spec["model"]):
        problems.append(f"name says '{gpu['name']}' but the hardware ID belongs to a {spec['model']}")
    if not any(abs(gpu["vram_mib"] - v) <= v * VRAM_TOLERANCE for v in spec["vram_mib"]):
        problems.append(f"{gpu['vram_mib']} MiB of memory, but a {spec['model']} has {spec['vram_mib']} MiB")
    if problems:
        return "mismatch", "; ".join(problems)
    return "ok", f"Hardware ID matches a real {spec['model']} with {gpu['vram_mib']} MiB."


def make_passport(gpu):
    status, _ = spec_check(gpu)
    return {
        "v": FORMAT_VERSION,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "model": gpu["name"],
        "device_id": gpu["device_id"],
        "vbios": gpu["vbios"],
        "vram_mib": gpu["vram_mib"],
        "driver": gpu["driver"],
        "spec": status,
        "uuid_hash": uuid_hash(gpu["uuid"]),
    }


def encode(passport):
    raw = json.dumps(passport, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode(link):
    data = link.split("#", 1)[-1].strip()
    try:
        passport = json.loads(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError("This is not a valid GPU Passport link.") from e
    required = {"v", "model", "device_id", "vram_mib", "uuid_hash"}
    if not isinstance(passport, dict) or not required <= passport.keys():
        raise ValueError("This passport link is incomplete or damaged.")
    if passport["v"] != FORMAT_VERSION:
        raise ValueError(f"Passport format v{passport['v']} needs a newer version of this tool.")
    return passport


def verify(passport, gpus):
    """Return (ok, messages). Runs on the BUYER's PC, which is the only result that can be trusted."""
    card = next((g for g in gpus if uuid_hash(g["uuid"]) == passport["uuid_hash"]), None)
    if card is None:
        return False, ["This is NOT the card in the passport (its unique hardware ID is different)."]
    messages = [f"Same physical card as in the passport (unique hardware ID matches): {card['name']}."]
    ok = True
    # A scammer can put their real card's ID in the link but claim a better model, so re-check every claim locally.
    if (model_name(str(passport["model"])) != model_name(card["name"])
            or card["device_id"] != passport["device_id"] or card["vram_mib"] != passport["vram_mib"]):
        ok = False
        messages.append(
            f"The passport claims a {passport['model']} (device {passport['device_id']}, {passport['vram_mib']} MiB), "
            f"but this card is a {card['name']} (device {card['device_id']}, {card['vram_mib']} MiB)."
        )
    status, detail = spec_check(card)
    if status == "mismatch":
        ok = False
        messages.append(f"Possible fake card: {detail}")
    elif status == "unknown":
        messages.append(f"Warning: {detail}")
    else:
        messages.append(detail)
    if passport.get("vbios") and card["vbios"] != passport["vbios"]:
        messages.append(f"Warning: BIOS changed since the passport was made ({passport['vbios']} -> {card['vbios']}).")
    return ok, messages


def main(argv=None):
    parser = argparse.ArgumentParser(description="GPU Passport: prove a used NVIDIA GPU is real and is the card you were sold.")
    parser.add_argument("--mock", action="store_true", help="use a fake RTX 3070 instead of nvidia-smi (for testing without an NVIDIA card)")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="seller: create a passport link for your card")
    create.add_argument("--gpu", type=int, default=0, help="which GPU to use if this PC has several (default: 0)")
    check = sub.add_parser("verify", help="buyer: check the card in this PC against a passport link")
    check.add_argument("link", help="the passport link from the listing")
    args = parser.parse_args(argv)

    gpus = read_gpus(mock=args.mock)
    if args.command == "create":
        if not 0 <= args.gpu < len(gpus):
            sys.exit(f"There is no GPU {args.gpu}. This PC has {len(gpus)} NVIDIA GPU(s): 0 to {len(gpus) - 1}.")
        gpu = gpus[args.gpu]
        status, detail = spec_check(gpu)
        print(f"Card: {gpu['name']} ({gpu['vram_mib']} MiB, BIOS {gpu['vbios']})")
        print(f"Model check: {status.upper()}: {detail}")
        print("\nYour passport link (put it in your listing):\n")
        print(SITE + "#" + encode(make_passport(gpu)))
        print(f"\nWhen the card arrives, the buyer opens GPU Passport ({DOWNLOAD}), chooses 2 and pastes this link.")
        return 0

    try:
        passport = decode(args.link)
    except ValueError as e:
        sys.exit(str(e))
    ok, messages = verify(passport, gpus)
    print("PASS" if ok else "FAIL")
    for m in messages:
        print("  - " + m)
    return 0 if ok else 1


def interactive(mock=False):
    """Menu for people who double-click the .exe instead of typing commands."""
    flags = ["--mock"] if mock else []
    print("GPU Passport\n")
    print("  1) I'm SELLING a card: create a passport link")
    print("  2) I BOUGHT a card: check it against a passport link")
    choice = input("\nType 1 or 2 and press Enter: ").strip()
    if choice == "1":
        return main(flags + ["create"])
    if choice == "2":
        link = input("Paste the passport link and press Enter: ").strip()
        return main(flags + ["verify", link])
    print("Please type 1 or 2.")
    return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(main())
    try:
        code = interactive()
    except SystemExit as e:  # error messages from sys.exit(...) would otherwise vanish with the window
        if isinstance(e.code, str):
            print(e.code)
        code = e.code if isinstance(e.code, int) else 1
    input("\nPress Enter to close...")  # keep a double-clicked window open so the result can be read
    sys.exit(code)
