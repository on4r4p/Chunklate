#!/usr/bin/python3.6
from argparse import ArgumentParser, SUPPRESS
from threading import Thread
from datetime import datetime
from contextlib import contextmanager
import numpy as np
import sys, os, binascii, re, random, time, zlib, cv2, ctypes, io, tempfile, inspect, difflib, collections, math , itertools


def Betterror(error_msg, def_name):
    try:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        Err_to_log = (
            "!!\nFile: %s has encounter a %s error in %s() at line %s\nError Message:%s\n!!"
            % (fname, exc_type, def_name, exc_tb.tb_lineno, error_msg)
        )
        if DEBUG is True:
            print(Err_to_log)

    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        Err_to_log = (
            "!!\nFile: %s has encounter a %s error in Betterror() at line %s\nError Message:%s\n!!"
            % (fname, exc_type, exc_tb.tb_lineno, e)
        )
        if DEBUG is True:
            print(Err_to_log)

    return Error_Log(Err_to_log)


def Error_Log(Err_to_log):
    global SideNotes
    try:
        CurrentDate = datetime.now()
        logfile = str(sys.path[0]) + "/Chunklate_Errors.log"
        with open(logfile, "a+") as fuck:
            fuck.write(str(CurrentDate) + "\n")
            fuck.write(Err_to_log + "\n")
        if 1 == 1:  # if DEBUG is True:
            SideNotes.append(Err_to_log)

    except Exception as e:
        Betterror(e, inspect.stack()[0][3])


def GetSpec():
    
    if b"IEND" in Chunks_History and Chunks_History[-1] == "IEND": ##TODO proper resolution estimation
            size = IDAT_Bytes_Len
            calc = math.floor(((size - 77) * 8 - 1) / 2) * 86 + 1
            MaxRes = int(math.sqrt(calc))
    else:
        try:
            size = os.path.getsize(FILE_Origin)
            calc = math.floor(((size - 77) * 8 - 1) / 2) * 86 + 1
            MaxRes = int(math.sqrt(calc))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
            MaxRes = 3210

    ThisYear = datetime.now().year
    CHUNKS_SPEC = {
    b"IHDR": {"nocolortype": (26,(8,8,2,2,2,2,2), ((i for i in range(1,MaxRes)),(i for i in range(1,MaxRes)),(1,2,4,8,16),(0,2,3,4,6),("0"),("0"),(0,1)) )},
    b"PLTE": {"nocolortype": ((6, 1536),(2,2,2),((i for i in range(256)) for j in range(3)) )},
    b"tRNS": {
        "colortype:0": ((4, 1024),(4),(i for i in range(65536)) ),
        "colortype:2": ((12, 3072),(4,4,4),((i for i in range(65536)) for j in range(3)) ),
        "colortype:3": ((2, 512),(2),(i for i in range(256))),
    },
    b"gAMA": {"nocolortype": (8,(8),(i for i in range(100001)))},
    b"cHRM": {"nocolortype": (64,(8,8,8,8,8,8,8,8),( (i for i in range(100001)) for j in range(8)) )},
    b"sRGB": {"nocolortype": (2,(2),(0,1,2,3))},
    b"bKGD": {
        "colortype:0": (4,(4),(i for i in range(65536))),
        "colortype:2": (12,(4,4,4),((i for i in range(65536)) for j in range(3)) ),
        "colortype:3": (2,(2),(i for i in range(256))),
        "colortype:4": (4,(4),(i for i in range(65536))),
        "colortype:6": (12,(4,4,4),((i for i in range(65536)) for j in range(3)) ),
    },
    b"pHYs": {"notype": (18,(8,8,2),((i for i in range(2147483647)),(i for i in range(2147483647)),(0,1) ) )},
    b"sBIT": {
        "colortype:0": (2,(2),(i for i in range(256))),
        "colortype:2": (6,(2,2,2),((i for i in range(256)) for j in range(3))),
        "colortype:3": (6,(2,2,2),((i for i in range(256)) for j in range(3))),
        "colortype:4": (4,(2,2),((i for i in range(256)) for j in range(2))),
        "colortype:6": (8,(2,2,2,2),((i for i in range(256)) for j in range(4))),
    },
    b"hIST": {"nocolortype": ((4, 1024),(4),(i for i in range(65536)))},
    b"tIME": {"nocolortype": (14,(4,2,2,2,2,2),(tuple(i for i in range(1970,ThisYear)),tuple(i for i in range(1,13)),tuple(i for i in range(1,32)),tuple(i for i in range(0,24)),tuple(i for i in range(0,60)),tuple(i for i in range(0,61))))},
    }
    return(CHUNKS_SPEC)

