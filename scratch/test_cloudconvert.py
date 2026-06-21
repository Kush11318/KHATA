import os
import sys
import time
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

# Add parent directory to sys.path so we can import from app.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app import convert_file_with_cloudconvert
except ImportError as e:
    print(f"Error importing from app.py: {e}")
    sys.exit(1)

def main():
    api_key = os.environ.get("CLOUDCONVERT_API_KEY")
    if not api_key:
        print("[-] CLOUDCONVERT_API_KEY is not configured in .env.")
        print("Please obtain a free API key from https://cloudconvert.com/ and add it to your .env file:")
        print("CLOUDCONVERT_API_KEY=your_api_key_here")
        return

    print("[+] CLOUDCONVERT_API_KEY found.")
    
    # Create a dummy text file to test the conversion
    dummy_content = b"INVOICE\n\nInvoice Number: INV-2026-999\nVendor: Khata AI Test Vendor\nTotal Amount: $500.00\nItems:\n- 1x AI Assistant Setup Service: $500.00\n"
    dummy_filename = "test_invoice.txt"
    
    print(f"[+] Starting conversion of '{dummy_filename}' (text to pdf)...")
    try:
        start_time = time.time()
        converted_bytes, output_filename = convert_file_with_cloudconvert(
            dummy_content, dummy_filename, target_format="pdf"
        )
        duration = time.time() - start_time
        
        print(f"[+] Conversion successful in {duration:.2f} seconds!")
        print(f"[+] Converted filename returned: {output_filename}")
        print(f"[+] Converted size: {len(converted_bytes)} bytes")
        
        # Save output for inspection
        output_path = os.path.join(os.path.dirname(__file__), output_filename)
        with open(output_path, "wb") as f:
            f.write(converted_bytes)
        print(f"[+] Saved converted file locally to: {output_path}")
        
    except Exception as e:
        print(f"[-] Conversion failed: {e}")

if __name__ == "__main__":
    main()
