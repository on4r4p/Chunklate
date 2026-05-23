from __future__ import annotations

from dataclasses import dataclass
import itertools
import math
import os
import struct
from typing import Any


VALID_IHDR_COLOR_TYPES = ("0", "2", "3", "4", "6")
GETSPEC_COLOR_CHUNKS = (b"IHDR", b"tRNS", b"bKGD", b"sBIT")
MINIMAL_CHUNKS = (b"PNG", b"IHDR", b"IDAT", b"IEND")
CRITICAL_CHUNKS = (b"PNG", b"IHDR", b"PLTE", b"IDAT", b"IEND")
CHUNKS = (
    b"sBIT",
    b"IEND",
    b"sPLT",
    b"tRNS",
    b"fRAc",
    b"hIST",
    b"dSIG",
    b"sTER",
    b"iCCP",
    b"sRGB",
    b"zTXt",
    b"gAMA",
    b"IDAT",
    b"sCAL",
    b"cHRM",
    b"bKGD",
    b"tEXt",
    b"tIME",
    b"iTXt",
    b"IHDR",
    b"gIFx",
    b"gIFg",
    b"oFFs",
    b"pCAL",
    b"PLTE",
    b"gIFt",
    b"pHYs",
    b"eXIf",
)
PRIVATE_CHUNKS = (
    b"cmOD",
    b"cmPP",
    b"cpIp",
    b"mkBF",
    b"mkBS",
    b"mkBT",
    b"mkTS",
    b"spAL",
    b"pcLb",
    b"prVW",
    b"JDAT",
    b"JSEP",
    b"DHDR",
    b"FRAM",
    b"SAVE",
    b"SEEK",
    b"nEED",
    b"DEFI",
    b"BACK",
    b"MOVE",
    b"CLON",
    b"SHOW",
    b"CLIP",
    b"LOOP",
    b"ENDL",
    b"PROM",
    b"fPRI",
    b"eXPI",
    b"BASI",
    b"IPNG",
    b"PPLT",
    b"PAST",
    b"TERM",
    b"DISC",
    b"pHYg",
    b"DROP",
    b"DBYK",
    b"ORDR",
    b"MAGN",
    b"MEND",
)
BEFORE_PLTE = (b"PNG", b"IHDR", b"gAMA", b"cHRM", b"iCCP", b"sRGB", b"sBIT")
AFTER_PLTE = (b"tRNS", b"hIST", b"bKGD")
BEFORE_IDAT = (
    b"PNG",
    b"sPLT",
    b"sBIT",
    b"pHYs",
    b"tRNS",
    b"hIST",
    b"gAMA",
    b"iCCP",
    b"sRGB",
    b"cHRM",
    b"PLTE",
    b"IHDR",
    b"bKGD",
)
BEFORE_IDAT2 = (
    b"IHDR",
    b"sPLT",
    b"sBIT",
    b"pHYs",
    b"tRNS",
    b"hIST",
    b"gAMA",
    b"iCCP",
    b"sRGB",
    b"cHRM",
    b"PLTE",
    b"bKGD",
)
UNIQUE_CHUNK = (
    b"PNG",
    b"sBIT",
    b"IEND",
    b"tRNS",
    b"hIST",
    b"sTER",
    b"iCCP",
    b"sRGB",
    b"gAMA",
    b"sCAL",
    b"cHRM",
    b"bKGD",
    b"IHDR",
    b"oFFs",
    b"pCAL",
    b"PLTE",
    b"pHYs",
    b"IEND",
    b"eXIf",
)
NO_ORDER_CHUNKS = (b"tIME", b"tEXt", b"zTXt", b"iTXt", b"fRAc", b"gIFg", b"gIFx", b"gIFt")
CHUNKS_LEN_NOT_FIXED = (b"PLTE", b"tRNS", b"hIST")
ALLCHUNKS = CHUNKS + PRIVATE_CHUNKS
LIBPNG_ERR = (
    "libpng error:",
    "Too much image data",
    "Out of memory",
    " in PLTE",
    "Invalid palette",
    " in IDAT",
    "is too large for this architecture",
    " in IHDR",
    "bad result",
    "conversion not supported",
    "known incorrect sRGB profile",
)


@dataclass(frozen=True)
class GetSpecContext:
    color_type: str
    min_resolution: int
    min_resolution_product: int
    chunks_spec: dict[bytes, dict[str, tuple[Any, Any, Any, Any]]]