def GetInfo(Chunk, data, Dummy=False):
    global SideNotes
    global IDAT_Bytes_Len
    global IDAT_Datastream
    global idatcounter
    global IDAT_Bytes_Len_History
    global IDAT_Avg_Len
    global IHDR_Height
    global IHDR_Width
    global IHDR_Depht
    global IHDR_Color
    global IHDR_Method
    global IHDR_Filter
    global IHDR_Interlace
    global bKGD_Gray
    global bKGD_Red
    global bKGD_Green
    global bKGD_Blue
    global bKGD_Index
    global PLTE_R
    global PLTE_G
    global PLTE_B
    global sPLT_Name
    global sPLT_Depht
    global sPLT_Red
    global sPLT_Green
    global sPLT_Blue
    global sPLT_Alpha
    global sPLT_Freq
    global cHRM_WhiteX
    global cHRM_WhiteY
    global cHRM_Redx
    global cHRM_Redy
    global cHRM_Greenx
    global cHRM_Greeny
    global cHRM_Bluex
    global cHRM_Bluey
    global gAMA
    global hIST
    global gIFID
    global gIFCD
    global gIFDT
    global gIFDT
    global gIFgM
    global gIFgU
    global gIFgT
    global iCCP_Name
    global iCCP_Method
    global iCCP_Profile
    global pHYs_Y
    global pHYs_X
    global pHYs_Unit
    global pCAL_Param
    global pCAL_Key
    global pCAL_Zero
    global pCAL_Max
    global pCAL_Eq
    global pCAL_PNBR
    global sBIT_Gray
    global sBIT_TrueR
    global sBIT_TrueG
    global sBIT_TrueB
    global sBIT_GrayScale
    global sBIT_GrayAlpha
    global sBIT_TrueAlphaR
    global sBIT_TrueAlphaG
    global sBIT_TrueAlphaB
    global sBIT_TrueAlpha
    global iTXt_String_List
    global iTXt_Key_List
    global iTXt_String
    global iTXt_Key
    global sTER
    global tEXt_Key_List
    global tEXt_Str_List
    global tEXt_Key
    global tEXt_Text
    global tIME_Yr
    global tIME_Mth
    global tIME_Day
    global tIME_Hr
    global tIME_Min
    global tIME_Sec
    global tRNS_Gray
    global tRNS_TrueR
    global tRNS_TrueG
    global tRNS_TrueB
    global tRNS_Index
    global zTXt_Key_List
    global zTXt_Str_List
    global zTXt_Key
    global zTXt_sep
    global zTXt_Meth
    global zTXt_Text

    ToFix = []
    iCCP_Name = ""
    iTXt_String = ""
    iTXt_Key = ""
    zTXt_String = ""
    zTXt_Key = ""
    tEXt_Text = ""
    tEXt_Key = ""
    Name = ""
    lastnm = ""

    Candy("Title", "Getting infos about:", Candy("Color", "white", str(Chunk)))

    if Chunk == "PNG":
        Candy(
            "Cowsay", " Well ..That's a start ..At least it looks like a png.", "good"
        )
    if Chunk == "IHDR":
        try:
            IHDR_Height = str(int(data[:8], 16))

        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-Error IHDR Height([0:8]):" + str(e))
        try:
            IHDR_Width = str(int(data[8:16], 16))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-Error IHDR Width([8:16]):" + str(e))
        try:
            IHDR_Depht = str(int(data[16:18], 16))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
            ToFix.append("-Error IHDR Depht([16:18]):" + str(e))

        try:
            IHDR_Color = str(int(data[18:20], 16))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-Error IHDR Color([18:20]):" + str(e))
        try:
            IHDR_Method = str(int(data[20:22], 16))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-Error IHDR Method([20:22]):" + str(e))

        try:
            IHDR_Filter = str(int(data[22:24], 16))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-Error IHDR Filter([22:24]):" + str(e))
        try:
            IHDR_Interlace = str(int(data[24:26], 16))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-Error IHDR Interlace([22:24]):" + str(e))
        try:
            print("-Width    :", Candy("Color", "yellow", IHDR_Height))
            print("-Height   :", Candy("Color", "yellow", IHDR_Width))
            print("-Depht    :", Candy("Color", "yellow", IHDR_Depht))
            print("-Color    :", Candy("Color", "yellow", IHDR_Color))
            print("-Method   :", Candy("Color", "yellow", IHDR_Method))
            print("-Filter   :", Candy("Color", "yellow", IHDR_Filter))
            print("-Interlace:", Candy("Color", "yellow", IHDR_Interlace))

            if len(data) != 26:
                print(
                    "-Bytes number :"
                    + Candy("Color", "red", " Wrong size")
                    + "IHDR size have to always be 13 bytes."
                    + Candy("Emoj", "bad")
                )
                #    print(data)
                ToFix.append("-IHDR size have to always be 13 bytes")

            if len(IHDR_Height) > 0:
                if int(IHDR_Height) > 2147483647:
                    print(
                        "-Height :"
                        + Candy("Color", "red", " Wrong size (Too high)")
                        + " Must be between 1 to 2147483647."
                        + Candy("Emoj", "bad")
                    )
                    ToFix.append(
                        "-IHDR Height Must be between 1 to 2147483647.CIndex([0:8])"
                    )
            else:
                print(
                    "-Height :"
                    + Candy("Color", "red", " Wrong size (Too low)")
                    + " Must be between 1 to 2147483647."
                    + Candy("Emoj", "bad")
                )
                ToFix.append(
                    "-IHDR Height Must be between 1 to 2147483647.CIndex([0:8])"
                )

            if len(IHDR_Width) > 0:
                if int(IHDR_Width) > 2147483647:
                    print(
                        "-Width :"
                        + Candy("Color", "red", " Wrong size (Too high)")
                        + " Must be between 1 to 2147483647."
                        + Candy("Emoj", "bad")
                    )
                    ToFix.append(
                        "-IHDR Width Must be between 1 to 2147483647.CIndex([8:16])"
                    )
            else:
                print(
                    "-Width :"
                    + Candy("Color", "red", " Wrong size (Too low)")
                    + " Must be between 1 to 2147483647."
                    + Candy("Emoj", "bad")
                )
                ToFix.append(
                    "-IHDR Width Must be between 1 to 2147483647.CIndex([8:16])"
                )

            if len(IHDR_Depht) > 0:
                if IHDR_Depht not in ["1", "2", "4", "8", "16"]:
                    print(
                        "-Bit depht :"
                        + Candy("Color", "red", " Wrong bit value")
                        + " Must be 1,2,4,8 or 16 "
                        + Candy("Emoj", "bad")
                    )
                    ToFix.append(
                        "-IHDR Depht: Wrong bit depht (depht must be 1,2,4,8 or 16).CIndex([16:18])"
                    )
            else:
                print(
                    "-Bit depht :"
                    + Candy("Color", "red", " Wrong bit value")
                    + " Must not be empty "
                    + Candy("Emoj", "bad")
                )
                ToFix.append("-IHDR Depht Must not be empty.CIndex([16:18])")

            if len(IHDR_Color) > 0:
                if IHDR_Color not in ["0", "2", "3", "4", "6"]:
                    print(
                        "-IHDR Color :"
                        + Candy("Color", "red", " Wrong bit value")
                        + " Must be 0,2,3,4 or 6 "
                        + Candy("Emoj", "bad")
                    )
                    ToFix.append("-IHDR Color Must be 0,2,3,4 or 6.")
                if IHDR_Color == "2" or IHDR_Color == "4" or IHDR_Color == "6":
                    if IHDR_Depht not in ["8", "16"]:
                        print(
                            "-IHDR Color :"
                            + Candy("Color", "red", " Wrong bit depht ")
                            + "for IHDR Color "
                            + IHDR_Color
                            + " must be 8 or 16 "
                            + Candy("Emoj", "bad")
                        )
                        ToFix.append(
                            "-IHDR Color :Wrong bit depht must be 8 or 16.CIndex([18:20])"
                        )
                if IHDR_Color == "3":
                    if IHDR_Depht not in ["1", "2", "4", "8"]:
                        print(
                            "-IHDR Color :"
                            + Candy("Color", "red", " Wrong bit depht ")
                            + "for IHDR Color 3 must be 1,2,4 or 8"
                            + Candy("Emoj", "bad")
                        )
                        ToFix.append(
                            "-IHDR Color 3: Wrong bit depht with IHDR Color type 3 (depht must be 1,2,4 or 8).CIndex([18:20])"
                        )
            else:
                print(
                    "-IHDR Color %s "
                    % (Candy("Color", "red", "Must not be empty"), Candy("Emoj", "bad"))
                )
                ToFix.append("-IHDR Color Must not be empty.CIndex([18:20])")

            if len(IHDR_Filter) > 0 and IHDR_Filter != "0":
                print(
                    "-Filter Method :"
                    + Candy("Color", "red", " Wrong value")
                    + " must be 0."
                    + Candy("Emoj", "bad")
                )
                ToFix.append(
                    "-IHDR Filter Method Wrong value must be 0.CIndex([22:24])"
                )
            elif len(IHDR_Filter) == 0:
                print(
                    "-Filter Method %s %s "
                    % (Candy("Color", "red", "Must not be empty"), Candy("Emoj", "bad"))
                )
                ToFix.append("-IHDR Filter Method Must not be empty.CIndex([22:24])")
            if len(IHDR_Method) > 0 and IHDR_Method != "0":
                print(
                    "-Compression Algorithms :"
                    + Candy("Color", "red", " Wrong value")
                    + " must be 0."
                    + Candy("Emoj", "bad")
                )
                ToFix.append(
                    "-IHDR Compression Algorithms : Wrong value must be 0.CIndex([20:22])"
                )
            elif len(IHDR_Method) == 0:
                print(
                    "-Compression Algorithms must not be empty %s %s "
                    % (Candy("Color", "red", "Must not be empty"), Candy("Emoj", "bad"))
                )
                ToFix.append(
                    "-IHDR Compression Algorithms must not be empty.CIndex([20:22])"
                )
            if len(IHDR_Interlace) > 0 and (
                IHDR_Interlace != "0" and IHDR_Interlace != "1"
            ):
                print(
                    "-Interlace Method :"
                    + Candy("Color", "red", " Wrong value")
                    + " must be 0 (no interlace) or 1 (Adam7 interlace)."
                    + Candy("Emoj", "bad")
                )
                ToFix.append(
                    "-IHDR Interlace Method :Wrong value must be 0 (no interlace) or 1 (Adam7 interlace).CIndex([22:24])"
                )
            elif len(IHDR_Interlace) == 0:
                print(
                    "-Interlace %s %s "
                    % (Candy("Color", "red", "Must not be empty"), Candy("Emoj", "bad"))
                )
                ToFix.append("-IHDR Interlace Must not be empty.CIndex([22:24])")

            if len(ToFix) > 0:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)
            else:
                print(
                    "\n-Errors Check :"
                    + Candy("Color", "green", " OK ")
                    + Candy("Emoj", "good")
                )

        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-Error IHDR:" + str(e))
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk == "IDAT":
        IDAT_Bytes_Len_History.append(int(Raw_Length, 16))
        try:
            IDAT_Avg_Len = collections.Counter(IDAT_Bytes_Len_History).most_common(1)[
                0
            ][0]
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            IDAT_Avg_Len = IDAT_Bytes_Len_History[-1]
        IDAT_Bytes_Len += len(data)
        IDAT_Datastream += data
        idatcounter += 1
        print("-Image Datastream.")

    if Chunk == "pHYs":
        try:
            pHYs_Y = str(int(data[:8], 16))
            print("-Pixels per unit, Y axis: ", Candy("Color", "yellow", pHYs_Y))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")

            ToFix.append("-Error pHYs Y:" + str(e))
        try:
            pHYs_X = str(int(data[8:16], 16))
            print("-Pixels per unit, X axis: ", Candy("Color", "yellow", pHYs_X))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")

            ToFix.append("-Error pHYs X:" + str(e))
        try:
            pHYs_Unit = str(int(data[16:18], 16))
            print("-Unit specifier         :", Candy("Color", "yellow", pHYs_Unit))
        except (NameError, ValueError) as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")

            ToFix.append("-Error pHYs U:" + str(e))
        try:
            if len(pHYs_Y) > 0:
                if int(pHYs_Y) > 2147483647:
                    print(
                        "-Pixels per unit, Y axis:"
                        + Candy("Color", "red", " Wrong size (Too high)")
                        + " Must be between 1 to 2147483647."
                        + Candy("Emoj", "bad")
                    )

                    ToFix.append(
                        "-Pixels per unit, Y axis: Wrong size (Too high) Must be between 1 to 2147483647."
                    )
            else:
                print(
                    "-Pixels per unit, Y axis :"
                    + Candy("Color", "red", " Wrong size (Too low)")
                    + " Must be between 1 to 2147483647."
                    + Candy("Emoj", "bad")
                )
                ToFix.append(
                    "-Pixels per unit, Y axis: Wrong size (Too low) Must be between 1 to 2147483647."
                )

            if len(pHYs_X) > 0:
                if int(pHYs_X) > 2147483647:
                    print(
                        "Pixels per unit, X axis"
                        + Candy("Color", "red", " Wrong size (Too high)")
                        + " Must be between 1 to 2147483647."
                        + Candy("Emoj", "bad")
                    )
                    ToFix.append(
                        "-Pixels per unit, X axis: Wrong size (Too high) Must be between 1 to 2147483647."
                    )
            else:
                print(
                    "-Pixels per unit, X axis"
                    + Candy("Color", "red", " Wrong size (Too low)")
                    + " Must be between 1 to 2147483647."
                    + Candy("Emoj", "bad")
                )
                ToFix.append(
                    "-Pixels per unit, X axis: Wrong size (Too low) Must be between 1 to 2147483647."
                )

            if len(pHYs_Unit) > 0:
                if pHYs_Unit != "0" and pHYs_Unit != "1":
                    print(
                        "-Unit specifier :"
                        + Candy("Color", "red", " Wrong value")
                        + " Must be between 0 (unknown) or 1(meter)."
                        + Candy("Emoj", "bad")
                    )

                    ToFix.append(
                        "-Unit specifier :Wrong value Must be between 0 (unknown) or 1(meter)."
                    )
            if len(ToFix) > 0:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)
            else:
                print(
                    "\n-Errors Check :"
                    + Candy("Color", "green", " OK ")
                    + Candy("Emoj", "good")
                )

        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")

            ToFix.append("-Error pHys:" + str(e))
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk == "bKGD":
        if IHDR_Color == "0" or IHDR_Color == "4":
            try:
                bKGD_Gray = str(int(data[:4], 16))
                print("-Gray    :", Candy("Color", "yellow", bKGD_Gray))
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                ToFix.append("-Error bKGD Gray:" + str(e))
                if DEBUG is True:
                    print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")

            if len(bKGD_Gray) > 0:
                if int(bKGD_Gray) > (2 ** int(IHDR_Depht)) - 1:
                    print(
                        "-Gray level :"
                        + Candy("Color", "red", " Wrong value")
                        + " Must be less than "
                        + str((2 ** int(IHDR_Depht)) - 1)
                    ) + Candy("Emoj", "bad")
                    ToFix.append(
                        "-Gray level : Wrong value Must be less than"
                        + str((2 ** int(IHDR_Depht)) - 1)
                    )

        if IHDR_Color == "2" or IHDR_Color == "6":
            try:
                try:
                    bKGD_Red = str(int(data[:4], 16))
                    print("-Red    :", Candy("Color", "red", bKGD_Red))
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    ToFix.append("-Error bKGD Red:" + str(e))

                    if DEBUG is True:
                        print(
                            Candy("Color", "red", "Error bKGD Red:"),
                            Candy("Color", "yellow", e),
                        )
                        if PAUSEDEBUG is True or PAUSEERROR is True:
                            Pause("Pause Debug")

                try:
                    bKGD_Green = str(int(data[4:8], 16))
                    print("-Green  :", Candy("Color", "green", bKGD_Green))
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    ToFix.append("-Error bKGD Green:" + str(e))
                    if DEBUG is True:
                        print(
                            Candy("Color", "red", "Error bKGD Green:"),
                            Candy("Color", "yellow", e),
                        )

                        if PAUSEDEBUG is True or PAUSEERROR is True:
                            Pause("Pause Debug")

                try:
                    bKGD_Blue = str(int(data[8:12], 16))
                    print("-Blue   :", Candy("Color", "blue", bKGD_Blue))
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    ToFix.append("-Error bKGD Blue:" + str(e))
                    if DEBUG is True:
                        print(
                            Candy("Color", "red", "Error bKGD Blue:"),
                            Candy("Color", "yellow", e),
                        )
                        if PAUSEDEBUG is True or PAUSEERROR is True:
                            Pause("Pause Debug")

                if len(bKGD_Red) > 0:
                    if int(bKGD_Red) > (2 ** int(IHDR_Depht)) - 1:
                        print(
                            "-Red level :"
                            + Candy("Color", "red", " Wrong value")
                            + " Must be less than "
                            + str((2 ** int(IHDR_Depht)) - 1)
                        ) + Candy("Emoj", "bad")
                        ToFix.append(
                            "-Red level : Wrong value Must be less than "
                            + str((2 ** int(IHDR_Depht)) - 1)
                        )
                if len(bKGD_Green) > 0:
                    if int(bKGD_Green) > (2 ** int(IHDR_Depht)) - 1:
                        print(
                            ""
                            + Candy("Color", "red", "")
                            + " Must be less than "
                            + str((2 ** int(IHDR_Depht)) - 1)
                        ) + Candy("Emoj", "bad")
                        ToFix.append(
                            "-Bkgd_Green Wrong value Must be less than "
                            + str((2 ** int(IHDR_Depht)) - 1)
                        )
                if len(bKGD_Blue) > 0:
                    if int(bKGD_Blue) > (2 ** int(IHDR_Depht)) - 1:
                        print(
                            "-Blue level :"
                            + Candy("Color", "red", " Wrong value")
                            + " Must be less than "
                            + str((2 ** int(IHDR_Depht)) - 1)
                        ) + Candy("Emoj", "bad")
                        ToFix.append(
                            "-Blue level : Wrong value Must be less than "
                            + str((2 ** int(IHDR_Depht)) - 1)
                        )

            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                ToFix.append("-Error Bkgd:" + str(e))

                if DEBUG is True:
                    print(
                        Candy("Color", "red", "Error bKGD:"),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")

        if IHDR_Color == "3":
            try:
                bKGD_Index = str(int(data[:2], 16))
                print("-Palette    :", Candy("Color", "yellow", bKGD_Index))
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                    if PAUSEDEBUG:
                        Pause("Pause Debug")
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)
    if Chunk == "PLTE":

        PLTE_R = []
        PLTE_G = []
        PLTE_B = []

        PLTNbr = len(data)

        if not str(int(PLTNbr) / 3).endswith(".0"):
            print(
                "-%s PLTE length: %s/3= %s (not divisible by 3). %s"
                % (
                    Candy("Color", "red", "Wrong"),
                    PLTNbr,
                    Candy("Color", "red", PLTNbr),
                    Candy("Emoj", "bad"),
                )
            )
            ToFix.append("-PLTE Total palettes number must be divisible by 3")

        for i in range(0, PLTNbr, 6):
            pltr = data[i : i + 2]
            try:
                int(pltr, 16)
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy(
                            "Color", "red", "Error palettes red number " + str(i) + ":"
                        ),
                        Candy("Color", "yellow", e),
                    )
                ToFix.append("-Error PLTER wrong value at" + str(i) + ":" + str(e))

            pltg = data[i + 2 : i + 4]
            try:
                int(pltg, 16)
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy(
                            "Color",
                            "red",
                            "Error palettes green number " + str(i + 2) + ":",
                        ),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                ToFix.append("-Error PLTEG wrong value at " + str(i + 2) + ":" + str(e))

            pltb = data[i + 4 : i + 6]

            try:
                int(pltb, 16)
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy(
                            "Color",
                            "red",
                            "Error palettes blue number " + str(i + 4) + ":",
                        ),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                ToFix.append("-Error PLTEB wrong value at " + str(i + 4) + ":" + str(e))

            PLTE_R.append(str(pltr))
            PLTE_G.append(str(pltg))
            PLTE_B.append(str(pltb))

        print("-%s Red palettes are stored." % Candy("Color", "yellow", len(PLTE_R)))
        if len(PLTE_R) > 256:
            Candy(
                "Color",
                "red",
                "Error palettes red Total number must be < 256 but is : %s"
                % len(PLTE_R),
            )
            ToFix.append("-Error PLTER > 256 :%s" % len(PLTE_R))

        print("-%s Green palettes are stored." % Candy("Color", "yellow", len(PLTE_G)))
        if len(PLTE_G) > 256:
            Candy(
                "Color",
                "red",
                "Error palettes green Total number must be < 256 but is : %s"
                % len(PLTE_G),
            )
            ToFix.append("-Error PLTER > 256 :%s" % len(PLTE_R))
        print("-%s Blue palettes are stored." % Candy("Color", "yellow", len(PLTE_B)))
        if len(PLTE_B) > 256:
            Candy(
                "Color",
                "red",
                "Error palettes blue Total number must be < 256 but is : %s"
                % len(PLTE_B),
            )
            ToFix.append("-Error PLTER > 256 :%s" % len(PLTE_R))
        print(
            "-%s RGB palettes are stored."
            % Candy("Color", "yellow", len(PLTE_R) + len(PLTE_G) + len(PLTE_B))
        )

        if len(IHDR_Depht) > 0:
            if len(PLTE_R) > 2 ** int(IHDR_Depht):
                print(
                    "-PLTE %s Red palettes not in bitdepht range: (must not be > 2 power of image Depht:%s).%s"
                    % (
                        Candy("Color", "red", str(len(pltb) - 1) + " Wrong"),
                        Candy("Color", "yellow", 2 ** int(IHDR_Depht)),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-PLTE Wrong RED %s palettes not in bitdepht range (must not be > 2 power of image Depht:%s)"
                    % (str(len(pltb) - 1), 2 ** int(IHDR_Depht))
                )
            elif len(PLTE_R) == 0:
                print(
                    "-PLTE RED palettes entry must %s . %s"
                    % (Candy("Color", "red", "Not be empty"), Candy("Emoj", "bad"))
                )
                ToFix.append("-PLTE Wrong RED palettes entry must Not be empty")

            if len(PLTE_G) > 2 ** int(IHDR_Depht):
                print(
                    "-PLTE %s  Green palettes not in bitdepht range: (must not be > 2 power of image Depht:%s).%s"
                    % (
                        Candy("Color", "red", str(len(pltb)) + " Wrong"),
                        Candy("Color", "yellow", 2 ** int(IHDR_Depht)),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-PLTE %s wrongGreen palettes not in bitdepht range: (must not be > 2 power of image Depht:%s)"
                    % (str(len(pltb)), 2 ** int(IHDR_Depht))
                )
            elif len(PLTE_G) == 0:
                print(
                    "-PLTE Green palettes entry must %s . %s"
                    % (Candy("Color", "red", "Not be empty"), Candy("Emoj", "bad"))
                )
                ToFix.append("-PLTE Wrong Green palettes entry must Not be empty")

            if len(PLTE_B) > 2 ** int(IHDR_Depht):
                print(
                    "-PLTE %s Blue palettes not in bitdepht range: (must not be > 2 power of image Depht:%s). %s"
                    % (
                        Candy("Color", "red", str(len(pltb)) + " Wrong"),
                        Candy("Color", "yellow", 2 ** int(IHDR_Depht)),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-PLTE Blue palettes not in bitdepht range")
            elif len(PLTE_G) == 0:
                print(
                    "-PLTE Blue palettes entry must %s . %s"
                    % (Candy("Color", "red", "Not be empty"), Candy("Emoj", "bad"))
                )
                ToFix.append("-PLTE Wrong Blue palettes entry must Not be empty")
        else:
            print(
                "-IHDR Depht value %s first.%s"
                % (Candy("Color", "red", "have to be fixed"), Candy("Emoj", "bad"))
            )
            ToFix.append("-IHDR Depht value have to be fixed first")

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

    if Chunk == "sPLT":
        sPLT_Red = []
        sPLT_Green = []
        sPLT_Blue = []
        sPLT_Alpha = []
        sPLT_Freq = []
        sPLT_Depht = []
        sPLT_Name = []
        sPLT_Ln = len(data)
        if sPLT_Ln <= 0:
            print(
                "-sPLT entries must %s . %s"
                % (Candy("Color", "red", "Not be empty"), Candy("Emoj", "bad"))
            )
            ToFix.append("-sPLT entries must Not be empty")

        elif NullFind(data) is False:
            print(
                "-sPLT %s any Null Bytes !%s . %s"
                % (Candy("Color", "red", "haven't found"), Candy("Emoj", "bad"))
            )
            ToFix.append("-sPLT haven't found any Null Bytes !")
        elif sPLT_Ln > 0 and NullFind(data) is not False:
            null_pos = NullFind(data)
            Name = data[:null_pos]
            ChrName = ""
            badchar = ["badchar"]

            for i in range(0, len(Name), 2):
                try:
                    nint = int(data[i : i + 2], 16)
                    nchar = chr(nint)
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    if DEBUG is True:
                        print(
                            Candy("Color", "red", "Error sPLt Name :"),
                            Candy("Color", "yellow", e),
                        )
                        if PAUSEDEBUG is True or PAUSEERROR is True:
                            Pause("Pause Debug")
                    nint = 258
                    nchar = chr(nint)

                if (nint not in range(32, 127)) and (nint not in range(161, 256)):
                    print(
                        "-Character %s at index %s in sPLT_Name\n-Replaced by [€] %s"
                        % (
                            Candy("Color", "red", "not allowed [" + nchar + "]"),
                            Candy("Color", "red", i),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Character not allowed %s at index %s in sPLT_Name\n-Replaced by [€] "
                        % (nchar, i)
                    )
                    ChrName += "€"
                    badchar.append(i)
                else:
                    ChrName += nchar

            if len(badchar) > 1:
                ToFix.append(badchar)

            Depht = str(int(data[null_pos + 2 : null_pos + 4], 16))
            if Depht != "8" and Depht != "16":
                print(
                    "-Sample depth is %s it must be 8 or 16 :%s %s"
                    % (
                        Candy("Color", "red", "not correct"),
                        Candy("Color", "red", Depht),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-Sample depth is not correct it must be 8 or 16")
            pos = 0
            for i in range(sPLT_Ln):
                if Depht == "8":
                    sPLT_Red.append(data[:pos])
                    sPLT_Green.append(data[pos : pos + 2])
                    sPLT_Blue.append(data[pos + 2 : pos + 4])
                    sPLT_Alpha.append(data[pos + 4 : pos + 6])
                    sPLT_Freq.append(data[pos + 6 : pos + 8])
                    pos += 8

                if Depht == "16":
                    sPLT_Red.append(data[:pos])
                    sPLT_Green.append(data[pos : pos + 4])
                    sPLT_Blue.append(data[pos + 4 : pos + 8])
                    sPLT_Alpha.append(data[pos + 8 : pos + 16])
                    sPLT_Freq.append(data[pos + 16 : pos + 24])
                    pos += 24
                else:
                    break

            if len(Name) > 79:
                print(
                    "-Length of sPLT name is %s :%s %s"
                    % (
                        Candy("Color", "red", "not Valid (Too long >79)"),
                        Candy("Color", "red", i),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-Length of sPLT name is not Valid (Too long >79)")

            print("-sPLT name : ", Candy("Color", "white", ChrName))

            print(
                "-%s Suggested Red palettes are stored."
                % Candy("Color", "yellow", len(sPLT_Red))
            )

            if Depht == "8":
                if not str(int(len(sPLT_Red)) / 6).endswith(".0"):
                    print(
                        "-%s Red sPLT length: %s /6= %s (not divisible by 6). %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Red)),
                            str(len(sPLT_Red) / 6),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Red sPLT length: %s /6= %s (not divisible by 6)."
                        % (len(sPLT_Red), str(len(sPLT_Red) / 6))
                    )

            elif Depht == "16":
                if not str(int(len(sPLT_Red)) / 10).endswith(".0"):
                    print(
                        "-%s Red sPLT length: %s/10= %s (not divisible by 10). %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Red)),
                            str(len(sPLT_Red) / 10),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Red sPLT length: %s /10= %s (not divisible by 10)."
                        % (len(sPLT_Red), str(len(sPLT_Red) / 10))
                    )

            print(
                "-%s Suggested Green palettes are stored."
                % Candy("Color", "yellow", len(sPLT_Green))
            )

            if Depht == "8":
                if not str(int(len(sPLT_Green)) / 6).endswith(".0"):
                    print(
                        "-%s Green sPLT length: %s /6= %s (not divisible by 6). %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Green)),
                            str(len(sPLT_Green) / 6),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Green sPLT length: %s /6= %s (not divisible by 6)."
                        % (len(sPLT_Green), str(len(sPLT_Green) / 6))
                    )

            elif Depht == "16":
                if not str(int(len(sPLT_Green)) / 10).endswith(".0"):
                    print(
                        "-%s Green sPLT length: %s/10= %s (not divisible by 10). %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Green)),
                            str(len(sPLT_Green) / 10),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Red sPLT length: %s /10= %s (not divisible by 10)."
                        % (len(sPLT_Green), str(len(sPLT_Green) / 10))
                    )

            print(
                "-%s Suggested Blue palettes are stored."
                % Candy("Color", "yellow", len(sPLT_Blue))
            )

            if Depht == "8":
                if not str(int(len(sPLT_Blue)) / 6).endswith(".0"):
                    print(
                        "-%s Blue sPLT length: %s /6= %s (not divisible by 6). %s "
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Blue)),
                            str(len(sPLT_Blue) / 6),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Green sPLT length: %s /6= %s (not divisible by 6)."
                        % (len(sPLT_Blue), str(len(sPLT_Blue) / 6))
                    )

            elif Depht == "16":
                if not str(int(len(sPLT_Blue)) / 10).endswith(".0"):
                    print(
                        "-%s Blue sPLT length:%s /10= %s (not divisible by 10). %s "
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Blue)),
                            str(len(sPLT_Blue) / 10),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Red sPLT length: %s /10= %s (not divisible by 10)."
                        % (len(sPLT_Blue), str(len(sPLT_Blue) / 10))
                    )

            print(
                "-%s Suggested Alpha palettes are stored."
                % Candy("Color", "yellow", len(sPLT_Alpha))
            )

            if Depht == "8":
                if not str(int(len(sPLT_Alpha)) / 6).endswith(".0"):
                    print(
                        "-%s Alpha sPLT length: %s /6= %s (not divisible by 6). %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Alpha)),
                            str(len(sPLT_Alpha) / 6),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Alpha sPLT length: %s /6= %s (not divisible by 6)."
                        % (len(sPLT_Alpha), str(len(sPLT_Alpha) / 6))
                    )

            elif Depht == "16":
                if not str(int(len(sPLT_Alpha)) / 10).endswith(".0"):
                    print(
                        "-%s Aplha sPLT length:%s /10= %s (not divisible by 10). %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Alpha)),
                            str(len(sPLT_Alpha) / 10),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Alpha sPLT length: %s /10= %s (not divisible by 10)."
                        % (len(sPLT_Alpha), str(len(sPLT_Alpha) / 10))
                    )

            print(
                "-%s Suggested Frequency values are stored."
                % Candy("Color", "yellow", len(sPLT_Freq))
            )

            if Depht == "8":
                if not str(int(len(sPLT_Freq)) / 6).endswith(".0"):
                    print(
                        "-%s Frequency sPLT length: %s /6= %s (not divisible by 6). %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Freq)),
                            str(len(sPLT_Freq) / 6),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Frequency sPLT length: %s /6= %s (not divisible by 6)."
                        % (len(sPLT_Freq), str(len(sPLT_Freq) / 6))
                    )

            elif Depht == "16":
                if not str(int(len(sPLT_Freq)) / 10).endswith(".0"):
                    print(
                        "-%s Frequency sPLT length:%s /10= %s (not divisible by 10). %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", len(sPLT_Freq)),
                            str(len(sPLT_Freq) / 10),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-Wrong Frequency sPLT length: %s /10= %s (not divisible by 10)."
                        % (len(sPLT_Freq), str(len(sPLT_Freq) / 10))
                    )

            sPLT_Depht.append(Depht)
            sPLT_Name.append(Name)

            for nm in sPLT_Name:
                if sPLT_Name.count(nm) > 1 and nm != lastnm:
                    print(
                        "-sPLT can be used multiple times %s share the same name. %s "
                        % (Candy("Color", "red", "but cannot"), Candy("Emoj", "bad"))
                    )
                    lastnm = nm
                    ToFix.append(
                        "-sPLT can be used multiple times but cannot share the same name."
                    )

        if len(ToFix) > 0:
            if len(badchar) > 1:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix, data)
            else:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

    if Chunk == "hIST":
        hIST = []
        if len(data) <= 0:
            print(
                "-hIST must %s . %s"
                % (Candy("Color", "red", "Not be empty"), Candy("Emoj", "bad"))
            )
            ToFix.append("-hIST must Not be empty")

        elif len(data) > 0:

            if b"PLTE" not in Chunks_History and b"sPLT" not in Chunks_History:
                print(
                    "-%s Chunk or %s is missing.(hIST must be used after one of them)"
                    % (Candy("Color", "red", "PLTE"), Candy("Color", "red", "sPLT"))
                )
                ToFix.append(
                    "-PLTE Chunk sPLT is missing.(hIST must be used after one of them)"
                )
            try:
                pos = 0
                for plt in range(0, len(data), 4):
                    hIST.append(data[plt : plt + 4])
                    pos = plt
                print(
                    "-%s Histogram frequencies are stored."
                    % Candy("Color", "yellow", len(hIST))
                )

                if b"PLTE" in Chunks_History:
                    
                    if len(hIST) != int((len(PLTE_R) + len(PLTE_G) + len(PLTE_B))/3):
                        print(
                            "-Histogram frequencies entries %s PLTE entries number %s"
                            % (
                                Candy("Color", "red", "must match"),
                                Candy("Emoj", "bad"),
                            )
                        )
                        ToFix.append(
                            "-Histogram frequencies entries must match PLTE entries number"
                        )

                if b"sPLT" in Chunks_History:
                    if len(hIST) != len(sPLT_Red) + len(sPLT_Green) + len(
                        sPLT_Blue
                    ) + len(sPLT_Aplha):
                        print(
                            "-Histogram frequencies entries %s sPLT entries number %s"
                            % (
                                Candy("Color", "red", "must match"),
                                Candy("Emoj", "bad"),
                            )
                        )
                        ToFix.append(
                            "-Histogram frequencies entries must match sPLT entries number"
                        )

            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix, data)
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

    if Chunk == "tIME":
        if len(data) < 14:
            print(
                "-tIME %s inside tIME data.%s"
                % (Candy("Color", "red", "Not enough bytes"), Candy("Emoj", "bad"))
            )
            ToFix.append("-tIME Not enough bytes inside tIME data.")

        else:
            try:
                tIME_Yr = str(int(data[:4], 16))
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy("Color", "red", "Error tIME Years:"),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                ToFix.append("-tIME Year is > than the current year")
            try:
                tIME_Mth = str(int(data[4:6], 16))
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy("Color", "red", "Error tIME Months:"),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                ToFix.append("-tIME Month value is not valid")
            try:
                tIME_Day = str(int(data[6:8], 16))
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy("Color", "red", "Error tIME Days:"),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                ToFix.append("-tIME Day value is not valid")
            try:
                tIME_Hr = str(int(data[8:10], 16))
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy("Color", "red", "Error tIME Hours:"),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                ToFix.append("-tIME Hour value is not valid")
            try:
                tIME_Min = str(int(data[10:12], 16))
            except Exception as e:
                if DEBUG is True:
                    print(
                        Candy("Color", "red", "Error tIME Minutes:"),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                ToFix.append("-tIME Minute value is not valid")
            try:
                tIME_Sec = str(int(data[12:14], 16))
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy("Color", "red", "Error tIME Seconds:"),
                        Candy("Color", "yellow", e),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                ToFix.append("-tIME Second value is not valid")

            if len(ToFix) == 0:
                print(
                    "-Last Modified: %s/%s/%s %s:%s:%s"
                    % (
                        Candy("Color", "white", tIME_Day),
                        Candy("Color", "white", tIME_Mth),
                        Candy("Color", "white", tIME_Yr),
                        Candy("Color", "white", tIME_Hr),
                        Candy("Color", "white", tIME_Min),
                        Candy("Color", "white", tIME_Sec),
                    )
                )
            if len(str(tIME_Yr)) > 0:
                if int(tIME_Yr) > datetime.now().year:
                    print(
                        "-Year is > than current year    : %s %s"
                        % (Candy("Color", "red", tIME_Yr), Candy("Emoj", "bad"))
                    )
                    ToFix.append("-Year is > than current year" + str(tIME_Yr))
            if len(str(tIME_Mth)) > 0:
                if int(tIME_Mth) not in range(1, 13):
                    print(
                        "-Month value is not valid   : %s %s"
                        % (Candy("Color", "red", tIME_Mth), Candy("Emoj", "bad"))
                    )
                    ToFix.append("-Month value is not valid " + str(tIME_Mth))
            if len(str(tIME_Day)) > 0:
                if int(tIME_Day) not in range(1, 32):
                    print(
                        "-Day value is not valid      : %s %s"
                        % (Candy("Color", "red", tIME_Day), Candy("Emoj", "bad"))
                    )
                    ToFix.append("-Day value is not valid" + str(tIME_Day))
            if len(str(tIME_Hr)) > 0:
                if int(tIME_Hr) not in range(0, 24):
                    print(
                        "-Hour value is not valid     : %s %s"
                        % (Candy("Color", "red", tIME_Hr), Candy("Emoj", "bad"))
                    )
                    ToFix.append("-Hour value is not valid " + str(tIME_Hr))
            if len(str(tIME_Min)) > 0:
                if int(tIME_Min) not in range(0, 60):
                    print(
                        "-Minute value is not valid  : %s %s"
                        % (Candy("Color", "red", tIME_Min), Candy("Emoj", "bad"))
                    )
                    ToFix.append("-Minute value is not valid" + str(tIME_Min))
            if len(str(tIME_Sec)) > 0:
                if int(tIME_Sec) not in range(0, 61):
                    print(
                        "-Second  value is not valid : %s %s"
                        % (Candy("Color", "red", tIME_Sec), Candy("Emoj", "bad"))
                    )
                    ToFix.append("-Second  value is not valid" + str(tIME_Sec))

            if len(ToFix) > 0:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)
            else:
                print(
                    "\n-Errors Check :"
                    + Candy("Color", "green", " OK ")
                    + Candy("Emoj", "good")
                )

    if Chunk == "tRNS":
        TRNSNBR = len(data)
        if len(IHDR_Color) == 0:
            print(
                "-IHDR Color value %s first.%s"
                % (Candy("Color", "red", "have to be fixed"), Candy("Emoj", "bad"))
            )
            ToFix.append("-IHDR Color Have to be either 0,2 or 3 when used with tRNS")
        elif len(data) == 0:
            print(
                "-tRNS Chunk %s "
                % (Candy("Color", "red", "Must not be empty"), Candy("Emoj", "bad"))
            )
            ToFix.append("-tRNS Chunk Must not be empty")
        elif str(IHDR_Color) not in ["0", "2", "3"]:
            print(
                "-IHDR Color %s either 0,2 or 3 when used with tRNS %s"
                % (Candy("Color", "red", "Have to be"), Candy("Emoj", "bad"))
            )
            print(
                "-IHDR Color value %s first.%s"
                % (Candy("Color", "red", "have to be fixed"), Candy("Emoj", "bad"))
            )
            ToFix.append(
                "-IHDR Color IHDR Color Have to be either 0,2 or 3 when used with tRNS"
            )
        elif len(data) > 0 and str(IHDR_Color) in ["0", "2", "3"]:
            if IHDR_Color == "0":
                try:
                    tRNS_Gray = str(int(data[:4], 16))
                    print("-Gray    :", Candy("Color", "yellow", tRNS_Gray))
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    if DEBUG is True:
                        print(
                            Candy("Color", "red", "Error tRNS gray:"),
                            Candy("Color", "yellow", e),
                        )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")
                    ToFix.append("-Error tRNS_Gray:" + str(e))

            if IHDR_Color == "2":
                try:
                    tRNS_TrueR = str(int(data[:4], 16))
                    print("-Red    :", Candy("Color", "red", tRNS_TrueR))
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    if DEBUG is True:
                        print(
                            Candy("Color", "red", "Error tRNS_TrueR:"),
                            Candy("Color", "yellow", e),
                        )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")

                    ToFix.append("-Error tRNS_TrueR:" + str(e))
                try:
                    tRNS_TrueG = str(int(data[4:8], 16))
                    print("-Green  :", Candy("Color", "green", tRNS_TrueG))
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    if DEBUG is True:
                        print(
                            Candy("Color", "red", "Error tRNS_TrueG:"),
                            Candy("Color", "yellow", e),
                        )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")

                    ToFix.append("-Error tRNS_TrueG:" + str(e))
                try:
                    tRNS_TrueB = str(int(data[8:16], 16))
                    print("-Blue   :", Candy("Color", "blue", tRNS_TrueB))
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    if DEBUG is True:
                        print(
                            Candy("Color", "red", "Error tRNS_TrueB:"),
                            Candy("Color", "yellow", e),
                        )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")

                    ToFix.append("-Error tRNS_TrueB:" + str(e))

            if IHDR_Color == "3":
                if b"PLTE" not in Chunks_History and b"sPLT" not in Chunks_History:
                    print(
                        "-%s Chunk or %s is missing.(tRNS must be used after one of them) %s"
                        % (
                            Candy("Color", "red", "PLTE"),
                            Candy("Color", "red", "sPLT"),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-PLTE Chunk or sPLT is missing.(tRNS must be used after one of them)"
                    )

                for i in range(0, TRNSNBR, 2):
                    try:
                        tRNS_Index.append(str(int(data[i : i + 2], 16)))
                    except Exception as e:
                        Betterror(e, inspect.stack()[0][3])
                        if DEBUG is True:
                            print(
                                Candy("Color", "red", "Error tRNS_Index:"),
                                Candy("Color", "yellow", e),
                            )
                            if PAUSEDEBUG is True or PAUSEERROR is True:
                                Pause("Pause Debug")

                        ToFix.append("-Error tRNS_Index:" + str(e))

                print(
                    "-%s Alpha indexes are stored."
                    % Candy("Color", "yellow", len(tRNS_Index))
                )

                if b"PLTE" in Chunks_History:
                    if (
                        (len(tRNS_Index) > len(PLTE_R))
                        or (len(tRNS_Index) > len(PLTE_G))
                        or (len(tRNS_Index) > len(PLTE_B))
                    ):
                        print(
                            "-tRNS Alpha indexes palettes entries %s PLTE entries number %s"
                            % (
                                Candy("Color", "red", "must not be superior to"),
                                Candy("Emoj", "bad"),
                            )
                        )
                        ToFix.append(
                            "-tRNS Alpha indexes palettes entries must not be superior to PLTE entries"
                        )

                if b"sPLT" in Chunks_History:
                    if (
                        (len(hIST) > len(sPLT_Red))
                        or (len(hIST) > len(sPLT_Green))
                        or (len(hIST) > len(sPLT_Blue))
                        or (len(hIST) > len(sPLT_Aplha))
                    ):
                        print(
                            "-tRNS Alpha indexes palettes entries %s sPLT entries number %s"
                            % (
                                Candy("Color", "red", "must not be superior to"),
                                Candy("Emoj", "bad"),
                            )
                        )
                        ToFix.append(
                            "-tRNS Alpha indexes palettes entries must not be superior to sPLT entries"
                        )

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

    if Chunk == "sRGB":
        sRGB = str(int(data[:2], 16))
        if sRGB == "0":
            print("-Rendering Perceptual :", Candy("Color", "yellow", sRGB))
        elif sRGB == "1":
            print("-Rendering Relative colorimetric :", Candy("Color", "yellow", sRGB))
        elif sRGB == "2":
            print("-Rendering Saturation :", Candy("Color", "yellow", sRGB))
        elif sRGB == "3":
            print("-Rendering Absolute colorimetric :", Candy("Color", "yellow", sRGB))
        else:
            print(
                "-%s sRGB value must be between 0 to 3. %s"
                % (Candy("Color", "red", "Wrong"), Candy("Emoj", "bad"))
            )
            ToFix.append("-sRGB value must be between 0 to 3.")

        if "cHRM".encode() in Chunks_History:
            print(
                "-%s already present cHRM will be %s if reconized by decoders %s"
                % (
                    Candy("Color", "red", "cHRM"),
                    Candy("Color", "red", "overide"),
                    Candy("Emoj", "bad"),
                )
            )
            ToFix.append("-cHRM is overided by sRGB chunk")

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

    if Chunk == "cHRM":
        try:
            cHRM_WhiteX = str(
                int.from_bytes(bytes.fromhex(data[:8]), byteorder="big", signed=False)
            )
            print("-WhiteX   :", Candy("Color", "white", cHRM_WhiteX))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "-cHRM WhiteX Error:"),
                    Candy("Color", "yellow", e),
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")

            ToFix.append("-cHRM WhiteX Error:" + str(e))
        try:
            cHRM_WhiteY = str(
                int.from_bytes(bytes.fromhex(data[8:16]), byteorder="big", signed=False)
            )
            print("-WhiteY   :", Candy("Color", "white", cHRM_WhiteY))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "-cHRM WhiteY Error:"),
                    Candy("Color", "yellow", e),
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-cHRM WhiteY Error:" + str(e))

        try:
            cHRM_Redx = str(
                int.from_bytes(
                    bytes.fromhex(data[16:24]), byteorder="big", signed=False
                )
            )
            print("-RedX     :", Candy("Color", "red", cHRM_Redx))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "-cHRM RedX Error:"),
                    Candy("Color", "yellow", e),
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-cHRM RedX Error:" + str(e))

        try:
            cHRM_Redy = str(
                int.from_bytes(
                    bytes.fromhex(data[24:32]), byteorder="big", signed=False
                )
            )
            print("-RedY     :", Candy("Color", "red", cHRM_Redy))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "-cHRM RedY Error:"),
                    Candy("Color", "yellow", e),
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-cHRM RedY Error:" + str(e))

        try:
            cHRM_Greenx = str(
                int.from_bytes(
                    bytes.fromhex(data[32:40]), byteorder="big", signed=False
                )
            )
            print("-GreenX   :", Candy("Color", "green", cHRM_Greenx))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "-cHRM GreenX Error:"),
                    Candy("Color", "yellow", e),
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
                ToFix.append("-cHRM GreenX Error:" + str(e))

        try:
            cHRM_Greeny = str(
                int.from_bytes(
                    bytes.fromhex(data[40:48]), byteorder="big", signed=False
                )
            )
            print("-GreenY   :", Candy("Color", "green", cHRM_Greeny))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "-cHRM GreenY Error:"),
                    Candy("Color", "yellow", e),
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-cHRM GreenY Error:" + str(e))

        try:
            cHRM_Bluex = str(
                int.from_bytes(
                    bytes.fromhex(data[48:56]), byteorder="big", signed=False
                )
            )
            print("-BlueX    :", Candy("Color", "blue", cHRM_Bluex))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "-cHRM BlueX Error:"),
                    Candy("Color", "yellow", e),
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-cHRM BlueX Error:" + str(e))

        try:
            cHRM_Bluey = str(
                int.from_bytes(
                    bytes.fromhex(data[56:64]), byteorder="big", signed=False
                )
            )
            print("-BlueY    :", Candy("Color", "blue", cHRM_Bluey))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "-cHRM BluY Error:"),
                    Candy("Color", "yellow", e),
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            ToFix.append("-cHRM BlueY Error:" + str(e))

        if "sRGB".encode() in Chunks_History or "iCCP".encode() in Chunks_History:
            print(
                "-%s or %s already present cHRM will be overide if reconized by decoders %s"
                % (
                    Candy("Color", "red", "sRGB"),
                    Candy("Color", "red", "iCCP"),
                    Candy("Emoj", "bad"),
                )
            )
            ToFix.append("-cHRM is overided by sRGB chunk and iCCP")

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

    if Chunk == "gAMA":
        try:
            gAMA = str(int(data[:8], 16))
            print("-Gama   :", Candy("Color", "white", gAMA))
            if gAMA == "0":
                print("-A gAMA Chunk of %s is Useless." % Candy("Color", "red", "0"))
                ToFix.append("-A gAMA Chunk of 0 is Useless.")
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            ToFix.append("-Gama value error" + str(e))
        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk == "iCCP":
        null = "00"
        null_pos = 0
        badchar = ["badchar"]
        for i in range(0, len(data), 2):
            nint = int(data[i : i + 2], 16)
            nchar = chr(nint)

            if data[i : i + 2] == "00":
                null_pos = i
                if i > 79:
                    print(
                        "-Length of iCCP Profile name is %s :%s"
                        % (Candy("Color", "red", "not Valid"), Candy("Color", "red", i))
                    )
                    ToFix.append("-Length of iCCP Profile name is not valid")
                break
            if (int(nint) not in range(32, 127)) and (int(nint) not in range(161, 255)):
                print(
                    "-Character %s at index %s in iCCP_Name\n-Replaced by [€]"
                    % (
                        Candy("Color", "red", "not allowed [" + nchar + "]"),
                        Candy("Color", "red", i),
                    )
                )
                ToFix.append(
                    "-Character not allowed %s at index %s in iCCP_Name\n-Replaced by [€]"
                    % (nchar, i)
                )
                badchar.append(i)
                iCCP_Name += "€"
            else:
                iCCP_Name += nchar
        if len(badchar) > 1:
            ToFix.append(badchar)

        iCCP_Method = int(data[null_pos + 2 : null_pos + 4], 16)

        if iCCP_Method > 0:
            print(
                "-Compression method is supposed to be %s but is %s instead ."
                % (Candy("Color", "green", "0"), Candy("Color", "red", method))
            )
            ToFix.append(
                "-Compression method is supposed to be 0 but is %s instead ." % method
            )

        iCCP_Profile = data[null_pos + 4 :]

        if int(int(Orig_CL, 16)) - (int(null_pos / 2) + 2) != int(
            len(iCCP_Profile) / 2
        ):
            print("-iCCP Profile length is %s" % Candy("Color", "red", "not Valid"))
            ToFix.append("-iCCP Profile length is not Valid")

        if "cHRM".encode() in Chunks_History:
            print(
                "-%s already present cHRM will be %s if reconized by decoders %s"
                % (
                    Candy("Color", "red", "cHRM"),
                    Candy("Color", "red", "overide"),
                    Candy("Emoj", "bad"),
                )
            )
            ToFix.append(
                "-cHRM already present cHRM will be overide if reconized by decoders"
            )

        print("-iCCP Profile Name :", Candy("Color", "yellow", iCCP_Name))
        print("-iCCP Profile Method :", Candy("Color", "yellow", iCCP_Method))

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

    if Chunk == "sBIT":
        if IHDR_Color == "0":
            sBIT_Gray = str(int(data[:2], 16))
            print(
                "-Significant greyscale bits    :", Candy("Color", "yellow", sBIT_Gray)
            )
            if sBIT_Gray == "0":
                print(
                    "-%s sBit value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-Significant greyscale bits (must be greater than 0) ")

        if IHDR_Color == "2" or IHDR_Color == "3":
            sBIT_TrueR = str(int(data[:2], 16))
            sBIT_TrueG = str(int(data[2:4], 16))
            sBIT_TrueB = str(int(data[4:6], 16))
            print("-significant bits Red    :", Candy("Color", "red", sBIT_TrueR))
            print("-significant bits Green  :", Candy("Color", "green", sBIT_TrueG))
            print("-significant bits Blue   :", Candy("Color", "blue", sBIT_TrueB))
            if sBIT_TrueR == "0":
                print(
                    "-%s sBit red value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-sBit red value (must be greater than 0")

            if sBIT_TrueG == "0":
                print(
                    "-%s sBit green value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-sBit green value (must be greater than 0")

            if sBIT_TrueB == "0":
                print(
                    "-%s sBit blue value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-sBit blue value (must be greater than 0")

            if IHDR_Color == "3":
                if int(sBIT_TrueR) > 8:
                    print(
                        "-%s sBit red value (must %s be greater than %s) %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", "not"),
                            Candy("Color", "red", "8"),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append("-sBit red value (must be greater than 0")
                if int(sBIT_TrueG) > 8:
                    print(
                        "-%s sBit green value (must %s be greater than %s) %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", "not"),
                            Candy("Color", "red", "8"),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append("-sBit green value (must not be greater than 8)")
                if int(sBIT_TrueB) > 8:
                    print(
                        "-%s sBit blue value (must %s be greater than %s) %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", "not"),
                            Candy("Color", "red", "8"),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append("-sBit blue value (must not be greater than 8)")
            else:
                if int(sBIT_TrueR) > int(IHDR_Depht):
                    print(
                        "-%s sBit red value (must %s be greater than %s) %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", "not"),
                            Candy("Color", "red", IHDR_Depht),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-sBit red value (must not be greater than %s)" % IHDR_Depht
                    )

                if int(sBIT_TrueG) > int(IHDR_Depht):
                    print(
                        "-%s sBit green value (must %s be greater than %s) %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", "not"),
                            Candy("Color", "red", IHDR_Depht),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-sBit green value (must not be greater than %s)" % IHDR_Depht
                    )

                if int(sBIT_TrueB) > int(IHDR_Depht):
                    print(
                        "-%s sBit blue value (must %s be greater than %s) %s"
                        % (
                            Candy("Color", "red", "Wrong"),
                            Candy("Color", "red", "not"),
                            Candy("Color", "red", IHDR_Depht),
                            Candy("Emoj", "bad"),
                        )
                    )
                    ToFix.append(
                        "-sBit blue value (must not be greater than %s)" % IHDR_Depht
                    )

        if IHDR_Color == "4":
            sBIT_GrayScale = str(int(data[:pos], 16))
            sBIT_GrayAlpha = str(int(data[:pos], 16))
            print(
                "-Gray scale significant bit:", Candy("Color", "white", sBIT_GrayScale)
            )
            print(
                "-Gray alpha significant bit:", Candy("Color", "white", sBIT_GrayAlpha)
            )
            if sBIT_GrayScale == "0":
                print(
                    "-%s sBit Grayscale value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-sBit Grayscale value (must not be greater than 0)")

            if sBIT_GrayAlpha == "0":
                print(
                    "-%s sBit Grayscale alpha value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-sBit Grayscale alpha value (must not be greater than 0)")

            if int(sBIT_GrayScale) > int(IHDR_Depht):
                print(
                    "-%s sBit Grayscale value (must %s be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "not"),
                        Candy("Color", "red", IHDR_Depht),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-sBit Grayscale value (must not be greater than %s)" % IHDR_Depht
                )

            if int(sBIT_GrayScale) > int(IHDR_Depht):
                print(
                    "-%s sBit Grayscale alpha value (must %s be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "not"),
                        Candy("Color", "red", IHDR_Depht),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-sBit Grayscale alpha value (must not be greater than %s)"
                    % IHDR_Depht
                )

        if IHDR_Color == "6":
            sBIT_TrueAlphaR = str(int(data[:2], 16))
            sBIT_TrueAlphaG = str(int(data[2:4], 16))
            sBIT_TrueAlphaB = str(int(data[4:6], 16))
            sBIT_TrueAlpha = str(int(data[6:8], 16))
            print(
                "-significant bits Alpha Red    :",
                Candy("Color", "red", sBIT_TrueAlphaR),
            )
            print(
                "-significant bits Alpha Green  :",
                Candy("Color", "green", sBIT_TrueAlphaG),
            )
            print(
                "-significant bits Alpha Blue   :",
                Candy("Color", "blue", sBIT_TrueAlphaB),
            )
            print(
                "-significant bits Alpha        :",
                Candy("Color", "white", sBIT_TrueAlpha),
            )

            if sBIT_TrueAlphaR == "0":
                print(
                    "-%s sBit True alpha red value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-sBit True alpha red value (must not be greater than 0)")

            if sBIT_TrueAlphaG == "0":
                print(
                    "-%s sBit True alpha green value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-sBit True alpha green value (must not be greater than 0)"
                )

            if sBIT_TrueAlphaB == "0":
                print(
                    "-%s sBit True alpha blue value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-sBit True alpha blue value (must not be greater than 0)")

            if sBIT_TrueAlpha == "0":
                print(
                    "-%s sBit True alpha value (must be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "0"),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append("-sBit True alpha value (must not be greater than 0)")

            if int(sBIT_TrueAlphaR) > int(IHDR_Depht):
                print(
                    "-%s sBit True alpha red value (must %s be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "not"),
                        Candy("Color", "red", IHDR_Depht),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-sBit True alpha red value (must not be greater than %s)"
                    % IHDR_Depht
                )

            if int(sBIT_TrueAlphaG) > int(IHDR_Depht):
                print(
                    "-%s sBit True alpha green value (must %s be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "not"),
                        Candy("Color", "red", IHDR_Depht),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-sBit True alpha green value (must not be greater than %s)"
                    % IHDR_Depht
                )

            if int(sBIT_TrueAlphaB) > int(IHDR_Depht):
                print(
                    "-%s sBit True alpha blue value (must %s be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "not"),
                        Candy("Color", "red", IHDR_Depht),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-sBit True alpha blue value (must not be greater than %s)"
                    % IHDR_Depht
                )

            if int(sBIT_TrueAlpha) > int(IHDR_Depht):
                print(
                    "-%s sBit True alpha value (must %s be greater than %s) %s"
                    % (
                        Candy("Color", "red", "Wrong"),
                        Candy("Color", "red", "not"),
                        Candy("Color", "red", IHDR_Depht),
                        Candy("Emoj", "bad"),
                    )
                )
                ToFix.append(
                    "-sBit True alpha  value (must not be greater than %s)" % IHDR_Depht
                )

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )

    if Chunk == "oFFs":
        try:
            oFFSX = str(
                int.from_bytes(bytes.fromhex(data[:8]), byteorder="big", signed=True)
            )
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            oFFSX = ""
        try:
            oFFSY = str(
                int.from_bytes(bytes.fromhex(data[8:16]), byteorder="big", signed=True)
            )
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            oFFSY = ""
        try:
            oFFSU = str(int(data[16:18], 16))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            oFFSU = ""

            print("-Offset position X    :", Candy("Color", "blue", oFFSX))
            print("-Offset position Y  :", Candy("Color", "purple", oFFSY))
            print("-Offset Unit   :", Candy("Color", "white", oFFSU))
            if int(oFFSX) not in range(-2147483647, 2147483648):
                print(
                    "-%s Offset position X must be between -2,147,483,647 to +2,147,483,647 %s"
                    % (Candy("Color", "red", "Wrong"), Candy("Emoj", "bad"))
                )
                ToFix.append(
                    "-Wrong Offset position X must be between -2,147,483,647 to +2,147,483,647"
                )
            if int(oFFSY) not in range(-2147483647, 2147483648):
                print(
                    "-%s Offset position Y must be between -2,147,483,647 to +2,147,483,647 %s"
                    % (Candy("Color", "red", "Wrong"), Candy("Emoj", "bad"))
                )
                ToFix.append(
                    "-Wrong Offset position Y must be between -2,147,483,647 to +2,147,483,647"
                )
            if oFFSU != "0" and oFFSU != "1":
                print(
                    "-%s Offset unit must be between 0 or 1 %s"
                    % (Candy("Color", "red", "Wrong"), Candy("Emoj", "bad"))
                )
                ToFix.append("-Wrong Offset unit must be between 0 or 1")
            if len(ToFix) > 0:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)
            else:
                print(
                    "\n-Errors Check :"
                    + Candy("Color", "green", " OK ")
                    + Candy("Emoj", "good")
                )

    if Chunk == "pCAL":
        pCAL_Param = []
        try:
            pCAL_Key = data.split("00")[0]
            for i in range(0, len(pCAL_Key), 2):
                if int(pCAL_Key[i : i + 2], 16) not in range(32, 127) and int(
                    pCAL_Key[i : i + 2], 16
                ) not in range(161, 256):
                    if pCAL_Key[i : i + 2] != "00" and pCAL_Key[i : i + 2] != "0a":
                        print(
                            "-Character %s at index %s in pCAL Keyword (must be between 32-126 and 161-255 but is %s)"
                            % (
                                Candy(
                                    "Color",
                                    "red",
                                    "not allowed [" + pCAL_Key[i : i + 2] + "]",
                                ),
                                Candy("Color", "red", i),
                                Candy("Color", "red", int(pCAL_Key[i : i + 2], 16)),
                            )
                        )
                        ToFix.append(
                            "-Character not allowed %s at index %s in pCAL Keyword (must be between 32-126 and 161-255 but is %s"
                            % (pCAL_Key[i : i + 2], i, int(pCAL_Key[i : i + 2], 16))
                        )

            if len(pCAL_Key) >= 79:
                print(
                    "-pCAL Keyword length is %s :%s"
                    % (
                        Candy("Color", "red", "not Valid"),
                        Candy("Color", "red", len(pCAL_Key)),
                    )
                )
                ToFix.append("-pCAL Keyword length is not Valid :%s" % (len(pCAL_Key)))
            Keypos = len(pCAL_Key) + 2
            pCAL_Zero = str(int(data[Keypos : Keypos + 8], 16))
            pCAL_Max = str(int(data[Keypos + 8 : Keypos + 16], 16))
            pCAL_Eq = str(int(data[Keypos + 16 : Keypos + 18], 16))
            pCAL_PNBR = str(int(data[Keypos + 18 : Keypos + 20], 16))

            if pCAL_PNBR == "0":
                pCAL_Unit = ""
            else:
                pCAL_Unit = bytes.fromhex(data[20:].split("00")[0])

            newlength = Keypos + 20

            for i in range(0, int(pCAL_PNBR)):
                param = ""
                try:
                    for j in range(0, len(data[newlength:]), 2):
                        hx = data[newlength + j : newlength + j + 2]
                        if hx != "00":
                            param += str(hx)
                        else:
                            break
                    pCAL_Param.append(param)
                    newlength += len(param) + 2
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                    if (PAUSEDEBUG or PAUSEERROR) is True:
                        Pause("Pause Debug")
                if DEBUG is True:
                    print(
                        Candy("Color", "red", "Error pCAL:"),
                        Candy("Color", "yellow", e),
                    )
                    if (PAUSEDEBUG or PAUSEERROR) is True:
                        Pause("Pause Debug")

            print(
                "-Calibration name    :",
                Candy(
                    "Color", "yellow", bytes.fromhex(pCAL_Key).decode(errors="replace")
                ),
            )
            print("-Original zero       :", Candy("Color", "yellow", pCAL_Zero))
            print("-Original max        :", Candy("Color", "yellow", pCAL_Max))
            print("-Equation type       :", Candy("Color", "yellow", pCAL_Eq))
            print("-Number of parameters:", Candy("Color", "yellow", pCAL_PNBR))

            if len(ToFix) > 0:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "Error pCAL2:"), Candy("Color", "yellow", e)
                )

    if Chunk == "gIFg":

        gIFgM = str(int(data[:2], 16))
        gIFgU = str(int(data[2:4], 16))
        gIFgT = str(int(data[4:6], 16))

        print("-Disposal Method    :", Candy("Color", "yellow", gIFgM))
        print("-User Input Flag    :", Candy("Color", "yellow", gIFgT))
        print("-Delay Time    :", Candy("Color", "yellow", gIFgT))

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)
    if Chunk == "gIFx":
        gIFID = str(int(data[:16], 16))
        gIFCD = str(int(data[16:22], 16))
        gIFDT = str(int(data[22:], 16))

        print("-Application Identifier    :", Candy("Color", "yellow", gIFID))
        print("-Authentication Code    :", Candy("Color", "yellow", gIFCD))
        print("-Application Data    :", Candy("Color", "yellow", gIFDT))

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk == "sTER":

        sTER = str(int(data[:2], 16))

        print("-Subimage mode    :", Candy("Color", "yellow", sTER))

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk == "tEXt":
        tEXt_Key_List = []
        tEXt_Str_List = []
        try:
            null_pos = NullFind(data)
            tEXt_Key = data[:null_pos]
            tEXt_Text = data[null_pos + 2 :]

            for i in range(0, len(data), 2):
                if int(data[i : i + 2], 16) not in range(32, 127) and int(
                    data[i : i + 2], 16
                ) not in range(161, 256):
                    if data[i : i + 2] != "00" and data[i : i + 2] != "0a":
                        print(
                            "-Character %s at index %s in tEXt Keyword (must be between 32-126 and 161-255 but is %s)"
                            % (
                                Candy(
                                    "Color",
                                    "red",
                                    "not allowed [" + data[i : i + 2] + "]",
                                ),
                                Candy("Color", "red", i),
                                Candy("Color", "red", int(data[i : i + 2], 16)),
                            )
                        )
                        ToFix.append(
                            "-Character not allowed %s at index %s in tEXt Keyword (must be between 32-126 and 161-255 but is %s)"
                            % (data[i : i + 2], i, int(data[i : i + 2], 16))
                        )

            if len(tEXt_Key) >= 79:
                print(
                    "-tEXt Keyword length is %s :%s"
                    % (
                        Candy("Color", "red", "not Valid"),
                        Candy("Color", "red", len(tEXt_Key)),
                    )
                )
                ToFix.append("-tEXt Keyword length is not Valid :%s" % (len(tEXt_Key)))
            tEXt_Key_List.append(bytes.fromhex(tEXt_Key).decode(errors="replace"))
            tEXt_Str_List.append(bytes.fromhex(tEXt_Text).decode(errors="ignore"))

            print(
                "-Keyword : ",
                Candy(
                    "Color", "green", bytes.fromhex(tEXt_Key).decode(errors="replace")
                ),
            )
            print(
                "-String  : ",
                Candy(
                    "Color", "green", bytes.fromhex(tEXt_Text).decode(errors="replace")
                ),
            )

            if len(ToFix) > 0:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)

        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")

    if Chunk == "zTXt":
        zTXt_Key_List = []
        zTXt_Str_List = []
        try:
            null_pos = NullFind(data)
            zTXt_Key = data[:null_pos]
            zTXt_Text = zlib.decompress(bytes.fromhex(data[null_pos + 4 :]))
            for i in range(0, len(zTXt_Key), 2):
                if int(zTXt_Key[i : i + 2], 16) not in range(32, 127) and int(
                    zTXt_Key[i : i + 2], 16
                ) not in range(161, 256):
                    if zTXt_Key[i : i + 2] != "00" and zTXt_Key[i : i + 2] != "0a":
                        print(
                            "-Character %s at index %s in zTXt Keyword (must be between 32-126 and 161-255 but is %s)"
                            % (
                                Candy(
                                    "Color",
                                    "red",
                                    "not allowed [" + zTXt_Key[i : i + 2] + "]",
                                ),
                                Candy("Color", "red", i),
                                Candy("Color", "red", int(zTXt_Key[i : i + 2], 16)),
                            )
                        )

            if len(zTXt_Key) >= 79:
                print(
                    "-zTXt Keyword length is %s :%s"
                    % (
                        Candy("Color", "red", "not Valid"),
                        Candy("Color", "red", len(zTXt_Key)),
                    )
                )
                ToFix.append("-tEXt Keyword length is not Valid :%s" % (len(zTXt_Key)))
            zTXt_Key_List.append(bytes.fromhex(zTXt_Key).decode(errors="replace"))
            zTXt_Str_List.append(zTXt_Text.decode(errors="ignore"))

            print(
                "-Keyword : ",
                Candy(
                    "Color", "green", bytes.fromhex(zTXt_Key).decode(errors="replace")
                ),
            )
            print(
                "-String  : ",
                Candy("Color", "green", zTXt_Text.decode(errors="ignore")),
            )

            if len(ToFix) > 0:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)

        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
    if Chunk == "iTXt":
        iTXt_Key_List = []
        iTXt_String_List = []
        try:
            null_pos = NullFind(data)
            iTXt_Key = data[:null_pos]

            for i in range(0, len(iTXt_Key), 2):
                if int(iTXt_Key[i : i + 2], 16) not in range(32, 127) and int(
                    iTXt_Key[i : i + 2], 16
                ) not in range(161, 256):
                    if iTXt_Key[i : i + 2] != "00" and iTXt_Key[i : i + 2] != "0a":
                        print(
                            "-Character %s at index %s in iTXt Keyword (must be between 32-126 and 161-255 but is %s)"
                            % (
                                Candy(
                                    "Color",
                                    "red",
                                    "not allowed [" + iTXt_Key[i : i + 2] + "]",
                                ),
                                Candy("Color", "red", i),
                                Candy("Color", "red", int(iTXt_Key[i : i + 2], 16)),
                            )
                        )

            if len(iTXt_Key) >= 79:
                print(
                    "-iTXt Keyword length is %s :%s"
                    % (
                        Candy("Color", "red", "not Valid"),
                        Candy("Color", "red", len(iTXt_Key)),
                    )
                )
                ToFix.append("-tEXt Keyword length is not Valid :%s" % (len(iTXt_Key)))

            iTXt_Flag = data[len(iTXt_Key) + 2 : len(iTXt_Key) + 4]
            iTXt_Compression = data[len(iTXt_Key) + 4 : len(iTXt_Key) + 6]

            newpos = len(iTXt_Key) + len(iTXt_Flag) + len(iTXt_Compression) + 2

            if data[newpos : newpos + 2] == "00":
                iTXt_Lang = ""
            else:
                null_pos = NullFind(data[newpos:])
                iTXt_Lang = data[newpos : newpos + null_pos]

            newpos = newpos + len(iTXt_Lang) + 2

            if iTXt_Lang == "00":
                iTXt_Key_Trad = ""
            else:
                null_pos = NullFind(data[newpos:])
                iTXt_Key_Trad = data[newpos : +newpos + null_pos]

            newpos = newpos + len(iTXt_Key_Trad) + 2
            iTXt_String = data[newpos:]

            if iTXt_Flag == "01":
                iTXt_String = zlib.decompress(bytes.fromhex(iTXt_String)).decode(
                    errors="ignore"
                )
            elif iTXt_Flag == "00":
                iTXt_String = bytes.fromhex(iTXt_String).decode(errors="replace")

            iTXt_Key_List.append(bytes.fromhex(iTXt_Key).decode(errors="replace"))
            iTXt_String_List.append(iTXt_String)

            print(
                "-Keyword             : ",
                Candy(
                    "Color", "green", bytes.fromhex(iTXt_Key).decode(errors="replace")
                ),
            )
            print("-Compression Flag    : ", Candy("Color", "green", iTXt_Flag))
            print("-Compression Method  : ", Candy("Color", "green", iTXt_Compression))
            print(
                "-Language            : ",
                Candy(
                    "Color", "green", bytes.fromhex(iTXt_Lang).decode(errors="replace")
                ),
            )
            print(
                "-Keyword Traduction  : ",
                Candy(
                    "Color",
                    "green",
                    bytes.fromhex(iTXt_Key_Trad).decode(errors="replace"),
                ),
            )
            print("-String              : ", Candy("Color", "green", iTXt_String))

            if len(ToFix) > 0:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)

        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
    if Chunk == "eXIf":
        eXIf_raw = []
        raw = ""
        sepcounter = 0
        eXIf_endian = bytes.fromhex(data[:4]).decode(errors="ignore")

        if eXIf_endian == "II":
            print("-eXif endianess is little-endian : ", eXIf_endian)
        elif eXIf_endian == "MM":
            print("-eXif endianess is big-endian : ", eXIf_endian)

        print("\nRaw values from eXIf data :\n\n")
        for i in range(0, len(data), 2):
            raw += data[i : i + 2]
            if data[i : i + 2] == "00":
                sepcounter += 1
                if sepcounter >= 3:
                    eXIf_raw.append(raw)
                    raw = ""
                    sepcounter = 0
        for raw in eXIf_raw:
            if len(raw) < 150:
                print("- " + bytes.fromhex(raw).decode(errors="ignore"))
            else:
                print("-Raw data is too long to be displayed")

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk == "spAL":
        print("-intermediate sPLT test version")

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk.encode(errors="ignore") in PRIVATE_CHUNKS:
        print("-Private Chunk")

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk.encode(errors="ignore") not in ALLCHUNKS:

        print("-%s" % Candy("Color", "red", "Unknown Chunk."))

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Dummy is False:
        CheckChunkOrder(Chunk, "TheGoodPlace")
    return


