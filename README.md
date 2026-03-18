# Cloudinary Bulk Upload Script

This script uploads all folders located in the same directory into Cloudinary, preserving the local folder structure.

## Example Folder Structure

```text
Cloudinary/
├── uploadCloudinary.py
├── requirements.txt
├── secrets.json
├── product1/
│   ├── product1_0.jpg
│   ├── product1_1.jpg
│   └── product1_2.jpg
├── product2/
│   ├── product2_0.jpg
│   ├── product2_1.jpg
│   └── product2_2.jpg
└── product5/
    ├── productImages/
    │   ├── product5_0.jpg
    │   ├── product5_1.jpg
    │   └── product5_2.jpg
    └── productVideos/
        ├── product5_0.mov
        └── product5_1.mov

The script uploads every sibling folder recursively.

```
pip install -r requirements.txt
```

## Credentials

The script loads credentials in this order:

CLOUDINARY_URL environment variable

secrets.json in the same folder as uploadCloudinary.py

Option 1: secrets.json

Create a secrets.json file beside the script:
```
{
  "cloud_name": "your_cloud_name",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "upload_prefix": "https://api.cloudinary.com"
}
```

Notes:
```
upload_prefix is optional if you use the default US endpoint.

For EU, use: https://api-eu.cloudinary.com

For AP, use: https://api-ap.cloudinary.com
```

Upload all folders to Cloudinary root:
```
python uploadCloudinary.py
```

Upload Into a Specific Existing Cloudinary Root Folder
```
python uploadCloudinary.py --to KontrolFreek
```

Behavior:
 - If the folder exists in Cloudinary root, uploads go inside it.
 - If it does not exist, the script falls back to Cloudinary root.

## Dry Run
Preview what would be uploaded:
```
python uploadCloudinary.py --to KontrolFreek --dry-run
```

Overwrite Existing Assets
```
python uploadCloudinary.py --to KontrolFreek --overwrite
```

## Include Root Files
By default, the script only uploads folders beside the script.

To also upload media files directly in the root folder:
```
python uploadCloudinary.py --include-root-files
```

## Use a Different Local Source Folder
```
python uploadCloudinary.py --source ./MyBatchFolder
```
What Gets Uploaded
 - All sibling folders are scanned recursively
 - Folder structure is preserved
 - Images, videos, and allowed raw files are uploaded (as long as not in ignore list)

The destination folder path is preserved under the chosen Cloudinary root folder
Example:
```
product5/productImages/image.jpg
→ KontrolFreek/product5/productImages/image
```

What Is Ignored
The script ignores these automatically:
 - uploadCloudinary.py
 - secrets.json
 - requirements.txt
 - README.md
 - .gitignore
 - all .py files
 - all .json files
 - hidden files and hidden folders by default

## Supported File Types

Current allowlist:
```
.jpg
.jpeg
.png
.webp
.gif
.mp4
.mov
.avi
.mkv
.webm
.pdf
```

If a file extension is not in the allowlist, it is skipped.

## Usage
Make sure your product folders are in the same directory as the script, or pass --source.

Wrong Cloudinary folder

Check the folder name passed to --to. If it does not exist, the script falls back to root.

Hidden files not uploading

Use:

python uploadCloudinary.py --include-hidden

secrets.json looks something like
{
  "cloud_name": "your_cloud_name",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "upload_prefix": "https://api.cloudinary.com"
}