def min_res_iter(min_res: int) -> int:
    count = 0
    for width in range(1, min_res):
        for _height in range(1, width + 1):
            count += 2
    return count


def estimate_max_resolution(file_size: int) -> int:
    if file_size < 77:
        calc = math.floor(((file_size) * 8 - 1) / 2) * 86 + 1
    else:
        calc = math.floor(((file_size - 77) * 8 - 1) / 2) * 86 + 1
    return int(math.sqrt(calc))


def estimate_max_resolution_from_file(file_path: str) -> tuple[int, int]:
    file_size = os.path.getsize(file_path)
    return estimate_max_resolution(file_size), file_size


def resolution_iteration_bounds(idat_byte_count: int, color_type_label: str) -> tuple[int, int]:
    min_resolution = int(idat_byte_count / 64)
    if min_resolution > 10000:
        min_resolution = int(min_resolution / 2)
    if color_type_label.endswith(":minres"):
        return min_resolution, min_res_iter(min_resolution)
    return min_resolution, min_resolution * min_resolution


def normalize_chunk_format(chunk_format: Any) -> Any:
    if any(item in ["!I", "!H", "!B"] for item in chunk_format):
        return chunk_format

    normalized = []
    for index, item in enumerate(chunk_format):
        if item == "!":
            normalized.append("%s%s" % (chunk_format[index], chunk_format[index + 1]))
    return normalized


def expand_chunk_data_item(item: Any) -> tuple[Any, ...]:
    if "i for i in range(" in item:
        start = int(item.split("range(")[1].split(",")[0])
        end = int(item.split(",")[1].split(")")[0])
        return tuple((i for i in range(start, end)))
    return tuple(item)


def expand_spec_values(
    product: Any,
    chunk_length_spec: Any,
    chunk_format: Any,
    chunk_data: Any,
    iter_count: int,
) -> tuple[Any, Any, tuple[Any, ...], tuple[tuple[Any, ...], ...]]:
    expanded_data = []
    expanded_format = []
    chunk_length_spec = chunk_length_spec * iter_count

    for index in range(0, iter_count):
        index += 1
        if index > 1:
            product = product * product

        for chunk_format_item in chunk_format:
            expanded_format.append(chunk_format_item)

        for chunk_data_item in chunk_data:
            expanded_data.append(expand_chunk_data_item(chunk_data_item))

    return product, chunk_length_spec, tuple(expanded_format), tuple(expanded_data)


def apply_custom_spec_selection(
    chunk_data: tuple[tuple[Any, ...], ...],
    struct_index: Any,
    min_resolution: int,
) -> tuple[int, tuple[tuple[Any, ...], ...]]:
    custom_product = []
    custom_struct = []
    for index in struct_index:
        double, dragon = itertools.tee(chunk_data[index])
        custom_product.append(double)
        custom_struct.append(tuple(dragon))

    custom_count = 1
    for item in custom_product:
        for count, _ in enumerate(item):
            pass
        custom_count *= count + 1

    if 0 in struct_index and 1 in struct_index:
        custom_count *= min_resolution

    return custom_count, tuple(custom_struct)


