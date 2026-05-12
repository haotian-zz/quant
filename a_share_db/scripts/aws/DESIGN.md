# S3 Data Backup Design

## Goal

Back up the entire local `a_share_db/data` directory to S3 as timestamped snapshots.
The backup command is intended to run periodically after local data updates.

## Snapshot Layout

Each run writes one immutable snapshot under a sortable UTC timestamp:

```text
s3://{bucket}/{prefix}/{YYYYMMDDTHHMMSSZ}/...
```

Default values:

```text
source root: a_share_db/data
prefix:      quant/a_share_db/data_backups
retention:   10 snapshots
storage:     GLACIER
```

Example object keys:

```text
quant/a_share_db/data_backups/20260512T061530Z/metadata/stock_basic.csv
quant/a_share_db/data_backups/20260512T061530Z/market_data/daily/none/600519.csv
quant/a_share_db/data_backups/20260512T061530Z/logs/etl_log.csv
```

The relative path below `a_share_db/data` is preserved in S3.

## Retention

Before uploading a new snapshot, the command lists existing snapshots directly below
`{prefix}/`. Snapshot directories must match:

```text
YYYYMMDDTHHMMSSZ
```

If the number of existing snapshots is greater than or equal to `--keep-backups`,
the oldest snapshots are deleted first so that the new upload finishes with at most
`--keep-backups` snapshots.

For example, with `--keep-backups 10`:

```text
existing snapshots: 10
delete oldest:      1
upload new:         1
final snapshots:    10
```

Deletion does not require restoring Glacier objects.

## Versioned Buckets

In a non-versioned bucket, deleting a snapshot prefix removes the objects.

In a versioned bucket, normal S3 deletion creates delete markers and old versions may
continue to consume storage. Use `--delete-all-versions` when the retention policy
must permanently delete every version and delete marker under the old snapshot prefix.

## Storage Class

The default storage class is `GLACIER` (S3 Glacier Flexible Retrieval). Override it
when needed:

```bash
--storage-class STANDARD
--storage-class GLACIER_IR
--storage-class DEEP_ARCHIVE
```

Glacier storage classes can have minimum storage duration charges. A retention window
shorter than the minimum billing period can still incur early deletion charges.

## Command

```bash
python3 a_share_db/scripts/aws/backup_data_to_s3.py \
  --bucket quant-922593397137-us-east-1-an
```

Useful options:

```bash
python3 a_share_db/scripts/aws/backup_data_to_s3.py \
  --bucket quant-922593397137-us-east-1-an \
  --prefix quant/a_share_db/data_backups \
  --keep-backups 10 \
  --storage-class GLACIER \
  --progress-every 100
```

Dry run:

```bash
python3 a_share_db/scripts/aws/backup_data_to_s3.py \
  --bucket quant-922593397137-us-east-1-an \
  --dry-run
```

AWS credentials and region are resolved by boto3's normal provider chain, including
environment variables, shared AWS config files, IAM roles, and SSO sessions.
