# Cloudinary Bulk Upload Script

This script uploads all folders located in the same directory into Cloudinary, preserving the folder structure.

---

## Folder Structure

Place the script in a root folder like this:

```
Cloudinary/
├── uploadCloudinary.py
├── product1/
├── product2/
├── product5/
```

Each folder (e.g. `product1`, `product5/productImages`) will be uploaded recursively.

---

## Requirements

Install dependencies:

```bash
pip install cloudinary requests
```

---

## Setup Credentials

Set your Cloudinary credentials using an environment variable.

### Windows (PowerShell)

```powershell
$env:CLOUDINARY_URL="cloudinary://<api_key>:<api_secret>@<cloud_name>"
```

### macOS / Linux

```bash
export CLOUDINARY_URL="cloudinary://<api_key>:<api_secret>@<cloud_name>"
```

---

## Basic Usage

Run the script from the root folder:

```bash
python uploadCloudinary.py
```

This uploads all folders into the **Cloudinary root directory**.

---

## Upload to Specific Cloudinary Folder

```bash
python uploadCloudinary.py --to Folder1
```

* If the folder exists → files are uploaded into it
* If not → files are uploaded to root

---

## Dry Run (Recommended First)

Preview what will be uploaded without sending anything:

```bash
python uploadCloudinary.py --to Folder1 --dry-run
```

---

## Overwrite Existing Files

```bash
python uploadCloudinary.py --to Folder1 --overwrite
```

---

## What Gets Uploaded

* All subfolders are processed recursively
* Folder structure is preserved in Cloudinary
* Example:

```
product5/productImages/image.jpg
→ Folder1/product5/productImages/image.jpg
```

---

## What Is Ignored

The script automatically ignores:

* `uploadCloudinary.py`
* `secrets.json`
* `.py` and `.json` files
* hidden files (e.g. `.git`, `.DS_Store`)

---

## Notes

* Only files inside folders are uploaded (not root files by default)
* Supports images, videos, and raw files
* Safe to reuse for multiple upload batches

---

## Quick Example

```bash
python uploadCloudinary.py --to Folder1 --dry-run
python uploadCloudinary.py --to Folder1 --overwrite
```

---

## Troubleshooting

* **Missing credentials**
  → Ensure `CLOUDINARY_URL` is set correctly

* **Nothing uploaded**
  → Check that your folders are in the same directory as the script

* **Wrong folder destination**
  → Verify the folder name passed with `--to`

---

## Summary

* Put folders beside the script
* Run one command
* Upload everything with structure preserved

---
