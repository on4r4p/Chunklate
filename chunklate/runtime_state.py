from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SampleSelection:
    sample: Any
    sample_name: str
    cloneswar: Any


@dataclass(frozen=True)
class LoadedSampleData:
    data_bytes: bytes
    data_hex: str


def main_loop_scan_reset_values() -> dict[str, object]:
    return {
        "IBN": 0,
        "IDAT_Bytes_Len": 0,
        "IDAT_Datastream": "",
    }


def main_loop_error_reset_values() -> dict[str, object]:
    return {
        "Bad_Current_Name": False,
        "Bad_Ancillary": False,
        "Bad_No_Next_Chunk": False,
        "Bad_Next_Name": False,
        "Bad_Next_Ancillary": False,
        "Bad_Length": False,
        "Bad_Infos": False,
        "Bad_Crc": False,
        "Bad_Critical": False,
        "Bad_Missplaced": False,
        "Skip_Bad_Current_Name": False,
        "Skip_Bad_Ancillary": False,
        "Skip_Bad_No_Next_Chunk": False,
        "Skip_Bad_Next_Name": False,
        "Skip_Bad_Next_Ancillary": False,
        "Skip_Bad_Length": False,
        "Skip_Bad_Infos": False,
        "Skip_Bad_Crc": False,
        "Skip_Bad_Critical": False,
        "Skip_Bad_Missplaced": False,
        "Skip_Bad_Libpng": False,
        "EOF": False,
        "Show_Must_Go_On": False,
    }


def main_loop_history_reset_values() -> dict[str, object]:
    return {
        "IDAT_Bytes_Len_History": [],
        "IDAT_Avg_Len": "",
        "Chunks_History": [],
        "Chunks_History_Index": [],
        "Bytes_History": [],
        "Loading_txt": "",
        "ERRORSFLAG": [],
        "PandoraBox": {},
        "Cornucopia": {},
        "SideNotes": [],
    }


def select_sample(current_sample: Any, cloneswar: Any, *, basename) -> SampleSelection:
    if cloneswar is False:
        return SampleSelection(
            sample=current_sample,
            sample_name=basename(current_sample),
            cloneswar=cloneswar,
        )
    return SampleSelection(
        sample=cloneswar,
        sample_name=basename(cloneswar),
        cloneswar=False,
    )


def sample_data_from_bytes(data: bytes) -> LoadedSampleData:
    return LoadedSampleData(data_bytes=data, data_hex=data.hex())


def load_sample_data(sample: Any, *, opener=open) -> LoadedSampleData:
    with opener(sample, "rb") as handle:
        return sample_data_from_bytes(handle.read())