def ChunkbyChunk(offset):
    global Have_A_KitKat

    global Raw_Length
    global Raw_Data
    global Raw_Crc
    global Raw_Type
    global Raw_NextChunk

    global Orig_CL
    global Orig_CT
    global Orig_NC
    global Orig_CD
    global Orig_CRC

    global CLoffX
    global CLoffB
    global CLoffI

    global CToffX
    global CToffB
    global CToffI

    global NCoffX
    global NCoffB
    global NCoffI

    global CDoffX
    global CDoffB
    global CDoffI

    global CrcoffX
    global CrcoffB
    global CrcoffI

    Raw_Length = DATAX[offset : offset + 8]
    Orig_CL = Raw_Length
    CLoffX = hex(int(offset / 2))
    CLoffB = int(offset / 2)
    CLoffI = offset

    Raw_Type = DATAX[offset + 8 : offset + 16]
    Orig_CT = bytes.fromhex(Raw_Type).decode(errors="ignore")
    CToffX = hex(int(offset / 2) + 4)
    CToffB = int(offset / 2) + 4
    CToffI = offset + 8

    Raw_Data = DATAX[offset + 16 : offset + 16 + (int(Raw_Length, 16) * 2)]
    Orig_CD = Raw_Data
    CDoffX = hex(int(offset / 2) + 8)
    CDoffB = int(offset / 2) + 8
    CDoffI = offset + 16

    Raw_Crc = DATAX[offset + 16 + len(Raw_Data) : offset + 16 + len(Raw_Data) + 8]
    Orig_CRC = Raw_Crc
    CrcoffX = hex(int(offset / 2) + int(Raw_Length, 16) + len(Raw_Type))
    CrcoffB = int(offset / 2) + int(Raw_Length, 16) + len(Raw_Type)
    CrcoffI = (int(offset / 2) + int(Raw_Length, 16) + len(Raw_Type)) * 2

    Raw_NextChunk = DATAX[offset + 32 + len(Raw_Data) : offset + 32 + len(Raw_Data) + 8]
    Orig_NC = bytes.fromhex(Raw_NextChunk)
    NCoffX = hex(int(offset / 2) + int(Raw_Length, 16) + len(Raw_Type) + len(Raw_Data))
    NCoffB = int(offset / 2) + int(Raw_Length, 16) + len(Raw_Type) + 16
    NCoffI = (int(offset / 2) + int(Raw_Length, 16) + len(Raw_Type) + 16) * 2

    Candy("Title", "Chunk Infos:")
    print(
        "-Found at offset            (%s/%s/%s): (%s/%s/%s) "
        % (
            Candy("Color", "yellow", "Hex"),
            Candy("Color", "blue", "Bytes"),
            Candy("Color", "purple", "Index"),
            Candy("Color", "yellow", CLoffX),
            Candy("Color", "blue", CLoffB),
            Candy("Color", "purple", CLoffI),
        )
    )
    print(
        "-Chunk Length:              (%s/%s)"
        % (
            Candy("Color", "yellow", hex(int(Raw_Length, 16))),
            Candy("Color", "blue", int(Raw_Length, 16)),
        )
    )
    print("")
    print(
        "-Found at offset            (%s/%s/%s): (%s/%s/%s) "
        % (
            Candy("Color", "yellow", "Hex"),
            Candy("Color", "blue", "Bytes"),
            Candy("Color", "purple", "Index"),
            Candy("Color", "yellow", CToffX),
            Candy("Color", "blue", CToffB),
            Candy("Color", "purple", CToffI),
        )
    )
    print(
        "-Chunk Type :               (%s/%s)"
        % (Candy("Color", "yellow", Raw_Type), Candy("Color", "blue", Orig_CT))
    )
    print("")
    print(
        "-Found Chunk Data at offset (%s/%s/%s): (%s/%s/%s) "
        % (
            Candy("Color", "yellow", "Hex"),
            Candy("Color", "blue", "Bytes"),
            Candy("Color", "purple", "Index"),
            Candy("Color", "yellow", CDoffX),
            Candy("Color", "blue", CDoffB),
            Candy("Color", "purple", CDoffI),
        )
    )
    # print("Chunk Data len  : (%s/%s/%s) "%())
    print("")
    print(
        "-Found at offset            (%s/%s/%s): (%s/%s/%s) "
        % (
            Candy("Color", "yellow", "Hex"),
            Candy("Color", "blue", "Bytes"),
            Candy("Color", "purple", "Index"),
            Candy("Color", "yellow", CrcoffX),
            Candy("Color", "blue", CrcoffB),
            Candy("Color", "purple", CrcoffI),
        )
    )
    print(
        "-Chunk Crc:                 (%s/offset :  %s)"
        % (Candy("Color", "yellow", Raw_Crc), Candy("Color", "yellow", hex(CrcoffB)))
    )

    print("")
    print(
        "-Found at offset            (%s/%s/%s): (%s/%s/%s) "
        % (
            Candy("Color", "yellow", "Hex"),
            Candy("Color", "blue", "Bytes"),
            Candy("Color", "purple", "Index"),
            Candy("Color", "yellow", NCoffX),
            Candy("Color", "blue", NCoffB),
            Candy("Color", "purple", NCoffI),
        )
    )
    print(
        "-Raw_NextChunk Type :       (%s/%s)"
        % (Candy("Color", "yellow", Raw_NextChunk), Candy("Color", "blue", Orig_NC))
    )

    return


def GroundhogDay(NewDay):

    sys.argv.append("--CLONE " + NewDay)
    strargs = "-cmd " + " ".join([i for i in sys.argv])
    if DEBUG is True:
        print("sys.executable was ", sys.executable)
        print("argv is ", strargs)
        print("rebooting chunklate")
        if PAUSEDEBUG is True:
            Pause("Pause:Reboot")
    os.execv(sys.executable, ["-cmd "] + sys.argv)


def Chunklate(sec):

    if os.name == "nt":
        print(
            """
╭─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╮
  <[0x00000016]>[C|H|U|N|K|L|A|T|E]<[0x98bd5cb8]>
╰─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╯
"""
        )
        if PAUSE is True:
            time.sleep(sec)

        return

    color = [
        "\033[1;31;49m",
        "\033[1;32;49m",
        "\033[1;34;49m",
        "\033[1;35;49m",
        "\033[1;33;49m",
        "\033[1;37;49m",
    ]

    length = "<[0x00000016]>"
    crc = "<[0x98bd5cb8]>"

    title = "\033[1;37;49m[\033[mC\033[1;37;49m|\033[mH\033[1;37;49m|\033[mU\033[1;37;49m|\033[mN\033[1;37;49m|\033[mK\033[1;37;49m|\033[mL\033[1;37;49m|\033[mA\033[1;37;49m|\033[mT\033[1;37;49m|\033[mE\033[1;37;49m]\033[m"

    top = "\n╭─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╮"
    bot = "╰─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╯\n"

    t_o_p = [i for i in top]
    b_o_t = [i for i in bot]

    l_e_n = [i for i in length]
    c_r_c = [i for i in crc]

    colored_len = ""
    colored_crc = ""
    toped = ""
    boted = ""

    for i, j in zip(l_e_n, c_r_c):

        rnd = random.randint(0, len(color) - 1)
        tmp = str(color[rnd]) + str(i) + str("\033[m")

        rnd2 = random.randint(0, len(color) - 1)
        tmp2 = str(color[rnd]) + str(j) + str("\033[m")

        colored_len += tmp
        colored_crc += tmp2

    for i, j in zip(t_o_p, b_o_t):

        rnd2 = random.randint(0, len(color) - 1)
        rnd3 = random.randint(0, len(color) - 1)

        tmp2 = str(color[rnd2]) + str(i) + str("\033[m")
        tmp3 = str(color[rnd3]) + str(j) + str("\033[m")

        toped += tmp2
        boted += tmp3

    print(toped)
    print("  " + colored_len + title + colored_crc)
    print(boted)

    if PAUSE is True:
        time.sleep(sec)


def Minibar():
    global CharPos
    global GoBack
    global Loading_txt
    global Loading_sep
    point = "."
    space = " "
    lnt = len(Loading_txt)
    if lnt < MAXCHAR and GoBack is False:
        Loading_txt = (point * CharPos) + space
        CharPos += 1
        print(Loading_txt, end="\r")
        lnt = len(Loading_txt)
    else:
        if lnt > 2:
            GoBack = True
            Loading_txt = (point * CharPos) + space
            CharPos -= 1
            print(Loading_txt, end="\r")
            lnt = len(Loading_txt)
        else:
            GoBack = False


def Loadingbar():

    Loading_txt = ""
    GoBack = False
    CharPos = 0
    PosLine = 0
    Tail = 0
    MAXCHAR = int(os.get_terminal_size(0)[0]) - 1
    Line = "¸.·´¯`·.¸"
    Linelst = []
    FishR = ["><(((º>", "⸌<(((º>", "><(((º>", "⸝<(((º>"]
    FishL = ["<º)))><", "<º)))>⸍", "<º)))><", "<º)))>⸜"]
    Trail = 3 * len(Line)
    TrailEnd = 0

    for i in range(0, MAXCHAR + 7):
        if PosLine <= len(Line) - 1:
            Linelst.append(Line[PosLine])
        else:
            PosLine = 0
            Linelst.append(Line[PosLine])
        PosLine += 1

    while WORKING == True:
        time.sleep(0.1)
        Ln = len(Loading_txt)
        if Ln < MAXCHAR - 7:
            if CharPos >= Trail:
                Loading_txt = (" " * TrailEnd) + Loading_txt[TrailEnd:]
                Loading_txt += Linelst[CharPos]
                TrailEnd += 1
            else:

                Loading_txt += Linelst[CharPos]

            if Tail > 3:
                Tail = 0

            print(Loading_txt + FishR[Tail], end="\r")
            CharPos += 1
            Ln = len(Loading_txt)
            Tail += 1
        else:

            fishapear = (MAXCHAR - 7) - (CharPos)
            Loading_txt = (" " * TrailEnd) + Loading_txt[TrailEnd:]
            if fishapear >= -7:
                Loading_txt += Linelst[CharPos]
            TrailEnd += 1

            if Tail > 3:
                Tail = 0

            print(Loading_txt + FishR[Tail][:fishapear], end="\r")
            CharPos += 1
            Tail += 1
            if TrailEnd >= MAXCHAR + 2:

                Loading_txt = ""
                PosLine = 0
                Trail = 3 * len(Line)
                Tail = 0
                TrailEnd = 0
                CharPos = 0
    return


