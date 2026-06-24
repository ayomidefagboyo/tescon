import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from app.services.cloudflare_r2 import get_r2_storage

# Load environment variables
load_dotenv()

def download_images(limit=None, specific_symbol=None, output_dir="downloads"):
    """
    Download processed images from Cloudflare R2 to a local directory.
    
    Args:
        limit (int, optional): Maximum number of images to download.
        specific_symbol (str, optional): Download only for this symbol number.
        output_dir (str): Local directory to save images.
    """
    r2 = get_r2_storage()
    if not r2:
        print("❌ Failed to initialize R2 storage. Check credentials.")
        return

    print(f"🔄 Connecting to R2 bucket: {r2.bucket_name}...")
    
    try:
        # List objects
        prefix = f"parts/{specific_symbol}/" if specific_symbol else "parts/"
        response = r2.s3_client.list_objects_v2(Bucket=r2.bucket_name, Prefix=prefix)
        
        if 'Contents' not in response:
            print("📭 No images found in the bucket.")
            return

        all_objects = response['Contents']
        total_found = len(all_objects)
        print(f"📦 Found {total_found} objects.")

        # Filter for images if needed (though everything in parts/ is likely an image)
        image_objects = [obj for obj in all_objects if obj['Key'].endswith(('.jpg', '.jpeg', '.png'))]
        
        if specific_symbol:
            # list_objects_v2 with prefix should handle this, but double check
            image_objects = [obj for obj in image_objects if f"parts/{specific_symbol}/" in obj['Key']]

        to_download = image_objects[:limit] if limit else image_objects
        count = len(to_download)
        
        print(f"⬇️  Downloading {count} images to '{output_dir}/'...")
        
        base_path = Path(output_dir)
        base_path.mkdir(exist_ok=True)

        downloaded_count = 0
        
        for obj in to_download:
            s3_key = obj['Key']
            # Expected format: parts/{symbol_number}/{filename}
            parts = s3_key.split('/')
            
            if len(parts) >= 3:
                symbol = parts[1]
                filename = parts[-1]
                
                # Create local folder: downloads/{symbol_number}/
                target_dir = base_path / symbol
                target_dir.mkdir(parents=True, exist_ok=True)
                
                target_file = target_dir / filename
                
                if target_file.exists():
                     print(f"⏭️  Skipping {filename} (already exists)")
                     continue

                print(f"📥 Downloading {filename}...")
                try:
                    r2.s3_client.download_file(r2.bucket_name, s3_key, str(target_file))
                    downloaded_count += 1
                except Exception as e:
                    print(f"❌ Error downloading {s3_key}: {e}")
            else:
                 print(f"⚠️  Skipping malformed key: {s3_key}")

        print(f"\n✅ Completed! Downloaded {downloaded_count} new images.")

    except Exception as e:
        print(f"❌ Error listing/downloading objects: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download processed images from R2.")
    parser.add_argument("--limit", type=int, help="Limit number of files to download", default=None)
    parser.add_argument("--symbol", type=str, help="Download only for a specific symbol number", default=None)
    parser.add_argument("--output", type=str, help="Output directory", default="downloads")
    
    args = parser.parse_args()
    
    download_images(limit=args.limit, specific_symbol=args.symbol, output_dir=args.output)
