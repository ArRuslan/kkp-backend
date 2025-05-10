import hmac
import struct
from base64 import b32decode
from time import time


class Mfa:
    @staticmethod
    def get_code(key: str, timestamp: int | float | None = None) -> str:
        key = key.upper()
        if timestamp is None:
            timestamp = time()
        key = b32decode(key.upper() + "=" * ((-len(key)) % 8))
        counter = struct.pack(">Q", int(timestamp // 30))
        mac = hmac.new(key, counter, "sha1").digest()
        offset = mac[-1] & 0x0f
        binary = struct.unpack(">L", mac[offset:offset + 4])[0] & 0x7fffffff
        return str(binary)[-6:].zfill(6)

    @classmethod
    def get_codes(cls, key: str) -> tuple[str, str]:
        return cls.get_code(key, time() - 5), cls.get_code(key, time() + 1)