def Sumform(waitforit, switch):
    if switch is True:
        sepa = " ▁ ▂ ▄ ▅ ▆ ▇ █ "
        rator = " █ ▇ ▆ ▅ ▄ ▂ ▁ "
    else:
        sepa = " ▁ ▂ ▄ ▅ ▆ ▇ █ █ ▇ ▆ ▅ ▄ ▂ ▁"
        rator = "▁ ▂ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▂ ▁"

    Spaaaaaaaace = " " * int((MAXCHAR / 2) - (len(sepa + waitforit + rator) / 2))
    Seperator = "\n" + Spaaaaaaaace + sepa + waitforit + rator + "\n\n"
    return Seperator


def Summarise(infos, Summary_Footer=False):
    global Summary_Header

    folder = FILE_DIR + "Folder_" + str(os.path.basename(FILE_Origin))
    folder = os.path.splitext(folder)[0] + "/"
    sep = "\n\n『" + Sample_Name + " :』\n"
    title = Sumform("▇ ▆ =|C|h|u|n|k|l|a|t|e| |S|u|m|m|a|r|y|= ▆ ▇", True)
    eof = Sumform("_,-=|S|u|m|m|a|r|y| |E|n|d|=-,_", False)
    tmp = ""
    if not os.path.exists(folder):
        os.mkdir(folder)

    if infos is not None:
        if len(SideNotes) > 0:
            for note in SideNotes:
                tmp += "\n" + str(note) + "\n"
            infos = tmp + infos + "\n"
        else:
            infos = "\n" + infos + "\n"
    elif len(SideNotes) > 0:
        for note in SideNotes:
            tmp += "\n" + str(note) + "\n"
        infos = tmp

    filename = (
        folder + "Summary_Of_" + os.path.splitext(os.path.basename(FILE_Origin))[0]
    )
    print(Candy("Color", "green", "-Saving Summary : "), filename)
    with open(filename, "a+") as f:

        if Summary_Header is True:
            f.write(title)
            Summary_Header = False

        if infos is not None:
            f.write(sep)
            f.write(infos)

        if Summary_Footer is True:
            f.write("\n\n『File Informations: 』\n")

            if len(IHDR_Height) > 0:
                f.write("\n")
                f.write("\n-IHDR Width    :" + IHDR_Height)
            if len(IHDR_Height) > 0:
                f.write("\n-IHDR Height   :" + IHDR_Width)
            if len(IHDR_Depht) > 0:
                f.write("\n-IHDR Depht    :" + IHDR_Depht)
            if len(IHDR_Color) > 0:
                f.write("\n-IHDR Color    :" + IHDR_Color)
            if len(IHDR_Method) > 0:
                f.write("\n-IHDR Method   :" + IHDR_Method)
            if len(IHDR_Interlace) > 0:
                f.write("\n-IHDR Interlace:" + IHDR_Interlace)

            if len(pHYs_X) > 0:
                f.write("\n")
                f.write("\n-pHYs Pixels per unit, X axis: " + pHYs_X)
            if len(pHYs_Y) > 0:
                f.write("\n-pHYs Pixels per unit, Y axis: " + pHYs_Y)
            if len(pHYs_Unit) > 0:
                f.write("\n-pHYs Unit specifier         :" + pHYs_Unit)

            if len(bKGD_Gray) > 0:
                f.write("\n")
                f.write("\n-bKGD Gray   :" + bKGD_Gray)
            if len(bKGD_Red) > 0:
                f.write("\n")
                f.write("\n-bKGD Red    :" + bKGD_Red)
            if len(bKGD_Green) > 0:
                f.write("\n-bKGD Green  :" + bKGD_Green)
            if len(bKGD_Blue) > 0:
                f.write("\n-bKGD Blue   :" + bKGD_Blue)
            if len(bKGD_Index) > 0:
                f.write("\n-bKGD Palette:" + bKGD_Index)

            if len(gAMA) > 0:
                f.write("\n")
                f.write("\n-Gama   :" + gAMA)

            if len(PLTE_R) > 0:
                f.write("\n")
                f.write("\n-PLTE Red Palettes    :" + str(len(PLTE_R)))
            if len(PLTE_G) > 0:
                f.write("\n-PLTE Green Palettes   :" + str(len(PLTE_G)))
            if len(PLTE_B) > 0:
                f.write("\n-PLTE Blue Palettes    :" + str(len(PLTE_B)))

            if len(sPLT_Red) > 0:
                f.write("\n")
                f.write("\n-sPLT Suggested Red palette stored:" + str(len(sPLT_Red)))
            if len(sPLT_Green) > 0:
                f.write(
                    "\n-sPLT Suggested Green palettes stored:" + str(len(sPLT_Green))
                )
            if len(sPLT_Blue) > 0:
                f.write("\n-sPLT Suggested Blue palettes stored:" + str(len(sPLT_Blue)))
            if len(sPLT_Alpha) > 0:
                f.write(
                    "\n-sPLT Suggested Alpha palettes stored:" + str(len(sPLT_Alpha))
                )
            if len(sPLT_Freq) > 0:
                f.write(
                    "\n-sPLT Suggested Frequencies palettes stored:"
                    + str(len(sPLT_Freq))
                )

            if len(hIST) > 0:
                f.write("\n-Histogram frequencies stored:" + str(len(hIST)))

            if len(tRNS_Gray) > 0:
                f.write("\n")
                f.write("\n-tRNS Transparency Gray     :" + tRNS_Gray)
            if len(tRNS_TrueR) > 0:
                f.write("\n-tRNS Transparency Red      :" + tRNS_TrueR)
            if len(tRNS_TrueG) > 0:
                f.write("\n-tRNS Transparency Green    :" + tRNS_TrueG)
            if len(tRNS_TrueB) > 0:
                f.write("\n-tRNS Transparency Blue     :" + tRNS_TrueB)
            if len(tRNS_Index) > 0:
                f.write("\n-tRNS Alpha indexes stored:" + str(len(tRNS_Index)))

            if len(sTER) > 0:
                f.write("\n-Subimage mode    :" + str(sTER))

            if len(cHRM_WhiteX) > 0:
                f.write("\n")
                f.write("\n-cHRM chromaticities WhiteX   :" + cHRM_WhiteX)
            if len(cHRM_WhiteY) > 0:
                f.write("\n-cHRM chromaticities WhiteY   :" + cHRM_WhiteY)
            if len(cHRM_Redx) > 0:
                f.write("\n-cHRM chromaticities RedX     :" + cHRM_Redx)
            if len(cHRM_Redy) > 0:
                f.write("\n-cHRM chromaticities RedY     :" + cHRM_Redy)
            if len(cHRM_Greenx) > 0:
                f.write("\n-cHRM chromaticities GreenX   :" + cHRM_Greenx)
            if len(cHRM_Greeny) > 0:
                f.write("\n-cHRM chromaticities GreenY   :" + cHRM_Greeny)
            if len(cHRM_Bluex) > 0:
                f.write("\n-cHRM chromaticities BlueX   :" + cHRM_Bluex)
            if len(cHRM_Bluey) > 0:
                f.write("\n-cHRM chromaticities BlueY   :" + cHRM_Bluey)

            if len(sBIT_Gray) > 0:
                f.write("\n")
                f.write("\n-sBIT Significant greyscale bits    :" + sBIT_Gray)
            if len(sBIT_TrueR) > 0:
                f.write("\n-sBIT significant bits Red    :" + sBIT_TrueR)
            if len(sBIT_TrueG) > 0:
                f.write("\n-sBIT significant bits Green  :" + sBIT_TrueG)
            if len(sBIT_TrueB) > 0:
                f.write("\n-sBIT significant bits Blue   :" + sBIT_TrueB)
            if len(sBIT_GrayScale) > 0:
                f.write("\n-sBIT Gray scale significant bit:" + sBIT_GrayScale)
            if len(sBIT_GrayAlpha) > 0:
                f.write("\n-sBIT Gray alpha significant bit:" + sBIT_GrayAlpha)
            if len(sBIT_TrueAlphaR) > 0:
                f.write("\n-sBIT significant bits Alpha Red    :" + sBIT_TrueAlphaR)
            if len(sBIT_TrueAlphaG) > 0:
                f.write("\n-sBIT significant bits Alpha Green  :" + sBIT_TrueAlphaG)
            if len(sBIT_TrueAlphaB) > 0:
                f.write("\n-sBIT significant bits Alpha Blue   :" + sBIT_TrueAlphaB)
            if len(sBIT_TrueAlpha) > 0:
                f.write("\n-sBIT significant bits Alpha        :" + sBIT_TrueAlpha)

            if len(pCAL_Key) > 0:
                f.write("\n")
                f.write(
                    "\n-pCAL Calibration name    :"
                    + bytes.fromhex(pCAL_Key).decode(errors="replace")
                )
            if len(pCAL_Zero) > 0:
                f.write("\n-pCAL Original zero       :" + pCAL_Zero)
            if len(pCAL_Max) > 0:
                f.write("\n-pCAL Original max        :" + pCAL_Max)
            if len(pCAL_Eq) > 0:
                f.write("\n-pCAL Equation type       :" + pCAL_Eq)
            if len(pCAL_PNBR) > 0:
                f.write("\n-pCAL Number of parameters:" + pCAL_PNBR)

            if len(iCCP_Name) > 0:
                f.write("\n")
                f.write("\n-iCCP Profile Name :" + iCCP_Name)

            if len(str(iCCP_Method)) > 0:
                f.write("\n-iCCP Profile Method :" + str(iCCP_Method))

            if len(sRGB) > 0:
                f.write("\n")
                f.write("\n-sRGB Rendering    :" + sRGB)

            if len(tIME_Yr) > 0:
                f.write("\n")
                f.write("\n-Year     :" + tIME_Yr)
            if len(tIME_Mth) > 0:
                f.write("\n-Month    :" + tIME_Mth)
            if len(tIME_Day) > 0:
                f.write("\n-Day      :" + tIME_Day)
            if len(tIME_Hr) > 0:
                f.write("\n-Hour     :" + tIME_Hr)
            if len(tIME_Min) > 0:
                f.write("\n-Minute   :" + tIME_Min)
            if len(tIME_Sec) > 0:
                f.write("\n-Seconde  :" + tIME_Sec)

            if len(tEXt_Key_List) > 0 and len(tEXt_Key_List) == len(tEXt_Str_List):
                f.write("\n")
                for s, k in zip(tEXt_Str_List, tEXt_Key_List):
                    txt = "\n-tEXt %s :\n%s\n" % (k, s)
                    f.write(txt)
            if len(iTXt_Key_List) > 0 and len(iTXt_Key_List) == len(iTXt_String_List):
                f.write("\n")
                for s, k in zip(iTXt_String_List, iTXt_Key_List):
                    txt = "\n-iTXt %s :\n%s\n" % (k, s)
                    f.write(txt)

            if len(zTXt_Key_List) > 0 and len(zTXt_Key_List) == len(zTXt_Str_List):
                f.write("\n")
                for s, k in zip(zTXt_Str_List, zTXt_Key_List):
                    txt = "\n-zTXt %s :\n%s\n" % (k, s)
                    f.write(txt)

            f.write(eof)


def Candy(mode, arg, data=None):
    if mode == "Emoj":
        if arg == "good":
            good = [
                "¯\(◉‿◉)/¯",
                "ᕦ(ò_óˇ)ᕤ",
                "(ง ͡ʘ ͜ʖ ͡ʘ)ง",
                "^• ̮•^",
                "(◍•ᴗ•◍)❤",
                "(ツ)",
                "❣◕ ‿ ◕❣",
                "(⁎⚈᷀᷁ᴗ⚈᷀᷁⁎)",
                "(☞ﾟヮﾟ)☞",
                "【ツ】",
                "☜(⌒▽⌒)☞",
                "(◡‿◡✿)",
                "(☆ω☆)",
                "∠(ᐛ)੭",
                "ଘ(੭ˊᵕˋ)੭* ੈ✩‧₊",
                "[̲̅$̲̅(̲̅ ͡° ͜ʖ ͡°̲̅)̲̅$̲̅]",
                "(ʘ ͜ʖ ʘ)",
                "( ͡ᵔ ͜ʖ ͡ᵔ)",
                "乁( • ω •乁)",
                "(〜￣▽￣)〜",
                "( o˘◡˘o) ┌iii┐",
                "(っ˘ڡ˘ς)",
                "(*°▽°*)",
                "⊂( ´ ▽ ` )⊃",
                "☆⌒(ゝ。∂)",
                "ヽ(✧◡✧)ノ",
                "(ᕦ｡◕‿‿◕)づ",
                "ᕙ(⇀‸↼)ᕗ",
                "ヽ('ノ)ノ",
                "ԅ(≖‿≖ԅ)",
                "(⩾‿⩽)",
                ">^.^<",
                "^^)",
                "(-^^-)",
                "( ˘ ³˘)♥",
                "♥‿♥",
                "(ಥ⌣ಥ)",
                "ʘ‿ʘ",
                "´ ▽ ` )ﾉ",
                "Σ ◕ ◡ ◕",
                "٩(｡͡•‿•｡)۶",
                "ᕕ( ᐛ )ᕗ",
                "☜(⌒▽⌒)☞",
                "(｡◕‿‿◕｡)",
                "(ღ˘⌣˘ღ)",
                "(∪ ◡ ∪)",
                "(▰˘◡˘▰)",
                "(✿ ♥‿♥)",
                "(｡◕ ‿ ◕｡)",
                "( ͡° ͜ʖ ͡°)",
                "(/◔ ◡ ◔)/",
                "(ᵔᴥᵔ)",
                "ʕつ ͡◔ ᴥ ͡◔ʔつ",
                "彡໒(⊙ ᴗ⊙)७彡",
                "(´◡`)",
                "(✯◡✯)",
                "(๑˘︶˘๑)",
                "｡^‿^｡",
                "ヽ(ヅ)ノ",
                "(^人^)",
                "(°◡°♡)",
                "(♥ ω♥ *)",
                "❀ ◕ ‿ ◕ ❀",
                "(⁀ᗢ⁀)",
                "ミ=͟͟͞͞(✿ʘ ᴗʘ)っ",
                "ଘ(੭*ˊᵕˋ)੭* ̀ˋ",
                "─=≡Σ(((つ^̀ω^́)つ ",
                "~( ˘▾˘~)",
                "(=^･ω･^=)",
                " ＼ʕ •ᴥ•ʔ／",
                "ヽ(•‿•)ノ",
                "ヾ(☆▽☆)",
                "(ツ)",
                "◝(^⌣^)◜",
                "ʕ ◉ ᴥ ◉ ʔ",
                "( =① ω① =)",
                ">(^.^)<",
            ]
            rnd = random.randint(0, len(good) - 1)
            return good[rnd]
        elif arg == "bad":
            bad = [
                "(⋟~⋞)",
                "(ノಠ ∩ಠ)ノ彡(o°o)",
                "(╯°□°)╯︵ ʞɔnℲ",
                "(ง ͠° ͟ʖ",
                "(#ಠQಠ#)",
                "(⋋▂⋌)",
                "(☞ﾟヮﾟ)☞ ┻━┻",
                "✂╰⋃╯",
                "‿︵‿ヽ(°□° )ノ︵‿︵",
                "、ヽ｀☂ヽ｀、",
                "(oT-T)尸",
                "(－‸ლ)",
                "(╯°益°)╯彡┻━┻",
                "(;´༎ຶٹ༎ຶ`)",
                "( ͡ಠ ʖ̯ ͡ಠ)",
                "(ఠ益ఠ)୨",
                "(∩` ﾛ ´)",
                "Q(`⌒´Q)",
                "٩(`皿´҂)ง",
                "(っ≧ω≦)っ",
                "─=≡Σ((( つ＞□＜)つ",
                "(凸✧∀✧)つ",
                "(￣_￣)・・・",
                "(ﾉಥ益ಥ)ﾉ",
                "↑_(ΦwΦ)Ψ",
                "୧((#Φ益Φ#))୨",
                "٩(╬ʘ益ʘ╬)۶",
                "[¬º-°]¬",
                "(°︹°)╭∩╮",
                "▀皿▀￣",
                "(っ˘ڡ˘ς)",
                "ლ(๏□ ๏ლ)",
                "(♨_♨)",
                "( ͡ಠ ʖ̯ ͡ಠ )",
                "(⩾ヘ⩽)",
                "(҂◡_◡)",
                "(~~,)",
                "(ಥ_ಥ)",
                "(ಥ﹏ಥ)",
                "(►_◄)",
                "(◉ ︵◉)",
                "ヽ(ｏ`皿′ｏ)ﾉ",
                "凸ಠ益ಠ)凸",
                "╯‵Д′)╯彡┻━┻",
                "¯\_(⊙︿⊙)_/¯",
                "ಠ︵ಠ 凸",
                "ヽ(`Д´)ﾉ",
                "(╯°□°）╯︵ ┻━┻",
                "(✖╭╮✖)",
                "(︶︹︺)",
                "(╯︵╰,)",
                "ヽ(˚௰˚)づ",
                "(⊙ ▂⊙ ✖ )",
                "ᕕ༼ ͠ຈ Ĺ̯ ͠ຈ ༽┌∩┐",
                "凸(>皿<)凸",
                "ʕ థ ౪ థ ʔ",
                "༼ ༎ຶ ᆺ ༎ຶ༽",
                "( ◥◣ _◢◤ )",
                "(━┳━ _ ━┳━)",
                "┐(￣ヘ￣)┌",
                "༼☯﹏☯༽",
                "(° -°） ︵ ┻━┻ ",
                "┻━┻︵ \(°□°)/ ︵ ┻━┻ ",
                "◕ ︵◕ ",
                "( ◡ ︵◡ )",
                "(；⌣̀_⌣́)",
                "( ´〒^〒`)",
                "(；￣Д￣)",
                "ʕ TᴥT ʔ ",
                "ヽ(๏ ∀ ๏ )ﾉ",
                "┗(･ω･;)┛",
                "(*￣o￣)",
                "ヽ(O_O )ﾉ",
                "ƪ( ` ▿▿▿▿ ´ ƪ) ",
                "(>ΦωΦ<)",
                "(x_x)⌒☆",
                "ヾ(⌣́︹⌣́ )ゞ ",
            ]
            rnd = random.randint(0, len(bad) - 1)
            return bad[rnd]
        if arg == "com":
            com = [
                "(◉_●`)",
                "(ب_ب)",
                "ಠ_ರೃ",
                "(^..^)ﾉ",
                "(´･o･｀*)",
                "(^◕~◕^)",
                "(⌐■_■)",
                "(ʘ ʖ̯ ʘ)",
                "(ʘ ͟ʖ ʘ)",
                "(.•́ _ʖ •̀.)",
                "( ͠° ͟ʖ ͡°)",
                "( ͡° ʖ̯ ͡°)",
                "＼(￣(oo)￣)／",
                "(∪｡∪)",
                "ε=ε=ε=ε=┌(;￣o￣)┘",
                "┬┴┬┴┤･ω･)ﾉ",
                "ﾍ(･_|",
                "|ω･)ﾉ",
                "(•́ _ʖ •̀)",
                "(￢ ￢)",
                "╮(￣ω￣;)╭",
                "(~ω~)",
                "(っ•́｡•́)",
                "(▀.▀￣)",
                "｡•́_•̀｡",
                "(ㆆ㉨ㆆ)",
                "¿Ⓧ_Ⓧﮌ",
                "ᕦ(ò_óˇ)ᕤ",
                "(Ծ‸ Ծ)",
                "(눈_눈)",
                "( ఠ ͟ʖ ఠ )",
                "(⥀.⥀)",
                "(~.~)",
                "(◔_◔)",
                "(๑•́ ₃ •̀๑)",
                "(ఠ_ఠ)",
                "(◎_◎)",
                "(⊙﹏⊙)",
                "(´･_･`)",
                "(ಠ_ಠ)",
                "（　ﾟДﾟ）",
                "~' ▽ '~ )ﾉ",
                "⁀⊙ ෴ ☉⁀",
                "(๏ᆺ   ๏ υ)",
                "─=≡Σ((( つ•̀ω•́)つ ",
                "⌗(́◉◞౪◟◉‵⌗)",
                "(∩｀-´)⊃━☆ﾟ.*･｡ﾟ ",
                "(〓￣(∵エ∵)￣〓)",
                "┬┴┬┴┤ᵒᵏ (･_├┬┴┬┴ ",
                "((유∀유|||))",
                "ε=ε=(っ* ´□` )っ",
                "（・⊝・∞）",
                "( ● ´⌓ `● )",
                "(╯•﹏•╰)",
                "˛˛ƪ(⌾⃝ ౪ ⌾⃝ ๑)و ̉ ̉ ",
                "( ؕؔʘ̥̥̥̥ ه ؔؕʘ̥̥̥̥ )? ",
                "(´⊙ ω ⊙`)！",
                "ლ(́◉◞౪◟◉‵ლ)",
                "(*′☉.̫☉)",
                "=͟͟͞͞ =͟͟͞͞ ﾍ ( ´ Д `)ﾉ ",
                "  (⁄ ⁄•⁄ω⁄•⁄ ⁄)",
                "(〃＞＿＜;〃)",
                "<(￣ ﹌ ￣)>",
                "(￣ ￣|||)",
                "(￢_￢;)",
                "＼(〇_ｏ)／",
                "(／。＼)",
                "〜(＞＜)〜",
                "(/ω＼)",
                "┐(￣～￣)┌",
                "┐(︶▽︶)┌",
                "ヽ(ˇヘˇ)ノ",
            ]
            rnd = random.randint(0, len(com) - 1)
            return com[rnd]

    if mode == "Color" and os.name != "nt":
        if arg == "red":
            prnt = "\033[1;31;49m%s\033[m" % data
        elif arg == "green":
            prnt = "\033[1;32;49m%s\033[m" % data
        elif arg == "blue":
            prnt = "\033[1;34;49m%s\033[m" % data
        elif arg == "purple":
            prnt = "\033[1;35;49m%s\033[m" % data
        elif arg == "yellow":
            prnt = "\033[1;33;49m%s\033[m" % data
        elif arg == "white":
            prnt = "\033[1;37;49m%s\033[m" % data
        return prnt
    elif mode == "Color" and os.name == "nt":
        prnt = data

    if mode == "Cowsay":
        BotL = "╰─"
        BotR = "─╯"
        mult = 0
        #       print("arg:",arg)
        #       print("barg:",arg.encode(errors='ignore'))
        for chr in arg:
            mult += 1

        if b"\x1b[1;31;49m" in arg.encode(errors="ignore"):
            mult = mult - (
                len(b"\x1b[1;31;49m")
                * arg.encode(errors="ignore").count(b"\x1b[1;31;49m")
            )
            Moj = str(Candy("Emoj", "com"))
        if b"\x1b[1;32;49m" in arg.encode(errors="ignore"):
            mult = mult - (
                len(b"\x1b[1;32;49m")
                * arg.encode(errors="ignore").count(b"\x1b[1;32;49m")
            )
        if b"\x1b[1;33;49m" in arg.encode(errors="ignore"):
            mult = mult - (
                len(b"\x1b[1;33;49m")
                * arg.encode(errors="ignore").count(b"\x1b[1;33;49m")
            )
        if b"\x1b[1;34;49m" in arg.encode(errors="ignore"):
            mult = mult - (
                len(b"\x1b[1;34;49m")
                * arg.encode(errors="ignore").count(b"\x1b[1;34;49m")
            )
        if b"\x1b[1;35;49m" in arg.encode(errors="ignore"):
            mult = mult - (
                len(b"\x1b[1;35;49m")
                * arg.encode(errors="ignore").count(b"\x1b[1;35;49m")
            )
        if b"\x1b[1;37;49m" in arg.encode(errors="ignore"):
            mult = mult - (
                len(b"\x1b[1;37;49m")
                * arg.encode(errors="ignore").count(b"\x1b[1;37;49m")
            )
        if b"\x1b[m" in arg.encode(errors="ignore"):
            mult = mult - (
                len(b"\x1b[m") * arg.encode(errors="ignore").count(b"\x1b[m")
            )
        if b"\x0A" in arg.encode(errors="ignore"):
            mult = mult - (len(b"\x0A") * arg.encode(errors="ignore").count(b"\x0A"))

        Sep = "━" * mult
        if data == "com":
            Moj = str(Candy("Emoj", "com"))
            lnMoj = len(Moj)
        elif data == "good":
            Moj = str(Candy("Emoj", "good"))
            lnMoj = len(Moj)
        else:
            Moj = str(Candy("Emoj", "bad"))
            lnMoj = len(Moj)
        CowSep = " " * lnMoj
        CowSep += "/\n"
        CowSep += str(Moj)

        Botrnp = BotL + Sep + BotR
        prnt = " " + str(arg)
        if len(prnt) >= MAXCHAR:
            fullprnt = prnt
            prnt = " "
            mult = int(mult / 2) + 5
            Sep = "━" * mult
            Botrnp = BotL + Sep + BotR
            for i in range(0, len(fullprnt), mult):
                if len(arg[i:]) > mult:
                    prnt += "  " + str(arg[i : i + mult]) + "\n"
                else:
                    prnt += "  " + str(arg[i:])
        if data == "com" and os.name != "nt":
            Cowsay = """
%s
\033[1;33;49m%s
%s
\033[m""" % (
                prnt,
                Botrnp,
                CowSep,
            )
        elif data == "good" and os.name != "nt":
            Cowsay = """
%s
\033[1;32;49m%s
%s
\033[m""" % (
                prnt,
                Botrnp,
                CowSep,
            )
        elif data == "bad" and os.name != "nt":
            Cowsay = """
%s
\033[1;31;49m%s
%s
\033[m""" % (
                prnt,
                Botrnp,
                CowSep,
            )
        elif os.name == "nt":
            Cowsay = """
%s
%s
%s
""" % (
                prnt,
                Botrnp,
                CowSep,
            )

        else:
            Cowsay = """
%s
%s
%s
""" % (
                prnt,
                Botrnp,
                CowSep,
            )

        print(Cowsay)
        if PAUSEDIALOGUE is True:
            pause = input("-Pause Dialogue-")

    if mode == "Title":
        BotL = "╰─"
        BotR = "─╯"
        TopL = "╭─"
        TopR = "─╮"
        Sep = (
            "━" * len(str(arg))
            if data == None
            else "━" * (len(str(arg) + str(data)) + 3)
            if "\x1b[m" not in data
            else "━" * (len(str(arg) + str(data)) - 12)
        )
        Toprnt = TopL + Sep + TopR
        Botrnp = BotL + Sep + BotR
        prnt = "  " + str(arg) if data == None else "  " + str(arg) + " " + str(data)
        if os.name == "nt":
            Title = """
%s
%s
%s
""" % (
                Toprnt,
                prnt,
                Botrnp,
            )
        elif os.name != "nt":
            Title = """
\033[1;37;49m%s\033[m
%s
\033[1;37;49m%s\033[m
""" % (
                Toprnt,
                prnt,
                Botrnp,
            )
        print(Title)


def SplitDigits(lst):
    return [DigDigits(k) for k in re.split(r"(\d+)", lst)]


def DigDigits(dig):
    return int(dig) if dig.isdigit() else dig


def ChunkStory(action, Chunk, start, end, chuck_length):
    global Chunks_History
    global Chunks_History_Index

    if type(Chunk) is not bytes:
        Chunk = Chunk.encode(errors="ignore")

    if action == "add":
        CHD = str(len(Chunks_History) - 1)+ ":"+ str(start)+ ":"+ str(end)+ ":"+ str(chuck_length)
        chkdbl = str(start)+ ":"+ str(end)+ ":"+ str(chuck_length)
        if chkdbl not in Chunks_History_Index:
           Chunks_History.append(Chunk)
           Chunks_History_Index.append(CHD)
    elif action == "del":
        try:
            del Chunks_History[Chunks_History.index(Chunk)]
            del Chunks_History_Index[Chunks_History.index(Chunk)]
        except Except as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                if PAUSEDEBUG is True:
                    Pause("Pause:Chunkstory")


def TheEnd():
    if DEBUG is True:

        print("Chnks nbr:", len(Chunks_History_Index))
        print("idacounter:", idatcounter)
        print(Chunks_History)
        print("IDAT_Bytes_Len:%s",IDAT_Bytes_Len)
    if PAUSEDEBUG is True:
        Pause("ThenEnd debug")
    Summarise(None, True)
    Chunklate(0)
    sys.exit(0)


def ToBitstory(bytenbr):
    global Bytes_History
    Bytes_History.append(bytenbr)


@contextmanager
def stderr_redirector(stream):
    original_stderr_fd = sys.stderr.fileno()

    def _redirect_stderr(to_fd):
        """Redirect stderr to the given file descriptor."""
        libc.fflush(c_stderr)
        sys.stderr.close()
        os.dup2(to_fd, original_stderr_fd)
        sys.stderr = io.TextIOWrapper(os.fdopen(original_stderr_fd, "wb"))

    saved_stderr_fd = os.dup(original_stderr_fd)
    try:
        tfile = tempfile.TemporaryFile(mode="w+b")
        _redirect_stderr(tfile.fileno())
        yield
        _redirect_stderr(saved_stderr_fd)
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read())
    finally:
        tfile.close()
        os.close(saved_stderr_fd)

