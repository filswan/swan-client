#!/usr/bin/env python3
from collections import defaultdict, namedtuple
from fileson import Fileson, gmt_str, gmt_epoch
from logdict import LogDict
from crypt import keygen as kg, AESFile, sha1, calc_etag
import argparse, os, sys, json, signal, time, hashlib, inspect, shutil, re
import boto3, threading
#from minio import Minio
import io

class BotoProgress(object):
    def __init__(self, ptype):
        self._seen = 0
        self._last = 0
        self._type = ptype
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen += bytes_amount
            if self._last + 2**20 > self._seen: return # every 1 MB
            sys.stdout.write("\r%.2f MB %sed" % (self._seen / 2**20, self._type))
            sys.stdout.flush()
            self._last = self._seen

class minioAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        m = re.match('minio://(.+?)/(.+)', values)
        if not m: raise ValueError('minio address in format minio://bucket/objpath')
        setattr(namespace, self.dest, (m.group(1), m.group(2)))

# Return key or if a filename, its contents
def key_or_file(key):
    if isinstance(key, bytes): return key # passthrough
    if os.path.exists(key):
        with open(key, 'r') as f: key = ''.join(f.read().split())
    return bytes.fromhex(key)

# These are the different argument types that can be added to a command
arg_adders = {
'password': lambda p: p.add_argument('password', type=str, nargs='?', help='Password', default=None),
'salt': lambda p: p.add_argument('salt', type=str, nargs='?', help='Salt', default=None),
'input': lambda p: p.add_argument('input', type=str, help='Input file'),
'output': lambda p: p.add_argument('output', type=str, help='Output file'),
'miniopath': lambda p: p.add_argument('miniopath', type=str, action=minioAction,
    help='minio path in form minio://bucket/objpath'),
'deep_archive': lambda p: p.add_argument('-d', '--deep-archive', action='store_true',
    help='Upload to minio DEEP_ARCHIVE storage class'),
'in_obj': lambda p: p.add_argument('in_obj', type=str, help='Input file or minio object name'),
'out_obj': lambda p: p.add_argument('out_obj', type=str, help='Output file or minio object name'),
'key': lambda p: p.add_argument('key', type=str,
    help='Key in hex format or filename of the keyfile'),
'keyfile': lambda p: p.add_argument('-k', '--keyfile', type=str,
    help='Key in hex format or filename of the keyfile'),
'partsize': lambda p: p.add_argument('-p', '--partsize', type=int,
    default=8, help='Multipart upload partsize (default 8 matching boto3)'),
'iterations': lambda p: p.add_argument('-i', '--iterations', type=str,
    default='1M', help='PBKDF2 iterations (default 1M)'),
'dbfile': lambda p: p.add_argument('dbfile', type=str,
    help='Database file (JSON format)'),
'logfile': lambda p: p.add_argument('logfile', type=str,
    help='Logfile to append all operations to'),
'source': lambda p: p.add_argument('source', type=str,
    help='Source directory'),
'destination': lambda p: p.add_argument('destination', type=str,
    help='Destination directory'),
'dir': lambda p: p.add_argument('dir', nargs='?', type=str, default=None,
    help='Directory to scan'),
'verbose': lambda p: p.add_argument('-v', '--verbose', action='count',
    default=0, help='Print verbose status. Repeat for even more.'),
'force': lambda p: p.add_argument('-f', '--force', action='store_true',
    help='Force action without additional prompts'),
        }

logfiles = []
def close_logs():
    while logfiles: logfiles.pop().close()

# Function per command
def keygen(args):
    """Create a 32 byte key for AES256 encryption with a password and salt."""
    if not args.password:
        if args.verbose: print('No password specified, generating random key')
        print(os.urandom(32).hex())
        return
    if not args.salt:
        print('Specify password AND salt or neither!')
        return
    iterations = int(args.iterations.replace('M', '000k').replace('k', '000'))
    start = time.time()
    keyhex = kg(args.password, args.salt, iterations).hex()
    print(keyhex)
    if args.verbose: print('Generating that took %.3f seconds' % (time.time()-start))
keygen.args = 'password salt iterations verbose'.split()

def cryptfile(infile, outfile, verbose=False):
    startTime, bs = time.time(), 0
    while True:
        data = infile.read(65536)
        if not data: break
        outfile.write(data)
        bs += len(data)
    secs = time.time() - startTime
    if verbose: print('%d b in %.1f s, %.2f GiB/s' % (bs, secs, bs/2**30/secs))

def encrypt(args):
    if not args.force and os.path.exists(args.output) and not 'y' in \
            input('Output exists! Do you wish to overwrite? [y/n] '): return
    with AESFile(args.input, 'rb', key_or_file(args.key)) as fin:
        with open(args.output, 'wb') as fout:
            cryptfile(fin, fout, verbose=args.verbose)
encrypt.args = 'input output key verbose force'.split()

