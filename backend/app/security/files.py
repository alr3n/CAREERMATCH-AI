"""Safe handling of uploaded file names and storage paths."""

from __future__ import annotations

import re
import shutil
import unicodedata
import uuid
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9._ -]+")


def sanitize_filename(name: str | None, max_length: int = 100) -> str:
    """Return a display-safe file name with no path components.

    The sanitised name is only used for display; files are stored under a
    random UUID so that a crafted name can never influence the storage path.
    """
    if not name:
        return "resume"
    name = unicodedata.normalize("NFKC", name)
    name = name.replace("\\", "/").split("/")[-1]
    name = _SAFE.sub("_", name).strip(" .")
    name = re.sub(r"\.{2,}", ".", name)
    if not name:
        return "resume"
    if len(name) > max_length:
        stem, dot, ext = name.rpartition(".")
        name = (stem[: max_length - len(ext) - 1] + "." + ext) if dot and len(ext) <= 5 else name[:max_length]
    return name


def user_storage_dir(base: Path, user_id: uuid.UUID) -> Path:
    return (base / "resumes" / user_id.hex).resolve()


def new_storage_path(base: Path, user_id: uuid.UUID, extension: str) -> Path:
    if extension not in {"pdf", "docx"}:
        raise ValueError("unsupported extension")
    directory = user_storage_dir(base, user_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = (directory / f"{uuid.uuid4().hex}.{extension}").resolve()
    ensure_within(base, path)
    return path


def ensure_within(base: Path, path: Path) -> None:
    base_resolved = base.resolve()
    if base_resolved != path and base_resolved not in path.resolve().parents:
        raise ValueError("path escapes storage directory")


def delete_file(base: Path, stored_path: str | None) -> None:
    if not stored_path:
        return
    path = Path(stored_path)
    try:
        ensure_within(base, path)
    except ValueError:
        return
    path.unlink(missing_ok=True)


def delete_user_files(base: Path, user_id: uuid.UUID) -> None:
    directory = user_storage_dir(base, user_id)
    try:
        ensure_within(base, directory)
    except ValueError:
        return
    if directory.exists():
        shutil.rmtree(directory, ignore_errors=True)