#haystack, value, FewYearsLater = Bruthex(cidx, value, str(haystack), total_len)
def Bruthex(cidx, value, datax, totalln):
    newvalues = []
    dataxlst = list(datax)
    value_ln = 0
    if value < 16 ** totalln:
        fullhx = hex(value).replace("0x", "").zfill(totalln)
        value += 1
    else:
        return (None, None, True)
    for c in cidx:
        dataxlst[c[0] : c[1]] = fullhx[value_ln : value_ln + c[2]]
        value_ln += c[2]
    return ("".join(dataxlst), value, False)

def SmashBruteBrawl(File, ChunkName, ChunkLenght, DataOffset,FromError, EditMode ,BruteCrc = False, BruteLenght = False):
    global WORKING
    global SideNotes

    Candy("Title", "Attempting Bruteforce To Repair Corrupted Chunk Data:")

    try:
       ChunkName = ChunkName.encode(errors="ignore")
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))

    CNamex_New = hex(int.from_bytes(ChunkName, byteorder="big")).replace("0x","")

    if DEBUG is False:
        Thread(target=Loadingbar).start()

    Bingo = False
    result = "result is empty"
#    chunknx = hex(int.from_bytes(ChunkName, byteorder="big")).replace("0x","")
    KNOWN_CHUNKS_SPEC = GetSpec()
    for key in KNOWN_CHUNKS_SPEC:
        for color_type, bytes_spec in KNOWN_CHUNKS_SPEC[key].items():
            if key == ChunkName:

                CNamex_New = hex(int.from_bytes(ChunkName, byteorder="big")).replace("0x","")

                if "nocolortype" in color_type:
                    chunklen_spec = bytes_spec[0]
                    chunk_format = bytes_spec[1]
                    chunk_data = bytes_spec[2]

                    if type(chunklen_spec) == tuple:
                       maxchunklen = max(chunklen_spec)
                       minchunklen = min(chunklen_spec)
                    else:
                       maxchunklen = chunklen_spec
                       minchunklen = chunklen_spec

    
    if maxchunklen  == minchunklen:
       maxchunklen += 1
       step = 1
    else:
       step = minchunklen

    if DEBUG is True:
        print("File:", File)
        print("ChunkName:",ChunkName)
        print("DataOffset:",DataOffset)
        print("ChunkLenght:",ChunkLenght)
        print("BruteCrc:",BruteCrc)
        print("EditMode:",EditMode)
        print("FromError:",FromError)
        print("chunklen_spec:",chunklen_spec)
        print("chunk_format:",chunk_format)
        print("chunk_data:",chunk_data)
        print("maxchunklen:",maxchunklen)
        print("minchunklen:",minchunklen)
        if PAUSEDEBUG is True:
            Pause("Pause:SmashBruteBrawl")

    for ln in range(minchunklen,maxchunklen,step):
        Lnx_New = hex(int(ln/2)).replace("0x","").zfill(8)
        if EditMode == "replace":
            if not BruteLenght and not BruteCrc:
                 Before_New = DATAX[:DataOffset]
                 After_New = DATAX[DataOffset+ChunkLenght+24:] #+24=chunklen+chunkname+data+crc

        shuffle = itertools.product(*chunk_data)
        for i in shuffle:
            hexvalue = ""
            for d,j in zip(chunk_format,i):
                hexvalue +=  hex(int(j)).replace("0x", "").zfill(d)

            newbytes = bytes.fromhex(hexvalue)
            checksum = hex(binascii.crc32(ChunkName + newbytes)).replace("0x", "").zfill(8)
            fullnewdatax = Lnx_New + CNamex_New + hexvalue + checksum
            newfilewanabe = Before_New + fullnewdatax + After_New

            f = io.BytesIO()
            try:
                with stderr_redirector(f):
                    newfilewanarray = np.fromstring(bytes.fromhex(newfilewanabe), np.uint8)
                    newfile = cv2.imdecode(newfilewanarray, cv2.IMREAD_COLOR)
                    cv2.imread(newfile)
                result = "{0}".format(f.getvalue().decode("utf-8"))
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(
                        Candy("Color", "red", "FullChunkForcerNoCrc Error:"),
                        Candy("Color", "yellow", e),
                    )
                    print("fullnewdatax:", fullnewdatax)
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause:Debug")
        #            Pause("pause")
            if "libpng error" not in result and result != "result is empty":
                diffobj = difflib.SequenceMatcher(None, datax[16:], fullnewdatax)
                good = ""
                bad = ""
                for block in diffobj.get_opcodes():
                    if block[0] != "equal":
                        good += "\033[1;32;49m%s\033[m" % fullnewdatax[block[1] : block[2]]
                        bad += "\033[1;31;49m%s\033[m" % datax[16:][block[1] : block[2]]
                    else:
                        good += fullnewdatax[block[1] : block[2]]
                        bad += datax[16:][block[1] : block[2]]
                Bingo = True
                break
            elif DEBUG is True:
                 print("\nBefore_New:",Before_New)
                 print("Middle:",DATAX[DataOffset:DataOffset+ChunkLenght])
                 print("After_New:",After_New[:50])
                 print("Lnx_New:",Lnx_New)
                 print("hexvalue:",hexvalue)
                 print("fullnewdatax:",fullnewdatax)
                 print("fullnewdatax byte:",bytes.fromhex(fullnewdatax))
                 print("result:",result)
                 print("\ndata before:\n",DATAX[:150])
                 print("data after:\n",newfilewanabe[:150])
                 #Pause("Pause")
    WORKING = False

    if Bingo is True:
        print(
            "-Bruteforce was %s %s"
            % (Candy("Color", "green", "Successfull!"), Candy("Emoj", "good"))
        )
        print(
            "-Chunk %s has been repaired by changing those bytes:\n"
            % Candy("Color", "green", Chunk)
        )
        print(bad)
        print("\n-With those bytes:\n")
        print(good)
        Candy("Cowsay", "Wow ...I wasn't sure this would work to be honest !", "good")
        SideNotes.append(
            "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull.\n-Chunk %s has been repaired by changing those bytes:\n%s\n-with bytes:\n%s"
            % (Chunk, datax[16:], fullnewdatax)
        )
        return CheckPoint(
            True,
            True,
            "MiniChunkForcerNoCrc",
            Chunk.decode(errors="ignore"),
            ["-Data has been corrupted"],
            fullnewdatax,
            DataOffset,
            DataOffset + ChunkLenght,
            "-Replacing Corrupted %s Data:\n%s\n-With:\n%s"
            % (Chunk.decode(errors="ignore"), datax[16:], fullnewdatax),
            Chunk.decode(errors="ignore"),
            FromError,
        )

    else:
        print(
            "-Bruteforce has %s %s"
            % (Candy("Color", "red", "Failed!"), Candy("Emoj", "bad"))
        )
        Candy("Cowsay", "I was afraid of this ..Looks like we r stuck..", "bad")
        SideNotes.append("\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!")
        TheEnd()
        return CheckPoint(
            True,
            False,
            "MiniChunkForcerNoCrc",
            Chunk.decode(errors="ignore"),
            ["-Bruteforcer has Failed"],
            FromError,
        )


def MiniChunkForcerNoCrc(File, Chunk, DataOffset, ChunkLenght, CIndexList, FromError): ## need to be merged with SmashBruteBrawl
    global WORKING
    global SideNotes
    Candy("Title", "Attempting To Repair Corrupted Chunk Data:")
    Chunk = Chunk.encode(errors="ignore")
    FewYearsLater = False
    value = 0
    cidx = []
    total_len = 0

    if DEBUG is True:
        print("file:", File)
        print("chunk:", Chunk)
        print("offd:", DataOffset)
        print("cl:", ChunkLenght)
        if PAUSEDEBUG is True:
            Pause("Pause:MiniChunkForcerNoCrc")
    try:
        with open(Sample, "rb") as f:
            data = f.read()
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
        TheEnd()

    datax = data.hex()[DataOffset:ChunkLenght]
    haystack = datax[16:-8]

    if DEBUG is False:
        Thread(target=Loadingbar).start()
    else:
        for i in CIndexList:
            print("CIndexList:",i)
        if PAUSEDEBUG is True:
            Pause("Pause:Reboot")
    Bingo = False
    result = "result is empty"
    needle = 0

    for key in CIndexList:
        print("key:",key)
        start = int(key.split("CIndex([")[1].split(":")[0])
        stop = int(key.split("CIndex([")[1].split(":")[1].split("])")[0])
        ln = stop - start
        total_len += ln
        cidx.append((start, stop, ln))
    #    print("heystack:",haystack)
    while True:

        haystack, value, FewYearsLater = Bruthex(cidx, value, str(haystack), total_len)
        if FewYearsLater is True:
            break
        newbytes = bytes.fromhex(haystack)
        checksum = hex(binascii.crc32(Chunk + newbytes)).replace("0x", "").zfill(8)
        fullnewdatax = datax[:16] + haystack + checksum
        newfilewanabe = DATAX[:DataOffset] + fullnewdatax + DATAX[ChunkLenght:]
        try:
            f = io.BytesIO()
            with stderr_redirector(f):
                newfilewanarray = np.fromstring(bytes.fromhex(newfilewanabe), np.uint8)
                newfile = cv2.imdecode(newfilewanarray, cv2.IMREAD_COLOR)
                cv2.imread(newfile)
            result = "{0}".format(f.getvalue().decode("utf-8"))
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "FullChunkForcerNoCrc Error:"),
                    Candy("Color", "yellow", e),
                )
                print("fullnewdatax:", fullnewdatax)
            if PAUSEDEBUG is True or PAUSEERROR is True:
                Pause("Pause:Debug")
        #            Pause("pause")
        if "libpng error" not in result and result != "result is empty":
            diffobj = difflib.SequenceMatcher(None, datax[16:], fullnewdatax)
            good = ""
            bad = ""
            for block in diffobj.get_opcodes():
                if block[0] != "equal":
                    good += "\033[1;32;49m%s\033[m" % fullnewdatax[block[1] : block[2]]
                    bad += "\033[1;31;49m%s\033[m" % datax[16:][block[1] : block[2]]
                else:
                    good += fullnewdatax[block[1] : block[2]]
                    bad += datax[16:][block[1] : block[2]]
            Bingo = True
            break

    WORKING = False

    if Bingo is True:
        print(
            "-Bruteforce was %s %s"
            % (Candy("Color", "green", "Successfull!"), Candy("Emoj", "good"))
        )
        print(
            "-Chunk %s has been repaired by changing those bytes:\n"
            % Candy("Color", "green", Chunk)
        )
        print(bad)
        print("\n-With those bytes:\n")
        print(good)
        Candy("Cowsay", "Wow ...I wasn't sure this would work to be honest !", "good")
        SideNotes.append(
            "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull.\n-Chunk %s has been repaired by changing those bytes:\n%s\n-with bytes:\n%s"
            % (Chunk, datax[16:], fullnewdatax)
        )
        return CheckPoint(
            True,
            True,
            "MiniChunkForcerNoCrc",
            Chunk.decode(errors="ignore"),
            ["-Data has been corrupted"],
            fullnewdatax,
            DataOffset,
            DataOffset + ChunkLenght,
            "-Replacing Corrupted %s Data:\n%s\n-With:\n%s"
            % (Chunk.decode(errors="ignore"), datax[16:], fullnewdatax),
            Chunk.decode(errors="ignore"),
            FromError,
        )

    else:
        print(
            "-Bruteforce has %s %s"
            % (Candy("Color", "red", "Failed!"), Candy("Emoj", "bad"))
        )
        Candy("Cowsay", "I was afraid of this ..Looks like we r stuck..", "bad")
        SideNotes.append("\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!")
        Candy("Cowsay", "Wanna try bruteforce the entire chunk ?", "com")
        Answer = Question()
        if Answer is True:
            return(SmashBruteBrawl(File, Chunk, ChunkLenght, DataOffset,FromError, "replace" ,BruteCrc = False, BruteLenght = False))
        else:
           TheEnd()
        return CheckPoint(
            True,
            False,
            "MiniChunkForcerNoCrc",
            Chunk.decode(errors="ignore"),
            ["-Bruteforcer has Failed"],
            FromError,
        )

def FullChunkForcerNoCrc(File, Chunk, DataOffset, ChunkLenght, FromError): ## need to be merged with SmashBruteBrawl
    global WORKING
    global SideNotes
    Candy("Title", "Attempting To Repair Corrupted Chunk Data:")
    Chunk = Chunk.encode(errors="ignore")
    Checklist = []
    if DEBUG is True:
        print("file:", File)
        print("chunk:", Chunk)
        print("offd:", DataOffset)
        print("cl:", ChunkLenght)
        if PAUSEDEBUG is True:
            Pause("Debug Pause:")

    try:
        with open(Sample, "rb") as f:
            data = f.read()
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
        TheEnd()

    if DEBUG is False:
        Thread(target=Loadingbar).start()
    datax = data.hex()[DataOffset:ChunkLenght]  # datax[16:-8]
    Bingo = False
    result = "result is empty"
    needle = 0
    needle2 = 2
    while needle2 <= len(datax) and Bingo is False:
        if needle < len(datax) - (needle2 - 1) and Bingo is False:
            for hexa in range(0, 16 ** needle2):
                newbyte = (hex(hexa).replace("0x", "")).zfill(needle2)
                newdatax_copy = (
                    datax[:needle] + newbyte + datax[needle + len(newbyte) :]
                )
                newdatax = bytes.fromhex(newdatax_copy)
                checksum = (
                    hex(binascii.crc32(Chunk + newdatax)).replace("0x", "").zfill(8)
                )
                #                print("dataxt:",datax[:16])
                #                print("newdataxt:",newdatax.hex())
                #                print("checksum:",checksum)
                fullnewdatax = datax[:16] + newdatax.hex() + checksum
                newfilewanabe = DATAX[:DataOffset] + fullnewdatax + DATAX[ChunkLenght:]

                #                print(newdatax_copy)
                try:
                    f = io.BytesIO()
                    with stderr_redirector(f):
                        newfilewanarray = np.fromstring(
                            bytes.fromhex(newfilewanabe), np.uint8
                        )
                        newfile = cv2.imdecode(newfilewanarray, cv2.IMREAD_COLOR)
                        #                            img = cv2.imshow("image", newfile)
                        cv2.imread(newfile)
                    result = "{0}".format(f.getvalue().decode("utf-8"))
                    print(result)
                    pause = input("pause")
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    print(
                        Candy("Color", "red", "Error FullChunkForcerNoCrc:"),
                        Candy("Color", "yellow", e),
                    )
                    if (PAUSEDEBUG or PAUSEERROR) is True:
                        Pause("Pause Debug")
                if DEBUG is True:
                    print("fullnewdatax:", fullnewdatax)
                    if PAUSEDEBUG is True:
                        Pause("Pause Debug")
                if "libpng error" not in result and result != "result is empty":
                    diffobj = difflib.SequenceMatcher(None, datax[16:], fullnewdatax)
                    good = ""
                    bad = ""
                    for block in diffobj.get_opcodes():
                        if block[0] != "equal":
                            good += (
                                "\033[1;32;49m%s\033[m"
                                % fullnewdatax[block[1] : block[2]]
                            )
                            bad += (
                                "\033[1;31;49m%s\033[m"
                                % datax[16:][block[1] : block[2]]
                            )
                        else:
                            good += fullnewdatax[block[1] : block[2]]
                            bad += datax[16:][block[1] : block[2]]
                    Bingo = True
                    break
            needle += 1
        else:
            needle = 0
            needle2 += 2
    #            print("needle2 = ",needle2)
    #            Pause("poz2")
    WORKING = False
    if Bingo is True:
        print(
            "-Bruteforce was %s %s"
            % (Candy("Color", "green", "Successfull!"), Candy("Emoj", "good"))
        )
        print(
            "-Chunk %s has been repaired by changing those bytes:\n"
            % Candy("Color", "green", Chunk)
        )
        print(bad)
        print("\n-With those bytes:\n")
        print(good)
        Candy("Cowsay", "Wow ...I wasn't sure this would work to be honest !", "good")
        SideNotes.append(
            "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull.\n-Chunk %s has been repaired by changing those bytes:\n%s\n-with bytes:\n%s"
            % (Chunk, datax[16:], fullnewdatax)
        )

        return CheckPoint(
            True,
            True,
            "FullChunkForcerNoCrc",
            Chunk.decode(errors="ignore"),
            ["-Data has been corrupted"],
            fullnewdatax,
            DataOffset,
            DataOffset + ChunkLenght,
            "-Replacing Corrupted %s Data:\n%s\n-With:\n%s"
            % (Chunk.decode(errors="ignore"), datax[16:], fullnewdatax),
            Chunk.decode(errors="ignore"),
            FromError,
        )

    else:
        print(
            "-Bruteforce has %s %s"
            % (Candy("Color", "red", "Failed!"), Candy("Emoj", "bad"))
        )
        Candy("Cowsay", "I was afraid of this ..Looks like we r stuck..", "bad")
        SideNotes.append("\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!")
        TheEnd()
        return CheckPoint(
            True,
            False,
            "FullChunkForcerNoCrc",
            Chunk.decode(errors="ignore"),
            ["-Bruteforcer has Failed"],
            FromError,
        )


def FullChunkForcerWithCrc(File, Chunk, OldCrc, DataOffset, ChunkLenght, FromError): ## need to be merged with SmashBruteBrawl
    global WORKING
    global SideNotes
    Candy("Title", "Attempting To Repair Corrupted Chunk Data:")
    Chunk = Chunk.encode(errors="ignore")
    if DEBUG is True:
        print("file:", File)
        print("chunk:", Chunk)
        print("crc:", OldCrc)
        print("offd:", DataOffset)
        print("cl:", ChunkLenght)
        if PAUSEDEBUG is True:
            Pause("Pause:Debug")

    try:
        with open(Sample, "rb") as f:
            data = f.read()
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
        TheEnd()
    if DEBUG is False:
        Thread(target=Loadingbar).start()
    #    if File == "IHDR-Wrong-Width.png":
    #        time.sleep(15)
    datax = data.hex()[DataOffset : DataOffset + (ChunkLenght * 2)]
    # datax = data.hex()[DataOffset : DataOffset + 6]
    Bingo = False
    needle = 0
    needle2 = 2
    while needle2 <= len(datax) and Bingo is False:
        if needle < len(datax) - (needle2 - 1) and Bingo is False:
            for hexa in range(0, 16 ** needle2):
                newbyte = (hex(hexa).replace("0x", "")).zfill(needle2)
                newdatax_copy = (
                    datax[:needle] + newbyte + datax[needle + len(newbyte) :]
                )
                newdatax = bytes.fromhex(newdatax_copy)
                checksum = (
                    hex(binascii.crc32(Chunk + newdatax)).replace("0x", "").zfill(8)
                )
                #                print(newdatax_copy)

                if checksum == OldCrc:
                    diffobj = difflib.SequenceMatcher(None, datax, newdatax_copy)
                    good = ""
                    bad = ""
                    for block in diffobj.get_opcodes():
                        if block[0] != "equal":
                            good += (
                                "\033[1;32;49m%s\033[m"
                                % newdatax_copy[block[1] : block[2]]
                            )
                            bad += "\033[1;31;49m%s\033[m" % datax[block[1] : block[2]]
                        else:
                            good += newdatax_copy[block[1] : block[2]]
                            bad += datax[block[1] : block[2]]
                    Bingo = True
                    break

            needle += 1
        else:
            needle = 0
            needle2 += 2
    #            print("needle2 = ",needle2)
    #            Pause("poz2")

    WORKING = False

    if Bingo is True:
        print(
            "-Bruteforce was %s %s"
            % (Candy("Color", "green", "Successfull!"), Candy("Emoj", "good"))
        )
        print(
            "-Previous Crc %s has been found by changing those bytes:\n"
            % Candy("Color", "green", OldCrc)
        )
        print(bad)
        print("\n-With those bytes:\n")
        print(good)
        Candy("Cowsay", "Wow ...I wasn't sure this would work to be honest !", "good")
        SideNotes.append(
            "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull.\n-Previous Crc %s has been found by changing those bytes:\n%s\n-with bytes:\n%s"
            % (OldCrc, datax, newdatax_copy)
        )

        #   Pause("Theend")
        #   TheEnd()
        return CheckPoint(
            True,
            True,
            "FullChunkForcerWithCrc",
            Chunk.decode(errors="ignore"),
            ["-Data has been corrupted"],
            newdatax_copy,
            DataOffset,
            DataOffset + (ChunkLenght * 2),
            "-Replacing Corrupted %s Data:\n%s\n-With:\n%s"
            % (Chunk.decode(errors="ignore"), datax, newdatax_copy),
            Chunk.decode(errors="ignore"),
            FromError,
        )

    else:
        print(
            "-Bruteforce has %s %s"
            % (Candy("Color", "red", "Failed!"), Candy("Emoj", "bad"))
        )
        Candy("Cowsay", "I was afraid of this ..Looks like we r stuck..", "bad")
        SideNotes.append("\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!")
        return CheckPoint(
            True,
            False,
            "FullChunkForcerWithCrc",
            Chunk.decode(errors="ignore"),
            ["-Bruteforcer has Failed"],
            FromError,
        )


def FindMagic():
    global SideNotes

    Candy("Title", "Looking for magic header:")

    magic = "89504e470d0a1a0a"
    magc = ["89504e470a1a0a00000004948445200", "89504e470a1a0a0000000d4948445200"]

    lenmagic = len(magic)
    pos = DATAX.find(magic)
    if pos != -1:
        ChunkStory("add", "PNG", pos, pos + lenmagic, int(pos / 2))
        print(
            "-%s is Magic : %s\n"
            % (
                Candy("Color", "white", Sample_Name),
                Candy("Color", "green", DATAX[:lenmagic]),
            )
        )
        print(
            "-Found Png Signature at offset (%s/%s/%s): (%s/%s/%s)\n"
            % (
                Candy("Color", "yellow", "Hex"),
                Candy("Color", "blue", "Bytes"),
                Candy("Color", "purple", "Index"),
                Candy("Color", "yellow", hex(int(pos / 2))),
                Candy("Color", "blue", int(pos / 2)),
                Candy("Color", "purple", pos),
            )
        )
        if DATAX.startswith(magic) is False:
            print("-File does not start with a png signature.")
            Candy("Cowsay", " Mkay ...Things just keeps better and better ..", "bad")
            print(
                "-Cutting %s bytes from %s since png header starts at offset %s ."
                % (
                    Candy("Color", "white", Sample_Name),
                    Candy("Color", "blue", int(pos / 2)),
                    Candy("Color", "white", Sample_Name),
                    Candy("Color", "blue", hex(int(pos / 2))),
                )
            )
            Zankentsu = DATAX[pos::]
            return CheckPoint(
                False,
                False,
                "FindMagic",
                "PngSig",
                ["Cutting at Magic"],
                Zankentsu,
                hex(int(pos / 2)),
            )

        else:
            return CheckPoint(
                False, False, "FindMagic", "PngSig", ["-Found Magic"], pos + lenmagic
            )

    else:
        print(
            "-File %s start with valid png signature .%s\n"
            % (Candy("Color", "red", "does not"), Candy("Emoj", "bad"))
        )
        Candy("Cowsay", " This better be a real png or else ....", "bad")
        for badnews in magc:
            pos = DATAX.find(badnews)
            if pos != -1:
                if badnews == magc[1]:
                    print(
                        "-Some bytes are %s from Png Signature.."
                        % Candy("Color", "red", "missing")
                    )
                    Candy(
                        "Cowsay",
                        " %s seems corrupted due to line feed conversion...It doesnt look that bad...But I ll keep that in mind while im on it.."
                        % (Candy("Color", "white", Sample_Name, "bad")),
                    )
                    SideNotes.append(
                        "-Corruption due to line feed conversion\n-File may still be recovered.\n-Not yet implemented."
                    )
                    # FullChunkForcerWithCrc()
                    TheEnd()

                if badnews == magc[0]:
                    Candy(
                        "Cowsay",
                        " Hang on a sec....This is bad news i m afraid..",
                        "com",
                    )
                    Candy(
                        "Cowsay",
                        " %s is badly corrupted ...I cannot guarantee any results and it may take forever to find a solution..."
                        % Sample_Name,
                        "com",
                    )
                    print(Candy("Color", "yellow", "\n-ToDo"))
                    SideNotes.append(
                        "-Major Corruption due to line feed conversion\n-File may not be recovered.\n-Not yet implemented."
                    )
                    TheEnd()

        Candy("Cowsay", " Ok let's dig a little bit deeper..", "bad")
        return CheckPoint(
            False, False, "FindMagic", "PngSig", ["-dig a little bit deeper"]
        )


def FindFuckingMagic():
    global SideNotes

    Candy("Title", "Looking harder for magic header:")
    Candy("Cowsay", " This may take me sometimes please wait ..", "com")
    Magic = "89504e470d0a1a0a"
    FullMagic = "89504e470d0a1a0a0000000d49484452"
    m_a_g_i_c = [i for i in FullMagic]
    start = 0
    end = len(FullMagic)
    BingoList = []
    while end <= len(DATAX):
        Minibar()
        Bingo = 0
        sample = DATAX[start:end]
        s_a_m_p_l_e = [i for i in sample]
        for i, j in zip(m_a_g_i_c, s_a_m_p_l_e):
            if i == j:
                Bingo += 1
        BingoList.append(str(Bingo) + " " + str(sample))
        start += 1
        end += 1
    BingoList.sort(key=SplitDigits)
    BingoList = BingoList[::-1]
    BestBingoScore = BingoList[0].split(" ")[0]
    BestBingoSig = BingoList[0].split(" ")[1]
    BestBingoCount = len(
        [
            b.split(" ")[0].count(BestBingoScore)
            for b in BingoList
            if int(b.split(" ")[0].count(BestBingoScore)) > 0
        ]
    )

    if BestBingoCount <= 2 and int(BestBingoScore) >= 14:
        pos = DATAX.find(BestBingoSig)
        print("\n...\n")
        print("-Done! %s\n" % Candy("Emoj", "good"))
        print(
            "-Found at offset %s with a score of %s/32 :\n %s\n"
            % (
                Candy("Color", "blue", hex(int(pos / 2))),
                Candy("Color", "green", BestBingoScore),
                Candy("Color", "purple", BestBingoSig),
            )
        )
        Candy(
            "Cowsay",
            " I think this is a good start to work with.Lets see where that leads us...",
            "good",
        )

        Odin = FullMagic + DATAX[pos + len(FullMagic) : :]
        return CheckPoint(
            False,
            False,
            "FindFuckingMagic",
            "PngSig",
            ["-Cutting at Magic"],
            Odin,
            hex(int(pos / 2)),
        )

    elif int(BestBingoScore) >= 14:
        # print("count:",BestBingoCount)
        # print("score:",BestBingoScore)
        print("\n\n")
        print("\n\n...")
        [print(BingoList[i]) for i in range(0, 20)]
        print(
            "\n\n-Found multiple %s png signatures"
            % Candy("Color", "yellow", "potentials")
        )
        Candy("Cowsay", " Looks like i gonna have to test them all.", "bad")
        print(Candy("Color", "yellow", "\n-ToDo"))
        SideNotes.append(
            "-FindFuckingMagic:Found multiple potentials png signatures\n-Not Implemented yet"
        )
        Candy("Cowsay", "Erf this case is not implemented yet ...", "bad")
        TheEnd()
    else:
        print("\n\n")
        [print(BingoList[i]) for i in range(0, 20)]
        print("\n\n-Matching score :", Candy("Color", "red", "too low"))
        print("\n...\n-Done\n")
        Candy(
            "Cowsay",
            " Im afraid i wasn't able to find anything that looks like a png signature.",
            "com",
        )
        Candy(
            "Cowsay",
            "Maybe i could try to find if there any Known Chunks names in this file ?",
            "good",
        )

        SideNotes.append(
            "-FindFuckingMagic:Png signatures matching score are too low\nLooking for any known Chunks in file-"
        )

        ChunksFound = {}
        CheckIdat = False
        Needle = 0

        while Needle < len(DATAX):
            scopex = DATAX[Needle : Needle + 8]
            if len(scopex) < 8:
                break
            try:
                scope = bytes.fromhex(scopex).lower()
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                    print(
                        Candy("Color", "red", "Scopex:"),
                        Candy("Color", "yellow", scopex),
                    )
                    if PAUSEDEBUG is True or PAUSEERROR is True:
                        Pause("Pause Debug")

            NeedleI = int(Needle / 2)
            NeedleX = hex(int(Needle / 2))
            Data_End_OffsetI = NeedleI - 8

            for Chk in CHUNKS:
                if Chk.lower() == scope:
                    Candy("Cowsay", " Bingo!!!", "good")
                    print(
                        "-Found the closest Chunk to our position:%s at offset %s %s"
                        % (
                            Candy("Color", "green", Chk),
                            Candy("Color", "blue", NeedleX),
                            Candy("Color", "yellow", NeedleI),
                        )
                    )
                    ChunksFound[Chk] = Needle
                    if scope == b"idat":
                        Candy(
                            "Cowsay",
                            "No need to go any further i think i have enough data now...",
                            "com",
                        )
                        CheckIdat = True
                        Needle = len(DATAX)
                        break

            Needle += 1

        if len(ChunksFound) == 0:
            Candy(
                "Cowsay",
                " ...??Just Reach the EOF and found nothing!!",
                "bad",
            )
            Candy(
                "Cowsay",
                "Can't do much about that sorry ...",
                "com",
            )
            SideNotes.append(
                "-FindFuckingMagic:Haven't found any known png chunk in this file."
            )
            TheEnd()
        elif CheckIdat is False:
            Candy(
                "Cowsay",
                " ...??Havn't found any IDAT Chunk!!",
                "bad",
            )
            Candy(
                "Cowsay",
                "Can't do much about that sorry ...",
                "com",
            )
            SideNotes.append(
                "-FindFuckingMagic:Haven't found any IDAT chunk in this file."
            )
            TheEnd()

        else:

            for ck in ChunksFound:
                print("ChunksFound Chunk:%s index:%s" % (ck, ChunksFound[ck]))

            FirstCheck = len([bidat for bidat in ChunksFound if bidat in BEFORE_IDAT])

            if FirstCheck == 0:
                Candy(
                    "Cowsay",
                    "Great...This is the worst situation..Some chunks are missing..",
                    "bad",
                )
                Candy(
                    "Cowsay",
                    "Will need to take care of this later.",
                    "com",
                )

                Candy(
                    "Cowsay",
                    "I just hope there were no PLTE inside or Missing IDAT!",
                    "com",
                )
                Candy(
                    "Cowsay",
                    "Cause i will not be able to repair this file without many years of bruteforcing !!",
                    "bad",
                )

                SideNotes.append(
                    "-FindFuckingMagic:Chunks known to be found before IDAT are missing."
                )

            Candy(
                "Cowsay",
                "Kay .. Let me try somthing.",
                "com",
            )
            Candy(
                "Cowsay",
                "Im going to prepend the PNG Chuck before the nearest Chunk and we'll see from there !",
                "good",
            )
            try:
                NearestPos = sorted(ChunksFound.items(), key=lambda kv: kv[1])[0][1]
                NearestChk = sorted(ChunksFound.items(), key=lambda kv: kv[1])[0][0]

            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))

            if NearestPos - 8 > 0:
                Lenx = DATAX[NearestPos - 8 : NearestPos]
            else:
                Lenx = DATAX[:NearestPos]

            Specheck = SpecLenght(NearestChk, Lenx)

            if Specheck != Lenx and type(Specheck) != list:
                Lenx = Specheck
            elif type(Specheck) == list:
                print(Candy("Color", "yellow", "\n-ToDo"))
                pass  # brutefore
            try:
                NearestPosX = hex(int(NearestPos / 2))
            except ZeroDivisionError:
                NearestPosX = hex(int(0))

            Odin = Magic + Lenx + DATAX[NearestPos::]
            if DEBUG is True:
                print("New:")
                print(Odin[: NearestPos + 64])
                print("Old:")
                print(DATAX[: NearestPos + 64])

            return CheckPoint(
                False,
                False,
                "FindFuckingMagic",
                "PngSig",
                ["-Prepending Magic"],
                Odin,
                NearestPosX,
            )


