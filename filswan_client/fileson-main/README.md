# Fileson - JSON File database tools

Fileson is a set of Python scripts to create JSON file databases and
use them to do various things, like compare differences between two
databases. There are a few key files:

* `fileson.py` contains `Fileson` class to read, manipulate and write
Fileson databases.
* `fileson_util.py` is a command-line toolkit to create Fileson
databases and do useful things with them

API documentation (everything very much subject to change) available
at https://fileson.readthedocs.io/en/latest/

## Create a Fileson database

```console
user@server:~$ python3 fileson_util.py scan files.fson ~/mydir
```

Fileson databases are essentially log files with JSON objects per row,
containing directory and file information (name, modified date, size)
for `~/mydir` and some additional metadata for each `scan` (changes to
entries are appended to the end).

To calculate an SHA1 checksum for the files as well:

```console
user@server:~$ python3 fileson_util.py scan files.fson ~/mydir -c sha1
```

Calculating SHA1 checksums is somewhat slow, around 1 GB/s on modern m.2 SSD
and 150 MB/s on a mechanical drive, so you can use `-c sha1fast` to only
include the beginning of the file. It will differentiate most cases quite
well.

Fileson databases are versioned. Once a database exists, repeated call to
`fileson_util.py scan` will update the database, keeping track of the changes.
You can then use this information to view changes between given runs, etc.

Normally SHA1 checksums are carried over if the previous version had a
file with same name, size and modification time. For a stricter version, you
can use `-s` or `--strict` to require full path match. Note that this means
calculating new checksum for all moved files.

## Duplicate detection

Once you have a Fileson database ready, you can do fun things like see if
you have any duplicates in your folder (cryptic string before duplicates
identifies the checksum collision, whether it is based on size or sha1):

```console
user@server:~$ python3 fileson_util.py duplicates pics.fson

1afc8e06e081b772eadd6a981a83f67077e2ef10
2009/2009-03-07/DSC_3962-2.NEF
2009/2009-03-07/DSC_3962.NEF
```

Many folders tend to have a lot of small files common (including empty files),
for example source code with git repositories, and that is OK so you can
use for example `-m 1M` to only show duplicates that have a minimum size of 1 MB.

You can skip database creation and give a directory to the command as well:

```console
user@server:~$ python3 fileson_util.py duplicates /mnt/d/SomeFolder -m 1M -c sha1fast
```

## Change detection

Once you have a Fileson database or two, you can compare them with
`fileson_util.py diff`. Like the duplicate command, one or both can be a directory.
Note that two files with different checksum types will essentially differ on all
files.

```console
user@server:~$ python3 fileson_util.py diff myfiles-2010.fson myfiles-2020.fson \
  myfiles-2010-2020.delta
```

The `myfiles-2010-2020.delta` now contains a row per difference between
the two databases/directories -- files that exist only in origin, only in target, or
have changed.

Let's say you move `some.zip` around a bit (JSON formatted for clarity):

```console
user@server:~$ python3 fileson_util.py scan files.fson ~/mydir -c sha1
user@server:~$ mv ~/mydir/some.zip ~/mydir/subdir/newName.zip
user@server:~$ python3 fileson_util.py diff files.fson ~/mydir -c sha1 -p
{"path": ".", "src": {"modified_gmt": "2021-02-28 19:42:05"},
    "dest": {"modified_gmt": "2021-02-28 19:42:26"}}
{"path": "some.zip", "src": {"size": 0, "modified_gmt": "2021-02-23 21:57:25"},
    "dest": null}
{"path": "subdir", "src": {"modified_gmt": "2021-02-28 19:42:05"},
    "dest": {"modified_gmt": "2021-02-28 19:42:26"}}
{"path": "subdir/newName.zip", "src": null,
    "dest": {"size": 0, "modified_gmt": "2021-02-23 21:57:25"}}
```

Doing an incremental backup would involve grabbing the deltas which have
`src` set to `null`. With SHA1 checksums, you could also only upload the new
file if the file blob has not been uploaded before (keeping a separate Fileson
object log of backed up files).

Loading Fileson databases has special syntax similar to `git` where you can
revert to previous versions with `db.fson~1` to get the previous version or
`db.fson~3` to back down 3 steps. This makes printing out changes after a scan
a breeze. Instead of the `fileson_util.py diff` invocation above, you could
update the db and see what changed:

```console
user@server:~$ python3 fileson_util.py scan files.fson
user@server:~$ python3 fileson_util.py diff files.fson~1 files.fson -p
[ same output as the above diff ]
```

Note that you did not have to specify checksum type or directory, as it
is detected automatically from the Fileson DB.

# Use Fileson for simple backups to local or cloud

Fileson contains a robust set of utilities to make backups locally or
into S3, either unencrypted or with secure AES256 encryption. For S3
you need to have `boto3` client configured first.

## Encryption

Encryption is done with 256 bit key that you can generate easily:

```console
user@server:~$ python3 fileson_backup.py keygen password salt > my.key
```

Now `my.key` contains a 64-hex key generated with given password and
salt (with PBKDF2 using AES256 and 1 million iterations by default).
You can use the key to encrypt and decrypt data.

```console
user@server:~$ python3 fileson_backup.py encrypt some.txt some.enc my.key
user@server:~$ python3 fileson_backup.py decrypt some.enc some2.txt my.key
user@server:~$ diff some.txt some2.txt
```

## Uploading to S3 and downloading

A simple upload/download client is also provided:

```console
user@server:~$ python3 fileson_backup.py upload some.txt s3://mybucket/objpath
user@server:~$ python3 fileson_backup.py download s3://mybucket/objpath some2.txt
user@server:~$ diff some.txt some2.txt
```

Just add `-k my.key` to encrypt/decrypt files on the fly with `upload` and `download`.

## Backup up a Fileson-scanned directory

Once you have a Fileson database at hand, you can do a backup run. Certain
considerations:

1. Base path of files is taken from Fileson DB, so if you used a relative
path when scanning, backup command needs to be run in the same directory.
2. To avoid backing up same files over and over, second command is a
backup logfile, essentially recording SHA1 hashes and locations of files
backed up.
3. You need to specify either a local directory or S3 path

Backup log is essentially a Fileson DB for your backup location,
and it is written line-by-line as backup is progressing. So if the
backup process gets interrupted, you can just rerun the backup command
and it should resume with next item that was not yet backed up.

Here is an example of simple backup to a local folder:

```console
user@server:~$ python3 fileson_scan.py scan db.fson ~/mydir -c sha1
user@server:~$ python3 fileson_backup.py backup db.fson db_backup.log /mnt/backup
```

That's it. Once files change, re-run `scan` to update changes and then
`backup` to upload any added objects.

Note: Support for removing files that no longer exist in `db.fson` from backup
location is not yet done.
