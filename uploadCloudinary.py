#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse

import requests
import cloudinary
import cloudinary.uploader


# Exact names to ignore anywhere
IGNORE_NAMES = {
    "uploadCloudinary.py",
    "secrets.json",
    "requirements.txt",
    "README.md",
    ".gitignore",
}

# Extensions to ignore anywhere
IGNORE_EXTENSIONS = {
    ".py",
    ".json",
}

# Allowed upload file types
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".pdf",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload sibling folders recursively to Cloudinary."
    )
    parser.add_argument(
        "--to",
        default="",
        help="Existing root-level Cloudinary folder. If not found or cannot be verified, falls back to Cloudinary root.",
    )
    parser.add_argument(
        "--source",
        default=".",
        help="Local root directory containing this script and product folders. Default: current directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing assets with the same public_id.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview uploads without actually uploading.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and folders.",
    )
    parser.add_argument(
        "--include-root-files",
        action="store_true",
        help="Also upload files directly in the root directory. Default: only folders are uploaded.",
    )
    return parser.parse_args()


def is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def should_ignore(path: Path, include_hidden: bool = False) -> bool:
    if path.name in IGNORE_NAMES:
        return True

    if path.suffix.lower() in IGNORE_EXTENSIONS:
        return True

    if not include_hidden and is_hidden(path):
        return True

    if path.is_file() and ALLOWED_EXTENSIONS:
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return True

    return False


def load_credentials() -> dict:
    """
    Priority:
    1. secrets.json beside this script
    2. CLOUDINARY_URL environment variable
    """
    script_dir = Path(__file__).resolve().parent
    secrets_path = script_dir / "secrets.json"

    if secrets_path.exists():
        with secrets_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        for key in ("cloud_name", "api_key", "api_secret"):
            if not data.get(key):
                raise RuntimeError(f"Missing '{key}' in secrets.json")

        return {
            "cloud_name": data["cloud_name"],
            "api_key": data["api_key"],
            "api_secret": data["api_secret"],
            "upload_prefix": data.get("upload_prefix", "https://api.cloudinary.com"),
        }

    cloudinary_url = os.environ.get("CLOUDINARY_URL", "").strip()
    upload_prefix = os.environ.get("CLOUDINARY_UPLOAD_PREFIX", "").strip()

    if cloudinary_url:
        parsed = urlparse(cloudinary_url)

        if parsed.scheme != "cloudinary":
            raise RuntimeError("CLOUDINARY_URL must start with cloudinary://")

        if not parsed.hostname or not parsed.username or not parsed.password:
            raise RuntimeError("CLOUDINARY_URL is missing cloud_name, api_key, or api_secret")

        return {
            "cloud_name": parsed.hostname,
            "api_key": parsed.username,
            "api_secret": parsed.password,
            "upload_prefix": upload_prefix or "https://api.cloudinary.com",
        }

    raise RuntimeError(
        "No Cloudinary credentials found. "
        "Create secrets.json or set CLOUDINARY_URL."
    )


def configure_cloudinary(creds: dict) -> None:
    cloudinary.config(
        cloud_name=creds["cloud_name"],
        api_key=creds["api_key"],
        api_secret=creds["api_secret"],
        secure=True,
        upload_prefix=creds["upload_prefix"],
    )


def admin_get(path: str, creds: dict, params: Optional[dict] = None) -> requests.Response:
    base = creds["upload_prefix"].rstrip("/")
    url = f"{base}/v1_1/{creds['cloud_name']}{path}"

    return requests.get(
        url,
        params=params or {},
        auth=(creds["api_key"], creds["api_secret"]),
        timeout=30,
    )


def get_folder_mode(creds: dict) -> str:
    """
    Try to detect folder mode through Admin API.
    If it fails (e.g. 401), fall back safely.
    """
    try:
        response = admin_get("/config", creds, params={"settings": "true"})
        response.raise_for_status()
        data = response.json()
        return data.get("settings", {}).get("folder_mode", "dynamic")
    except Exception as exc:
        print(f"[WARN] Could not read Cloudinary folder mode: {exc}")
        print("[WARN] Falling back to 'dynamic' mode.")
        return "dynamic"