def Ancillary(Chunk):
    global Bad_Ancillary
    Candy("Title", "Ancillary Check:", Candy("Color", "white", Chunk))
    Charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    Semantics = []
    try:
        Chunk = Chunk.decode(errors="ignore")
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])

    for i in Chunk:
        if i in Charset:
            if i == i.upper():
                Semantics.append(i)
            elif i == i.lower():
                Semantics.append(i)
        else:
            break

    if len(Semantics) != 4:
        print(
            "-[%s] is %s Chunks's naming conventions"
            % (Chunk, Candy("Color", "red", "Not Following"))
        )
        Candy(
            "Cowsay",
            "Meaning that could be an unknown private chunk that got corrupt .....Or a Known chunk that got corrupt ...",
            "com",
        )
        Candy("Cowsay", "..Or Not even a chunk's name at all ...", "bad")
        Bad_Ancillary = False

    elif len(Semantics) == 4:
        print(
            "-[%s] %s Chunks's naming conventions"
            % (Chunk, Candy("Color", "green", "Seems to be Following"))
        )
        Candy(
            "Cowsay", "If this is a real Chunk this means that %s is :" % Chunk, "good"
        )
        if Semantics[0] == Semantics[0].upper():
            print(
                "-"
                + Candy("Color", "green", Semantics[0])
                + ":"
                + Candy("Color", "yellow", "Critical")
            )
        else:
            print(
                "-"
                + Candy("Color", "green", Semantics[0])
                + ":"
                + Candy("Color", "yellow", "Not Critical")
            )
        if Semantics[1] == Semantics[1].upper():
            print(
                "-"
                + Candy("Color", "green", Semantics[1])
                + ":"
                + Candy("Color", "yellow", "Private")
            )
        else:
            print(
                "-"
                + Candy("Color", "green", Semantics[1])
                + ":"
                + Candy("Color", "yellow", "Not Private")
            )
        if Semantics[2] == Semantics[2].upper():
            print(
                "-"
                + Candy("Color", "green", Semantics[2])
                + ":"
                + Candy("Color", "yellow", "Conform to PNG specifications")
            )
        else:
            print(
                "-"
                + Candy("Color", "green", Semantics[2])
                + ":"
                + Candy("Color", "yellow", "Not Conform to PNG specifications")
            )
        if Semantics[3] == Semantics[3].upper():
            print(
                "-"
                + Candy("Color", "green", Semantics[3])
                + ":"
                + Candy("Color", "yellow", "Unsafe to Copy")
            )
        else:
            print(
                "-"
                + Candy("Color", "green", Semantics[3])
                + ":"
                + Candy("Color", "yellow", "Safe to Copy")
            )
        Bad_Ancillary = True


def NullFind(data, search4=None):
    null_pos = ""
    if search4 == None:
        search4 = "00"
    for i in range(0, len(data), len(search4)):
        if data[i : i + len(search4)] == search4:
            null_pos = i
            break
    if len(str(null_pos)) > 0:
        return null_pos
    else:
        return False


def LibpngCheck(file):
    Candy("Title", "Libpng Returned :%s" % (Candy("Color", "white", Sample_Name)))
    f = io.BytesIO()
    with stderr_redirector(f):
        cv2.imread(file)
    result = "{0}".format(f.getvalue().decode("utf-8"))
    if len(result) > 0:

        print(
            "-Libpng Check: %s %s"
            % (Candy("Color", "red", "FAILED!"), Candy("Emoj", "bad"))
        )



        return CheckPoint(True, False, "LibpngCheck", file, ["-" + result])
    else:
        print(
            "-Libpng Check: %s %s"
            % (Candy("Color", "green", "Ok!"), Candy("Emoj", "good"))
        )

        Candy(
            "Cowsay",
            "Good ! The AllMighty Libpng is happy !",
            "good",
        )
        return CheckPoint(
            False, False, "LibpngCheck", file, ["-Libpng has not found any error"]
        )


def Double_Check(CType, ChunkLen, LastCType):

    Candy("Title", "Double Check:")

    print(
        "Or maybe am i missing something ?\nJust let me double check again just to be sure..."
    )

    if len(DATAX) / 2 < 67:
        print(
            "-Wrong File Length.\n\n...\n\nERrr...\nThere are not enough bytes in %s to be a valid png.\n%s is %s bytes long and the very minimum size for a png is 67 bytes so...\ni can't help you much further sorry.\n"
            % (
                Candy("Color", "white", Sample_Name),
                Candy("Color", "white", Sample_Name),
                Candy("Color", "red", int(len(DATAX) / 2)),
            )
        )
        TheEnd()

    Candy(
        "Cowsay",
        " But this time let's forget about the usual specifications of png format so This way i will be able to know if a chunk is missing somewhere.",
        "good",
    )

    NearbyChunk(CType, ChunkLen, LastCType, DoubleCheck=True)


def DummyChunk(Chunkname, bad_pos, bad_start, bad_end,FromError):
    Candy("Title", "Creating DummyChunk:")

#    for c, i in zip(Chunks_History, Chunks_History_Index):
#        print("chunk:%s index:%s" % (c, i))

    Candy(
        "Cowsay",
        "Mkay i will need to get some infos on the file before..",
        "com",
    )
    ##TODO
    if Chunkname == b"IHDR":

       DummyLength = SpecLenght(Chunkname)
       DummyName = hex(int.from_bytes(Chunkname, byteorder="big")).replace("0x","")
       DummyData = "00000010000000100803000000"
       DummyCrc = hex(binascii.crc32(Chunkname + bytes.fromhex(DummyData))).replace("0x","")
       DumDum = DummyLength + DummyName + DummyData + DummyCrc


       if DEBUG is True:

            print("bad pos:", bad_pos)
            print("bad_start:", bad_start)
            print("bad_end:", bad_end)
            print("datax:", DATAX[bad_start:bad_end])
            print("dumylen:",DummyLength)
            print("dumyname:",DummyName)
            print("dumydata:",DummyData)
            print("dumycrc;",DummyCrc)
            print("dumdum:",DumDum)
            if PAUSEDEBUG is True :
                    Pause("Pause Debug")

       DummyFix = DATAX[:bad_start] + DumDum + DATAX[bad_start:]


       Candy(
        "Cowsay",
        "Fake datas ready to be served! Bonne appetit !",
        "good",
        )

       return CheckPoint(
                        True,
                        False,
                        "DummyChunk",
                        Chunkname,
                        ["Filling with a dummy chunk"],
                        DummyFix,
                        len(DummyData),
                        bad_pos,
                        bad_start,
                        bad_end,
                        FromError,
                    )


    print(Candy("Color", "yellow", "\n-ToDo"))
    TheEnd()


