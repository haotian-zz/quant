# AWS Backup Scripts

This directory contains AWS helper scripts for `a_share_db`.

Current command:

```bash
python3 a_share_db/scripts/aws/backup_data_to_s3.py \
  --bucket quant-922593397137-us-east-1-an \
  --profile quant-s3-backup \
  --storage-class STANDARD
```

The default backup target is:

```text
s3://quant-922593397137-us-east-1-an/quant/a_share_db/data_backups/{YYYYMMDDTHHMMSSZ}/...
```

The script uploads the configured local data root. By default this is:

```text
/Volumes/QuantDB/a_share_db/data
```

It keeps the newest 10 timestamped backups by default, and deletes the oldest
backup before uploading a new one when there are already 10 backups.

## Credential Model

Recommended setup:

```text
Mac local profile: quant-base
  -> uses IAM user access key for quant-backup-user
  -> can only call sts:AssumeRole

Mac local profile: quant-s3-backup
  -> uses quant-base as source_profile
  -> assumes IAM role QuantS3BackupRole
  -> gets temporary S3 backup permissions
```

The script should use:

```bash
--profile quant-s3-backup
```

## AWS Resources

Use these names:

```text
AWS account: 922593397137
S3 bucket:   quant-922593397137-us-east-1-an
IAM user:    quant-backup-user
IAM role:    QuantS3BackupRole
Region:      us-east-1
S3 prefix:   quant/a_share_db/data_backups/
```

## Create IAM User

Create an IAM user:

```text
IAM -> Users -> Create user
User name: quant-backup-user
Console access: disabled
```

Create an access key for CLI use:

```text
IAM -> Users -> quant-backup-user -> Security credentials -> Create access key
Use case: Command Line Interface (CLI)
```

Save the access key id and secret access key. They are only shown once.

## User Permission Policy

Attach this policy to `quant-backup-user`. It does not grant S3 access. It only
allows the user to assume the backup role.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAssumeQuantS3BackupRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::922593397137:role/QuantS3BackupRole"
    }
  ]
}
```

## Role Trust Policy

Set this trust policy on `QuantS3BackupRole`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowQuantBackupUserAssumeRole",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::922593397137:user/quant-backup-user"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

This answers: who is allowed to assume this role?

## Role S3 Permission Policy

Attach this policy to `QuantS3BackupRole`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOnlyBackupPrefix",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:ListBucketVersions",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": "arn:aws:s3:::quant-922593397137-us-east-1-an",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "quant/a_share_db/data_backups/",
            "quant/a_share_db/data_backups/*"
          ]
        }
      }
    },
    {
      "Sid": "WriteAndDeleteBackupObjects",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:DeleteObjectVersion",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": "arn:aws:s3:::quant-922593397137-us-east-1-an/quant/a_share_db/data_backups/*"
    }
  ]
}
```

If bucket versioning stays disabled, `s3:ListBucketVersions` and
`s3:DeleteObjectVersion` are not required, but keeping them is harmless for this
restricted prefix.

## Local AWS Profile Setup

Configure the base profile with the `quant-backup-user` access key:

```bash
aws configure --profile quant-base
```

Use:

```text
AWS Access Key ID:     access key for quant-backup-user
AWS Secret Access Key: secret key for quant-backup-user
Default region name:   us-east-1
Default output format: json
```

`~/.aws/credentials` should contain:

```ini
[quant-base]
aws_access_key_id = ...
aws_secret_access_key = ...
```

`~/.aws/config` should contain:

```ini
[profile quant-base]
region = us-east-1
output = json

[profile quant-s3-backup]
role_arn = arn:aws:iam::922593397137:role/QuantS3BackupRole
source_profile = quant-base
region = us-east-1
output = json
```

Do not put `role_arn` under `[profile quant-base]`. `quant-base` is the source
profile. `quant-s3-backup` is the assume-role profile used by scripts.

## Verify Credentials

Check the base IAM user:

```bash
aws sts get-caller-identity --profile quant-base
```

Expected ARN shape:

```text
arn:aws:iam::922593397137:user/quant-backup-user
```

Check the assumed role:

```bash
aws sts get-caller-identity --profile quant-s3-backup
```

Expected ARN shape:

```text
arn:aws:sts::922593397137:assumed-role/QuantS3BackupRole/...
```

Check S3 prefix access:

```bash
aws s3 ls s3://quant-922593397137-us-east-1-an/quant/a_share_db/data_backups/ \
  --profile quant-s3-backup
```

An empty prefix can return no rows. That is OK if the command exits successfully.

## Dry Run

```bash
python3 a_share_db/scripts/aws/backup_data_to_s3.py \
  --bucket quant-922593397137-us-east-1-an \
  --profile quant-s3-backup \
  --storage-class STANDARD \
  --dry-run
```

## Single File Upload Test

The backup script accepts a directory as `--source-root`. To test one file while
preserving the production path shape, stage it in `/tmp`:

```bash
mkdir -p /tmp/a_share_db_s3_test/metadata
cp /Volumes/QuantDB/a_share_db/data/metadata/trade_calendar.csv \
  /tmp/a_share_db_s3_test/metadata/

python3 a_share_db/scripts/aws/backup_data_to_s3.py \
  --bucket quant-922593397137-us-east-1-an \
  --profile quant-s3-backup \
  --source-root /tmp/a_share_db_s3_test \
  --prefix quant/a_share_db/data_backups \
  --storage-class STANDARD \
  --progress-every 1
```

The uploaded object key will look like:

```text
quant/a_share_db/data_backups/{YYYYMMDDTHHMMSSZ}/metadata/trade_calendar.csv
```

## Full Backup

```bash
python3 a_share_db/scripts/aws/backup_data_to_s3.py \
  --bucket quant-922593397137-us-east-1-an \
  --profile quant-s3-backup \
  --storage-class STANDARD
```

## Bucket Settings

Recommended bucket settings for this backup workflow:

```text
Bucket type:         General purpose
Bucket versioning:   Disabled
Default encryption:  SSE-S3
Bucket Key:          Disabled unless using SSE-KMS
Storage class:       STANDARD
```
