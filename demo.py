"""
Stego-Cloud CLI Demo
====================
Command-line interface for the complete steganography pipeline.

Usage:
    # Check capacity of a carrier image
    python demo.py capacity --image sunset.png

    # Hide a secret file inside a carrier image
    python demo.py encode --secret passwords.txt --carrier sunset.png --output stego.png --password "MySecret"

    # Extract a hidden file from a stego-image
    python demo.py decode --image stego.png --output extracted.txt --password "MySecret"

    # Generate a carrier image using Gemini AI
    python demo.py generate --description "sunset over mountains" --output carrier.png

    # Full demo: auto-generate carrier, encode, decode, verify
    python demo.py full-demo --secret passwords.txt --password "MySecret"
"""

import argparse
import sys
import io
import hashlib
from pathlib import Path

# Fix Windows console encoding (cp1252 can't display emoji)
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core import crypto_engine, stego_engine, utils
from core.image_provider import generate_carrier_image, get_or_create_carrier


def cmd_capacity(args):
    """Show the hiding capacity of an image."""
    print("=" * 60)
    print("📊 IMAGE CAPACITY ANALYSIS")
    print("=" * 60)

    info = utils.get_image_info(args.image)
    print(f"  File:       {info['path']}")
    print(f"  Format:     {info['format']}")
    print(f"  Resolution: {info['resolution']}")
    print(f"  Pixels:     {info['total_pixels']:,}")
    print(f"  File Size:  {info['file_size']}")
    print(f"  Capacity:   {info['max_capacity']}")
    print("=" * 60)


def cmd_encode(args):
    """Encrypt and hide a secret file inside a carrier image."""
    print("=" * 60)
    print("🔐 ENCODING: Hide Secret File")
    print("=" * 60)

    secret_path = Path(args.secret)
    carrier_path = Path(args.carrier)
    output_path = Path(args.output)

    # Read the secret file
    print(f"\n📄 Secret file: {secret_path}")
    secret_data = secret_path.read_bytes()
    file_info = utils.get_file_info(secret_path)
    print(f"   Size: {file_info['size_readable']}")
    print(f"   Type: {file_info['extension']}")

    # Show carrier info
    print(f"\n🖼️  Carrier image: {carrier_path}")
    img_info = utils.get_image_info(carrier_path)
    print(f"   Resolution: {img_info['resolution']}")
    print(f"   Capacity: {img_info['max_capacity']}")

    # Step 1: Encrypt
    print(f"\n🔒 Step 1: Encrypting with AES-256-GCM...")
    encrypted = crypto_engine.encrypt(secret_data, args.password)
    print(f"   Encrypted size: {utils.format_size(len(encrypted))}")
    print(f"   (Overhead: {len(encrypted) - len(secret_data)} bytes for salt+nonce+tag)")

    # Step 2: Validate capacity
    print(f"\n📐 Step 2: Validating capacity...")
    validation = utils.validate_capacity(carrier_path, len(encrypted))
    print(f"   {validation['message']}")

    if not validation["can_fit"]:
        print("\n❌ FAILED: Image too small for this payload.")
        sys.exit(1)

    # Step 3: Encode via LSB steganography
    print(f"\n📝 Step 3: Injecting into carrier image via LSB steganography...")
    result_path = stego_engine.encode(carrier_path, encrypted, output_path)
    print(f"   Output: {result_path}")

    # Step 4: Verify
    print(f"\n✅ Step 4: Verifying output...")
    output_info = utils.get_image_info(result_path)
    print(f"   Output resolution: {output_info['resolution']}")
    print(f"   Output file size:  {output_info['file_size']}")

    # Hash comparison
    original_hash = hashlib.sha256(secret_data).hexdigest()[:16]
    print(f"\n   Original file SHA-256 (first 16): {original_hash}")

    print("\n" + "=" * 60)
    print("🎉 SUCCESS! Secret file has been hidden inside the image.")
    print(f"   The stego-image is visually identical to the original.")
    print(f"   Output: {result_path}")
    print("=" * 60)


