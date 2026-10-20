"""
Bang ma VISCII: bang ma tieng Viet cu ma game dung cho chuoi (ten nhan vat, ten map, ten vat pham).
File nay duoc tao tu dong boi cong_cu/tao_bang_viscii.py tu bang chuan cua glibc.
"""

BANG_VISCII = (
    '\x00\x01\u1eb2\x03\x04\u1eb4\u1eaa\x07\x08\t\n\x0b\x0c\r\x0e\x0f'
    '\x10\x11\x12\x13\u1ef6\x15\x16\x17\x18\u1ef8\x1a\x1b\x1c\x1d\u1ef4\x1f'
    ' !"#$%&\'()*+,-./'
    '0123456789:;<=>?'
    '@ABCDEFGHIJKLMNO'
    'PQRSTUVWXYZ[\\]^_'
    '`abcdefghijklmno'
    'pqrstuvwxyz{|}~\x7f'
    '\u1ea0\u1eae\u1eb0\u1eb6\u1ea4\u1ea6\u1ea8\u1eac\u1ebc\u1eb8\u1ebe\u1ec0\u1ec2\u1ec4\u1ec6\u1ed0'
    '\u1ed2\u1ed4\u1ed6\u1ed8\u1ee2\u1eda\u1edc\u1ede\u1eca\u1ece\u1ecc\u1ec8\u1ee6\u0168\u1ee4\u1ef2'
    '\xd5\u1eaf\u1eb1\u1eb7\u1ea5\u1ea7\u1ea9\u1ead\u1ebd\u1eb9\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7\u1ed1'
    '\u1ed3\u1ed5\u1ed7\u1ee0\u01a0\u1ed9\u1edd\u1edf\u1ecb\u1ef0\u1ee8\u1eea\u1eec\u01a1\u1edb\u01af'
    '\xc0\xc1\xc2\xc3\u1ea2\u0102\u1eb3\u1eb5\xc8\xc9\xca\u1eba\xcc\xcd\u0128\u1ef3'
    '\u0110\u1ee9\xd2\xd3\xd4\u1ea1\u1ef7\u1eeb\u1eed\xd9\xda\u1ef9\u1ef5\xdd\u1ee1\u01b0'
    '\xe0\xe1\xe2\xe3\u1ea3\u0103\u1eef\u1eab\xe8\xe9\xea\u1ebb\xec\xed\u0129\u1ec9'
    '\u0111\u1ef1\xf2\xf3\xf4\xf5\u1ecf\u1ecd\u1ee5\xf9\xfa\u0169\u1ee7\xfd\u1ee3\u1eee'
)

_BANG_NGUOC = {ky_tu: ma for ma, ky_tu in enumerate(BANG_VISCII)}


def giai_ma(du_lieu):
    """bytes VISCII (lay tu game) -> chuoi Python."""
    return "".join(BANG_VISCII[b] for b in du_lieu)


def ma_hoa(chuoi):
    """chuoi Python -> bytes VISCII (de so sanh hoac gui vao game)."""
    return bytes(_BANG_NGUOC[ky_tu] for ky_tu in chuoi)
