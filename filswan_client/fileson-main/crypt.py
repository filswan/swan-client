"""On-the-fly AES256 CTR encryption with file-like interface."""
from Crypto.Cipher import AES
from Crypto.Util import Counter
import hashlib, os

def sha1(s: object) -> bytes:
    """One-off sha1 hashing of bytes or a string (encoded as utf8)."""
    m = hashlib.sha1()
    if isinstance(s, str): m.update(s.encode('utf8'))
    else: m.update(s)
    return m.digest()

# Courtesy of Tom Gardiner at Teppen.io
# https://teppen.io/2018/10/23/aws_s3_verify_etags/
def calc_etag(infile, partsize=8):
    """Calculate AWS S3 Etag based on partsize."""
    md5_digests = []
    if partsize < 2**16: partsize *= 2**20
    for chunk in iter(lambda: infile.read(partsize), b''):
      md5_digests.append(hashlib.md5(chunk).digest())
    if len(md5_digests)==1: return md5_digests[0].hex()
    return hashlib.md5(b''.join(md5_digests)).hexdigest() + '-' + \
        str(len(md5_digests))

def keygen(password: str, salt: str, iterations: int=10**6) -> bytes:
    """Generate a 32 byte key from password and salt using PBKDF2.

    Args:
        password (str): Password string (encoded to utf8)
        salt (str): Salt (encoded to utf8)
        iterations (int): Number of iterations, 1M is the default

    Returns:
        bytes: 32 byte key
    """
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf8'),
        salt.encode('utf8'), iterations)

class AESFile:
    """On-the-fly AES encryption (on read) and decryption (on write).

    Uses CTR mode with 16 byte initial value (iv). When reading,
    returns the iv first, then encrypted payload. On writing, first
    16 bytes are assumed to contain the iv.

    Does the bare minimum, you may get errors if not careful. See
    Python's :class:`io.IOBase` for details on most methods.

    Args:
        filename (str): File to open for reading (encrypt on the fly)
            or writing (decrypt on the fly)
        mode (str): Either 'rb' or 'wb', just like with :func:`io.open`
        key (bytes): Encryption/decryption key (32 bytes for AES256)
        iv (bytes): Initial value (16 bytes), if not set uses os.urandom

    Returns:
        AESFile: File-like object
    """
    def __initAES(self) -> None:
        self.obj = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(
            128, initial_value=int.from_bytes(self.iv, byteorder='big')))

    def __init__(self, filename: str, mode: str, key: bytes, iv: bytes=None) -> None:
        """Init the class. Documented in class docstring."""
        if not mode in ('wb', 'rb'): 
            raise RuntimeError('Only rb and wb modes supported!')

        self._pos = 0
        self.key = key
        self.mode = mode
        self.fp = open(filename, mode)

        if mode == 'rb':
            self.iv = iv or os.urandom(16)
            self.__initAES()
        else: self.iv = bytearray(16)

    def __enter__(self) -> None:
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.fp.close()

    def write(self, data : bytes) -> int:
        """Write data and decrypt on the fly. First 16 bytes absorbed as iv."""
        datalen = len(data)
        if self._pos < 16:
            ivlen = min(16-self._pos, datalen)
            self.iv[self._pos:self._pos+ivlen] = data[:ivlen]
            self._pos += ivlen
            if self._pos == 16: self.__initAES() # ready to init now
            data = data[ivlen:]
        if data: self._pos += self.fp.write(self.obj.decrypt(data))
        return datalen

    def read(self, size: int=-1) -> bytes:
        """Read data and encrypt on the fly. First 16 bytes returned are iv."""
        ivpart = b''
        if self._pos < 16:
            if size == -1: ivpart = self.iv
            else:
                ivpart = self.iv[self._pos:min(16, self._pos+size)]
                size -= len(ivpart)
        enpart = self.obj.encrypt(self.fp.read(size)) if size else b''
        self._pos += len(ivpart) + len(enpart)
        return ivpart + enpart

    def tell(self) -> int:
        """Tell the current position.

        Note that when reading, goes 16 bytes further than the file
        being read, due to the fact that iv is injected to start.
        """
        return self._pos

    # only in read mode (encrypting)
    def seek(self, offset: int, whence: int=0) -> None:
        """Seek to given position.

        Only offset 0 is supported (relative to start, current position
        or end depending on whence parameter). Otherwise dummy-encrypting
        stuff might get really slow.

        Args:
            offset (int): Offset, has to be 0
            whence (int): 0,1,2 for absolute,relative,end-based

        Raises:
            RuntimeError: If offset is nonzero
        """
        if whence==0 and offset==self._pos: return # nop
        if offset: raise RuntimeError('Only seek(0, whence) supported')

        self.fp.seek(offset, whence) # offset=0 works for all whences
        if whence==0: # absolute positioning, offset=0
            self._pos = 0
            self.__initAES()
        elif whence==2: # relative to file end, offset=0
            self._pos = 16 + self.fp.tell()

    def close(self) -> None:
        """Close the file stream."""
        self.fp.close()