def cloudinary_root_folder_exists(folder_name: str, creds: dict) -> bool:
    """
    Check whether a root folder exists.
    If verification fails, return False so the script falls back to root.
    """
    folder_name = folder_name.strip().strip("/")
    if not folder_name:
        return False

    try:
        encoded = quote(folder_name, safe="")
        response = admin_get(f"/folders/{encoded}", creds)

        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False

        response.raise_for_status()
        return False
    except Exception as exc:
        print(f"[WARN] Could not verify Cloudinary folder '{folder_name}': {exc}")
        print("[WARN] Falling back to Cloudinary root.")
        return False


def detect_resource_type(file_path: Path) -> str:
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif"}
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    raw_exts = {".pdf"}

    ext = file_path.suffix.lower()

    if ext in image_exts:
        return "image"
    if ext in video_exts:
        return "video"
    if ext in raw_exts:
        return "raw"

    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        if mime.startswith("image/"):
            return "image"
        if mime.startswith("video/"):
            return "video"

    return "raw"


def join_cloudinary_path(*parts: str) -> str:
    cleaned = [p.strip().strip("/") for p in parts if p and p.strip().strip("/")]
    return "/".join(cleaned)


def iter_upload_candidates(base_dir: Path, include_hidden: bool, include_root_files: bool):
    for item in sorted(base_dir.iterdir()):
        if should_ignore(item, include_hidden=include_hidden):
            continue

        if item.is_dir():
            yield item
        elif include_root_files and item.is_file():
            yield item


def upload_file(
    file_path: Path,
    base_dir: Path,
    cloudinary_root: str,
    folder_mode: str,
    overwrite: bool,
    dry_run: bool,
) -> None:
    relative = file_path.relative_to(base_dir)
    relative_parent = relative.parent.as_posix() if relative.parent.as_posix() != "." else ""
    destination_folder = join_cloudinary_path(cloudinary_root, relative_parent)

    resource_type = detect_resource_type(file_path)
    public_id = file_path.stem

    if dry_run:
        print(
            f"[DRY RUN] {file_path} -> "
            f"folder='{destination_folder or '/'}' public_id='{public_id}' resource_type='{resource_type}'"
        )
        return

    kwargs = {
        "resource_type": resource_type,
        "public_id": public_id,
        "overwrite": overwrite,
        "unique_filename": False,
    }

    if folder_mode == "dynamic":
        if destination_folder:
            kwargs["asset_folder"] = destination_folder
            kwargs["public_id_prefix"] = destination_folder
    else:
        if destination_folder:
            kwargs["folder"] = destination_folder

    result = cloudinary.uploader.upload(str(file_path), **kwargs)
    print(f"[UPLOADED] {file_path} -> public_id={result.get('public_id')}")


def main() -> int:
    args = parse_args()
    base_dir = Path(args.source).resolve()

    if not base_dir.exists() or not base_dir.is_dir():
        raise RuntimeError(f"Source directory does not exist or is not a directory: {base_dir}")

    creds = load_credentials()
    configure_cloudinary(creds)

    folder_mode = get_folder_mode(creds)

    requested_root = args.to.strip().strip("/")
    if requested_root and cloudinary_root_folder_exists(requested_root, creds):
        effective_root = requested_root
        print(f"[INFO] Using existing Cloudinary root folder: {effective_root}")
    else:
        effective_root = ""
        if requested_root:
            print(f"[INFO] Cloudinary folder '{requested_root}' not found or could not be verified. Falling back to root.")
        else:
            print("[INFO] No Cloudinary root folder specified. Uploading to root.")

    print(f"[INFO] Folder mode: {folder_mode}")
    print(f"[INFO] Local source: {base_dir}")

    candidates = list(
        iter_upload_candidates(
            base_dir=base_dir,
            include_hidden=args.include_hidden,
            include_root_files=args.include_root_files,
        )
    )

    if not candidates:
        print("[INFO] Nothing to upload.")
        return 0

    for item in candidates:
        if item.is_file():
            upload_file(
                file_path=item,
                base_dir=base_dir,
                cloudinary_root=effective_root,
                folder_mode=folder_mode,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
            )
            continue

        for file_path in sorted(item.rglob("*")):
            if not file_path.is_file():
                continue
            if should_ignore(file_path.relative_to(base_dir), include_hidden=args.include_hidden):
                continue

            upload_file(
                file_path=file_path,
                base_dir=base_dir,
                cloudinary_root=effective_root,
                folder_mode=folder_mode,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
            )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)