def decrypt(args):
    if not args.force and os.path.exists(args.output) and not 'y' in \
            input('Output exists! Do you wish to overwrite? [y/n] '): return
    with open(args.input, 'rb') as fin:
        with AESFile(args.output, 'wb', key_or_file(args.key)) as fout:
            cryptfile(fin, fout, verbose=args.verbose)
decrypt.args = 'input output key verbose force'.split()

def etag(args):
    with open(args.input, 'rb') as f: print(calc_etag(f, args.partsize))
etag.args = 'input partsize'.split()


def backup(args):
    """Perform backup based on latest Fileson DB state."""
    fs = Fileson.load_or_scan(args.dbfile, checksum='sha1')
    if fs.get(':checksum:', None) != 'sha1':
        print('Backup only works with full SHA1 hash. Safety first.')
        return

    log = Fileson.load(args.logfile)
    log.startLogging(args.logfile)
    log[':backup:'] = log.get(':backup:', 0) + 1
    log[':dbfile:'] = args.dbfile
    log[':date_gmt:'] = gmt_str()
    log[':destination:'] = args.destination

    if args.keyfile:
        key = key_or_file(args.keyfile)
        log[':keyhash:'] = sha1(key).hex()

    m = re.match('minio//(.+?)/(.+)', args.destination)
    if m:
        bucket, folder = m.group(1), m.group(2)
        myargs = namedtuple('myargs', 'input miniopath keyfile deep_archive verbose')
        make_backup = lambda a,b: upload(myargs(a, (bucket, folder+'/'+b),
            key if args.keyfile else None, args.deep_archive, True))
    else:
        if args.keyfile:
            myargs = namedtuple('myargs', 'input output key verbose force')
            make_backup = lambda a,b: encrypt(myargs(a,
                os.path.join(args.destination, b), key, False, True))
        else: make_backup = lambda a,b: shutil.copyfile(a,
                os.path.join(args.destination, b))

    uploaded = { log[p]['sha1']: p for p in log.files() }

    seed = log[':date_gmt:'] # for backup filename generation
    for p in fs.files():
        o = fs[p]
        if o['sha1'] in uploaded:
            if args.verbose: print('Already uploaded', p)
            continue
        name = sha1(seed+o['sha1']).hex() # deterministic random name
        print('Backup', p.split(os.sep)[-1], o['sha1'], 'to', name)
        make_backup(os.path.join(fs[':directory:'], p), name)
        log[name] = { 'sha1': o['sha1'], 'size': o['size'] }

    log.endLogging()
backup.args = 'dbfile logfile destination keyfile deep_archive verbose'.split() # args to add

def restore(args):
    """Restore backup based on Fileson DB and backup log."""
    fs = Fileson.load(args.dbfile)
    if fs.get(':checksum:', None) != 'sha1':
        print('Cannot restore without SHA1 hash.')
        return

    log = Fileson.load(args.logfile)

    if args.keyfile:
        key = key_or_file(args.keyfile)
        myargs = namedtuple('myargs', 'input output key verbose force')
        make_restore = lambda a,b: decrypt(myargs(a, b, key, False, True))
        keyhash = sha1(key).hex()
        if keyhash != log[':keyhash:']:
            print(f'Provided key hash {keyhash} does not match backup file!')
            return
    else: make_restore = lambda a,b: shutil.copyfile(a, b)

    uploaded = { log[p]['sha1']: p for p in log.files() }
    for p in sorted(fs.dirs()):
        fp = args.destination
        if p != '.': fp = os.path.join(fp, p)
        print('mkdir', fp)
        os.makedirs(fp, exist_ok=True)
        mtime = gmt_epoch(fs[p]['modified_gmt'])
        os.utime(fp, (mtime, mtime))

    for p in sorted(fs.files()):
        b = uploaded.get(fs[p]['sha1'], None)
        if not b:
            print('Missing', p, fs[p])
            continue
        fp = os.path.join(args.destination, p)
        bp = os.path.join(args.source, b)
        print('get', fp, 'from', bp)
        make_restore(bp, fp)
        mtime = gmt_epoch(fs[p]['modified_gmt'])
        os.utime(fp, (mtime, mtime))
restore.args = 'dbfile logfile source destination keyfile verbose'.split() # args to add

if __name__ == "__main__":
    # register signal handler to close any open log files
    signal.signal(signal.SIGINT, close_logs)

    # create the top-level parser
    parser = argparse.ArgumentParser(description='Fileson backup utilities')
    subparsers = parser.add_subparsers(help='sub-command help')

    # add commands using function metadata and properties
    for name,cmd in inspect.getmembers(sys.modules[__name__]):
        if inspect.isfunction(cmd) and hasattr(cmd, 'args'):
            cmd.parser = subparsers.add_parser(cmd.__name__, description=cmd.__doc__)
            for argname in cmd.args: arg_adders[argname](cmd.parser)
            cmd.parser.set_defaults(func=cmd)

    # parse the args and call whatever function was selected
    args = parser.parse_args()
    if len(sys.argv)==1: parser.print_help(sys.stderr)
    else: args.func(args)