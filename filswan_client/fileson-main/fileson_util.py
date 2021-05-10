#!/usr/bin/env python3
from collections import defaultdict
from fileson import Fileson
import argparse, os, sys, json, random, inspect

# These are the different argument types that can be added to a command
arg_adders = {
'checksum': lambda p: p.add_argument('-c', '--checksum', type=str,
    choices=Fileson.summer.keys(), default=None,
    help='Checksum method (if relevant in the context)'),
'db_or_dir': lambda p: p.add_argument('db_or_dir', type=str,
    help='Database file or directory, supports db.fson~1 history mode.'),
'dbfile': lambda p: p.add_argument('dbfile', type=str,
    help='Database file (JSON format)'),
'delta': lambda p: p.add_argument('delta', nargs='?',
    type=argparse.FileType('w'), default='-',
    help='filename for delta or - for stdout (default)'),
'dest': lambda p: p.add_argument('dest', type=str, help='Destination DB'),
'dir': lambda p: p.add_argument('dir', nargs='?', type=str, default=None,
    help='Directory to scan'),
'force': lambda p: p.add_argument('-f', '--force', action='store_true',
    help='Force action without additional prompts'),
'minsize': lambda p: p.add_argument('-m', '--minsize', type=str, default='0',
    help='Minimum size (e.g. 100, 10k, 1M)'),
'percent': lambda p: p.add_argument('percent', type=int,
    help='Percentage of checksums to check'),
'src': lambda p: p.add_argument('src', type=str,
    help='Source DB, use src.fson~1 to access previous version etc.'),
'strict': lambda p: p.add_argument('-s', '--strict', action='store_true',
    help='Skip checksum only on full path (not just name) match'),
'verbose': lambda p: p.add_argument('-v', '--verbose', action='count',
    default=0, help='Print verbose status. Repeat for even more.'),
        }

# Function per command
def duplicates(args):
    """Look for duplicates using Fileson DB."""
    minsize = int(args.minsize.replace('G', '000M').replace('M', '000k').replace('k', '000'))

    fs = Fileson.load_or_scan(args.db_or_dir, checksum=args.checksum)
    files = [(p,fs[p]) for p in fs.files() if fs[p]['size'] >= minsize]
    checksum = fs.get(':checksum:', None) or 'size'

    if checksum == 'size': print('No checksum, using file size!')
        
    csums = defaultdict(list)
    for p,o in files: csums[o[checksum]].append(p)

    for csum,ps in csums.items():
        if len(ps)>1: print(csum, *ps, sep='\n')
duplicates.args = 'db_or_dir minsize checksum'.split() # args to add

def stats(args):
    """Show statistics of a Fileson DB."""
    fs = Fileson.load_or_scan(args.db_or_dir)

    print(len(fs.files()), 'files', len(fs.dirs()), 'directories')

    if args.verbose:
        print('Metadata history:')
        for i,t in enumerate(fs.log):
            if len(t)==2 and t[0][0]==':': print(f'{i:05d}: {t[0]:12s} {t[1]}')

    dirs = list(fs.dirs())
    if dirs: print('Max dir depth', max(p.count(os.sep) for p in dirs))

    files = list(fs.files())
    if files:
        print('Total file size %.2f GiB' %
                (sum(fs[p]['size'] for p in files)/2**30))
        print('Max file size %.3f GiB' % 
                (max(fs[p]['size'] for p in files)/2**30))
stats.args = ['db_or_dir', 'verbose'] # args to add

def checksum(args):
    """Change or re-run checksums for a Fileson DB."""
    fs = Fileson.load(args.dbfile)
    checksum = fs.get(':checksum:', None)
    if not checksum:
        print('No checksum in the DB!')
        return
    if args.verbose: print('Existing checksum', checksum)

    directory = args.dir or fs.get(':directory:', None)
    if not directory:
        print('No directory specified and none in DB!')
        return
    if args.verbose: print('Base directory', directory)

    files = {p: o for p,r,o in fs.genItems('files')}
    n = args.percent * len(files) // 100
    if args.verbose: print('Rechecking', n, 'files\' checksums')
    csummer = Fileson.summer[fs.checksum]

    for p in random.sample(files.keys(), k=n):
        f = files[p]
        fp = os.path.join(args.dir, p)
        old = f[fs.checksum]
        new = csummer(fp, f)
        if old == new:
            if args.verbose: print('OK', fp.split(os.sep)[-1])
        else:
            print('FAIL', fp)
            print('old', old, 'vs.', new, 'new')
checksum.args = 'dbfile percent dir force verbose'.split() # args to add

def diff(args):
    """Show difference between two Fileson objects (or directories)."""
    src = Fileson.load_or_scan(args.src)
    dest = Fileson.load_or_scan(args.dest)
    for p in sorted(set(src) | set(dest)):
        s = src.get(p, None)
        d = dest.get(p, None)
        if p[0] != ':' and s != d:
            json.dump({'path': p, 'src': s, 'dest': d}, args.delta)
            args.delta.write('\n')
diff.args = 'src dest delta'.split() # args to add

def copy(args):
    """Make a copy of (specified version of the) database."""
    if not os.path.exists(args.dest) or args.force or 'y' in \
            input('Do you wish to overwrite target? (Y/N) ').lower():
        fs = Fileson.load(args.src)
        fs.save(args.dest)
copy.args = 'src dest force'.split() # args to add

def scan(args):
    """Create fileson JSON file database."""
    fs = Fileson.load(args.dbfile)

    if not args.dir:
        if not ':directory:' in fs:
            print('No directory specified and none in DB!')
            return
        args.dir = fs[':directory:']
        if args.verbose: print('Using', args.dir, 'from DB')

    # If checksum not set but exists in fs, get it
    if not args.checksum:
        args.checksum = fs.get(':checksum:', None)
        if args.verbose and args.checksum:
            print('Using checksum', args.checksum, 'from DB')

    fs.scan(args.dir, checksum=args.checksum, verbose=args.verbose, strict=args.strict)
    fs.save(args.dbfile)
scan.args = 'dbfile dir checksum strict verbose'.split() # args to add

if __name__ == "__main__":
    # create the top-level parser
    parser = argparse.ArgumentParser(description='Fileson database utilities')
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