def cmd_decode(args):
    """Extract and decrypt a hidden file from a stego-image."""
    print("=" * 60)
    print("🔓 DECODING: Extract Secret File")
    print("=" * 60)

    stego_path = Path(args.image)
    output_path = Path(args.output)

    print(f"\n🖼️  Stego-image: {stego_path}")
    img_info = utils.get_image_info(stego_path)
    print(f"   Resolution: {img_info['resolution']}")

    # Step 1: Extract hidden data via LSB
    print(f"\n📝 Step 1: Extracting hidden bits via LSB decoding...")
    encrypted_data = stego_engine.decode(stego_path)
    print(f"   Extracted: {utils.format_size(len(encrypted_data))}")

    # Step 2: Decrypt
    print(f"\n🔓 Step 2: Decrypting with AES-256-GCM...")
    try:
        decrypted = crypto_engine.decrypt(encrypted_data, args.password)
    except ValueError as e:
        print(f"\n❌ DECRYPTION FAILED: {e}")
        sys.exit(1)

    print(f"   Decrypted size: {utils.format_size(len(decrypted))}")

    # Step 3: Save
    print(f"\n💾 Step 3: Saving extracted file...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(decrypted)
    print(f"   Saved to: {output_path}")

    # Hash
    extracted_hash = hashlib.sha256(decrypted).hexdigest()[:16]
    print(f"\n   Extracted file SHA-256 (first 16): {extracted_hash}")

    print("\n" + "=" * 60)
    print("🎉 SUCCESS! Secret file has been extracted and decrypted.")
    print(f"   Output: {output_path}")
    print("=" * 60)


def cmd_generate(args):
    """Generate a carrier image using Gemini AI."""
    print("=" * 60)
    print("🤖 GENERATE: AI Carrier Image")
    print("=" * 60)

    description = args.description or "beautiful high resolution landscape photography"
    output_dir = Path(args.output_dir) if args.output_dir else Path("sample_images")

    print(f"\n📝 Description: {description}")
    print(f"📁 Output directory: {output_dir}")

    path = generate_carrier_image(
        description=description,
        output_dir=output_dir,
        filename=args.filename,
    )

    print(f"\n✅ Carrier image ready: {path}")
    info = utils.get_image_info(path)
    print(f"   Resolution: {info['resolution']}")
    print(f"   Capacity: {info['max_capacity']}")


def cmd_full_demo(args):
    """Run the complete pipeline: generate carrier → encode → decode → verify."""
    print("=" * 60)
    print("🚀 FULL DEMO: Complete Stego-Cloud Pipeline")
    print("=" * 60)

    secret_path = Path(args.secret)
    password = args.password

    # Read secret file
    print(f"\n📄 Secret file: {secret_path}")
    secret_data = secret_path.read_bytes()
    print(f"   Size: {utils.format_size(len(secret_data))}")

    # Step 1: Get/generate carrier image
    print(f"\n🤖 Step 1: Getting carrier image via AI...")
    description = args.description or "beautiful nature landscape with mountains and lake"
    encrypted_preview = crypto_engine.encrypt(secret_data, password)
    carrier_path = get_or_create_carrier(
        required_bytes=len(encrypted_preview),
        description=description,
    )

    # Step 2: Encrypt
    print(f"\n🔒 Step 2: Encrypting secret file with AES-256-GCM...")
    encrypted = crypto_engine.encrypt(secret_data, password)
    print(f"   Encrypted size: {utils.format_size(len(encrypted))}")

    # Step 3: Encode
    stego_output = Path("output") / "stego_demo.png"
    print(f"\n📝 Step 3: Hiding encrypted data in carrier image...")
    stego_engine.encode(carrier_path, encrypted, stego_output)
    print(f"   Stego-image saved: {stego_output}")

    # Step 4: Decode
    print(f"\n📝 Step 4: Extracting hidden data from stego-image...")
    extracted_encrypted = stego_engine.decode(stego_output)
    print(f"   Extracted: {utils.format_size(len(extracted_encrypted))}")

    # Step 5: Decrypt
    print(f"\n🔓 Step 5: Decrypting extracted data...")
    extracted = crypto_engine.decrypt(extracted_encrypted, password)
    print(f"   Decrypted size: {utils.format_size(len(extracted))}")

    # Step 6: Verify
    print(f"\n🔍 Step 6: Verifying integrity...")
    original_hash = hashlib.sha256(secret_data).hexdigest()
    extracted_hash = hashlib.sha256(extracted).hexdigest()

    if original_hash == extracted_hash:
        print(f"   ✅ SHA-256 MATCH!")
        print(f"      Original:  {original_hash[:32]}...")
        print(f"      Extracted: {extracted_hash[:32]}...")
    else:
        print(f"   ❌ MISMATCH!")
        print(f"      Original:  {original_hash[:32]}...")
        print(f"      Extracted: {extracted_hash[:32]}...")
        sys.exit(1)

    if secret_data == extracted:
        print(f"   ✅ BYTE-FOR-BYTE IDENTICAL!")
    else:
        print(f"   ❌ DATA MISMATCH!")
        sys.exit(1)

    # Save extracted for manual comparison
    extracted_path = Path("output") / f"extracted_{secret_path.name}"
    extracted_path.parent.mkdir(parents=True, exist_ok=True)
    extracted_path.write_bytes(extracted)

    print("\n" + "=" * 60)
    print("🎉 FULL DEMO COMPLETE!")
    print(f"   Original:  {secret_path}")
    print(f"   Carrier:   {carrier_path}")
    print(f"   Stego:     {stego_output}")
    print(f"   Extracted: {extracted_path}")
    print(f"   Result:    PERFECT MATCH ✅")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Stego-Cloud: Secure steganographic cloud storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo.py capacity --image sunset.png
  python demo.py encode --secret passwords.txt --carrier sunset.png --output stego.png --password "Secret123"
  python demo.py decode --image stego.png --output extracted.txt --password "Secret123"
  python demo.py generate --description "sunset over ocean"
  python demo.py full-demo --secret passwords.txt --password "Secret123"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # capacity
    cap_parser = subparsers.add_parser("capacity", help="Check image capacity")
    cap_parser.add_argument("--image", required=True, help="Path to image file")

    # encode
    enc_parser = subparsers.add_parser("encode", help="Hide a file inside an image")
    enc_parser.add_argument("--secret", required=True, help="Path to secret file")
    enc_parser.add_argument("--carrier", required=True, help="Path to carrier image")
    enc_parser.add_argument("--output", required=True, help="Output stego-image path (.png)")
    enc_parser.add_argument("--password", required=True, help="Encryption password")

    # decode
    dec_parser = subparsers.add_parser("decode", help="Extract a file from a stego-image")
    dec_parser.add_argument("--image", required=True, help="Path to stego-image")
    dec_parser.add_argument("--output", required=True, help="Output file path for extracted data")
    dec_parser.add_argument("--password", required=True, help="Decryption password")

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate carrier image via AI")
    gen_parser.add_argument("--description", help="Description of image to generate")
    gen_parser.add_argument("--output-dir", help="Output directory (default: sample_images)")
    gen_parser.add_argument("--filename", help="Custom filename for the image")

    # full-demo
    demo_parser = subparsers.add_parser("full-demo", help="Run full encode→decode pipeline")
    demo_parser.add_argument("--secret", required=True, help="Path to secret file")
    demo_parser.add_argument("--password", required=True, help="Encryption password")
    demo_parser.add_argument("--description", help="AI image description")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "capacity": cmd_capacity,
        "encode": cmd_encode,
        "decode": cmd_decode,
        "generate": cmd_generate,
        "full-demo": cmd_full_demo,
    }

    try:
        commands[args.command](args)
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
