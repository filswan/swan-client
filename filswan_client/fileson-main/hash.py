import sys
import hashlib

def sha_file(filename, quick=False):
    sha1 = hashlib.sha1()
    with open(filename, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data: break
            sha1.update(data)
            if quick: break
    return sha1.hexdigest()

if __name__ == "__main__":
    print(sha_file(sys.argv[1]))
