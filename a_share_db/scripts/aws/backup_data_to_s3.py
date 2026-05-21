#!/usr/bin/env python3
"""Back up the configured local data root to timestamped S3 snapshots."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from a_share_db.constant.aws import (
    DEFAULT_KEEP_BACKUPS,
    DEFAULT_S3_BACKUP_PREFIX,
    DEFAULT_S3_STORAGE_CLASS,
    S3_BACKUP_BUCKET_ENV,
    S3_DELETE_BATCH_SIZE,
    SUPPORTED_S3_STORAGE_CLASSES,
    TIMESTAMP_FORMAT,
    TIMESTAMP_RE,
)
from a_share_db.constant.paths import DATA_ROOT
from a_share_db.utils.progress import ProgressReporter


@dataclass(frozen=True)
class LocalFile:
    path: Path
    relative_key: str
    size_bytes: int


@dataclass(frozen=True)
class BackupSnapshot:
    timestamp: str
    prefix: str


def normalize_s3_prefix(prefix: str) -> str:
    return prefix.strip("/")


def make_timestamp(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).strftime(TIMESTAMP_FORMAT)


def iter_local_files(source_root: Path) -> Iterator[LocalFile]:
    for path in sorted(source_root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative_key = path.relative_to(source_root).as_posix()
        yield LocalFile(
            path=path,
            relative_key=relative_key,
            size_bytes=path.stat().st_size,
        )


def collect_local_files(source_root: Path) -> list[LocalFile]:
    if not source_root.exists():
        raise FileNotFoundError(f"Source root does not exist: {source_root}")
    if not source_root.is_dir():
        raise NotADirectoryError(f"Source root is not a directory: {source_root}")
    return list(iter_local_files(source_root))


def get_s3_client(profile: str | None = None, region: str | None = None):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError(
            "boto3 is required. Install dependencies with: "
            "pip install -r a_share_db/requirements.txt"
        ) from exc

    session_kwargs = {}
    if profile:
        session_kwargs["profile_name"] = profile
    if region:
        session_kwargs["region_name"] = region
    return boto3.Session(**session_kwargs).client("s3")


def list_backup_snapshots(s3_client, bucket: str, prefix: str) -> list[BackupSnapshot]:
    root_prefix = normalize_s3_prefix(prefix)
    list_prefix = f"{root_prefix}/" if root_prefix else ""
    paginator = s3_client.get_paginator("list_objects_v2")
    snapshots: list[BackupSnapshot] = []

    for page in paginator.paginate(
        Bucket=bucket,
        Prefix=list_prefix,
        Delimiter="/",
    ):
        for item in page.get("CommonPrefixes", []):
            snapshot_prefix = item["Prefix"].rstrip("/")
            timestamp = snapshot_prefix.rsplit("/", 1)[-1]
            if TIMESTAMP_RE.match(timestamp):
                snapshots.append(
                    BackupSnapshot(timestamp=timestamp, prefix=snapshot_prefix)
                )

    return sorted(snapshots, key=lambda snapshot: snapshot.timestamp)


def iter_current_objects(s3_client, bucket: str, prefix: str) -> Iterator[dict[str, str]]:
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix.rstrip('/')}/"):
        for item in page.get("Contents", []):
            yield {"Key": item["Key"]}


def iter_all_object_versions(
    s3_client,
    bucket: str,
    prefix: str,
) -> Iterator[dict[str, str]]:
    paginator = s3_client.get_paginator("list_object_versions")
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix.rstrip('/')}/"):
        for item in page.get("Versions", []):
            yield {"Key": item["Key"], "VersionId": item["VersionId"]}
        for item in page.get("DeleteMarkers", []):
            yield {"Key": item["Key"], "VersionId": item["VersionId"]}


def batched(items: Iterable[dict[str, str]], batch_size: int) -> Iterator[list[dict[str, str]]]:
    batch: list[dict[str, str]] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def delete_snapshot_prefix(
    s3_client,
    bucket: str,
    snapshot_prefix: str,
    delete_all_versions: bool = False,
) -> int:
    iterator = (
        iter_all_object_versions(s3_client, bucket, snapshot_prefix)
        if delete_all_versions
        else iter_current_objects(s3_client, bucket, snapshot_prefix)
    )
    deleted_count = 0
    for batch in batched(iterator, S3_DELETE_BATCH_SIZE):
        s3_client.delete_objects(
            Bucket=bucket,
            Delete={
                "Objects": batch,
                "Quiet": True,
            },
        )
        deleted_count += len(batch)
    return deleted_count


def upload_snapshot(
    s3_client,
    bucket: str,
    snapshot_prefix: str,
    files: list[LocalFile],
    storage_class: str,
    progress_every: int,
) -> int:
    extra_args = {"StorageClass": storage_class}
    progress = ProgressReporter(
        total=len(files),
        every=progress_every,
        label="Upload",
    )

    uploaded_count = 0
    for index, local_file in enumerate(files, start=1):
        key = f"{snapshot_prefix}/{local_file.relative_key}"
        s3_client.upload_file(
            Filename=str(local_file.path),
            Bucket=bucket,
            Key=key,
            ExtraArgs=extra_args,
        )
        uploaded_count += 1
        progress.maybe_print(
            current=index,
            row_count=uploaded_count,
            extra=f"bytes={local_file.size_bytes}",
        )
    return uploaded_count


def run_s3_data_backup(
    bucket: str,
    source_root: Path = DATA_ROOT,
    prefix: str = DEFAULT_S3_BACKUP_PREFIX,
    keep_backups: int = DEFAULT_KEEP_BACKUPS,
    storage_class: str = DEFAULT_S3_STORAGE_CLASS,
    timestamp: str | None = None,
    profile: str | None = None,
    region: str | None = None,
    dry_run: bool = False,
    delete_all_versions: bool = False,
    progress_every: int = 100,
) -> dict[str, object]:
    if keep_backups < 1:
        raise ValueError("--keep-backups must be at least 1")

    storage_class = storage_class.upper()
    if storage_class not in SUPPORTED_S3_STORAGE_CLASSES:
        allowed = ", ".join(sorted(SUPPORTED_S3_STORAGE_CLASSES))
        raise ValueError(f"Unsupported storage class: {storage_class}. Allowed: {allowed}")

    if timestamp is not None and not TIMESTAMP_RE.match(timestamp):
        raise ValueError("Timestamp must match YYYYMMDDTHHMMSSZ")

    files = collect_local_files(source_root)
    if not files:
        raise RuntimeError(f"No files found under source root: {source_root}")

    total_bytes = sum(item.size_bytes for item in files)
    snapshot_timestamp = timestamp or make_timestamp()
    normalized_prefix = normalize_s3_prefix(prefix)
    snapshot_prefix = (
        f"{normalized_prefix}/{snapshot_timestamp}"
        if normalized_prefix
        else snapshot_timestamp
    )

    s3_client = get_s3_client(profile=profile, region=region)
    existing_snapshots = list_backup_snapshots(s3_client, bucket=bucket, prefix=prefix)
    if any(snapshot.timestamp == snapshot_timestamp for snapshot in existing_snapshots):
        raise RuntimeError(f"Snapshot already exists: s3://{bucket}/{snapshot_prefix}/")

    delete_count = max(0, len(existing_snapshots) - keep_backups + 1)
    snapshots_to_delete = existing_snapshots[:delete_count]
    deleted_objects = 0

    if not dry_run:
        for snapshot in snapshots_to_delete:
            deleted_objects += delete_snapshot_prefix(
                s3_client=s3_client,
                bucket=bucket,
                snapshot_prefix=snapshot.prefix,
                delete_all_versions=delete_all_versions,
            )
        uploaded_count = upload_snapshot(
            s3_client=s3_client,
            bucket=bucket,
            snapshot_prefix=snapshot_prefix,
            files=files,
            storage_class=storage_class,
            progress_every=progress_every,
        )
    else:
        uploaded_count = 0

    return {
        "bucket": bucket,
        "source_root": str(source_root),
        "prefix": normalized_prefix,
        "snapshot_timestamp": snapshot_timestamp,
        "snapshot_prefix": snapshot_prefix,
        "snapshot_uri": f"s3://{bucket}/{snapshot_prefix}/",
        "storage_class": storage_class,
        "existing_backup_count": len(existing_snapshots),
        "keep_backups": keep_backups,
        "deleted_snapshot_count": len(snapshots_to_delete),
        "deleted_object_count": deleted_objects,
        "deleted_snapshots": [snapshot.timestamp for snapshot in snapshots_to_delete],
        "file_count": len(files),
        "total_bytes": total_bytes,
        "uploaded_count": uploaded_count,
        "dry_run": dry_run,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload the configured local data root to S3 as a timestamped backup snapshot."
    )
    parser.add_argument(
        "--bucket",
        default=os.getenv(S3_BACKUP_BUCKET_ENV),
        help=f"Target S3 bucket. Defaults to env var {S3_BACKUP_BUCKET_ENV}.",
    )
    parser.add_argument(
        "--prefix",
        default=DEFAULT_S3_BACKUP_PREFIX,
        help=f"S3 prefix for backup snapshots. Default: {DEFAULT_S3_BACKUP_PREFIX}.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DATA_ROOT,
        help=f"Local directory to back up. Default: {DATA_ROOT}.",
    )
    parser.add_argument(
        "--keep-backups",
        type=int,
        default=DEFAULT_KEEP_BACKUPS,
        help=f"Number of timestamped snapshots to retain. Default: {DEFAULT_KEEP_BACKUPS}.",
    )
    parser.add_argument(
        "--storage-class",
        default=DEFAULT_S3_STORAGE_CLASS,
        help=f"S3 storage class for uploaded objects. Default: {DEFAULT_S3_STORAGE_CLASS}.",
    )
    parser.add_argument(
        "--timestamp",
        help="Override snapshot timestamp in YYYYMMDDTHHMMSSZ format. Default: current UTC time.",
    )
    parser.add_argument(
        "--profile",
        help="AWS profile name for boto3 Session.",
    )
    parser.add_argument(
        "--region",
        help="AWS region name for boto3 Session.",
    )
    parser.add_argument(
        "--delete-all-versions",
        action="store_true",
        help="Delete every object version and delete marker under expired snapshots.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List retention actions and local file counts without deleting or uploading.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Print upload progress every N files. Use 0 to disable. Default: 100.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.bucket:
        print(
            f"S3 bucket is required. Pass --bucket or set {S3_BACKUP_BUCKET_ENV}.",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_s3_data_backup(
            bucket=args.bucket,
            source_root=args.source_root,
            prefix=args.prefix,
            keep_backups=args.keep_backups,
            storage_class=args.storage_class,
            timestamp=args.timestamp,
            profile=args.profile,
            region=args.region,
            dry_run=args.dry_run,
            delete_all_versions=args.delete_all_versions,
            progress_every=args.progress_every,
        )
    except Exception as exc:
        print(f"backup_data_to_s3 failed: {exc}", file=sys.stderr)
        return 1

    if result["dry_run"]:
        print(
            f"Dry run would upload {result['file_count']} files "
            f"({result['total_bytes']} bytes) to {result['snapshot_uri']}"
        )
        print(
            f"Existing backups: {result['existing_backup_count']}; "
            f"would delete snapshots: {result['deleted_snapshot_count']}; "
            f"retention: {result['keep_backups']}."
        )
    else:
        print(
            f"Uploaded {result['uploaded_count']} files "
            f"({result['total_bytes']} bytes) to {result['snapshot_uri']}"
        )
        print(
            f"Existing backups: {result['existing_backup_count']}; "
            f"deleted snapshots: {result['deleted_snapshot_count']} "
            f"({result['deleted_object_count']} objects); "
            f"retention: {result['keep_backups']}."
        )
    if result["deleted_snapshots"]:
        print("Deleted snapshots:")
        for timestamp in result["deleted_snapshots"]:
            print(f"  {timestamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
