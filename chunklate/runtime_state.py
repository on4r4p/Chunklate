from __future__ import annotations


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