def build_chunks_spec(
    current_year: int,
    idat_byte_count: int,
    max_resolution: int,
    min_resolution: int,
    min_resolution_product: int,
) -> dict[bytes, dict[str, tuple[Any, Any, Any, Any]]]:
    ThisYear = current_year
    IBN = idat_byte_count
    ibn = int(idat_byte_count / 64)
    Mxr = max_resolution
    Mnr = min_resolution
    MnrF = min_resolution_product

    return {
            b"IHDR": {
                "nocolortype:maxres": (
                    ((Mxr - 1) * (Mxr - 1)) * 5 * 5 * 2,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mxr),
                        ("i for i in range(1,%s)"%Mxr),
                        (1, 2, 4, 8, 16),
                        (0, 2, 3, 4, 6),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "nocolortype:medres": (
                    ((ibn - 1) * (ibn - 1)) * 5 * 5 * 2,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%ibn),
                        ("i for i in range(1,%s)"%ibn),
                        (1, 2, 4, 8, 16),
                        (0, 2, 3, 4, 6),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "nocolortype:minres:custom": (
                    MnrF * 5 * 5 * 2,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        (1, 2, 4, 8, 16), (0, 2, 3, 4, 6), ("0"), ("0"), (0, 1)),
                ),
                "nocolortype:minres": (
                    MnrF * 5 * 5 * 2,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (("i for i in range(1,%s)"%Mnr), (1, 2, 4, 8, 16), (0, 2, 3, 4, 6), ("0"), ("0"), (0, 1)),
                ),
                "colortype:0:minres:custom": (
                    MnrF * 10,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        (1, 2, 4, 8, 16),
                        ("0"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),

                "colortype:0:minres": (
                    MnrF * 10,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mnr),
                        (1, 2, 4, 8, 16),
                        ("0"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:0:medres": (
                    ((ibn - 1) * (ibn - 1)) *10,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%ibn),
                        ("i for i in range(1,%s)"%ibn),
                        (1, 2, 4, 8, 16),
                        ("0"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:0:maxres": (
                    ((Mxr - 1) * (Mxr - 1)) *10,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mxr),
                        ("i for i in range(1,%s)"%Mxr),
                        (1, 2, 4, 8, 16),
                        ("0"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:2:minres:custom": (
                    MnrF * 4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        (8, 16),
                        ("2"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),

                "colortype:2:minres": (
                    MnrF * 4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(0,%s)"%Mnr),
                        (8, 16),
                        ("2"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:2:medres": (
                    ((ibn - 1) * (ibn - 1)) *4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%ibn),
                        ("i for i in range(1,%s)"%ibn),
                        (8, 16),
                        ("2"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:2:maxres": (
                    ((Mxr - 1) * (Mxr - 1)) *4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mxr),
                        ("i for i in range(1,%s)"%Mxr),
                        (8, 16),
                        ("2"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:3:minres:custom": (
                    MnrF * 8,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        (1, 2, 4, 8),
                        ("3"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:3:minres": (
                    MnrF * 8,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mnr),
                        (1, 2, 4, 8),
                        ("3"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:3:medres": (
                    ((ibn - 1) * (ibn - 1)) *8,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%ibn),
                        ("i for i in range(1,%s)"%ibn),
                        (1, 2, 4, 8),
                        ("3"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:3:maxres": (
                    ((Mxr - 1) * (Mxr - 1)) *8,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mxr),
                        ("i for i in range(1,%s)"%Mxr),
                        (1, 2, 4, 8),
                        ("3"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:4:minres:custom": (
                    MnrF * 4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        (8, 16),
                        ("4"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:4:minres": (
                    MnrF * 4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mnr),
                        (8, 16),
                        ("4"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:4:medres": (
                    ((ibn - 1) * (ibn - 1)) *4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%ibn),
                        ("i for i in range(1,%s)"%ibn),
                        (8, 16),
                        ("4"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:4:maxres": (
                    ((Mxr - 1) * (Mxr - 1)) *4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mxr),
                        ("i for i in range(1,%s)"%Mxr),
                        (8, 16),
                        ("4"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:6:minres:custom": (
                    MnrF * 4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        ("i for i in range(1,%s)"%int(IBN / 64)),
                        (8, 16),
                        ("6"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:6:minres": (
                    MnrF * 4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mnr),
                        (8, 16),
                        ("6"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:6:medres": (
                    ((ibn - 1) * (ibn - 1)) *4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%ibn),
                        ("i for i in range(1,%s)"%ibn),
                        (8, 16),
                        ("6"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
                ),
                "colortype:6:maxres": (
                    ((Mxr - 1) * (Mxr - 1)) *4,
                    26,
                    ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1,%s)"%Mxr),
                        ("i for i in range(1,%s)"%Mxr),
                        (8, 16),
                        ("6"),
                        ("0"),
                        ("0"),
                        (0, 1),
                    ),
           ),
            },
            b"PLTE": {
                "nocolortype": (
                    16581375,
                    (6, 1536),
                    ("!B", "!B", "!B"),
                    (
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                    ),
                )
            },
            b"tRNS": {
                "colortype:0": (65535, (4, 1024), ("!H"), ("i for i in range(0,65536)")),
                "colortype:2": (
                    196605,
                    (12, 3072),
                    ("!H", "!H", "!H"),
                    (
                        ("i for i in range(0,65536)"),
                        ("i for i in range(0,65536)"),
                        ("i for i in range(0,65536)"),
                    ),
                ),
                "colortype:3": (255, (2, 512), ("!B"), ("i for i in range(0,256)")),
            },
            b"gAMA": {"nocolortype": (100000, 8, ("!I"), ("i for i in range(0,100001)"))},
            b"cHRM": {
                "nocolortype": (
                    800000,
                    64,
                    ("!I", "!I", "!I", "!I", "!I", "!I", "!I", "!I"),
                    (
                        ("i for i in range(0,100001)"),
                        ("i for i in range(0,100001)"),
                        ("i for i in range(0,100001)"),
                        ("i for i in range(0,100001)"),
                        ("i for i in range(0,100001)"),
                        ("i for i in range(0,100001)"),
                        ("i for i in range(0,100001)"),
                        ("i for i in range(0,100001)"),
                    ),
                )
            },
            b"sRGB": {"nocolortype": (4, 2, ("!B"), (0, 1, 2, 3))},
            b"bKGD": {
                "colortype:0": ((65535), 4, ("!H"), ("i for i in range(0,65536)")),
                "colortype:2": (
                    (196605),
                    12,
                    ("!H", "!H", "!H"),
                    (
                        ("i for i in range(0,65536)"),
                        ("i for i in range(0,65536)"),
                        ("i for i in range(0,65536)"),
                    ),
                ),
                "colortype:3": ((255), 2, ("!B"), ("i for i in range(0,256)")),
                "colortype:4": ((65535), 4, ("!H"), ("i for i in range(0,65536)")),
                "colortype:6": (
                    (196605),
                    12,
                    ("!H", "!H", "!H"),
                    (
                        ("i for i in range(0,65536)"),
                        ("i for i in range(0,65536)"),
                        ("i for i in range(0,65536)"),
                    ),
                ),
            },
            b"pHYs": {
                "nocolortype": (
                    (4611686014132420609),
                    18,
                    ("!I", "!I", "!B"),
                    (
                        ("i for i in range(0,2147483647)"),
                        ("i for i in range(0,2147483647)"),
                        (0, 1),
                    ),
                )
            },
            b"sBIT": {
                "colortype:0": (255, 2, ("!B"), ("i for i in range(0,256)")),
                "colortype:2": (
                    16581375,
                    6,
                    ("!B", "!B", "!B"),
                    (
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                    ),
                ),
                "colortype:3": (
                    16581375,
                    6,
                    ("!B", "!B", "!B"),
                    (
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                    ),
                ),
                "colortype:4": (
                    65025,
                    4,
                    ("!B", "!B"),
                    (("i for i in range(0,256)"), ("i for i in range(0,256)")),
                ),
                "colortype:6": (
                    16581375,
                    8,
                    ("!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                        ("i for i in range(0,256)"),
                    ),
                ),
            },
            b"hIST": {"nocolortype": (65536, (4, 1024), ("!H"), ("i for i in range(0,65536)"))},
            b"tIME": {
                "nocolortype": (
                    ((1970 - ThisYear) * 12 * 31 * 23 * 59 * 60),
                    14,
                    ("!H", "!B", "!B", "!B", "!B", "!B"),
                    (
                        ("i for i in range(1970,%s)"%str(ThisYear+1)),
                        ("i for i in range(1,13)"),
                        ("i for i in range(1,32)"),
                        ("i for i in range(0,24)"),
                        ("i for i in range(0,60)"),
                        ("i for i in range(0,61)"),
                    ),
                )
            },
            b"IDAT": {
                "nocolortype": (
                    256,
                    (2,4), #limited due to human life time .
                    ("!B"),
                    (
                        ("i for i in range(0,256)"),
                    ),
                )
            },
            b"IEND": {"nocolortype": (1, 8, ("!I"), ("1229278788"))},

        }


def find_chunk_spec(chunks_spec: dict[Any, dict[Any, Any]], chunk_name: Any, color_type: str) -> Any | None:
    for key in chunks_spec:
        for color, bytes_spec in chunks_spec[key].items():
            if key == chunk_name and color == color_type:
                return bytes_spec
    return None


def select_spec_fields(
    product: Any,
    chunk_length_spec: Any,
    chunk_format: Any,
    chunk_data: Any,
    color_type: str,
    fields: list[str] | tuple[str, ...],
) -> tuple[Any, ...] | None:
    to_return = []
    for field in fields:
        if field == "All":
            return (
                product,
                len(str(product)),
                chunk_length_spec,
                chunk_format,
                chunk_data,
                color_type,
            )
        if field == "Product":
            to_return.append(product)
            to_return.append(len(str(product)))
        elif field == "Length":
            to_return.append(chunk_length_spec)
        elif field == "Format":
            to_return.append(chunk_format)
        elif field == "Data":
            to_return.append(chunk_data)
        elif field == "Color":
            to_return.append(color_type)

    if len(to_return) > 0:
        return tuple(to_return)
    return None


def resolve_getspec_result(
    bytes_spec: tuple[Any, Any, Any, Any],
    color_type: str,
    fields: list[str] | tuple[str, ...],
    mode: str,
    struct_index: Any,
    iter_count: int,
    min_resolution: int,
) -> tuple[Any, ...] | None:
    product = bytes_spec[0]
    chunk_length_spec = bytes_spec[1]
    chunk_format = normalize_chunk_format(bytes_spec[2])
    chunk_data = bytes_spec[3]

    product, chunk_length_spec, chunk_format, chunk_data = expand_spec_values(
        product,
        chunk_length_spec,
        chunk_format,
        chunk_data,
        iter_count,
    )

    if mode == "Custom":
        product, chunk_data = apply_custom_spec_selection(
            chunk_data,
            struct_index,
            min_resolution,
        )

    return select_spec_fields(
        product,
        chunk_length_spec,
        chunk_format,
        chunk_data,
        color_type,
        fields,
    )


def getspec_color_type(
    chunk_name: bytes,
    mode: str,
    brute_level: int,
    ihdr_color: Any,
    ihdr_height: int,
    ihdr_width: int,
    pandora_box: dict[Any, Any],
    cornucopia: dict[Any, Any],
    pandemonium: dict[Any, Any],
    allchunks: list[bytes] | tuple[bytes, ...],
    skip_bad_crc: bool,
) -> str:
    if chunk_name in GETSPEC_COLOR_CHUNKS:
        return color_type_label(
            chunk_name,
            mode,
            brute_level,
            ihdr_color,
            ihdr_height,
            ihdr_width,
            pandora_box,
            cornucopia,
            pandemonium,
            allchunks,
            skip_bad_crc,
        )
    return "nocolortype"


def build_getspec_context(
    current_year: int,
    chunk_name: bytes,
    mode: str,
    idat_byte_count: int,
    max_resolution: int,
    brute_level: int,
    ihdr_color: Any,
    ihdr_height: int,
    ihdr_width: int,
    pandora_box: dict[Any, Any],
    cornucopia: dict[Any, Any],
    pandemonium: dict[Any, Any],
    allchunks: list[bytes] | tuple[bytes, ...],
    skip_bad_crc: bool,
) -> GetSpecContext:
    color_type = getspec_color_type(
        chunk_name,
        mode,
        brute_level,
        ihdr_color,
        ihdr_height,
        ihdr_width,
        pandora_box,
        cornucopia,
        pandemonium,
        allchunks,
        skip_bad_crc,
    )
    min_resolution, min_resolution_product = resolution_iteration_bounds(
        idat_byte_count,
        color_type,
    )
    return GetSpecContext(
        color_type=color_type,
        min_resolution=min_resolution,
        min_resolution_product=min_resolution_product,
        chunks_spec=build_chunks_spec(
            current_year=current_year,
            idat_byte_count=idat_byte_count,
            max_resolution=max_resolution,
            min_resolution=min_resolution,
            min_resolution_product=min_resolution_product,
        ),
    )


def resolve_getspec(
    context: GetSpecContext,
    chunk_name: bytes,
    fields: list[str] | tuple[str, ...],
    mode: str,
    struct_index: Any,
    iter_count: int,
) -> tuple[Any, ...] | None:
    bytes_spec = find_chunk_spec(context.chunks_spec, chunk_name, context.color_type)
    if bytes_spec is None:
        return None
    return resolve_getspec_result(
        bytes_spec,
        context.color_type,
        fields,
        mode,
        struct_index,
        iter_count,
        context.min_resolution,
    )


def estimate_idat_bytes_from_hex(data_hex: str, known_chunks: tuple[bytes, ...] = CHUNKS) -> int:
    byte_count = 0
    last_byte_count = 0
    needle = 0
    idat_switch = False
    enough = False

    while needle < len(data_hex):
        scope_hex = data_hex[needle : needle + 8]
        if len(scope_hex) < 8:
            break
        if enough:
            break

        try:
            scope = bytes.fromhex(scope_hex)
        except ValueError:
            needle += 1
            continue

        if scope == b"IDAT":
            idat_switch = True
            if last_byte_count == 0:
                last_byte_count = needle
            else:
                byte_count += (needle - last_byte_count) - 24
                last_byte_count = needle
        elif idat_switch:
            for chunk in known_chunks:
                if chunk == scope:
                    byte_count += (needle - last_byte_count) - 24
                    last_byte_count = needle
                    enough = True
                    break
        needle += 1

    return int(byte_count / 2)


def iter_product_values(chunk_data: Any, color_type: str):
    for candidate in itertools.product(*chunk_data):
        if color_type.endswith("minres"):
            for width in range(1, candidate[0] + 1):
                width_first = tuple([candidate[0]] + [width] + list(candidate[1:]))
                yield width_first
                height_first = tuple([width] + [candidate[0]] + list(candidate[1:]))
                if height_first != width_first:
                    yield height_first
        else:
            yield candidate


def random_sample_hex(data: Any, color_type: str, chunk_format: Any, random_float) -> str | None:
    bvalue = b""
    idx = 0
    lncf = len(chunk_format) - 1
    for candidate in iter_product_values(data, color_type):
        if random_float() < 0.5:
            for item in candidate:
                if idx < lncf:
                    bvalue += struct.pack(chunk_format[idx], int(item))
                    idx += 1
                else:
                    bvalue += struct.pack(chunk_format[idx], int(item))
                    idx = 0
            return bvalue.hex()
    return None


def ihdr_state_is_safe(
    pandora_box: dict[Any, Any],
    cornucopia: dict[Any, Any],
    pandemonium: dict[Any, Any],
    allchunks: list[bytes] | tuple[bytes, ...],
    ihdr_color: Any,
    ihdr_height: int,
    ihdr_width: int,
    skip_bad_crc: bool,
) -> tuple[bool, bool]:
    safe_value = True
    width_unknown = False
    height_unknown = False

    for key in pandora_box:
        if "IHDR" in str(key):
            if "Wrong Crc" in str(key) and skip_bad_crc is False:
                if str(key) not in cornucopia:
                    safe_value = False
            if "bad adaptive filter" in str(key):
                if str(key) not in cornucopia:
                    safe_value = False
            if "-IHDR Color" in str(key):
                if str(key) not in cornucopia:
                    safe_value = False
            if "IHDR: CRC error" in str(key):
                if str(key) not in cornucopia:
                    safe_value = False
            if "StructIndex:0" in str(key):
                width_unknown = True
            if "StructIndex:1" in str(key):
                height_unknown = True

    use_min_res = width_unknown and height_unknown

    for _file, file_value in pandemonium.items():
        for errors, errors_values in file_value.items():
            if "Filling with a dummy chunk" in errors:
                for tools, _tools_values in errors_values.items():
                    chunk_name = "".join(
                        [
                            chunk.decode(errors="ignore")
                            for chunk in allchunks
                            if chunk.decode(errors="ignore") in tools
                        ]
                    )
                    if chunk_name == "IHDR":
                        safe_value = False

    if ihdr_color not in VALID_IHDR_COLOR_TYPES:
        safe_value = False

    if ihdr_height == 0 or ihdr_width == 0:
        safe_value = False

    return safe_value, use_min_res


def color_type_label(
    get_chunk: bytes,
    mode: str,
    brute_level: int,
    ihdr_color: Any,
    ihdr_height: int,
    ihdr_width: int,
    pandora_box: dict[Any, Any],
    cornucopia: dict[Any, Any],
    pandemonium: dict[Any, Any],
    allchunks: list[bytes] | tuple[bytes, ...],
    skip_bad_crc: bool,
) -> str:
    safe_value, use_min_res = ihdr_state_is_safe(
        pandora_box,
        cornucopia,
        pandemonium,
        allchunks,
        ihdr_color,
        ihdr_height,
        ihdr_width,
        skip_bad_crc,
    )

    if safe_value is False:
        if get_chunk == b"IHDR":
            if brute_level == 0:
                if mode == "Custom" and not use_min_res:
                    return "nocolortype:minres:custom"
                return "nocolortype:minres"
            if brute_level == 1:
                return "nocolortype:medres"
            return "nocolortype:maxres"
        return "nocolortype"

    if brute_level == 0:
        if mode == "Custom" and not use_min_res:
            return "colortype:" + str(ihdr_color) + ":minres:custom"
        return "colortype:" + str(ihdr_color) + ":minres"
    if brute_level == 1:
        return "colortype:" + str(ihdr_color) + ":medres"
    return "colortype:" + str(ihdr_color) + ":maxres"