def NearbyChunk(CType, ChunkLen, LastCType, DoubleCheck, FromError=None):
    Candy("Title", "Chunk N Destroy:")
    Candy("Cowsay", "Now where shall i start..?", "com")
    if DoubleCheck is False:
        Excluded = CheckChunkOrder(LastCType, "Fix")
    else:
        Candy("Cowsay", " ==Safety Off==", "com")
        Excluded = []

    Needle = CLoffI + 16

    while Needle < len(DATAX):

        scopex = DATAX[Needle : Needle + 8]
        try:
            scope = bytes.fromhex(scopex).lower()
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
                print(
                    Candy("Color", "red", "Scopex:"), Candy("Color", "yellow", scopex)
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            TheEnd()
        NeedleI = int(Needle / 2)
        NeedleX = hex(int(Needle / 2))
        Data_End_OffsetI = NeedleI - 8

        for Chk in CHUNKS:
            if Chk.lower() == scope:
                Candy("Cowsay", " Bingo!!!", "good")
                print(
                    "-Found the closest Chunk to our position:%s at offset %s %s"
                    % (
                        Candy("Color", "green", Chk),
                        Candy("Color", "blue", NeedleX),
                        Candy("Color", "yellow", NeedleI),
                    )
                )
                if Chk in Excluded:
                    print(
                        "\n-Chunk position is %s %s\n"
                        % (Candy("Color", "red", "Not Valid "), Candy("Emoj", "bad"))
                    )
                    Candy(
                        "Cowsay",
                        " But that chunk [%s] is not supposed to be here .."
                        % Candy("Color", "red", Chk),
                        "com",
                    )
                    Candy("Cowsay", " ITS A TRAP !! RUN !!!!!!!", "bad")
                    Candy(
                        "Cowsay",
                        " I seriously doubt that i could be of any uses with this one ..",
                        "com",
                    )
                    Candy(
                        "Cowsay",
                        " If you are sure %s is a png i can try to fill the gap but i cannot guarantee any result.."
                        % Candy("Color", "white", Sample_Name),
                        "com",
                    )
                    if b"IHDR" not in Chunks_History:
                        Candy("Cowsay", " Especially without IHDR chunk..", "bad")
                    print(Candy("Color", "yellow", "\n-ToDo"))
                    SideNotes.append("-NearbyChunk:Missplaced Chunk")
                    TheEnd()
                else:
                    LenCalc = Data_End_OffsetI - CDoffB
                    if "-" in str(LenCalc):
                        print(
                            "-Chunk position is %s %s\n"
                            % (
                                Candy("Color", "red", "Not Valid "),
                                Candy("Emoj", "bad"),
                            )
                        )
                        print(
                            "-Got Wrong Result for length...:",
                            Candy("Color", "red", LenCalc),
                        )
                        Candy("Cowsay", " Another one byte the dust ...", "bad")
                        print("dataendofI:", Data_End_OffsetI)
                        print("CDoffb:", CDoffB)
                        print(Candy("Color", "yellow", "\n-ToDo"))
                        TheEnd()
                    print(
                        "-Chunk position is %s %s\n"
                        % (Candy("Color", "green", "Valid "), Candy("Emoj", "good"))
                    )
                    FixedLen = str("0x%08X" % LenCalc)[2::]

                    SolvedMsg = (
                        "-Found Chunk[%s] has Wrong length at offset: %s\n-Found next chunk: %s at: %s\n-Replaced with: %s old value was: %s"
                        % (Orig_CT, CLoffX, Chk, NeedleX, FixedLen, Orig_CL)
                    )

                    return CheckPoint(
                        True,
                        True,
                        "NearbyChunk",
                        Orig_CT,
                        [SolvedMsg],
                        FixedLen,
                        CLoffI,
                        CLoffI + 8,
                        Orig_CT,
                        #                           SolvedMsg,
                        FromError,
                    )

                    return ()
        Needle += 1
    if DoubleCheck is True:
        Candy("Cowsay", " ...??NOTHING AGAIN!?!?!?!?", "bad")
        Candy("Cowsay", " THEY PLAYED US LIKE A DAMN FIDDLE !!!", "bad")
        Candy("Cowsay", " AMa Outta Here !Do It YourSelf FFS!!", "bad")
        TheEnd()
    else:
        Candy(
            "Cowsay",
            " ...??Just Reach the EOF and found nothing!!Can't do much about that sorry ...",
            "com",
        )

    if ChunkLen != None and CType != None:
        Double_Check(CType, ChunkLen, LastCType)

    return ()


def TheGoodPlace(Missplaced_Chunkname, Missplaced_Chunkpos, ToFix_Chunkname):
    Candy("Title", "TheGoodPlace :")
    Candy("Cowsay", "Mkay, so what do we have here ..", "com")

    bad_pos = int(
        Chunks_History_Index[Missplaced_Chunkpos].split(":")[0].replace(" ", "")
    )
    bad_start = int(
        Chunks_History_Index[Missplaced_Chunkpos].split(":")[1].replace(" ", "")
    )
    bad_end = int(
        Chunks_History_Index[Missplaced_Chunkpos].split(":")[2].replace(" ", "")
    )
    start, end, pos = None, None, None

    for nb, key in enumerate(PandoraBox):
        if "Missplaced" in str(key):
            print("\n-\033[1;31;49mCriticalHit\033[m: ", key)

    for chnk, index in zip(Chunks_History, Chunks_History_Index):
        if ToFix_Chunkname == chnk:
            pos = int(index.split(":")[0].replace(" ", ""))
            start = int(index.split(":")[1].replace(" ", ""))
            end = int(index.split(":")[2].replace(" ", ""))
            break  # Temp Break

    if start == None and end == None:

        print(
            "-Missing Data %s %s"
            % (Candy("Color", "red", "Has Not Been Found"), Candy("Emoj", "bad"))
        )
        Candy("Cowsay", "This is not good..", "bad")
        return CheckPoint(
            True,
            False,
            "TheGoodPlace",
            ToFix_Chunkname,
            ["-Missing Data Has Not Been Found : [%s]"%ToFix_Chunkname],
            ToFix_Chunkname,
            bad_pos,
            bad_start,
            bad_end,
        )

    else:
        print(
            "\n-Found %s:[%s] at Chunk Position:%s Starting at:%s Ending at:%s %s"
            % (
                Candy("Color", "green", "Missing Data"),
                ToFix_Chunkname,
                pos,
                start,
                end,
                Candy("Emoj", "good"),
            )
        )
        Candy("Cowsay", "Sounds good to me , where's my rubber tape already ?", "good")
        Rubber = DATAX[start:end]
        Tape = DATAX[:start] + DATAX[end:]
        Rubber_Tape = Tape[:bad_start] + Rubber + Tape[bad_start:]
        return CheckPoint(
            True,
            True,
            "TheGoodPlace",
            ToFix_Chunkname,
            [
                "-Found Missing Data:[%s] at Chunk Position:%s Starting at:%s Ending at:%s"
                % (ToFix_Chunkname, pos, start, end)
            ],
            Rubber_Tape,
        )

    print()
    if DEBUG is True:
        print("Missplaced_Chunkname:", Chunks_History[Missplaced_Chunkpos])
        print(
            "Chunks_History_Index[Missplaced_Chunkpos]:",
            Chunks_History_Index[Missplaced_Chunkpos],
        )
        print("ToFix_Chunkname:", ToFix_Chunkname)
        print("Chunk_History and Infos :")
        for a, b in zip(Chunks_History, Chunks_History_Index):
            print("Chunk:", a)
            print("Index Infos", b)
        #        print(Rubber in DATAX)
        #        print(Rubber in Tape)
        #        print(DATAX[:start])
        #        print()
        #        print(Rubber)
        #        print()
        #        print(DATAX[end:])
        #        sys.exit()
        if PAUSEDEBUG is True:
            Pause("Pause Debug")

    TheEnd()


def CheckChunkOrder(lastchunk, mode):
    global Warning
    global SideNotes

    ToFix = []

    try:
        lastchunk = lastchunk.encode(errors="ignore")
    except AttributeError as e:
        Betterror(e, inspect.stack()[0][3])
        #      print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

    if mode == "Critical":

        Candy("Title", "Critical Chunks Check :")
        for chnk in MINIMAL_CHUNKS:
            if chnk not in Chunks_History:
                print(
                    "-Critical Chunk %s is %s !"
                    % (chnk, Candy("Color", "red", "Missing"))
                )
                ToFix.append("-Critical Chunk %s is Missing" % chnk)
        if len(ToFix) > 0:
            CheckPoint(True, False, "CheckChunkOrder", "Critical", ToFix)
            # TheEnd()
        else:
            print(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )
        return

    if mode == "TheGoodPlace":
        Candy("Title", "Missplaced Chunks Check:")

        Done = False
        Used_Chunks = list(dict.fromkeys(Chunks_History))
        Excluded = [used for used in Used_Chunks if used in UNIQUE_CHUNK]
#        print(Excluded)
        Candy(
            "Cowsay",
            " So far we came across those chunks in "
            + Sample_Name
            + "\n "
            + str([i.decode(errors="ignore") for i in Used_Chunks]),
            "good",
        )

        if lastchunk in UNIQUE_CHUNK:
            if lastchunk in Excluded:
                print(
                    "-%s chunk %s be used multiple times."
                    % (
                        Candy("Color", "red", lastchunk.decode(errors="ignore")),
                        Candy("Color", "red", "cannot"),
                    )
                )
                ToFix.append("-Multiple")

        if len(Chunks_History) > 0:
            if Chunks_History[0] != b"PNG":
                print(
                    "-PNG signature have to be placed %s all the other chunks. %s"
                    % (Candy("Color", "red", "Before"), Candy("Emoj", "bad"))
                )
                ToFix.append("-Missplaced")
        if len(Chunks_History) > 1:
            if Chunks_History[1] != b"IHDR":
                for nb, key in enumerate(PandoraBox):
                    if "Should be IHDR Instead At Chunk Number:" in str(key):
                        Done = True
                        break

                if Done is False:
                    print(
                        "-IHDR Chunk have to be placed %s and after Png Signature. %s"
                        % (
                            Candy("Color", "red", "Before all the other chunks"),
                            Candy("Emoj", "bad"),
                        )
                    )

                    return CheckPoint(
                        True,
                        False,
                        "CheckChunkOrder",
                        Chunks_History[-1],
                        [
                            "-Missplaced [%s] Should be IHDR Instead At Chunk Number:%s"
                            % (Chunks_History[-1], str(len(Chunks_History) - 1))
                        ],
                        Chunks_History[-1],
                        len(Chunks_History) - 1,
                        b"IHDR",
                    )

                elif DEBUG is True:
                    print(
                        "-Already Saved : Missplaced [%s]:Should be IHDR Instead At Chunk Number:%s"
                        % (Chunks_History[-1], str(len(Chunks_History) - 1))
                    )
                    if PAUSEDEBUG is True:
                        Pause("Pause Debug")

        if b"PLTE" in Used_Chunks:
            if lastchunk in BEFORE_PLTE:
                shutup = [
                    Excluded.append(forbid)
                    for forbid in CHUNKS
                    if forbid in BEFORE_PLTE
                ]
                if lastchunk in Excluded:
                    print(
                        "-%s  %s must appears before PLTE Chunk. %s"
                        % (
                            Candy(
                                "Color",
                                "red",
                                lastchunk.decode(errors="ignore") + " is missplaced",
                            ),
                            lastchunk.decode(errors="ignore"),
                            Candy("Emoj", "bad"),
                        )
                    )
                    # print(Excluded)
                    ToFix.append(
                        "-"
                        + lastchunk.decode(errors="ignore")
                        + " is missplaced must appears before PLTE Chunk"
                    )

        if b"IDAT" not in Used_Chunks:
            pass

        if b"IDAT" in Used_Chunks:
            shutup = [
                Excluded.append(forbid) for forbid in CHUNKS if forbid in BEFORE_IDAT2
            ]
            if lastchunk in Excluded:
                print(
                    "-%s  %s must be before IDAT Chunk. %s"
                    % (
                        Candy(
                            "Color",
                            "red",
                            lastchunk.decode(errors="ignore") + " is missplaced",
                        ),
                        lastchunk.decode(errors="ignore"),
                        Candy("Emoj", "bad"),
                    )
                )
                # print(Excluded)
                ToFix.append("-Missplaced")

        if len(ToFix) > 0:
            CheckPoint(True, False, "CheckChunkOrder", "Missplaced", ToFix)
            print(
                "\n-Missplaced Chunk Check :"
                + Candy("Color", "red", " FAILED ")
                + Candy("Emoj", "bad")
            )
        else:
            print(
                "\n-Missplaced Chunk Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )
        return

    if mode == "Fix":

        Candy("Title", "Checking Already Used Chunks :")
        if Chunks_History[0] == b"PNG" and len(Chunks_History) == 1:

            Candy(
                "Cowsay",
                " After Png Header always Follow IHDR this is quite hard to miss..Excluding evrything else",
                "com",
            )
            Excluded = [exclude for exclude in CHUNKS if exclude != b"IHDR"]
            return Excluded

        Used_Chunks = list(dict.fromkeys(Chunks_History))
        Excluded = [used for used in Used_Chunks if used in UNIQUE_CHUNK]
        Candy(
            "Cowsay",
            " So far we came across those chunks in "
            + Sample_Name
            + str([i.decode(errors="ignore") for i in Used_Chunks]),
            "good",
        )

        if b"IDAT" not in Used_Chunks:

            if lastchunk in BEFORE_PLTE and b"IHDR" not in Used_Chunks:
                shutup = [
                    Excluded.append(forbid)
                    for forbid in CHUNKS
                    if forbid not in BEFORE_PLTE
                ]
                Candy(
                    "Cowsay",
                    " %s chunk must be placed before any PLTE related chunks we can forget about thoses:\n%s"
                    % (
                        Candy("Color", "green", lastchunk.decode(errors="ignore")),
                        [i.decode(errors="ignore") for i in Excluded],
                    ),
                    "bad",
                )

            if lastchunk in AFTER_PLTE:
                shutup = [
                    Excluded.append(forbid)
                    for forbid in CHUNKS
                    if forbid in BEFORE_PLTE
                ]
                Candy(
                    "Cowsay",
                    " %s chunk must be placed after PLTE related chunks we can forget about thoses:\n%s"
                    % (lastchunk, [i.decode(errors="ignore") for i in Excluded]),
                    "bad",
                )

            Excluded.append(b"IEND")

        elif b"IDAT" in Used_Chunks:
            shutup = [
                Excluded.append(forbid) for forbid in CHUNKS if forbid in BEFORE_IDAT
            ]

            if int(IHDR_Color) == 3:
                shutup = [
                    Excluded.append(forbid)
                    for forbid in CHUNKS
                    if forbid not in BEFORE_PLTE
                ]
                Candy(
                    "Cowsay",
                    " AH ! I knew this day would come ...You See when Image Header color type is set to 3 (Indexed Colors)..PLTE chunk must be placed before any IDAT chunks so that only means one thing ..More code to write for me.",
                    "com",
                )
                print(Candy("Color", "yellow", "\n-ToDo"))
                TheEnd()

            elif (
                (int(IHDR_Color) == 2)
                or (int(IHDR_Color) == 6)
                and (
                    "PLTE".encode() not in Chunks_History
                    and "sPLT".encode not in Chunks_History
                )
            ):
                if Warning is False:
                    Warning = True
                    ToFix.append(
                        "-There is a chance that some Critical Palette chunks are missing."
                    )
                    Candy(
                        "Cowsay",
                        " There is a chance that some %s chunks are %s."
                        % (
                            Candy("Color", "red", "Critical Palette"),
                            Candy("Color", "red", "Missing"),
                        ),
                        "com",
                    )
            if lastchunk == b"IDAT":
                Candy(
                    "Cowsay",
                    " So ..the last Chunk Type was IDAT so we either looking for another IDAT,IEND or one of them:%s"
                    % [i.decode(errors="ignore") for i in NO_ORDER_CHUNKS],
                    "com",
                )

        return Excluded


def BruteChunk(CType, LastCType, ChunkLen, FromError):
    Candy("Title", "Chunk Scrabble Solver:")
    ErrorA = False
    BingoLst = []
    ToFix = []
    if DEBUG is True:
        print(CType)
        print(LastCType)
        print(ChunkLen)
        print(FromError)
        if PAUSEDEBUG is True:
            Pause("Pause:Debug")

    if type(CType) == bytes:
        CTypeLst = [i.lower() for i in CType.decode(errors="ignore")]
    else:
        CTypeLst = [i.lower() for i in CType]

    Candy(
        "Cowsay", " Maybe it's name got corrupted somehow. Let's see about that.", "com"
    )

    Excluded = CheckChunkOrder(LastCType, "Fix")
    for name in CHUNKS:
        if name not in Excluded:
            Bingo = 0
            ChkLst = [i.lower() for i in name.decode(errors="ignore")]

            for i, j in zip(CTypeLst, ChkLst):
                if i == j:
                    Bingo += 1
            BingoLst.append(str(Bingo) + " " + name.decode(errors="ignore"))

    # [print(i) for i in BingoLst]

    BingoLst.sort(key=SplitDigits)
    BingoLst = BingoLst[::-1]

    BestBingoScore = BingoLst[0].split(" ")[0]
    BestBingoName = BingoLst[0].split(" ")[1]

    BestBingoCount = len(
        [b.count(BestBingoScore) for b in BingoLst if int(b.count(BestBingoScore)) > 0]
    )

    if BestBingoCount <= 2 and int(BestBingoScore) >= 2:

        print(
            "-"
            + str(Candy("Color", "green", "Scrabble Solved."))
            + str(Candy("Emoj", "good"))
        )
        Candy(
            "Cowsay",
            " Ah looks like we've got a winner! :%s"
            % Candy("Color", "green", BestBingoName),
            "good",
        )

        Bchanged = str(len(CType) - int(BestBingoScore))
        SolvedMsg = (
            "-Found Chunk[%s] has wrong name at offset: %s but BruteChunk changed %s bytes turning it into a valid Chunk name: %s"
            % (Orig_CT, CToffX, Bchanged, BestBingoName)
        )

        return CheckPoint(
            True,
            True,
            "CheckChunkName",
            Orig_CT,
            [SolvedMsg],
            BestBingoName.encode().hex(),
            CToffI,
            CToffI + 8,
            Orig_CT,
            SolvedMsg,
            FromError,
        )
    else:

        Candy("Title", "WHO'S THAT POKEMON !?:")
        Candy("Cowsay", " Arg that's all gibberish ...", "com")
        print(
            "\nI need you to choose something looking a like [%s] that is actually a real chunk name can you help ?\nOk Please select the right name for the chunk:\n"
            % Candy("Color", "purple", str(CType))
        )

        for i, j in enumerate(BingoLst):
            print(
                "Score %s ,if you choose this name enter number: %s"
                % (Candy("Color", "green", j), Candy("Color", "yellow", i))
            )

        print(
            "\nIf you feel as lost as me then this might be a Length Problem type : wtf"
        )
        print("\nOr Type quit to ...quit.\n")
        Choice = input("WHO'S THAT POKEMON !? :")
        while True:
            try:
                if (Choice.lower() != "quit" or Choice.lower() != "wtf") and int(
                    Choice
                ) <= len(BingoLst):
                    if int(Choice) in range(0, len(BingoLst)):
                        answer = BingoLst[int(Choice)].split(" ")[1]
                        SaveClone(
                            answer.encode().hex(),
                            CrcoffI + 16,
                            CrcoffI + 24,
                            "-Found Chunk[%s] has wrong name at offset: %s\n-Chunk seems corrupted user has decided to choose Chunk[%s] as a replacement."
                            % (Orig_CT, CToffX, BingoLst[int(Choice)].encode()),
                        )
                        return ()
            except Exception as e:
                Betterror(e, inspect.stack()[0][3])
                if DEBUG is True:
                    print("Error WHO'S THAT POKEMON : ", e)
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
                pass

            if Choice.lower() == "quit":
                Candy("Cowsay", " Take Care Bye !", "good")
                TheEnd()
            if Choice.lower() == "wtf":
                Candy("Cowsay", " Fine , time to investigate that length..", "com")
                NearbyChunk(CType, ChunkLen, LastCType, False)
                return ()
            Choice = input("WHO'S THAT POKEMON !? :")


def CheckChunkName(ChunkType, ChunkLen, LastCType, Next=None):

    if type(ChunkType) == bytes:
        CType = ChunkType
    elif type(ChunkType) != bytes:
        try:
            CType = bytes.fromhex(ChunkType)
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            CType = ChunkType.encode(errors="ignore")

    if Next != None:
        Candy("Title", "Checking Next Chunk Type:", Candy("Color", "white", CType))
    else:
        Candy("Title", "Checking Current Chunk Type:", Candy("Color", "white", CType))

    for name in ALLCHUNKS:
        if name.lower() == CType.lower():
            if name == CType:
                print(
                    "\n-Chunk name:"
                    + Candy("Color", "green", " OK! ")
                    + Candy("Emoj", "good")
                )
                if Next == None:
                    return CheckPoint(
                        False,
                        False,
                        "CheckChunkName",
                        CType,
                        [
                            "-Name is valid for Chunk[%s]." % CType,
                        ],
                        Next,
                    )
                else:

                    return CheckPoint(
                        False,
                        False,
                        "CheckChunkName",
                        CType,
                        [
                            "-Name is valid for next Chunk[%s]." % CType,
                        ],
                        Next,
                    )

            else:
                print(
                    "\n-Chunk name:"
                    + Candy("Color", "red", " FAILED! ")
                    + Candy("Emoj", "bad")
                )
                print("\nMonkey wanted Banana :", Candy("Color", "green", name))
                print("Monkey got Pullover :", Candy("Color", "red", CType))
                print()
                if Next == None:
                    return CheckPoint(
                        True,
                        False,
                        "CheckChunkName",
                        CType,
                        [
                            "-Found Chunk[%s] Wrong Ancillary in known Chunk name at offset: %s"
                            % (Orig_CT, CToffX)
                        ],
                        CToffX,
                        CToffI,
                        CToffI + 8,
                        Orig_CT,
                        name,
                        Next,
                    )
                else:

                    return CheckPoint(
                        True,
                        False,
                        "CheckChunkName",
                        CType,
                        [
                            "-Found Next Chunk[%s] Wrong Ancillary in known Chunk name at offset: %s"
                            % (Orig_CT, CToffX)
                        ],
                        CToffX,
                        CToffI,
                        CToffI + 8,
                        Orig_CT,
                        name,
                        Next,
                    )

    print("\n-Chunk name:" + Candy("Color", "red", " FAILED! ") + Candy("Emoj", "bad"))
    if Next == None:
        Candy(
            "Cowsay",
            "Mokay That could explain all this mess...",
            "com",
        )
        if (
            (Chunks_History[-1] == b"IDAT")
            and (IDAT_Avg_Len != int(ChunkLen, 16))
            and Orig_NC != b"IEND"
        ):
            return CheckPoint(
                True,
                False,
                "CheckChunkName",
                CType,
                [
                    "-Found Chunk[%s] has Wrong Chunk name at offset: %s and length is not the same than before."
                    % (CType, CToffX)
                ],
                CType,
                ChunkLen,
                CToffI,
                LastCType,
                Next,
            )
        else:
            return CheckPoint(
                True,
                False,
                "CheckChunkName",
                CType,
                [
                    "-Found Chunk[%s] has Wrong Chunk name at offset: %s"
                    % (CType, CToffX)
                ],
                CType,
                ChunkLen,
                CToffI,
                LastCType,
                Next,
            )
    else:

        Candy(
            "Cowsay",
            "But let's ignore it for now we will see about that later ...",
            "com",
        )

        return CheckPoint(
            True,
            False,
            "CheckChunkName",
            CType,
            [
                "-Found Next Chunk[%s] has Wrong Chunk name after Chunk[%s] "
                % (Orig_NC, LastCType)
            ],
            Orig_NC,
            ChunkLen,
            NCoffI,
            LastCType,
            Next,
        )

def SpecLenght(chunk_name, chunk_length=None):
    global SideNotes

    if chunk_length:
       Candy("Title", "Get Lenght from Spec:")
       Candy("Cowsay", "Kay ..Just Checking if the length part is legit..", "com")

    stop = False

    KNOWN_CHUNKS_SPEC = GetSpec()
    for key in KNOWN_CHUNKS_SPEC:
        if stop is True:
            break
        for color_type, bytes_spec in KNOWN_CHUNKS_SPEC[key].items():
            if key == chunk_name:

                if "nocolortype" in color_type:

                    chunklen_spec = int(bytes_spec[0]/2)
                    chunk_format = bytes_spec[1],bytes_spec[2]

                    if type(chunklen_spec) == tuple:

                        print(Candy("Color", "yellow", "\n-ToDo"))
                        stop = True
                        break
                    else:
                        real_length = hex(int(chunklen_spec)).replace("0x", "").zfill(8)

                        if not chunk_length:
                            return(real_length)

                        print("-Real %s Length: %s " % (key, real_length))
                        if real_length == chunk_length:
                            Candy(
                                "Cowsay",
                                "Looks good to me !",
                                "good",
                            )
                            SideNotes.append(
                                "-SpecLenght:Giving correct length:  %s -" % chunk_length
                            )
                            return chunk_length
                        else:
                            print("-Given %s Length was : %s " % (chunk_name, chunk_length))
                            Candy(
                                "Cowsay",
                                "length part is corrupted!",
                                "bad",
                            )
                            SideNotes.append(
                                "-SpecLenght:Giving correct length:  %s -" % real_length
                            )
                            print("\n-Returning correct fixed length :", real_length)
                            return real_length

                if "colortype" in color_type:

                    print(Candy("Color", "yellow", "\n-ToDo"))
                    stop = True
                    break
            # print("Chunk:",key)
            # print("name:%s value:%s"%(name,value))
            # print("min:%s, max:%s"%(value[0],value[1]))


def CheckLength(Cdata, Clen, Ctype):

    Candy("Title", "Checking Data Length:", Candy("Color", "white", str(Clen)))

    Candy(
        "Cowsay",
        " So ..The length part is saying that data is %s bytes long."
        % Candy("Color", "yellow", int(Clen, 16)),
        "com",
    )

    #    ToBitstory(int(Clen, 16))

    if int(Clen, 16) > 26736:
        Candy("Cowsay", " Really!? That much ?", "com")

    if Chunks_History[-1] == b"IDAT":
        if IDAT_Avg_Len != int(Clen, 16):
            Candy(
                "Cowsay", "Weird why does the length is not the same as before ?", "com"
            )

    if len(Orig_NC) != 4:
        Candy(
            "Cowsay",
            " ..And this is what iv found there ... : "
            + Candy("Color", "red", "[NOTHING]"),
            "com",
        )
        return CheckPoint(
            True,
            False,
            "CheckLength",
            Ctype,
            ["-No NextChunk"],
            Ctype,
            Clen,
            Chunks_History[-1],
        )
    else:
        Candy(
            "Cowsay",
            " ..So depending on that the next chunk seems to be : "
            + Candy("Color", "yellow", Orig_NC),
            "com",
        )
        return CheckPoint(
            False, False, "CheckLength", Ctype, ["-Found NextChunk"], Clen
        )


def Question(id=None):
    global IFOP
    Candy("Title", "QUESTION!")

    if DEBUG is True:
        print("IFOP:\n", IFOP)
        print("\nId:", id)
        if PAUSEDEBUG is True:
            Pause("Pause Debug")

    if AUTO is False:

        Response = input("Answer(yes/no):").lower()
        while Response != "yes" and Response != "no":
            Response = input("Answer(yes/no):").lower()
        if Response == "yes":
            Candy("Cowsay", "Fine , let me see what i can do .", "good")
            Answer = True

        elif Response == "no":
            Candy("Cowsay", "Ok ,just do not make eye contact !", "com")
            Answer = False
    else:
        print("-%s\n" % Candy("Color", "green", "Auto Answer Mode"))
        Answer = True

    if id != None:
        Sondage = (
            "Infos:" + str(id) + " Answer:" + str(Answer) + " Offset:" + str(CLoffI)
        )
        if Sondage not in IFOP:
            IFOP.append(Sondage)
            return Answer
        else:
            print("-%s\n" % Candy("Color", "red", "Error Already fixed"))
            print("-%s\n" % Candy("Color", "red", "Answer Changed"))
            Candy("Cowsay", "Huh ..? Déja-vu ?", "com")
            if DEBUG is True:
                print("IFOP:\n")
                [print(i) for i in IFOP]
                print("\nId:", id)
                print("\nAnswer:", Answer)
            if PAUSEDEBUG is True:
                Pause("Question")

            Answer = not Answer
            Sondage = (
                "Infos:" + str(id) + " Answer:" + str(Answer) + " Offset:" + str(CLoffI)
            )
            if Sondage not in IFOP:
                IFOP.append(Sondage)
                return Answer
            else:
                print(
                    "-%s\n"
                    % Candy(
                        "Color",
                        "red",
                        "Loop Detected please contact github.com/on4r4p/Chunklate",
                    )
                )
            if DEBUG is True:
                print("IFOP:\n")
                [print(i) for i in IFOP]
                print("\nId:", id)
                print("\nAnswer:", Answer)
            if PAUSEDEBUG is True:
                Pause("Pause Question")
                TheEnd()
    # TheEnd()
    return Answer


def Checksum(Ctype, Cdata, Crc, next=None):
    Candy("Title", "Check Crc Validity:")
    Ctype = bytes.fromhex(Ctype)
    Cdata = bytes.fromhex(Cdata)
    Crc = hex(int.from_bytes(bytes.fromhex(Crc), byteorder="big"))
    checksum = hex(binascii.crc32(Ctype + Cdata))
    if checksum == Crc:
        print(
            "-Crc Check :"
            + Candy("Color", "green", " OK ")
            + Candy("Emoj", "good")
            + "\n"
        )
        if next == None:
            ChunkStory("add", Ctype, CLoffI, CrcoffI + 8, int(Orig_CL, 16))
        return CheckPoint(
            False,
            False,
            "Checksum",
            Ctype,
            ["-Crc is correct"],
        )
    else:
        print(
            "-Crc Check :" + Candy("Color", "red", " FAILED! ") + Candy("Emoj", "bad")
        )
        if len(Crc) == 0 or len(checksum) == 0:
            print("\nMonkey wanted Banana :", Candy("Color", "green", checksum))
            print("Monkey got Pullover :", Candy("Color", "red", Crc))
            Candy("Cowsay", " Hold on a sec ... Must have missed something...", "com")
            print()
            TheEnd()

        if len(checksum) < 10:
            checksum = "0x" + (checksum[2::].zfill(8))
        print("\nMonkey wanted Banana :", Candy("Color", "green", checksum))
        print("Monkey got Pullover :", Candy("Color", "red", Crc))

        return CheckPoint(
            True,
            False,
            "Checksum",
            Ctype,
            ["-Wrong Crc"],
            checksum[2::],
            CrcoffI,
            CrcoffI + 8,
            Orig_CT,
            CrcoffX,
            Orig_CRC,
            int(Orig_CL, 16),
            CDoffI,
        )


def SaveClone(DataFix, start, end, infos):
    global Show_Must_Go_On
    Show_Must_Go_On = True

    Candy("Title", "Saving Clone")
    try:
        print("-Data : %s\n" % bytes.fromhex(DataFix))
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        print("-Data : %s\n" % DataFix)

    Summarise(infos)
    Before = DATAX[:start]
    After = DATAX[end:]
    Fix = Before + DataFix + After
    WriteClone(Fix)


def WriteClone(data):
    global Sample
    global Have_A_KitKat
    global Pandemonium
    global ArkOfCovenant

    Pandemonium[Sample] = PandoraBox
    ArkOfCovenant[Sample] = Cornucopia

    data = bytes.fromhex(data)
    name, dir = Naming(FILE_Origin)

    print(Candy("Color", "green", "-Saving to : "), dir + "/" + name)
    with open(dir + "/" + name, "wb") as f:
        f.write(data)
    Sample = dir + "/" + name
    Have_A_KitKat = True

    if PAUSE is True:
        Pause("-Saved Press Return to continue:")

    return None


def Relics(FromError):
    Candy("Title", "Opening the Ark Of The Covenant :")

    if DEBUG is True:
        print("len pandemonium :", len(Pandemonium))
        for nb, key in enumerate(PandoraBox):
            print("Pandorbox Key:", str(key))
            for toolkey, keyvalue in PandoraBox[key].items():
                print("PandoraBox toolkey:", toolkey)
                print("PandoraBox keyvalue:", keyvalue)
        for c, i in zip(Chunks_History, Chunks_History_Index):
            print("\nCame accross that chunk: ", c)
            print("With those index: ", i)
        if PAUSEDEBUG is True:
            Pause("-Debug Pause Press Return to continue:")

    if len(Pandemonium) >= 1:
        Candy("Cowsay", "This is a short summary of what we have done :", "good")

        for nb1, (file, file_value) in enumerate(Pandemonium.items()):
            print(
                "%s:-Errors fixed in File %s :"
                % (Candy("Color", "white", "[File:%s]" % nb1), file)
            )

            for nb2, (errors, errors_values) in enumerate(file_value.items()):
                print("%s:%s" % (Candy("Color", "red", "    [-%s]" % nb2), errors))
                for nb3, (tools, tools_values) in enumerate(errors_values.items()):
                    if type(tools_values) == str or type(tools_values) == bytes:
                         if len(tools_values) > 100:
                            if type(tools_values) == bytes :
                                short_value = tools_values[0:40] + b"...To big to be displayed ..."
                            if type(tools_values) == str:
                                short_value = tools_values[0:40] + "...To big to be displayed ..."
                            print(
                                "%s:%s:%s"
                                % (
                                    Candy("Color", "yellow", "        [Tool used :%s]" % nb3),
                                    tools,
                                    short_value,
                                )
                             )
                         else:
                            print(
                                "%s:%s:%s"
                                % (
                                    Candy("Color", "yellow", "        [Tool used :%s]" % nb3),
                                    tools,
                                    tools_values,
                                )
                             )

                    else:
                        print(
                            "%s:%s:%s"
                            % (
                                Candy("Color", "yellow", "        [Tool used :%s]" % nb3),
                                tools,
                                tools_values,
                            )
                         )

        if len(Pandemonium) == 1:
            Candy("Cowsay", "Only one Error,That is short indeed ..", "com")

            for nb1, (file, file_value) in enumerate(Pandemonium.items()):
                for nb2, (errors, errors_values) in enumerate(file_value.items()):
                    if "Wrong Crc" in errors:
                        for nb3, (tools, tools_values) in enumerate(
                            errors_values.items()
                        ):
                            Chunkname = "".join(
                                [
                                    chnk.decode(errors="ignore")
                                    for chnk in ALLCHUNKS
                                    if chnk.decode(errors="ignore") in tools
                                ]
                            )

                        Candy(
                            "Cowsay",
                            "Perhaps that wasn't a Crc problem after all..",
                            "com",
                        )
                        Candy(
                            "Cowsay",
                            "Maybe the culprit was in fact the %s Data itself!"
                            % Chunkname,
                            "bad",
                        )
                        Candy(
                            "Cowsay",
                            "How about taking a coffee break while im taking care of something?",
                            "good",
                        )
                        print("Chunkname:", Chunkname)
                        # def Checksum(Ctype, Cdata, Crc,next=None):
                        Chunk = Pandemonium[file][errors][Chunkname + "_Tool_3"]
                        OldCrc = Pandemonium[file][errors][Chunkname + "_Tool_5"]
                        ChunkLenght = Pandemonium[file][errors][Chunkname + "_Tool_6"]
                        DataOffset = Pandemonium[file][errors][Chunkname + "_Tool_7"]
                        if nb1 == 0:
                            FullChunkForcerWithCrc(
                                FILE_Origin,
                                Chunk,
                                OldCrc,
                                DataOffset,
                                ChunkLenght,
                                FromError,
                            )
                            return ()
                        else:
                            pass
                            FullChunkForcerWithCrc(
                                os.path.dirname(Sample) + "/" + file,
                                Chunk,
                                OldCrc,
                                DataOffset,
                                ChunkLenght,
                                FromError,
                            )
                            return ()
                    # print("%s:%s"%(Candy("Color","red","    [Error:%s]"%nb2),errors))
                    # for nb3,(tools,tools_values) in enumerate(errors_values.items()):
                    #    print("%s:%s:%s"%(Candy("Color","yellow","        [Tool:%s]"%nb3),tools,tools_values))
                    else:
                        if DEBUG is True:
                            if PAUSEDEBUG is True or PAUSEERROR is True:
                                Pause("Pause Pandemonium Debug")
                        Candy("Cowsay", "Erf this case is not implemented yet ...", "bad")
                        TheEnd()
            return ()

        if len(Pandemonium) > 1:

            for nb1, (file, file_value) in enumerate(Pandemonium.items()):
                for nb2, (errors, errors_values) in enumerate(file_value.items()):
                    if "Filling with a dummy chunk" in errors:
                        for nb3, (tools, tools_values) in enumerate(
                            errors_values.items()
                        ):
                            ChunkName = "".join(
                                [
                                    chnk.decode(errors="ignore")
                                    for chnk in ALLCHUNKS
                                    if chnk.decode(errors="ignore") in tools
                                ]
                            )

                        ChunkLenght = Pandemonium[file][errors][ChunkName + "_Tool_1"]
                        DataOffset = Pandemonium[file][errors][ChunkName + "_Tool_3"]

                        if ChunkName.encode() in CRITICAL_CHUNKS:
                            ChunkLenght = Pandemonium[file][errors][ChunkName + "_Tool_1"]
                            DataOffset = Pandemonium[file][errors][ChunkName + "_Tool_3"]
                            Candy(
                                "Cowsay",
                                "Ok it's time to brute force that dummy %s chunk .."%(ChunkName),
                                "good",
                                )
                            Candy(
                                "Cowsay",
                                "I mean we have to since it is a critical chunk..",
                                "com",
                                )
                            Candy(
                                "Cowsay",
                                "I hope you brought a book...A big one ..Cause it may takes forever.",
                                "bad",
                                )
                            Candy(
                                "Cowsay",
                                "Shall i begin ? Otherwise Chunklate is going to close.",
                                "bad",
                                )

                            Answer = Question()
                            if Answer is True:
                                 return(SmashBruteBrawl(file, ChunkName, ChunkLenght, DataOffset,FromError, "replace" ,BruteCrc = False, BruteLenght = False))
                            else:
                                TheEnd()
                        else:
                            Candy(
                                "Cowsay",
                                "We better remove that %s chunk than trying to bruteforce it"%(ChunkName),
                                "com",
                                )
                            Candy(
                                "Cowsay",
                                "I mean it would be less time consuming since it is not a critical chunk",
                                "com",
                                )
                            Candy(
                                "Cowsay",
                                "Do you still want to bruteforce this chunk ?",
                                "com",
                                )
                            Answer = Question()
                            if Answer is True:
                                ##TODO
                                print(Candy("Color", "yellow", "\n-ToDo"))
                                TheEnd()
                            else:
                                 return(SmashBruteBrawl(file, ChunkName, ChunkLenght, DataOffset,FromError, "replace" ,BruteCrc = False, BruteLenght = False))

            TheEnd()

    else:

        CIndexList = []
        ChosenOne = ""

        print(
            "-%s has been Fixed yet. %s"
            % (Candy("Color", "red", "No Error"), Candy("Emoj", "bad"))
        )
        Candy(
            "Cowsay",
            "Erf...Kay let me check if iv forgot any error somewhere ..",
            "com",
        )

        if len(PandoraBox) > 0:
            for key in PandoraBox:
                if "GetInfo" in str(key):
                    for CC in MINIMAL_CHUNKS:
                        if CC.decode(errors="ignore") in str(key):
                            ChosenOne = CC.decode(errors="ignore")
                            break
                if len(ChosenOne) > 0:
                    break
            [CIndexList.append(k) for k in PandoraBox if ChosenOne in k and "CIndex" in k]

            if len(CIndexList) > 0:

                [
                    print("\n-\033[1;31;49mCriticalHit\033[m: ", key)
                    for k in PandoraBox
                    if ChosenOne in k
                ]
                Candy(
                    "Cowsay",
                    "Hm yeah that could be problematic indeed..",
                    "com",
                )
                Candy(
                    "Cowsay",
                    "And of course Crc is valid ...This must be a joke..",
                    "bad",
                )
                Candy(
                    "Cowsay",
                    "We can't just let this thing like that The allmighty libpng will yell at us for sure!",
                    "com",
                )
                Candy(
                    "Cowsay",
                    "So what do you say ? Shall we try to fix it ?",
                    "com",
                )
                Candy(
                    "Cowsay",
                    "(Beware this could take some time !!)",
                    "bad",
                )
                Answer = Question()
                if Answer is True:
                    if (
                        len(ChosenOne.encode()) > 0
                        and ChosenOne.encode() in Chunks_History
                        and len(CIndexList) > 0
                    ):
#                        if ChosenOne.encode() in CRITICAL_CHUNKS:

#                            Candy(
#                               "Cowsay",
#                               "This chunk is Critical and cannot be trusted not matter what crc is saying!",
#                               "bad",
#                               )
#                            SmashBruteBrawl(File, ChunkName, ChunkLenght, DataOffset,FromError, EditMode ,BruteCrc = False, BruteLenght = False)
#
#                        else:
                        for c, i in zip(Chunks_History, Chunks_History_Index):
                            if c == ChosenOne.encode():
#SmashBruteBrawl(File, ChunkName, ChunkLenght, DataOffset,FromError, EditMode ,BruteCrc = False, BruteLenght = False)
                                return MiniChunkForcerNoCrc(
                                    Sample_Name,
                                    ChosenOne,
                                    int(i.split(":")[1]),
                                    int(i.split(":")[2]),
                                    CIndexList,
                                    FromError,
                                )
                    else:
                        Candy(
                            "Cowsay",
                            "This is bad ..i don't have enough info to handle this error quickly..",
                            "com",
                        )

                        Candy(
                            "Cowsay",
                            "(I need to bruteforce every chunks until libpng is happy ...)",
                            "com",
                        )
                        Candy(
                            "Cowsay",
                            "(And this will definitively take some ..time ...like years maybe..Are you ok ?)",
                            "bad",
                        )

                        Answer = Question()
                        if Answer is True:
                            for c, i in zip(Chunks_History, Chunks_History_Index):
                                print("Chunk_history:", c.decode(errors="ignore"))
                                FullChunkForcerNoCrc(
                                    Sample_Name,
                                    c.decode(errors="ignore"),
                                    int(i.split(":")[1]),
                                    int(i.split(":")[2]),
                                    FromError,
                                )

            else:

                for key in PandoraBox:
                    if "GetInfo" in str(key):
                        for C in ALLCHUNKS:
                            if C.decode(errors="ignore") in str(key):
                                [
                                    print("\n-\033[1;31;49mCriticalHit\033[m: ", key)
                                    for k in PandoraBox
                                    if C.decode(errors="ignore") in k
                                ]
                                Candy(
                                    "Cowsay",
                                    "We'll need to use full brute force if you really want to fix it ..",
                                    "com",
                                )
                                Candy(
                                    "Cowsay",
                                    "(Beware this could take some ..time ... Do you wanna try ?)",
                                    "bad",
                                )
                                Answer = Question()
                                if Answer is True:
                                    for c, i in zip(
                                        Chunks_History, Chunks_History_Index
                                    ):
                                        if c == C.decode(errors="ignore"):

                                            return FullChunkForcerNoCrc(
                                                Sample_Name,
                                                C.decode(errors="ignore"),
                                                int(i.split(":")[1]),
                                                int(i.split(":")[2]),
                                                FromError,
                                            )

        Candy(
            "Cowsay",
            "Couldn't find anything in all those lines of codes which could handle this..",
            "bad",
        )
        Candy("Cowsay", "We r out of luck for now sorry..", "bad")
        TheEnd()


def Naming(filename):

    newdir = FILE_DIR + "Folder_" + str(os.path.basename(filename))
    newdir = os.path.splitext(newdir)[0]
    if not os.path.exists(newdir):
        os.mkdir(newdir)
    filename = os.path.basename(filename)

    if "." in filename:
        filename = os.path.splitext(filename)[0]
    filename += "."
    fileid = 0
    check = os.path.exists(newdir + "/" + filename + str(fileid) + "_Fixed.png")
    while check == True:
        fileid += 1
        check = os.path.exists(newdir + "/" + filename + str(fileid) + "_Fixed.png")
    filename = filename + str(fileid) + "_Fixed.png"

    return (filename, newdir)


def FixItFelix(Chunk=None):
    Candy("Title", "Fix It Felix: ", Candy("Color", "white", Chunk))

    global Skip_Bad_Current_Name
    global Skip_Bad_Ancillary
    global Skip_Bad_No_Next_Chunk
    global Skip_Bad_Next_Name
    global Skip_Bad_Next_Ancillary
    global Skip_Bad_Infos
    global Skip_Bad_Lenght
    global Skip_Bad_Crc
    global Skip_Bad_Missplaced
    global Skip_Bad_Critical
    global Skip_Bad_Libpng
    global Old_Bad_Crc
    global EOF
    global Show_Must_Go_On

    try:
        chkd = Chunk.decode(errors="ignore") + "_Tool_"
    except AttributeError as e:
        Betterror(e, inspect.stack()[0][3])
        chkd = Chunk + "_Tool_"

    if DEBUG is True:
        print("EOF:", EOF)
        print("Bad_Current_Name:", Bad_Current_Name)
        print("Bad_Ancillary:", Bad_Ancillary)
        print("Bad_No_Next_Chunk:", Bad_No_Next_Chunk)
        print("Bad_Next_Name:", Bad_Next_Name)
        print("Bad_Next_Ancillary:", Bad_Next_Ancillary)
        print("Bad_Lenght:", Bad_Lenght)
        print("Bad_Infos:", Bad_Infos)
        print("Bad_Crc:", Bad_Crc)
        print("Bad_Critical:", Bad_Critical)
        print("Bad_Missplaced:", Bad_Missplaced)
        print("Bad_Libpng:", Bad_Libpng)
        print("Skip_Bad_Current_Name:", Skip_Bad_Current_Name)
        print("Skip_Bad_Ancillary:", Skip_Bad_Ancillary)
        print("Skip_Bad_No_Next_Chunk:", Skip_Bad_No_Next_Chunk)
        print("Skip_Bad_Next_Name:", Skip_Bad_Next_Name)
        print("Skip_Bad_Next_Ancillary:", Skip_Bad_Next_Ancillary)
        print("Skip_Bad_Lenght:", Skip_Bad_Lenght)
        print("Skip_Bad_Infos:", Skip_Bad_Infos)
        print("Skip_Bad_Crc:", Skip_Bad_Crc)
        print("Skip_Bad_Critical:", Skip_Bad_Critical)
        print("Skip_Bad_Missplaced:", Skip_Bad_Missplaced)
        print("Skip_Bad_Libpng:", Skip_Bad_Libpng)
        print()
        print("PandoraBox:\n", PandoraBox)

        for nb, key in enumerate(PandoraBox):

            print("Len PandoraBox:", len(PandoraBox))
            for toolkey, keyvalue in PandoraBox[key].items():
                print("PandoraBox toolkey:", toolkey)
                print("PandoraBox keyvalue:", keyvalue)

        print()
        print("Cornucopia:")
        for nb, key in enumerate(Cornucopia):
            print("Len Cornucopia:", len(Cornucopia))
            for toolkey, keyvalue in Cornucopia[key].items():
                print("Cornucopia toolkey:", toolkey)
                print("Cornucopia keyvalue:", keyvalue)

        if PAUSEDEBUG is True:
            Pause("FixItFelix Debug Pause:")

    if Bad_Next_Name is False:
        PandoraBox_len = len(PandoraBox)
    else:
        PandoraBox_len = len(PandoraBox) - 1

    for nb, key in enumerate(PandoraBox):

        if "Wrong Crc" in str(key) and Skip_Bad_Crc is False:

            if str(key) not in Cornucopia:
                print("\n-\033[1;31;49mCriticalHit\033[m: ", key)

                if PandoraBox_len <= 1:
                    Candy("Cowsay", "Crc checksum is not valid !!!", "bad")
                    Candy(
                        "Cowsay",
                        "This looks like an easy fix since there is no real errors beside the Crc issue.Do you wish to try to fix it ?",
                        "com",
                    )
                    Answer = Question(key)
                    if Answer is True:
                        return SaveClone(
                            PandoraBox[key][chkd + "0"],
                            PandoraBox[key][chkd + "1"],
                            PandoraBox[key][chkd + "2"],
                            (
                                "-Found Chunk[%s] has Wrong Crc at offset: %s\n-Replaced with: %s old value was: %s"
                                % (
                                    PandoraBox[key][chkd + "3"],
                                    PandoraBox[key][chkd + "4"],
                                    PandoraBox[key][chkd + "0"],
                                    PandoraBox[key][chkd + "5"],
                                )
                            ),
                        )
                    else:
                        Skip_Bad_Crc = None
                else:
                    Candy(
                        "Cowsay",
                        "Crc checksum is not valid and there are %s other errors !"
                        % (PandoraBox_len),
                        "bad",
                    )

                    Candy(
                        "Cowsay",
                        "We may want to fix them first before jumping on that Crc what do you think ?",
                        "com",
                    )
                
                Answer = Question(key)
                if Answer is False:
                    return SaveClone(
                        PandoraBox[key][chkd + "0"],
                        PandoraBox[key][chkd + "1"],
                        PandoraBox[key][chkd + "2"],
                        (
                            "-Found Chunk[%s] has Wrong Crc at offset: %s\n-Replaced with: %s old value was: %s"
                            % (
                                PandoraBox[key][chkd + "3"],
                                PandoraBox[key][chkd + "4"],
                                PandoraBox[key][chkd + "0"],
                                PandoraBox[key][chkd + "5"],
                            )
                        ),
                    )
                else:
                    ChunkStory("add", PandoraBox[key][chkd + "3"].encode(), CLoffI, CrcoffI + 8, int(Orig_CL, 16))
#                    ChunkStory("add", Ctype, CLoffI, PandoraBox[key][chkd + "2"],PandoraBox[key][chkd + "6"])
        #return CheckPoint(
#            True,
#            False,
#            "Checksum",
#            Ctype,
#            ["-Wrong Crc"],
#            checksum[2::],
#            CrcoffI,
#            CrcoffI + 8,
#            Orig_CT,
#            CrcoffX,
#            Orig_CRC,
#            int(Orig_CL, 16),
#            CDoffI,
#        )
                    Old_Bad_Crc = PandoraBox[key][chkd + "5"]
                    Skip_Bad_Crc = True

            else:
                print("\n-\033[1;31;49mCriticalHit\033[m: ", key)
                if DEBUG is True:
                    if PAUSEDEBUG is True:
                        print("-Cornucopia is True")

        elif "libpng error:" in str(key):
            if str(key) not in Cornucopia:
                print("\n-\033[1;31;49mCriticalHit\033[m: ", key)
                if Skip_Bad_Libpng is False:
                    Candy(
                        "Cowsay",
                        "The All Mighty Libpng has spoken ...",
                        "com",
                    )
                    Candy("Cowsay", "Damned!! We were so close !", "bad")

                    Candy(
                        "Cowsay",
                        "We should go some step back before to see if we can do something else..",
                        "com",
                    )
                    Candy(
                        "Cowsay",
                        "Are you agree ? Otherwise Chunklate is going to exit",
                        "com",
                    )

                    Answer = Question(key)
                    if Answer is True:
                        Skip_Bad_Libpng = True
                        return Relics(str(key))
                    else:

                        Candy("Cowsay", "See You Space Cowboy....", "good")
                        TheEnd()

            else:
                print("\n-\033[1;32;49mSolved\033[m: ", Cornucopia[key][chkd + "3"])
                SaveClone(
                    Cornucopia[key][chkd + "0"],
                    Cornucopia[key][chkd + "1"],
                    Cornucopia[key][chkd + "2"],
                    Cornucopia[key][chkd + "3"],
                )

                return GroundhogDay(Sample)

        elif "has Wrong Chunk name at offset:" in str(key):

            if Skip_Bad_Current_Name is False:

                if str(key) not in Cornucopia:
                    print("\n-\033[1;31;49mCriticalHit\033[m: ", key)
                    Ancillary(PandoraBox[key][chkd + "0"])

                    if Bad_Ancillary is True:
                        Candy(
                            "Cowsay",
                            "I don't know that chunk but it has passed Ancillary nomenclature check ..",
                            "com",
                        )
                        if Bad_Crc is True:
                            Candy(
                                "Cowsay",
                                "But since Crc is not valid there is more chances that this Chunkname is corrupt.",
                                "bad",
                            )
                        else:

                            Candy(
                                "Cowsay",
                                "and since Crc is valid too this may be a legit private chunk..",
                                "com",
                            )

                    else:

                        Candy(
                            "Cowsay",
                            "I don't know that chunk and it has failed Ancillary nomenclature check ..",
                            "bad",
                        )
                        if Bad_Crc is True:
                            Candy(
                                "Cowsay",
                                "And since Crc is wrong this definitely looks like a corrupted Chunkname .",
                                "bad",
                            )
                        else:

                            Candy(
                                "Cowsay",
                                "But the CRC is still Valid !!! Usually this means that it has been made on purpose by someone...",
                                "bad",
                            )

                            Candy(
                                "Cowsay",
                                "Or....SOMEHTING !!",
                                "com",
                            )

                    if "and length is not the same than before." in str(key):
                        Candy(
                            "Cowsay",
                            "By the way IDAT chunk's length is different from the one usually used for some reason..",
                            "com",
                        )
                        Candy(
                            "Cowsay",
                            "May i suggest to start by checking if this a length problem ?",
                            "good",
                        )
                        Answer = Question(key)
                        if Answer is True:

                            return NearbyChunk(
                                PandoraBox[key][chkd + "0"],
                                PandoraBox[key][chkd + "1"],
                                PandoraBox[key][chkd + "2"],
                                False,
                                key,
                            )

                        else:
                            Skip_Bad_Next_Name = True
                            Pause("Else")
                    if Bad_Crc is False:
                        Candy(
                            "Cowsay",
                            "Do you want me to try to fix this regardless of CRC's validity ?",
                            "com",
                        )
                    else:

                        Candy(
                            "Cowsay",
                            "How about im taking care of the rest ?",
                            "com",
                        )

                    Answer = Question(key)
                    if Answer is True:
                        return BruteChunk(
                            PandoraBox[key][chkd + "0"],
                            PandoraBox[key][chkd + "3"],
                            PandoraBox[key][chkd + "1"],
                            str(key),
                        )

                    else:
                        Skip_Bad_Current_Name = True
                else:
                    print("\n-\033[1;32;49mSolved\033[m: ", Cornucopia[key][chkd + "4"])
                    return SaveClone(
                        Cornucopia[key][chkd + "0"],
                        Cornucopia[key][chkd + "1"],
                        Cornucopia[key][chkd + "2"],
                        Cornucopia[key][chkd + "3"],
                    )
                    pass

        elif "No NextChunk" in str(key):
            if Skip_Bad_No_Next_Chunk is False:
                print("\n-\033[1;31;49mCriticalHit\033[m: ", key)
                GoodEnding = "0000000049454E44AE426082"
                if Chunk == "IEND" and int(PandoraBox[key][chkd + "1"]) == 0:
                    for key in PandoraBox:
                        if "No NextChunk" in str(key):
                            Candy(
                                "Cowsay",
                                "That one is a false positive im removing it ..",
                                "good",
                            )
                            PandoraBox.pop(key, "key_not_found")
                            SideNotes.append(
                                "-Found False-Positive :[Error:-No NextChunk]."
                            )
                            break
                    ChunkStory("add", b"IEND", CLoffI, CrcoffI + 8, int(Orig_CL, 16))

                    if DATAX[-len(GoodEnding) :].upper() == GoodEnding:
                        CheckChunkOrder(b"IEND", "Critical")
                        Candy("Cowsay", "We have reached the end of file.", "good")
                        EOF = True
                        SideNotes.append("-Reached the end of file.")

                        if Bad_Missplaced is False:
                            Candy("Cowsay", "Ok let's feed the Kraken now..", "com")
                            return LibpngCheck(Sample)
                        else:
                            for nb, key in enumerate(PandoraBox):
                                if "Missplaced" in str(key) and EOF is True:
                                    rustine = []
                                    for toolkey, keyvalue in PandoraBox[key].items():
                                        rustine.append(keyvalue)
                                    Candy(
                                        "Cowsay", "But the fun isnt over yet..", "com"
                                    )
                                    return TheGoodPlace(
                                        rustine[0], rustine[1], rustine[2]
                                    )
                    else:
                        print(DATAX[-len(GoodEnding) :])
                        SideNotes.append("-Not ending with regular IEND Chunk")
                        TheEnd()
                elif PandoraBox[key][chkd + "0"] == "IEND":
                    print(
                        "-%s length for IEND %s "
                        % (Candy("Color", "red", "Wrong"), Candy("Emoj", "bad"))
                    )

                    SideNotes.append("-Wrong length for IEND")  # TODO
                    TheEnd()

                else:
                    print(
                        "\n-End of File Reached but IEND Chunk is %s ! %s"
                        % (Candy("Color", "red", " MISSING! "), Candy("Emoj", "bad"))
                    )

                    SideNotes.append("-End of File Reached but IEND Chunk is missing")

                    Candy(
                        "Cowsay",
                        "A length error maybe ? Do you want me to have a look ?",
                        "com",
                    )

                    Answer = Question(key)
                    if Answer is True:
                        return NearbyChunk(
                            PandoraBox[key][chkd + "0"],
                            PandoraBox[key][chkd + "1"],
                            PandoraBox[key][chkd + "2"],
                            False,
                            key,
                        )
                    else:
                        TheEnd()

        elif "gAMA Chunk of 0 is Useless" in str(key):
            Candy("Cowsay", "Bah that's that's just a warning who cares ?! !", "good")
            PandoraBox.pop(key, "key_not_found")
            SideNotes.append("-Found False-Positive :[Error:-%s]." % (str(key)))
            return FixItFelix

        else:

            print("\n-\033[1;31;49mCriticalMiss\033[m: ", key)
            if DEBUG is True:
                if PAUSEDEBUG is True:
                    Pause("Pause:Debug")
    Show_Must_Go_On = True


def CheckPoint(error, fixed, function, chunk, infos, *ToolKit):
    global Bad_Current_Name
    global Bad_Ancillary
    global Bad_No_Next_Chunk
    global Bad_Next_Name
    global Bad_Next_Ancillary
    global Bad_Infos
    global Bad_Lenght
    global Bad_Crc
    global Bad_Missplaced
    global Bad_Critical
    global Bad_Libpng
    global SideNotes
    global ERRORSFLAG
    global Cornucopia
    global PandoraBox

    Candy("Title", "CheckPoint")
    print(
        """
   ( (
    ) )
  ........
  |      |]
  \      /
   `----'"""
    )

    if DEBUG is True:
        print("error:", error)
        print("fixed:", fixed)
        print("function:", function)
        print("infos:", infos)
        print("chunk:", chunk)
        print("ToolKit:")
        for i, a in enumerate(ToolKit):
            print("Arg%s:%s type:%s" % (i, a, type(a)))
        print("Pandora:")
        for nb, key in enumerate(PandoraBox):
            print("key:", str(key))

        if PAUSEDEBUG is True:
            Pause("Checkpoint pause")

    if type(chunk) != bytes:
        chunkstr = chunk
    else:
        try:
            chunkstr = chunk.decode(errors="ignore")
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                print(
                    Candy("Color", "red", "Error Checkpoint:"),
                    Candy("Color", "yellow", e),
                )

            chunkstr = "johnnybytesme"

    for info in infos:
        if error is True:
            TOOLS = {}
            Fnum = 0

            if fixed is False:
                for key in PandoraBox:
                    while key.startswith(str(function) + "_Error_" + str(Fnum)):
                        Fnum += 1

            for Tnum, tool in enumerate(ToolKit):
                TOOLS[str(chunkstr) + "_Tool_" + str(Tnum)] = tool

            if fixed is False:
                SideNotes.append("Error:" + str(info))
                PandoraBox[
                    str(function) + "_Error_" + str(Fnum) + ":" + str(info)
                ] = TOOLS
                if PAUSEERROR is True:
                    Pause("Pause:Error")
            else:
                SideNotes.append("Error Fixed:" + str(info))
                Cornucopia[ToolKit[-1]] = TOOLS

        if function == "TheGoodPlace":
            if "Found Missing Data" in info:
                return WriteClone(ToolKit[0])
            if "Missing Data Has Not Been Found" in info:
                return DummyChunk(ToolKit[0], ToolKit[1], ToolKit[2], ToolKit[3],info)

        if function == "DummyChunk":

             if "Filling with a dummy chunk" in info:
                return WriteClone(ToolKit[0])

        if function == "FullChunkForcerWithCrc":
            if "Data has been corrupted" in info:
                SideNotes.append("-CheckPoint: %s" % info)
                FixItFelix(ToolKit[4])
            else:

                SideNotes.append("-CheckPoint: %s" % info)
                TheEnd()

        if function == "FindMagic":
            if info == "-Found Magic":
                offset = ToolKit[0]
                SideNotes.append(
                    "-CheckPoint: Returning next position based on Magic Offset %s"
                    % ToolKit[0]
                )
                return offset

            if info == "-Cutting at Magic":
                Summarise(
                    "-File does not start with a png signature.\n-Found a png signature at offset: %s\n-Creating starting with the right signature."
                    % ToolKit[1]
                )
                return WriteClone(ToolKit[0])

            if info == "-dig a little bit deeper":
                SideNotes.append("-CheckPoint: Finding Harder Magic Header")
                return FindFuckingMagic()

        if function == "FindFuckingMagic":
            if info == "-Cutting at Magic":
                Summarise(
                    "-File does not start with a png signature.\n-Found a png signature at offset: %s\n-Creating starting with the right signature."
                    % ToolKit[1]
                )
                return WriteClone(ToolKit[0])

            if info == "-Prepending Magic":
                Summarise(
                    "-File does not start with a png signature.\n-Did prepending a png signature at offset: %s\n-Creating starting with the right signature."
                    % ToolKit[1]
                )
                return WriteClone(ToolKit[0])

        if function == "CheckLength":

            if info == "-Found NextChunk":
                SideNotes.append(
                    "-CheckPoint:From Chunk [%s] Found NextChunk at length previously indicated for checking [%s]."
                    % (chunk, ToolKit[0])
                )
                return CheckChunkName(Raw_NextChunk, int(ToolKit[0], 16), chunk, True)
            else:
                Bad_No_Next_Chunk = error

        if function == "NearbyChunk":

            return SaveClone(
                ToolKit[0],
                ToolKit[1],
                ToolKit[2],
                ToolKit[3],
            )
        if function == "CheckChunkOrder":
            if chunk == "Critical":
                Bad_Critical = error
            if "Missplaced" in info:
                Bad_Missplaced = error

        if function == "Checksum":

            if "Wrong Crc" in info:
                Bad_Crc = error

        if function == "LibpngCheck":
            if "libpng error:" in info:
                Bad_Libpng = error
                FixItFelix("LibpngCheck")

            elif "libpng warning:" in info:
                print("\n-\033[1;31;49mCriticalHit\033[m: ", info)
                Candy(
                    "Cowsay", "Bah that's that's just a warning who cares ?! !", "good"
                )
                Candy(
                    "Cowsay",
                    "im removing it ..",
                    "good",
                )
                for nb, key in enumerate(PandoraBox):

                    if "libpng warning:" in str(key):
                        PandoraBox.pop(key, "key_not_found")
                        SideNotes.append(
                            "-Found False-Positive :[Error:-%s]." % (str(key))
                        )
                        break

                if Chunks_History[-1] == b"IEND" and EOF is True:
                    Candy(
                        "Cowsay",
                        "Well maybe i am missing something but as for my abilities my job is done here!",
                        "good",
                    )
                    Candy("Cowsay", "See you Space Cowboy...", "good")
                    TheEnd()

            else:
                Candy(
                    "Cowsay",
                    "Well maybe i am missing something but as far as my current abilities goes the job is done for me here!",
                    "good",
                )
                Candy("Cowsay", "See you Space Cowboy...", "good")
                TheEnd()

        if function == "CheckChunkName":

            if "turning it into a valid Chunk name" in info:

                SideNotes.append("-%s: %s" % (function, info))
                FixItFelix(ToolKit[3])

            if "Wrong Ancillary in known Chunk name at offset" in info:
                if ToolKit[5] != None:
                    Bad_Next_Ancillary = error
                else:
                    Bad_Ancillary = error

            if "has Wrong Chunk name at offset:" in info:
                Bad_Current_Name = error

            if "has Wrong Chunk name after Chunk[" in info:
                Bad_Next_Name = error
    return ()


def Pause(msg):
    pause = input(msg)
    return ()


def main():
    global IDAT_Bytes_Len
    global IDAT_Datastream
    global idatcounter
    global FirStart
    global FILE_Origin
    global CLEAR
    global PAUSE
    global DEBUG
    global PAUSEDEBUG
    global PAUSEERROR
    global PAUSEDIALOGUE
    global AUTO
    global CLONESWAR
    global Bad_Ancillary
    global FILE_DIR
    global DATAX
    global ERRORSFLAG
    global PandoraBox
    global Cornucopia
    global IDAT_Bytes_Len_History
    global IDAT_Avg_Len
    global Chunks_History
    global Chunks_History_Index
    global Bytes_History
    global Loading_txt
    global Bad_No_Next_Chunk
    global Bad_Current_Name
    global Bad_Ancillary
    global Bad_Next_Name
    global Bad_Next_Ancillary
    global Bad_Infos
    global Bad_Lenght
    global Bad_Crc
    global Bad_Missplaced
    global Bad_Critical
    global Bad_Libpng
    global Skip_Bad_Current_Name
    global Skip_Bad_Ancillary
    global Skip_Bad_No_Next_Chunk
    global Skip_Bad_Next_Name
    global Skip_Bad_Next_Ancillary
    global Skip_Bad_Infos
    global Skip_Bad_Lenght
    global Skip_Bad_Crc
    global Skip_Bad_Missplaced
    global Skip_Bad_Critical
    global Skip_Bad_Libpng
    global EOF
    global IFOP
    global Show_Must_Go_On
    global SideNotes
    global Sample
    global Sample_Name
    global Have_A_KitKat

    parser = ArgumentParser()
    parser.add_argument(
        "-f", "--file", dest="FILENAME", help="File path.", default=None, metavar="FILE"
    )
    parser.add_argument(
        "-c",
        "--CLEAR",
        dest="CLEAR",
        help="CLEAR screen at each saves.",
        action="store_true",
    )
    parser.add_argument(
        "-p", "--pause", dest="PAUSE", help="Pause at each saves.", action="store_true"
    )
    parser.add_argument(
        "-d", "--debug", dest="DEBUG", help="Debug stuffs.", action="store_true"
    )
    parser.add_argument(
        "-dp",
        "--pause-debug",
        dest="PAUSEDEBUG",
        help="Pause at Debug stuffs.",
        action="store_true",
    )
    parser.add_argument(
        "-ep",
        "--pause-error",
        dest="PAUSEERROR",
        help="Pause at errors.",
        action="store_true",
    )
    parser.add_argument(
        "-sp",
        "--pause-dialogue",
        dest="PAUSEDIALOGUE",
        help="Pause at dialogues.",
        action="store_true",
    )
    parser.add_argument(
        "-a", "--auto", dest="AUTO", help="Auto Choose action.", action="store_true"
    )

    Args, unknown = parser.parse_known_args()
    unknown = " ".join([i for i in unknown])
    if "--CLONE" in unknown:
        CLONESWAR = unknown.split("--CLONE ")[1]

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    if Args.FILENAME is None:
        print("-f,--filename arguments is missing.")
        sys.exit(1)

    FILE_Origin = Args.FILENAME
    CLEAR = Args.CLEAR
    PAUSE = Args.PAUSE
    PAUSEDEBUG = Args.PAUSEDEBUG
    PAUSEERROR = Args.PAUSEERROR
    PAUSEDIALOGUE = Args.PAUSEDIALOGUE
    DEBUG = Args.DEBUG
    AUTO = Args.AUTO
    Sample = FILE_Origin

    if PAUSEDEBUG is True:
        DEBUG = True

    while True:

        if CLEAR is True:
            if FirStart is False:
                if os.name == "posix":
                    sys.stdout.write("\033c")
                elif os.name == "nt":
                    os.system("cls")
            else:
                FirStart = False
        IDAT_Bytes_Len = 0
        IDAT_Datastream = ""
        Bad_Current_Name = False
        Bad_Ancillary = False
        Bad_No_Next_Chunk = False
        Bad_Next_Name = False
        Bad_Next_Ancillary = False
        Bad_Lenght = False
        Bad_Infos = False
        Bad_Crc = False
        Bad_Critical = False
        Bad_Missplaced = False
        Skip_Bad_Current_Name = False
        Skip_Bad_Ancillary = False
        Skip_Bad_No_Next_Chunk = False
        Skip_Bad_Next_Name = False
        Skip_Bad_Next_Ancillary = False
        Skip_Bad_Lenght = False
        Skip_Bad_Infos = False
        Skip_Bad_Crc = False
        Skip_Bad_Critical = False
        Skip_Bad_Missplaced = False
        Skip_Bad_Libpng = False
        EOF = False
        Show_Must_Go_On = False
        TmpFixIHDR = False
        IDAT_Bytes_Len_History = []
        IDAT_Avg_Len = ""
        Chunks_History = []
        Chunks_History_Index = []
        Bytes_History = []
        Loading_txt = ""
        # IFOP = []
        ERRORSFLAG = []
        PandoraBox = {}
        Cornucopia = {}
        SideNotes = []
        Chunklate(1)

        if CLONESWAR is False:
            Sample_Name = os.path.basename(Sample)
        else:
            Sample = CLONESWAR
            Sample_Name = os.path.basename(CLONESWAR)
            CLONESWAR = False

        print("-Proceeding with: ", Candy("Color", "white", Sample_Name))
        try:
            with open(Sample, "rb") as f:
                data = f.read()
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            print(Candy("Color", "red", "Error:"), Candy("Color", "yellow", e))
            sys.exit(1)

        DATAX = data.hex()

        Candy("Cowsay", " %s is loaded!" % Candy("Color", "green", Sample_Name), "good")
        Offset = FindMagic()
        if Offset != None:

            while Offset < len(DATAX):

                ChunkbyChunk(Offset)

                CheckLength(Orig_CD, Orig_CL, Orig_CT)

                CheckChunkName(Orig_CT, Orig_CL, Chunks_History[-1])

                GetInfo(Orig_CT, Raw_Data)

                Checksum(Raw_Type, Raw_Data, Raw_Crc)

                while True:
                    FixItFelix(Orig_CT)
                    if Show_Must_Go_On is True:
                        break

                Offset = (
                    Offset
                    + len(Raw_Length)
                    + len(Raw_Type)
                    + len(Raw_Data)
                    + len(Raw_Crc)
                )

                if Have_A_KitKat is True:
                    Have_A_KitKat = False
                    break

        # print("Reached End of %s\n"%Sample_Name)
        # CheckChunkOrder(b'IEND',"Critical")
        # TheEnd()


###


###

MINIMAL_CHUNKS = [b"PNG", b"IHDR", b"IDAT", b"IEND"]
CRITICAL_CHUNKS = [b"PNG", b"IHDR", b"PLTE", b"IDAT", b"IEND"]
CHUNKS = [
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
]
PRIVATE_CHUNKS = [
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
]

BEFORE_PLTE = [b"PNG", b"IHDR", b"gAMA", b"cHRM", b"iCCP", b"sRGB", b"sBIT"]

AFTER_PLTE = [b"tRNS", b"hIST", b"bKGD"]  # but before idat

BEFORE_IDAT = [
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
]

BEFORE_IDAT2 = [
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
]

UNIQUE_CHUNK = [
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
]

NO_ORDER_CHUNKS = [
    b"tIME",
    b"tEXt",
    b"zTXt",
    b"iTXt",
    b"fRAc",
    b"gIFg",
    b"gIFx",
    b"gIFt",
]


ALLCHUNKS = [
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
]

IFOP = []
Chunks_History = []
IDAT_Bytes_Len_History = []
Chunks_History_Index = []
pCAL_Param = []
PLTE_R = []
PLTE_G = []
PLTE_B = []
sPLT_Name = []
sPLT_Depht = []
sPLT_Red = []
sPLT_Green = []
sPLT_Blue = []
sPLT_Alpha = []
sPLT_Freq = []
hIST = []
tEXt_Key_List = []
tEXt_Str_List = []
iTXt_String_List = []
iTXt_Key_List = []
tRNS_Index = []
zTXt_Key_List = []
zTXt_Str_List = []
SideNotes = []
ERRORSFLAG = []

PandoraBox = {}
Cornucopia = {}
ArkOfCovenant = {}
Pandemonium = {}


libc = ctypes.CDLL(None)
c_stderr = ctypes.c_void_p.in_dll(libc, "stderr")

# TMPFIX = False

FirStart = True
Switch = False
GoBack = False
WORKING = True
MAXCHAR = int(os.get_terminal_size(0)[0]) - 1
CharPos = 1
Have_A_KitKat = False
TmpFixIHDR = False
Warning = False
Summary_Header = True
Bad_Current_Name = False
Bad_Ancillary = False
Bad_No_Next_Chunk = False
Bad_Next_Name = False
Bad_Next_Ancillary = False
Bad_Lenght = False
Bad_Infos = False
Bad_Crc = False
Bad_Critical = False
Bad_Missplaced = False
Bad_Libpng = False
Skip_Bad_Current_Name = False
Skip_Bad_Ancillary = False
Skip_Bad_No_Next_Chunk = False
Skip_Bad_Next_Name = False
Skip_Bad_Next_Ancillary = False
Skip_Bad_Lenght = False
Skip_Bad_Infos = False
Skip_Bad_Crc = False
Skip_Bad_Critical = False
Skip_Bad_Missplaced = False
Skip_Bad_Libpng = False
EOF = False
Show_Must_Go_On = False
CLEAR = False
PAUSE = False
DEBUG = False
PAUSEDEBUG = False
PAUSEERROR = False
PAUSEDIALOGUE = False
AUTO = False
CLONESWAR = False

IDAT_Bytes_Len = 0
IDAT_Datastream = ""
idatcounter = 0
Old_Bad_Crc = ""
IDAT_Avg_Len = ""
FILE_Origin = ""
FILE_DIR = ""
Loading_txt = ""
DATAX = ""
Sample_Name = ""
Sample = ""

Raw_Length = ""
Raw_Data = ""
Raw_Crc = ""
Raw_NextChunk = ""
Raw_Type = ""
Orig_CL = ""
Orig_CT = ""
Orig_NC = ""
Orig_CD = ""
Orig_CRC = ""
CLoffX = ""
CLoffB = ""
CLoffI = ""
CToffX = ""
CToffB = ""
CToffI = ""
NCoffX = ""
NCoffB = ""
NCoffI = ""
NCoff_CRC = ""
Bad_Ancillary = ""
CDoffX = ""
CDoffB = ""
CDoffI = ""
CrcoffX = ""
CrcoffB = ""
CrcoffI = ""
iCCP_Name = ""
iCCP_Method = ""
iCCP_Profile = ""
IHDR_Height = ""
IHDR_Width = ""
IHDR_Depht = ""
IHDR_Color = ""
IHDR_Method = ""
IHDR_Filter = ""
IHDR_Interlace = ""
bKGD_Gray = ""
bKGD_Red = ""
bKGD_Green = ""
bKGD_Blue = ""
bKGD_Index = ""
sRGB = ""

pCAL_Key = ""
pCAL_Zero = ""
pCAL_Max = ""
pCAL_Eq = ""
pCAL_PNBR = ""

cHRM_WhiteX = ""
cHRM_WhiteY = ""
cHRM_Redx = ""
cHRM_Redy = ""
cHRM_Greenx = ""
cHRM_Greeny = ""
cHRM_Bluex = ""
cHRM_Bluey = ""

gAMA = ""

pHYs_Y = ""
pHYs_X = ""
pHYs_Unit = ""
sTER = ""
gIFID = ""
gIFCD = ""
gIFDT = ""
gIFgM = ""
gIFgU = ""
gIFgT = ""

sBIT_Gray = ""
sBIT_TrueR = ""
sBIT_TrueG = ""
sBIT_TrueB = ""
sBIT_GrayScale = ""
sBIT_GrayAlpha = ""
sBIT_TrueAlphaR = ""
sBIT_TrueAlphaG = ""
sBIT_TrueAlphaB = ""
sBIT_TrueAlpha = ""

tEXt_Key = ""
tEXt_Text = ""

iTXt_String = ""
iTXt_Key = ""
tIME_Yr = ""
tIME_Mth = ""
tIME_Day = ""
tIME_Hr = ""
tIME_Min = ""
tIME_Sec = ""
tRNS_Gray = ""
tRNS_TrueR = ""
tRNS_TrueG = ""
tRNS_TrueB = ""

zTXt_Key = ""
zTXt_Meth = ""
zTXt_Text = ""


if __name__ == "__main__":
    main()
