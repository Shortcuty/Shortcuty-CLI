"""Stream local workflows through the public signer and safely save the result."""

import hashlib
import math
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote
from email.message import Message

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from shortcuty_cli.http import ShortcutyAPIError, request


SIGN_URL = "https://sign.shortcuty.app/api/v1/sign"
CHUNK_SIZE = 64 * 1024


def safe_filename(value):
    """Treat a server filename as a basename on both Windows and POSIX."""
    value = str(value).replace("\\", "/").split("/")[-1]
    value = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "_", value).strip(" .")
    stem = value[:-9] if value.lower().endswith(".shortcut") else value
    stem = stem.strip(" .")
    if not stem or stem.split(".")[0].upper() in {
        "CON", "PRN", "AUX", "NUL", *["COM" + str(i) for i in range(1, 10)],
        *["LPT" + str(i) for i in range(1, 10)],
    }:
        stem = "workflow — Signed"
    while len(stem.encode("utf-8")) > 220:
        stem = stem[:-1]
    return stem + ".shortcut"


def download_filename(header, input_name):
    """Prefer RFC 5987 UTF-8 filename* over its ASCII fallback."""
    match = re.search(r"filename\*\s*=\s*([^;]+)", header or "", re.I)
    if match:
        try:
            charset, _, value = match.group(1).strip().strip('"').split("'", 2)
            return safe_filename(unquote(value, encoding=charset or "utf-8", errors="strict"))
        except (ValueError, LookupError, UnicodeError):
            pass
    message = Message()
    message["Content-Disposition"] = header or ""
    filename = message.get_filename()
    if filename:
        return safe_filename(filename)
    stem = Path(input_name).stem
    stem = re.sub(r"(?:[\s—_-]+(?:un)?signed)+$", "", stem, flags=re.I).strip()
    if re.fullmatch(r"(?:un)?signed", stem, re.I):
        stem = ""
    return safe_filename((stem or "workflow") + " — Signed.shortcut")


def check_destination(destination, source, force):
    if destination.is_dir():
        raise ShortcutyAPIError("Output must be a file path, not a directory")
    if not destination.parent.is_dir():
        raise ShortcutyAPIError("Output directory does not exist")
    if not force and (os.path.lexists(destination) or destination.resolve() == source.resolve()):
        raise ShortcutyAPIError("Output already exists or is the input file; choose --output or use --force")


def check_hash(value, actual, label):
    if value is not None and (not re.fullmatch(r"[a-fA-F0-9]{64}", value) or value.lower() != actual):
        raise ShortcutyAPIError("Signing response {} checksum mismatch".format(label))


def sign_shortcut(file_path, output=None, force=False, timeout=300):
    """Sign once; commit output only after its format, length and hashes pass."""
    source = Path(file_path)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ShortcutyAPIError("Timeout must be positive")
    if source.suffix.lower() != ".shortcut":
        raise ShortcutyAPIError("Input must be an unsigned .shortcut file")
    destination = Path(output) if output is not None else None
    temporary = None
    try:
        if destination is not None:
            check_destination(destination, source, force)
        if not source.is_file():
            raise ShortcutyAPIError("Input must be a regular file")
        with source.open("rb") as upload, requests.Session() as session:
            # The public signer needs no credentials, including implicit .netrc auth.
            session.auth = lambda prepared: prepared
            input_hash = hashlib.sha256()
            size = 0
            for chunk in iter(lambda: upload.read(CHUNK_SIZE), b""):
                size += len(chunk)
                input_hash.update(chunk)
            if not size:
                raise ShortcutyAPIError("Input file is empty")
            upload.seek(0)
            body = MultipartEncoder(fields={
                "file": (source.name, upload, "application/octet-stream")
            })
            # This separate session never receives Creator API credentials.
            response = request(
                session, "POST", SIGN_URL, timeout, data=body,
                headers={"Content-Type": body.content_type, "Accept": "application/octet-stream",
                         "Accept-Encoding": "identity"},
                stream=True,
            )
            try:
                # The upload is consumed before response headers arrive. Release its
                # handle so --force can replace the input on Windows as well.
                upload.close()
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
                if response.status_code != 200 or content_type != "application/octet-stream":
                    raise ShortcutyAPIError("Expected HTTP 200 signed binary file from the signer")
                check_hash(response.headers.get("X-Shortcut-Input-SHA256"), input_hash.hexdigest(), "input")
                if destination is None:
                    destination = Path(download_filename(response.headers.get("Content-Disposition"), source.name))
                check_destination(destination, source, force)
                digest, prefix, written = hashlib.sha256(), b"", 0
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=str(destination.parent), prefix=".shortcuty-", delete=False
                ) as target:
                    temporary = Path(target.name)
                    for chunk in response.iter_content(CHUNK_SIZE):
                        if not chunk:
                            continue
                        prefix = (prefix + chunk)[:4]
                        digest.update(chunk)
                        written += len(chunk)
                        target.write(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                if prefix != b"AEA1":
                    raise ShortcutyAPIError("Signer returned an invalid signed file (expected AEA1)")
                length = response.headers.get("Content-Length")
                encoding = response.headers.get("Content-Encoding", "identity").lower()
                if encoding == "identity" and length is not None and (not length.isdigit() or int(length) != written):
                    raise ShortcutyAPIError("Signing response was incomplete (size mismatch)")
                check_hash(response.headers.get("X-Shortcut-Signed-SHA256"), digest.hexdigest(), "signed")
                if force:
                    os.replace(temporary, destination)
                else:
                    # Atomic no-clobber commit, including a destination created during upload.
                    os.link(temporary, destination)
                return {"output": str(destination), "size": written, "signed_sha256": digest.hexdigest()}
            finally:
                response.close()
    except requests.exceptions.RequestException:
        raise ShortcutyAPIError("Signing transfer failed; no output saved. Request was not retried.") from None
    except OSError as error:
        if isinstance(error, FileExistsError):
            raise ShortcutyAPIError("Output already exists; choose --output or use --force") from None
        raise ShortcutyAPIError("Unable to read input or save output: {}".format(error.strerror)) from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
