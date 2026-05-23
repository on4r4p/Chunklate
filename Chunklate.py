#!/usr/bin/env python3
from argparse import ArgumentParser, SUPPRESS
from datetime import datetime,timedelta
try:
    from PIL import Image,ImageShow,ImageTk
except ModuleNotFoundError:
    Image = ImageShow = ImageTk = None

try:
    from inputimeout import inputimeout
except ModuleNotFoundError:
    def inputimeout(prompt="", timeout=None):
        return input(prompt)

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

try:
    import tkinter
except ModuleNotFoundError:
    tkinter = None

import sys, os, binascii, random, time, zlib, io, inspect, types, difflib, collections, itertools, shutil

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None

try:
    import psutil
except ModuleNotFoundError:
    psutil = None

try:
    import imagehash
except ModuleNotFoundError:
    imagehash = None

from chunklate import ancillary, bruteforce, checkpoint, checkpoint_runtime, chunk_info, chunk_order, chunk_report, chunk_scanner, chunk_state, chunk_story, cli, decisions, dummy_chunk, error_log, fixit_felix, history, nearby, output, palette, palette_runtime, palette_ui, prompts, question_runtime, relics, relics_runtime, relics_ui, runtime_state, sorting, specs, stdio, ui, ui_runtime, writer
from chunklate.png import (
    PngFormatError,
    chunk_type_crc_matches,
    detect_png_signature_recovery,
    iter_chunks,
    known_bad_srgb_profile_warning,
    legacy_crc_decision,
    legacy_length_decision,
)


def Betterror(error_msg, def_name): ##useless since 3.11
    try:
        Err_to_log = error_log.format_exception_from_exc_info(
            sys.exc_info(),
            def_name,
            error_msg,
        )
        if DEBUG is True:
            PRINT(Err_to_log)

    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        Err_to_log = error_log.format_exception_from_exc_info(
            sys.exc_info(),
            "Betterror",
            e,
        )
        if DEBUG is True:
            PRINT(Err_to_log)

    return Error_Log(Err_to_log)


def Error_Log(Err_to_log):
    global SideNotes
    try:
        error_log.append_error_log(Err_to_log, str(sys.path[0]))
        if 1 == 1:  # if DEBUG is True:
            SideNotes.append(Err_to_log)

    except Exception as e:
        Betterror(e, inspect.stack()[0][3])


# Relics state model:
# - PandoraBox holds current-file findings that still need a decision or repair.
#   Keys look like "Function_Error_N:message"; values are "<Chunk>_Tool_N" dicts.
# - Cornucopia holds fixes already accepted by CheckPoint/FixItFelix.
# - WriteClone snapshots those two stores into Pandemonium/ArkOfCovenant so
#   Relics can react to the repair history when libpng reports a later failure.
def CheckPoint_Record_Finding(registration):
    if registration.side_note is not None:
        SideNotes.append(registration.side_note)
    return relics.record_checkpoint_registration(PandoraBox, Cornucopia, registration)


def CheckPoint_Apply_Flags(flags):
    if not flags:
        return
    globals().update(flags)


def CheckPoint_Print_Libpng_Critical(info):
    PRINT("\n-\033[1;31;49mCriticalHit\033[m: %s" % info)


def CheckPoint_Discard_Libpng_Warning():
    for nb, key in enumerate(PandoraBox):
        if "libpng warning:" in str(key):
            relics.discard_pandora_error(PandoraBox, key)
            SideNotes.append("-Found False-Positive :[Error:-%s]." % (str(key)))
            break


def CheckPoint_Libpng_End_Success(message):
    Candy(
        "Cowsay",
        message,
        "good",
    )
    Candy("Cowsay", "Your file is here :", "good")
    name, sample_dir = Naming(FILE_Origin)
    PRINT(Candy("Color", "green", "-Saved in : %s/%s") % (sample_dir, Sample_Name))
    Candy("Cowsay", "See you Space Cowboy...", "good")
    TheEnd()


def CheckPoint_Runtime():
    return checkpoint_runtime.CheckPointRuntime(
        write_clone=WriteClone,
        dummy_chunk=DummyChunk,
        summarise=Summarise,
        find_fucking_magic=FindFuckingMagic,
        check_chunk_name=CheckChunkName,
        save_clone=SaveClone,
        fix_it_felix=FixItFelix,
        relics=Relics,
        smash_brute_brawl=SmashBruteBrawl,
        candy=Candy,
        emit=PRINT,
        end=TheEnd,
        question=Question,
        print_libpng_critical=CheckPoint_Print_Libpng_Critical,
        discard_libpng_warning=CheckPoint_Discard_Libpng_Warning,
        libpng_end_success=CheckPoint_Libpng_End_Success,
    )


def CheckPoint_Action_Write_Clone(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_write_clone(CheckPoint_Runtime(), toolkit)


def CheckPoint_Action_Dummy_Chunk_From_The_Good_Place(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_dummy_chunk_from_the_good_place(
        CheckPoint_Runtime(),
        toolkit,
        info,
    )


def CheckPoint_Action_Return_Value(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_return_value(decision.return_value)


def CheckPoint_Action_Summarise_And_Write_Clone(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_summarise_and_write_clone(
        CheckPoint_Runtime(),
        decision.summary,
        toolkit,
    )


def CheckPoint_Action_Find_Fucking_Magic(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_find_fucking_magic(CheckPoint_Runtime())


def CheckPoint_Action_Check_Chunk_Name(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_check_chunk_name(
        CheckPoint_Runtime(),
        Raw_NextChunk,
        chunk,
        toolkit,
    )


def CheckPoint_Action_Save_Clone(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_save_clone(CheckPoint_Runtime(), toolkit)


def CheckPoint_Action_Save_Clone_Missing_Bytes(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_save_clone_missing_bytes(CheckPoint_Runtime(), toolkit)


def CheckPoint_Action_Fix_It_Felix_Continue(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_fix_it_felix_continue(
        CheckPoint_Runtime(),
        decision.return_value,
    )


def CheckPoint_Action_Fix_It_Felix_Return(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_fix_it_felix_return(
        CheckPoint_Runtime(),
        decision.return_value,
    )


def CheckPoint_Action_Libpng_Warning_Relics(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_libpng_warning_relics(CheckPoint_Runtime(), info)


def CheckPoint_Action_Discard_Libpng_Warning(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_discard_libpng_warning(
        CheckPoint_Runtime(),
        decision.action,
        info,
    )


def CheckPoint_Action_Libpng_End_Success(decision, chunk, info, toolkit):
    return checkpoint_runtime.run_libpng_end_success(CheckPoint_Runtime())


def CheckPoint_SmashBruteBrawl_Relaunch(
    toolkit,
    from_error,
    *,
    bf_mode=None,
    has_old_crc=False,
    old_crc=None,
):
    return checkpoint_runtime.run_smash_brute_brawl_relaunch(
        CheckPoint_Runtime(),
        toolkit,
        from_error,
        bf_mode=bf_mode,
        has_old_crc=has_old_crc,
        old_crc=old_crc,
    )


def CheckPoint_Action_SmashBruteBrawl_Retry_IHDR(decision, chunk, info, toolkit):
    global Brute_LvL

    Brute_LvL += 1
    SideNotes.append("-CheckPoint: %s" % info)
    return checkpoint_runtime.run_smash_brute_brawl_retry_ihdr(
        CheckPoint_Runtime(),
        toolkit,
        toolkit[8],
        Brute_LvL,
    )


def CheckPoint_Action_SmashBruteBrawl_Ask_TwoBytes_Retry(decision, chunk, info, toolkit):
    global Brute_LvL

    Brute_LvL += 1
    Answer = checkpoint_runtime.ask_smash_brute_brawl_twobytes_retry(
        CheckPoint_Runtime(),
        toolkit,
        brute_level=Brute_LvL,
        eta=ETA,
        ihdr_interlace=IHDR_Interlace,
    )
    if Answer:
        SideNotes.append("-CheckPoint: Increasing BfLvl: %s" % info)
        if "OldCrc" in info:
            CheckPoint_SmashBruteBrawl_Relaunch(
                toolkit,
                toolkit[9],
                has_old_crc=True,
                old_crc=toolkit[8],
            )
        else:
            CheckPoint_SmashBruteBrawl_Relaunch(toolkit, toolkit[8])
        return False, None

    return CheckPoint_SmashBruteBrawl_Handle_TwoBytes_Decline(info, toolkit)


def CheckPoint_SmashBruteBrawl_Handle_TwoBytes_Decline(info, toolkit):
    if toolkit[1] == b"IDAT" and IHDR_Interlace == "1":
        Answer = checkpoint_runtime.ask_smash_brute_brawl_dummy_idat_fallback(
            CheckPoint_Runtime()
        )
        if Answer is True:
            SideNotes.append("-CheckPoint:User choose to replace IDAT: %s" % info)
            if "OldCrc" in info:
                DummyChunk(toolkit[1], toolkit[3], toolkit[3], toolkit[2], toolkit[9])
            else:
                DummyChunk(toolkit[1], toolkit[3], toolkit[3], toolkit[2], toolkit[8])
            return False, None

        SideNotes.append("-CheckPoint: %s User chose to quit." % info)
        TheEnd()
        return False, None

    return CheckPoint_Action_SmashBruteBrawl_End_Failed_NonCustom(
        None,
        None,
        info,
        toolkit,
    )


def CheckPoint_Action_SmashBruteBrawl_End_Failed_NonCustom(decision, chunk, info, toolkit):
    SideNotes.append("-CheckPoint: %s" % info)
    return checkpoint_runtime.run_smash_brute_brawl_end_failed_noncustom(
        CheckPoint_Runtime()
    )


def CheckPoint_Action_SmashBruteBrawl_Ask_Custom_Brutus(decision, chunk, info, toolkit):
    global Brute_LvL

    SideNotes.append(
        "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!(CUSTOM END)"
    )
    Answer = checkpoint_runtime.ask_smash_brute_brawl_custom_brutus(CheckPoint_Runtime())
    if Answer is True:
        Brute_LvL = 0
        CheckPoint_SmashBruteBrawl_Relaunch(toolkit, toolkit[8], bf_mode="Brutus")
    else:
        CheckPoint_Runtime().end()
    return False, None


def CheckPoint_Action_SmashBruteBrawl_End_Unhandled(decision, chunk, info, toolkit):
    SideNotes.append("-CheckPoint: %s" % info)
    return checkpoint_runtime.run_smash_brute_brawl_end_unhandled(CheckPoint_Runtime())


CHECKPOINT_ACTION_HANDLERS = {
    "write_clone": CheckPoint_Action_Write_Clone,
    "dummy_chunk_from_the_good_place": CheckPoint_Action_Dummy_Chunk_From_The_Good_Place,
    "return_value": CheckPoint_Action_Return_Value,
    "summarise_and_write_clone": CheckPoint_Action_Summarise_And_Write_Clone,
    "find_fucking_magic": CheckPoint_Action_Find_Fucking_Magic,
    "check_chunk_name": CheckPoint_Action_Check_Chunk_Name,
    "save_clone": CheckPoint_Action_Save_Clone,
    "save_clone_missing_bytes": CheckPoint_Action_Save_Clone_Missing_Bytes,
    "fix_it_felix_continue": CheckPoint_Action_Fix_It_Felix_Continue,
    "fix_it_felix_return": CheckPoint_Action_Fix_It_Felix_Return,
    "libpng_warning_relics": CheckPoint_Action_Libpng_Warning_Relics,
    "discard_libpng_warning": CheckPoint_Action_Discard_Libpng_Warning,
    "discard_libpng_warning_and_end": CheckPoint_Action_Discard_Libpng_Warning,
    "libpng_end_success": CheckPoint_Action_Libpng_End_Success,
    "smash_brute_brawl_retry_ihdr_harder": CheckPoint_Action_SmashBruteBrawl_Retry_IHDR,
    "smash_brute_brawl_ask_twobytes_retry": CheckPoint_Action_SmashBruteBrawl_Ask_TwoBytes_Retry,
    "smash_brute_brawl_end_failed_noncustom": CheckPoint_Action_SmashBruteBrawl_End_Failed_NonCustom,
    "smash_brute_brawl_ask_custom_brutus": CheckPoint_Action_SmashBruteBrawl_Ask_Custom_Brutus,
    "smash_brute_brawl_end_unhandled": CheckPoint_Action_SmashBruteBrawl_End_Unhandled,
}


def CheckPoint_Apply_Action_Decision(decision, chunk, info, toolkit):
    if decision.side_note is not None:
        SideNotes.append(decision.side_note)

    CheckPoint_Apply_Flags(decision.flags)

    if decision.action is None:
        return False, None

    handler = CHECKPOINT_ACTION_HANDLERS.get(decision.action)
    if handler is not None:
        return handler(decision, chunk, info, toolkit)

    raise ValueError("Unknown CheckPoint action decision: %s" % decision.action)


def Pandemonium_Remember_Current_Sample():
    relics.remember_sample(Pandemonium, ArkOfCovenant, Sample, PandoraBox, Cornucopia)


def IDAT_Bytes_Nbr():  # tmpworkaround
    global IBN
    IBN = specs.estimate_idat_bytes_from_hex(DATAX, tuple(CHUNKS))



def Max_Res():
    try:
        MaxRes, size = specs.estimate_max_resolution_from_file(FILE_Origin)
        if DEBUG:
            PRINT("Size:%s"%str(size))
            PRINT(
                "-Maximum resolution estimation based on file size: %s*%s"
                % (MaxRes, MaxRes)
            )
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))
        TheEnd()

    return MaxRes


def GetSpec(GetChunk,Mode,Fields=["All"],StructIndex=None,IterNbr=1):

    if DEBUG:
         PRINT("GetChunk:%s"%GetChunk)
         PRINT("Mode:%s"%Mode)
         PRINT("Fields:%s"%Fields)

    if IBN == 0:
            IDAT_Bytes_Nbr()

    context = specs.build_getspec_context(
        current_year=datetime.now().year,
        chunk_name=GetChunk,
        mode=Mode,
        idat_byte_count=IBN,
        max_resolution=Max_Res(),
        brute_level=Brute_LvL,
        ihdr_color=IHDR_Color,
        ihdr_height=IHDR_Height,
        ihdr_width=IHDR_Width,
        pandora_box=PandoraBox,
        cornucopia=Cornucopia,
        pandemonium=Pandemonium,
        allchunks=ALLCHUNKS,
        skip_bad_crc=Skip_Bad_Crc,
    )

    if DEBUG:
            if GetChunk in specs.GETSPEC_COLOR_CHUNKS:
                PRINT("-ColorType set to:%s"% context.color_type)
            PRINT(
                "-Smalest resolution estimation based on file size: %s*%s"
                % (context.min_resolution, context.min_resolution)
            )

    try:
        result = specs.resolve_getspec(
            context,
            GetChunk,
            Fields,
            Mode,
            StructIndex,
            IterNbr,
        )
    except (NameError, ValueError) as e:
        Betterror(e, inspect.stack()[0][3])
        if DEBUG is True:
           PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))
        if PAUSEDEBUG is True or PAUSEERROR is True:
             Pause("Pause Debug")
        TheEnd()

    if result is not None:
        return result

    PRINT("-Error in GetSpec: Didnt Found matching result")
    PRINT("GetColor:%s"% context.color_type)
    PRINT("GetChunk:%s"% GetChunk)
    PRINT(Candy("Color", "yellow", "\n-ToDo"))
    return


def Sync_Chunk_Info_Legacy_State(section=None):
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
    global tRNS_Index
    global pCAL_Param
    global pCAL_Key
    global pCAL_Zero
    global pCAL_Max
    global pCAL_Eq
    global pCAL_PNBR
    global cHRM_WhiteX
    global cHRM_WhiteY
    global cHRM_Redx
    global cHRM_Redy
    global cHRM_Greenx
    global cHRM_Greeny
    global cHRM_Bluex
    global cHRM_Bluey
    global iCCP_Name
    global iCCP_Method
    global iCCP_Profile
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
    global gIFgM
    global gIFgU
    global gIFgT
    global gIFID
    global gIFCD
    global gIFDT
    global sTER
    global tEXt_Key_List
    global tEXt_Str_List
    global tEXt_Key
    global tEXt_Text
    global zTXt_Key_List
    global zTXt_Str_List
    global zTXt_Key
    global zTXt_Text
    global iTXt_String_List
    global iTXt_Key_List
    global iTXt_String
    global iTXt_Key
    global eXIf_endian

    sections = {section} if isinstance(section, str) else set(section or ())
    sync_all = section is None

    if sync_all or "ihdr" in sections:
        IHDR_Width = CHUNK_INFO_STATE.ihdr_width
        IHDR_Height = CHUNK_INFO_STATE.ihdr_height
        IHDR_Depht = CHUNK_INFO_STATE.ihdr_depth
        IHDR_Color = CHUNK_INFO_STATE.ihdr_color
        IHDR_Method = CHUNK_INFO_STATE.ihdr_method
        IHDR_Filter = CHUNK_INFO_STATE.ihdr_filter
        IHDR_Interlace = CHUNK_INFO_STATE.ihdr_interlace

    if sync_all or "idat" in sections:
        IDAT_Bytes_Len = CHUNK_INFO_STATE.idat_bytes_len
        IDAT_Datastream = CHUNK_INFO_STATE.idat_datastream
        idatcounter = CHUNK_INFO_STATE.idat_counter
        IDAT_Bytes_Len_History = list(CHUNK_INFO_STATE.idat_bytes_len_history)
        IDAT_Avg_Len = CHUNK_INFO_STATE.idat_avg_len

    if sync_all or "plte" in sections:
        PLTE_R = list(CHUNK_INFO_STATE.plte_r)
        PLTE_G = list(CHUNK_INFO_STATE.plte_g)
        PLTE_B = list(CHUNK_INFO_STATE.plte_b)

    if sync_all or "splt" in sections:
        sPLT_Name = list(CHUNK_INFO_STATE.splt_name)
        sPLT_Depht = list(CHUNK_INFO_STATE.splt_depth)
        sPLT_Red = list(CHUNK_INFO_STATE.splt_red)
        sPLT_Green = list(CHUNK_INFO_STATE.splt_green)
        sPLT_Blue = list(CHUNK_INFO_STATE.splt_blue)
        sPLT_Alpha = list(CHUNK_INFO_STATE.splt_alpha)
        sPLT_Freq = list(CHUNK_INFO_STATE.splt_freq)

    if sync_all or "trns" in sections:
        tRNS_Index = list(CHUNK_INFO_STATE.trns_index)

    if sync_all or "pcal" in sections:
        pCAL_Param = list(CHUNK_INFO_STATE.pcal_param)
        pCAL_Key = CHUNK_INFO_STATE.pcal_key
        pCAL_Zero = CHUNK_INFO_STATE.pcal_zero
        pCAL_Max = CHUNK_INFO_STATE.pcal_max
        pCAL_Eq = CHUNK_INFO_STATE.pcal_eq
        pCAL_PNBR = CHUNK_INFO_STATE.pcal_pnbr

    if sync_all or "chrm" in sections:
        cHRM_WhiteX = CHUNK_INFO_STATE.chrm_white_x
        cHRM_WhiteY = CHUNK_INFO_STATE.chrm_white_y
        cHRM_Redx = CHUNK_INFO_STATE.chrm_red_x
        cHRM_Redy = CHUNK_INFO_STATE.chrm_red_y
        cHRM_Greenx = CHUNK_INFO_STATE.chrm_green_x
        cHRM_Greeny = CHUNK_INFO_STATE.chrm_green_y
        cHRM_Bluex = CHUNK_INFO_STATE.chrm_blue_x
        cHRM_Bluey = CHUNK_INFO_STATE.chrm_blue_y

    if sync_all or "iccp" in sections:
        iCCP_Name = CHUNK_INFO_STATE.iccp_name
        iCCP_Method = CHUNK_INFO_STATE.iccp_method
        iCCP_Profile = CHUNK_INFO_STATE.iccp_profile

    if sync_all or "sbit" in sections:
        sBIT_Gray = CHUNK_INFO_STATE.sbit_gray
        sBIT_TrueR = CHUNK_INFO_STATE.sbit_true_r
        sBIT_TrueG = CHUNK_INFO_STATE.sbit_true_g
        sBIT_TrueB = CHUNK_INFO_STATE.sbit_true_b
        sBIT_GrayScale = CHUNK_INFO_STATE.sbit_gray_scale
        sBIT_GrayAlpha = CHUNK_INFO_STATE.sbit_gray_alpha
        sBIT_TrueAlphaR = CHUNK_INFO_STATE.sbit_true_alpha_r
        sBIT_TrueAlphaG = CHUNK_INFO_STATE.sbit_true_alpha_g
        sBIT_TrueAlphaB = CHUNK_INFO_STATE.sbit_true_alpha_b
        sBIT_TrueAlpha = CHUNK_INFO_STATE.sbit_true_alpha

    if sync_all or "gifg" in sections:
        gIFgM = CHUNK_INFO_STATE.gifg_disposal_method
        gIFgU = CHUNK_INFO_STATE.gifg_user_input_flag
        gIFgT = CHUNK_INFO_STATE.gifg_delay_time

    if sync_all or "gifx" in sections:
        gIFID = CHUNK_INFO_STATE.gifx_application_identifier
        gIFCD = CHUNK_INFO_STATE.gifx_authentication_code
        gIFDT = CHUNK_INFO_STATE.gifx_application_data

    if sync_all or "ster" in sections:
        sTER = CHUNK_INFO_STATE.ster_mode

    if sync_all or "text" in sections:
        tEXt_Key_List = list(CHUNK_INFO_STATE.text_key_list)
        tEXt_Str_List = list(CHUNK_INFO_STATE.text_str_list)
        tEXt_Key = CHUNK_INFO_STATE.text_key
        tEXt_Text = CHUNK_INFO_STATE.text_text

    if sync_all or "ztxt" in sections:
        zTXt_Key_List = list(CHUNK_INFO_STATE.ztxt_key_list)
        zTXt_Str_List = list(CHUNK_INFO_STATE.ztxt_str_list)
        zTXt_Key = CHUNK_INFO_STATE.ztxt_key
        zTXt_Text = CHUNK_INFO_STATE.ztxt_text

    if sync_all or "itxt" in sections:
        iTXt_Key_List = list(CHUNK_INFO_STATE.itxt_key_list)
        iTXt_String_List = list(CHUNK_INFO_STATE.itxt_string_list)
        iTXt_Key = CHUNK_INFO_STATE.itxt_key
        iTXt_String = CHUNK_INFO_STATE.itxt_string

    if sync_all or "exif" in sections:
        eXIf_endian = CHUNK_INFO_STATE.exif_endian


def Sync_Chunk_Info_State_From_Legacy(section=None):
    sections = {section} if isinstance(section, str) else set(section or ())
    sync_all = section is None

    if sync_all or "ihdr" in sections:
        CHUNK_INFO_STATE.set_ihdr_legacy(
            height=IHDR_Height,
            width=IHDR_Width,
            depth=IHDR_Depht,
            color=IHDR_Color,
            method=IHDR_Method,
            filter_method=IHDR_Filter,
            interlace=IHDR_Interlace,
        )

    if sync_all or "plte" in sections:
        CHUNK_INFO_STATE.set_plte_legacy(PLTE_R, PLTE_G, PLTE_B)

    if sync_all or "splt" in sections:
        CHUNK_INFO_STATE.set_splt_legacy(
            names=sPLT_Name,
            depths=sPLT_Depht,
            red=sPLT_Red,
            green=sPLT_Green,
            blue=sPLT_Blue,
            alpha=sPLT_Alpha,
            freq=sPLT_Freq,
        )


def Chunk_Report_Color(color, value):
    return Candy("Color", color, value)


def Chunk_Report_Emoji(name):
    return Candy("Emoj", name)


####
def GetInfo(Chunk, data, Dummy=False):
    ToFix = []
    globals().update(
        iCCP_Name="",
        iTXt_String="",
        iTXt_Key="",
        zTXt_Key="",
        tEXt_Text="",
        tEXt_Key="",
    )
    zTXt_String = ""
    Name = ""
    lastnm = ""

    def set_legacy(**values):
        globals().update(values)

    def print_ok():
        PRINT(
            "\n-Errors Check :"
            + Candy("Color", "green", " OK ")
            + Candy("Emoj", "good")
        )

    def checkpoint_or_ok(check_data=None):
        if len(ToFix) > 0:
            if check_data is None:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)
            else:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix, check_data)
        else:
            print_ok()

    def checkpoint_only(check_data=None):
        if len(ToFix) > 0:
            if check_data is None:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix)
            else:
                CheckPoint(True, False, "GetInfo", Chunk, ToFix, check_data)

    Candy("Title", "Getting infos about:", Candy("Color", "white", str(Chunk)))

    def handle_png():
        Candy(
            "Cowsay", " Well ..That's a start ..At least it looks like a png.", "good"
        )

    def handle_ihdr():
        IHDR_Info = chunk_info.parse_ihdr(data, max_resolution=Max_Res())
        CHUNK_INFO_STATE.apply_ihdr(IHDR_Info)
        Sync_Chunk_Info_Legacy_State("ihdr")

        chunk_report.render_ihdr(IHDR_Info, PRINT, Chunk_Report_Color)

        ToFix.extend(IHDR_Info.fixes)
        checkpoint_or_ok()

    def handle_idat():
        IDAT_Info = CHUNK_INFO_STATE.next_idat(data, Raw_Length)
        CHUNK_INFO_STATE.apply_idat(IDAT_Info)
        Sync_Chunk_Info_Legacy_State("idat")
        chunk_report.render_idat(IDAT_Info, PRINT, Chunk_Report_Color)
        ToFix.extend(IDAT_Info.fixes)
        checkpoint_only()

    def handle_phys():
        pHYs_Info = chunk_info.parse_phys(data)
        set_legacy(pHYs_Y=pHYs_Info.y, pHYs_X=pHYs_Info.x, pHYs_Unit=pHYs_Info.unit)

        chunk_report.render_phys(pHYs_Info, PRINT, Chunk_Report_Color, Chunk_Report_Emoji)

        ToFix.extend(pHYs_Info.fixes)
        checkpoint_or_ok()

    def handle_bkgd():
        bKGD_Info = chunk_info.parse_bkgd(data, IHDR_Color, IHDR_Depht)
        set_legacy(
            bKGD_Gray=bKGD_Info.gray,
            bKGD_Red=bKGD_Info.red,
            bKGD_Green=bKGD_Info.green,
            bKGD_Blue=bKGD_Info.blue,
            bKGD_Index=bKGD_Info.index,
        )

        chunk_report.render_bkgd(bKGD_Info, PRINT, Chunk_Report_Color)

        ToFix.extend(bKGD_Info.fixes)
        checkpoint_or_ok()

    def handle_plte():
        PLTE_Info = chunk_info.parse_plte(data, IHDR_Depht)
        CHUNK_INFO_STATE.apply_plte(PLTE_Info)
        Sync_Chunk_Info_Legacy_State("plte")

        chunk_report.render_plte(PLTE_R, PLTE_G, PLTE_B, PRINT, Chunk_Report_Color)

        ToFix.extend(PLTE_Info.fixes)
        checkpoint_or_ok()

    def handle_splt():
        sPLT_Info = chunk_info.parse_splt(
            data,
            previous_names=tuple(CHUNK_INFO_STATE.splt_name),
        )
        CHUNK_INFO_STATE.apply_splt(sPLT_Info)
        Sync_Chunk_Info_Legacy_State("splt")

        chunk_report.render_splt(
            sPLT_Info,
            sPLT_Red,
            sPLT_Green,
            sPLT_Blue,
            sPLT_Alpha,
            sPLT_Freq,
            PRINT,
            Chunk_Report_Color,
        )

        ToFix.extend(sPLT_Info.fixes)
        checkpoint_or_ok(data)

    def handle_hist():
        hIST_Info = chunk_info.parse_hist(
            data,
            has_plte=b"PLTE" in Chunks_History,
            has_splt=b"sPLT" in Chunks_History,
            plte_entries=CHUNK_INFO_STATE.plte_entry_count(),
            splt_entries=CHUNK_INFO_STATE.splt_entry_count(),
        )
        set_legacy(hIST=list(hIST_Info.entries))
        chunk_report.render_hist(hIST, PRINT, Chunk_Report_Color)

        ToFix.extend(hIST_Info.fixes)
        checkpoint_or_ok(data)

    def handle_time():
        tIME_Current_Year = datetime.now().year
        tIME_Info = chunk_info.parse_time(data, current_year=tIME_Current_Year)
        set_legacy(
            tIME_Yr=tIME_Info.year,
            tIME_Mth=tIME_Info.month,
            tIME_Day=tIME_Info.day,
            tIME_Hr=tIME_Info.hour,
            tIME_Min=tIME_Info.minute,
            tIME_Sec=tIME_Info.second,
        )
        chunk_report.render_time(
            tIME_Info,
            tIME_Current_Year,
            PRINT,
            Chunk_Report_Color,
            Chunk_Report_Emoji,
        )
        ToFix.extend(tIME_Info.fixes)
        checkpoint_or_ok()

    def handle_trns():
        tRNS_Info = chunk_info.parse_trns(
            data,
            IHDR_Color,
            has_plte=b"PLTE" in Chunks_History,
            has_splt=b"sPLT" in Chunks_History,
            plte_entries=len(CHUNK_INFO_STATE.plte_r),
            splt_entries=len(CHUNK_INFO_STATE.splt_red),
        )
        set_legacy(
            tRNS_Gray=tRNS_Info.gray,
            tRNS_TrueR=tRNS_Info.true_r,
            tRNS_TrueG=tRNS_Info.true_g,
            tRNS_TrueB=tRNS_Info.true_b,
        )
        CHUNK_INFO_STATE.apply_trns(tRNS_Info)
        Sync_Chunk_Info_Legacy_State("trns")

        chunk_report.render_trns(tRNS_Info, PRINT, Chunk_Report_Color)

        ToFix.extend(tRNS_Info.fixes)
        checkpoint_or_ok()

    def handle_srgb():
        sRGB_Info = chunk_info.parse_srgb(data, has_chrm=b"cHRM" in Chunks_History)
        set_legacy(sRGB=sRGB_Info.value)
        chunk_report.render_srgb(
            sRGB_Info,
            b"cHRM" in Chunks_History,
            PRINT,
            Chunk_Report_Color,
            Chunk_Report_Emoji,
        )
        ToFix.extend(sRGB_Info.fixes)

        checkpoint_or_ok()

    def handle_chrm():
        cHRM_Info = chunk_info.parse_chrm(
            data,
            has_srgb_or_iccp=b"sRGB" in Chunks_History or b"iCCP" in Chunks_History,
        )
        CHUNK_INFO_STATE.apply_chrm(cHRM_Info)
        Sync_Chunk_Info_Legacy_State("chrm")
        chunk_report.render_chrm(
            cHRM_Info,
            b"sRGB" in Chunks_History or b"iCCP" in Chunks_History,
            PRINT,
            Chunk_Report_Color,
            Chunk_Report_Emoji,
        )
        ToFix.extend(cHRM_Info.fixes)

        checkpoint_or_ok()

    def handle_gama():
        gAMA_Info = chunk_info.parse_gama(data)
        set_legacy(gAMA=gAMA_Info.value)
        chunk_report.render_gama(gAMA_Info, PRINT, Chunk_Report_Color)
        ToFix.extend(gAMA_Info.fixes)
        checkpoint_only()

    def handle_iccp():
        iCCP_Info = chunk_info.parse_iccp(
            data,
            raw_length_hex=Orig_CL,
            has_chrm=b"cHRM" in Chunks_History,
        )
        CHUNK_INFO_STATE.apply_iccp(iCCP_Info)
        Sync_Chunk_Info_Legacy_State("iccp")

        chunk_report.render_iccp(
            iCCP_Info,
            b"cHRM" in Chunks_History,
            PRINT,
            Chunk_Report_Color,
            Chunk_Report_Emoji,
        )
        ToFix.extend(iCCP_Info.fixes)

        checkpoint_or_ok()

    def handle_sbit():
        sBIT_Info = chunk_info.parse_sbit(data, IHDR_Color, IHDR_Depht)
        CHUNK_INFO_STATE.apply_sbit(sBIT_Info)
        Sync_Chunk_Info_Legacy_State("sbit")

        chunk_report.render_sbit(sBIT_Info, PRINT, Chunk_Report_Color)

        ToFix.extend(sBIT_Info.fixes)
        checkpoint_or_ok()

    def handle_offs():
        oFFs_Info = chunk_info.parse_offs(data)
        CHUNK_INFO_STATE.apply_offs(oFFs_Info)

        chunk_report.render_offs(oFFs_Info, PRINT, Chunk_Report_Color, Chunk_Report_Emoji)
        ToFix.extend(oFFs_Info.fixes)
        checkpoint_or_ok()

    def handle_pcal():
        pCAL_Info = chunk_info.parse_pcal(data)
        CHUNK_INFO_STATE.apply_pcal(pCAL_Info)
        Sync_Chunk_Info_Legacy_State("pcal")

        chunk_report.render_pcal(pCAL_Info, PRINT, Chunk_Report_Color)

        ToFix.extend(pCAL_Info.fixes)
        checkpoint_only()

    def handle_gifg():
        gIFg_Info = chunk_info.parse_gifg(data)
        CHUNK_INFO_STATE.apply_gifg(gIFg_Info)
        Sync_Chunk_Info_Legacy_State("gifg")

        chunk_report.render_gifg(gIFg_Info, PRINT, Chunk_Report_Color)
        ToFix.extend(gIFg_Info.fixes)

        checkpoint_only()

    def handle_gifx():
        gIFx_Info = chunk_info.parse_gifx(data)
        CHUNK_INFO_STATE.apply_gifx(gIFx_Info)
        Sync_Chunk_Info_Legacy_State("gifx")

        chunk_report.render_gifx(gIFx_Info, PRINT, Chunk_Report_Color)
        ToFix.extend(gIFx_Info.fixes)

        checkpoint_only()

    def handle_ster():
        sTER_Info = chunk_info.parse_ster(data)
        CHUNK_INFO_STATE.apply_ster(sTER_Info)
        Sync_Chunk_Info_Legacy_State("ster")

        chunk_report.render_ster(sTER_Info, PRINT, Chunk_Report_Color)
        ToFix.extend(sTER_Info.fixes)

        checkpoint_only()

    def handle_text():
        tEXt_Info = chunk_info.parse_text(data)
        CHUNK_INFO_STATE.apply_text(tEXt_Info)
        Sync_Chunk_Info_Legacy_State("text")

        chunk_report.render_text(tEXt_Info, PRINT, Chunk_Report_Color)

        ToFix.extend(tEXt_Info.fixes)
        checkpoint_only()

    def handle_ztxt():
        zTXt_Info = chunk_info.parse_ztxt(data)
        CHUNK_INFO_STATE.apply_ztxt(zTXt_Info)
        Sync_Chunk_Info_Legacy_State("ztxt")

        chunk_report.render_ztxt(zTXt_Info, PRINT, Chunk_Report_Color)

        ToFix.extend(zTXt_Info.fixes)
        checkpoint_only()

    def handle_itxt():
        iTXt_Info = chunk_info.parse_itxt(data)
        CHUNK_INFO_STATE.apply_itxt(iTXt_Info)
        Sync_Chunk_Info_Legacy_State("itxt")

        chunk_report.render_itxt(iTXt_Info, PRINT, Chunk_Report_Color)

        ToFix.extend(iTXt_Info.fixes)
        checkpoint_only()

    def handle_exif():
        eXIf_Info = chunk_info.parse_exif(data)
        CHUNK_INFO_STATE.apply_exif(eXIf_Info)
        Sync_Chunk_Info_Legacy_State("exif")

        chunk_report.render_exif(eXIf_Info, PRINT, Chunk_Report_Color)
        ToFix.extend(eXIf_Info.fixes)

        checkpoint_only()

    def handle_spal():
        spAL_Info = chunk_info.parse_spal(data)
        chunk_report.render_spal(spAL_Info, PRINT, Chunk_Report_Color)
        ToFix.extend(spAL_Info.fixes)

        checkpoint_only()

    handlers = {
        b"PNG": handle_png,
        b"IHDR": handle_ihdr,
        b"IDAT": handle_idat,
        b"pHYs": handle_phys,
        b"bKGD": handle_bkgd,
        b"PLTE": handle_plte,
        b"sPLT": handle_splt,
        b"hIST": handle_hist,
        b"tIME": handle_time,
        b"tRNS": handle_trns,
        b"sRGB": handle_srgb,
        b"cHRM": handle_chrm,
        b"gAMA": handle_gama,
        b"iCCP": handle_iccp,
        b"sBIT": handle_sbit,
        b"oFFs": handle_offs,
        b"pCAL": handle_pcal,
        b"gIFg": handle_gifg,
        b"gIFx": handle_gifx,
        b"sTER": handle_ster,
        b"tEXt": handle_text,
        b"zTXt": handle_ztxt,
        b"iTXt": handle_itxt,
        b"eXIf": handle_exif,
        b"spAL": handle_spal,
    }

    handler = handlers.get(Chunk)
    if handler is not None:
        handler()

    if Chunk in PRIVATE_CHUNKS:
        PRINT("-Private Chunk")

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Chunk not in ALLCHUNKS:

        PRINT("-%s" % Candy("Color", "red", "Unknown Chunk."))

        if len(ToFix) > 0:
            CheckPoint(True, False, "GetInfo", Chunk, ToFix)

    if Dummy is False:
        CheckChunkOrder(Chunk, "TheGoodPlace")
    return


####


def YouShallPass(Chunk, data):
    def passes(info):
        return len(info.fixes) == 0

    def validate_bkgd():
        Sync_Chunk_Info_State_From_Legacy("ihdr")
        return passes(
            chunk_info.parse_bkgd(data, CHUNK_INFO_STATE.ihdr_color, CHUNK_INFO_STATE.ihdr_depth)
        )

    def validate_plte():
        Sync_Chunk_Info_State_From_Legacy("ihdr")
        return passes(chunk_info.parse_plte(data, CHUNK_INFO_STATE.ihdr_depth))

    def validate_splt():
        Sync_Chunk_Info_State_From_Legacy("splt")
        return passes(
            chunk_info.parse_splt(
                data,
                previous_names=tuple(CHUNK_INFO_STATE.splt_name),
            )
        )

    def validate_hist():
        Sync_Chunk_Info_State_From_Legacy(("plte", "splt"))
        return passes(
            chunk_info.parse_hist(
                data,
                has_plte=b"PLTE" in Chunks_History,
                has_splt=b"sPLT" in Chunks_History,
                plte_entries=CHUNK_INFO_STATE.plte_entry_count(),
                splt_entries=CHUNK_INFO_STATE.splt_entry_count(),
            )
        )

    def validate_trns():
        Sync_Chunk_Info_State_From_Legacy(("ihdr", "plte", "splt"))
        return passes(
            chunk_info.parse_trns(
                data,
                CHUNK_INFO_STATE.ihdr_color,
                has_plte=b"PLTE" in Chunks_History,
                has_splt=b"sPLT" in Chunks_History,
                plte_entries=len(CHUNK_INFO_STATE.plte_r),
                splt_entries=len(CHUNK_INFO_STATE.splt_red),
            )
        )

    def validate_sbit():
        Sync_Chunk_Info_State_From_Legacy("ihdr")
        return passes(
            chunk_info.parse_sbit(
                data,
                CHUNK_INFO_STATE.ihdr_color,
                CHUNK_INFO_STATE.ihdr_depth,
            )
        )

    validators = {
        b"IHDR": lambda: passes(chunk_info.parse_ihdr(data)),
        b"pHYs": lambda: passes(chunk_info.parse_phys(data)),
        b"bKGD": validate_bkgd,
        b"PLTE": validate_plte,
        b"sPLT": validate_splt,
        b"hIST": validate_hist,
        b"tIME": lambda: passes(chunk_info.parse_time(data)),
        b"tRNS": validate_trns,
        b"sRGB": lambda: passes(
            chunk_info.parse_srgb(data, has_chrm=b"cHRM" in Chunks_History)
        ),
        b"cHRM": lambda: passes(
            chunk_info.parse_chrm(
                data,
                has_srgb_or_iccp=b"sRGB" in Chunks_History or b"iCCP" in Chunks_History,
            )
        ),
        b"gAMA": lambda: passes(chunk_info.parse_gama(data)),
        b"iCCP": lambda: passes(
            chunk_info.parse_iccp(
                data,
                raw_length_hex=Orig_CL,
                has_chrm=b"cHRM" in Chunks_History,
            )
        ),
        b"sBIT": validate_sbit,
        b"oFFs": lambda: passes(chunk_info.parse_offs(data)),
        b"pCAL": lambda: passes(chunk_info.parse_pcal(data)),
        b"gIFg": lambda: passes(chunk_info.parse_gifg(data)),
        b"gIFx": lambda: passes(chunk_info.parse_gifx(data)),
        b"sTER": lambda: passes(chunk_info.parse_ster(data)),
        b"tEXt": lambda: passes(chunk_info.parse_text(data)),
        b"zTXt": lambda: passes(chunk_info.parse_ztxt(data)),
        b"iTXt": lambda: passes(chunk_info.parse_itxt(data)),
        b"eXIf": lambda: passes(chunk_info.parse_exif(data)),
    }

    validator = validators.get(Chunk)
    if validator is not None:
        return validator()

    return True


def Sync_Chunk_Scanner_Legacy_State(scan):
    globals().update(scan.legacy_globals())


def ChunkbyChunk(offset):
    ChunkScan = chunk_scanner.scan_legacy_chunk(DATA_BYTES, offset)
    Sync_Chunk_Scanner_Legacy_State(ChunkScan)

    Candy("Title", "Chunk Infos:")
    chunk_report.render_legacy_chunk_window(
        ChunkScan.window,
        PRINT,
        lambda color, value: Candy("Color", color, value),
    )

    return


def GroundhogDay(NewDay):

    Relaunch = runtime_state.groundhogday_relaunch_args(sys.argv, NewDay)
    sys.argv[:] = Relaunch.argv
    if DEBUG is True:
        PRINT("sys.executable was %s"% sys.executable)
        PRINT("argv is %s"% Relaunch.strargs)
        PRINT("rebooting chunklate")
        if PAUSEDEBUG is True:
            Pause("Pause:Reboot")
    os.execv(sys.executable, Relaunch.exec_args)


def Chunklate(sec):

    for line in ui.render_chunklate_banner(os.name, random.randint):
        print(line)

    if PAUSE is True:
        time.sleep(sec)


def Minibar(Indication=""):
    global CharPos
    global GoBack
    global Loading_txt
    global Loading_sep
    Step = ui.minibar_step(Indication, Loading_txt, CharPos, GoBack, MAXCHAR)
    Loading_txt = Step.loading_text
    CharPos = Step.char_pos
    GoBack = Step.go_back
    if Step.should_print:
        print(Loading_txt, end="\r")


def Loadingbar(fishs, fishsize, loop, build):

    global ThksForTheFish
    global FishPos
    global LenFishList


    if build:
#        Pause("build")
        BuiltLoadingbar = ui.build_loadingbar_frames(
            fishs,
            fishsize,
            int(os.get_terminal_size(0)[0]),
        )
        ThksForTheFish = BuiltLoadingbar.frames
        LenFishList = BuiltLoadingbar.len_fish_list
        FishPos = BuiltLoadingbar.fish_pos
    else:
#        Pause("pas build")
        Progress = ui.loadingbar_progress(
            fishs,
            fishsize,
            loop,
            ThksForTheFish,
            FishPos,
            LenFishList,
        )
        FishPos = Progress.fish_pos
        print(Progress.text, end="\r")


def Sumform(waitforit, switch):
    return output.summary_separator(waitforit, switch, MAXCHAR)


def Summarise(infos, Summary_Footer=False):
    global Summary_Header
    global SideNotes

    sep = "\n\n『" + Sample_Name + " :』\n"
    title = Sumform("▇ ▆ =|C|h|u|n|k|l|a|t|e| |S|u|m|m|a|r|y|= ▆ ▇", True)
    eof = Sumform("_,-=|S|u|m|m|a|r|y| |E|n|d|=-,_", False)
    infos = output.summary_body(infos, SideNotes)

    filename = output.summary_path(FILE_Origin, FILE_DIR)
    print(Candy("Color", "green", "-Saving Summary : "), filename)
    with open(filename, "a+") as f:

        if Summary_Header is True:
            f.write(title)
            Summary_Header = False

        if infos is not None:
            f.write(sep)
            f.write(infos)

        if Summary_Footer is True:
            f.write(output.render_summary_footer(globals(), eof))
    SideNotes = []

def Legacy_UI_Runtime():
    return ui_runtime.LegacyUiRuntime(
        emit=PRINT,
        random_int=random.randint,
        max_columns=MAXCHAR,
        no_dialogue=NODIALOGUE,
        use_color=os.name != "nt",
        pause_dialogue_enabled=PAUSEDIALOGUE,
        pause_dialogue=lambda: prompts.pause_dialogue(input, PAUSEDIALOGUE),
    )


def Candy(mode, arg, data=None):
    return Legacy_UI_Runtime().candy(mode, arg, data)


def SplitDigits(lst):
    return sorting.natural_sort_key(lst)


def DigDigits(dig):
    return sorting.digit_or_text(dig)


def ChunkStory(action, Chunk, start, end, chuck_length):
    global Chunks_History
    global Chunks_History_Index

    if action == "add":
        chunk_story.add(Chunks_History, Chunks_History_Index, Chunk, start, end, chuck_length)
    elif action == "del":
        try:
            chunk_story.delete_legacy(Chunks_History, Chunks_History_Index, Chunk)
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))
                if PAUSEDEBUG is True:
                    Pause("Pause:Chunkstory")


def TheEnd():
    if DEBUG is True:
        for line in output.the_end_debug_lines(
            Chunks_History_Index,
            idatcounter,
            Chunks_History,
            IDAT_Bytes_Len,
        ):
            PRINT(line)
    if PAUSEDEBUG is True:
        Pause("ThenEnd debug")
    Summarise(None, True)
    Chunklate(0)
    sys.exit(0)


def ToBitstory(bytenbr):
    global Bytes_History
    history.append_byte_history(Bytes_History, bytenbr)


def stderr_redirector(stream):
    return stdio.stderr_redirector(stream)

def Product(chunk_data,color_type,gen_nbr=None):
     yield from specs.iter_product_values(chunk_data, color_type)


class Tk_Gen_Scale_Plte:

    def __init__(self, master=None, label='', value=0,to=None,from_=None,ln=None,afn=None,bfn=None,h=None,w=None,nbr=None):
        widget = palette_ui.create_palette_scale(
            tkinter_module=tkinter,
            master=master,
            label=label,
            value=value,
            from_=from_,
            to=to,
            length=ln,
            command=lambda event: Tk_ImgUpdate_Plte(event,nbr=nbr,bfn=bfn,afn=afn,h=h,w=w),
            grid_options={"padx": 10, "pady": 5},
        )
        self.var = widget.var
        self.s = widget.scale
    def clean(self):
       self.s.destroy()


def Tk_Render_Plte_Preview(wanabyte, w, h):
    global frame_img
    global im, pil_image, tk_image

    im, pil_image, tk_image = palette_ui.render_preview_label(
        wanabyte,
        frame_img,
        w,
        h,
        cv2_module=cv2,
        numpy_module=np,
        image_module=Image,
        image_tk_module=ImageTk,
        tkinter_module=tkinter,
    )


def Sync_Palette_Legacy_State():
    global Plte_Blst, slider_list, wanabyte

    if palette_state is not None:
        Plte_Blst = palette_state.values
        slider_list = palette_state.sliders
        wanabyte = palette_state.wanabyte


def Tk_ImgUpdate_Plte(event,nbr=None,bfn=None,afn=None,w=None,h=None):
    global Plte_Blst
    global palette_state
    global window,tk_image,frame_img,pil_image,im,wanabyte

    if palette_state is not None:
        wanabyte = palette_ui.update_palette_state_value(
            palette_state,
            index=int(nbr),
            raw_value=event,
            before=bfn,
            after=afn,
        )
        Sync_Palette_Legacy_State()
    else:
        palette.set_palette_value(Plte_Blst, int(nbr), event)
        wanabyte = palette.build_palette_png(bfn, Plte_Blst, afn)

    Tk_Render_Plte_Preview(wanabyte, w, h)

#    if DEBUG:
#        PRINT("PlteId : %s Value : %s Plte_Blst[PlteId]:%s bvalue: %s Lnx_New : %s"%(str(nbr),str(event),str(Plte_Blst[nbr]),str(bvalue),str(Lnx_New)))

def Tk_X11_Randomize_Plte(bfn=None,afn=None,w=None,h=None):
    global Plte_Blst
    global palette_state
    global window,tk_image,frame_img,pil_image,im,wanabyte

    rnd_x11 = random.sample(X11_Colors,len(X11_Colors))


    if palette_state is not None:
        wanabyte = palette_ui.apply_palette_state_colors(
            palette_state,
            colors=rnd_x11,
            before=bfn,
            after=afn,
        )
        Sync_Palette_Legacy_State()
    else:
        palette_ui.apply_color_table(Plte_Blst, slider_list, rnd_x11)
        wanabyte = palette.build_palette_png(bfn, Plte_Blst, afn)

    Tk_Render_Plte_Preview(wanabyte, w, h)

def Tk_X11_Plte(bfn=None,afn=None,w=None,h=None):
    global Plte_Blst
    global palette_state
    global window,tk_image,frame_img,pil_image,im,wanabyte


    if palette_state is not None:
        wanabyte = palette_ui.apply_palette_state_colors(
            palette_state,
            colors=X11_Colors,
            before=bfn,
            after=afn,
        )
        Sync_Palette_Legacy_State()
    else:
        palette_ui.apply_color_table(Plte_Blst, slider_list, X11_Colors)
        wanabyte = palette.build_palette_png(bfn, Plte_Blst, afn)

    Tk_Render_Plte_Preview(wanabyte, w, h)


def Tk_Web_Safe_Randomize_Plte(bfn=None,afn=None,w=None,h=None):
    global Plte_Blst
    global palette_state
    global window,tk_image,frame_img,pil_image,im,wanabyte

    rnd_216 = random.sample(Web_Safe_Colors,len(Web_Safe_Colors))


    if palette_state is not None:
        wanabyte = palette_ui.apply_palette_state_colors(
            palette_state,
            colors=rnd_216,
            before=bfn,
            after=afn,
        )
        Sync_Palette_Legacy_State()
    else:
        palette_ui.apply_color_table(Plte_Blst, slider_list, rnd_216)
        wanabyte = palette.build_palette_png(bfn, Plte_Blst, afn)

    Tk_Render_Plte_Preview(wanabyte, w, h)

def Tk_Web_Safe_Plte(bfn=None,afn=None,w=None,h=None):
    global Plte_Blst
    global palette_state
    global window,tk_image,frame_img,pil_image,im,wanabyte


    if palette_state is not None:
        wanabyte = palette_ui.apply_palette_state_colors(
            palette_state,
            colors=Web_Safe_Colors,
            before=bfn,
            after=afn,
        )
        Sync_Palette_Legacy_State()
    else:
        palette_ui.apply_color_table(Plte_Blst, slider_list, Web_Safe_Colors)
        wanabyte = palette.build_palette_png(bfn, Plte_Blst, afn)

    Tk_Render_Plte_Preview(wanabyte, w, h)


def Tk_Randomize_Plte(bfn=None,afn=None,w=None,h=None):
    global Plte_Blst
    global palette_state
    global window,tk_image,frame_img,pil_image,im,wanabyte

    if palette_state is not None:
        wanabyte = palette_ui.randomize_palette_state(
            palette_state,
            random_int=random.randint,
            before=bfn,
            after=afn,
        )
        Sync_Palette_Legacy_State()
    else:
        palette_ui.random_palette_values(Plte_Blst, slider_list, random.randint)
        wanabyte = palette.build_palette_png(bfn, Plte_Blst, afn)

    Tk_Render_Plte_Preview(wanabyte, w, h)

def Tk_update_scrollregion_Plte(event):
    global canvas_slider
    canvas_slider.configure(scrollregion=canvas_slider.bbox("all"))

def Tk_Save_Plte(Tkwin,Cancel,ChunkLength,DataOffset,FromError,wanabyte):
    global slider_list
    global palette_state

    active_sliders = palette_state.sliders if palette_state is not None else slider_list
    active_values = palette_state.values if palette_state is not None else Plte_Blst
    active_wanabyte = palette_state.wanabyte if palette_state is not None else wanabyte

    for slider in active_sliders:
         slider.clean()

    Tkwin.destroy()
    Tkwin.quit()

    CheckpointCall = palette_ui.save_checkpoint(
        cancel=Cancel,
        palette_values=active_values,
        wanabyte=active_wanabyte,
        chunk_length=ChunkLength,
        data_offset=DataOffset,
        from_error=FromError,
    )
    return CheckPoint(
        CheckpointCall.error,
        CheckpointCall.fixed,
        CheckpointCall.function,
        CheckpointCall.chunk,
        list(CheckpointCall.infos),
        *CheckpointCall.toolkit,
    )


def Guess_Palettes_Nbr(bfn,afn):
    global SideNotes

    Hashs_Lst = []
    PLTE_Guess_Nbr = None
    palette_values = []
    f = io.BytesIO()
    for n,colorx in enumerate(X11_Colors):
        palette_values.append(int(colorx, 16))
        wanabyte = palette.build_palette_png(bfn, palette_values, afn)
        f = io.BytesIO()

        with stderr_redirector(f):
             try:
                 im = cv2.imdecode(np.frombuffer(wanabyte, np.uint8), -1)
             except Exception as e:
                 pass
        result = "{0}".format(f.getvalue().decode("utf-8"))
        if any(s in result for s in LIBPNG_ERR):
             print("-Error Guess_Palettes_Nbr():",result)
#             return()
             TheEnd()
#        name, dir = Naming(FILE_Origin)
#        tmpname =  dir+"/"+"BF-TST-"+str(datetime.now().strftime('-%y%m%d%H%M%S-'))+name
#        with open(tmpname, "wb") as f:
#                 f.write(wanabyte)
#        print("-Saved here:",tmpname)

        try:
            pil_image = Image.fromarray(im)
        except Exception as e:
           Betterror(e, inspect.stack()[0][3])
           print("-Error Guess_Palettes_Nbr():",e)
           TheEnd()

#        current_hash = imagehash.colorhash(pil_image)
#        current_hash = imagehash.dhash(pil_image)
#        current_hash = imagehash.average_hash(pil_image)
        current_hash = imagehash.phash(pil_image)
        Hashs_Lst.append(current_hash)
        if len(Hashs_Lst) > 1:
             distance_last = Hashs_Lst[-2] - Hashs_Lst[-1]
             distance_orig = Hashs_Lst[0] - Hashs_Lst[-1]
#             print("-Palette:%s len(hlst):last hash:%s current hash:%s distance(last-current):%s distance(first-current):%s"%(n,Hashs_Lst[-2],Hashs_Lst[-1],distance_last,distance_orig))
#             if current_hash in Hashs_Lst:
#                 print("        current hash %s already in Hashs_Lst"%(current_hash))
             if distance_last != 0:
                     PLTE_Guess_Nbr = n

    if PLTE_Guess_Nbr:
        PRINT("-PLTE palettes number estimation: %s"% Candy("Color", "green", str(PLTE_Guess_Nbr)))
        SideNotes.append("-PLTE palettes number estimation: %s"%str(PLTE_Guess_Nbr))
        return(PLTE_Guess_Nbr)
    else:
        PRINT(Candy("Color", "yellow", "Warning:%s")%"Could not estimate palette number.")
        SideNotes.append("Warning:Could not estimate palette number.Returning Max Palettes number according to IHDR Depht")
        return(2 ** int(IHDR_Depht)-1)



def Tk_Manual_Plte(
    File,
    ChunkName,
    ChunkLength,
    DataOffset,
    FromError
):
    global SideNotes
    global Plte_Blst
    global palette_state
    global window,tk_image,frame_img,pil_image,im,canvas_slider,slider_list,wanabyte

    Candy("Title", "Manually Bruteforcing Chunk Datas:")

    try:
        ChunkName = ChunkName.encode(errors="ignore")
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        if DEBUG is True:
            PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))


    PaletteSession = palette_runtime.create_manual_palette_session(
        data_hex=DATAX,
        data_offset=DataOffset,
        chunk_length=ChunkLength,
        chunk_name=ChunkName,
        guess_palette_count=Guess_Palettes_Nbr,
    )
    Before_New = PaletteSession.before
    After_New = PaletteSession.after
    wanabyte = PaletteSession.wanabyte
    Palette_nbr = PaletteSession.palette_count

    palette_state = PaletteSession.state
    Plte_Blst = palette_state.values

    if DEBUG is True:
        fullnewdatax = palette_runtime.manual_palette_full_new_data(PaletteSession)
        PRINT("File:%s"% File)
        PRINT("ChunkName:%s"% ChunkName)
        PRINT("DataOffset:%s"% DataOffset)
        PRINT("ChunkLength:%s"% ChunkLength)
        PRINT("Before_New:%s"% Before_New.hex())
        PRINT("After_New:%s"% After_New[:20].hex())
        PRINT("fullnewdatax:%s"%fullnewdatax.hex())
        PRINT("Palette_nbr:%s"%Palette_nbr)


    im = cv2.imdecode(np.frombuffer(wanabyte, np.uint8), -1)
    pil_image = Image.fromarray(im)

    window = palette_ui.create_palette_editor_window(
        tkinter_module=tkinter,
        title="PLTE Editor:%s"%FILE_Origin,
    )

    layout = palette_ui.build_editor_layout(window.winfo_screenwidth(), pil_image.size)
    basewidth = layout.basewidth
    hsize = layout.hsize

    editor_frames = palette_ui.create_palette_editor_frames(
        tkinter_module=tkinter,
        window=window,
        layout=layout,
    )
    frame_img = editor_frames.img

    Tk_Render_Plte_Preview(wanabyte, basewidth, hsize)

    frame_slider = editor_frames.slider
    frame_action = editor_frames.action

    action_buttons = palette_ui.create_palette_action_buttons(
        tkinter_module=tkinter,
        master=frame_action,
        specs=palette_ui.build_palette_action_button_specs(
            web_safe=lambda: Tk_Web_Safe_Plte(bfn=Before_New,afn=After_New,h=hsize,w=basewidth),
            web_random=lambda: Tk_Web_Safe_Randomize_Plte(bfn=Before_New,afn=After_New,h=hsize,w=basewidth),
            x11=lambda: Tk_X11_Plte(bfn=Before_New,afn=After_New,h=hsize,w=basewidth),
            x11_random=lambda: Tk_X11_Randomize_Plte(bfn=Before_New,afn=After_New,h=hsize,w=basewidth),
            randomize=lambda: Tk_Randomize_Plte(bfn=Before_New,afn=After_New,h=hsize,w=basewidth),
            save=lambda: Tk_Save_Plte(window,False,ChunkLength,DataOffset,FromError,wanabyte),
            cancel=lambda: Tk_Save_Plte(window,True,ChunkLength,DataOffset,FromError,wanabyte),
        ),
        grid_options={"padx": 10, "pady": 5},
    )
    x216_btn = action_buttons["x216_btn"]
    random_web_btn = action_buttons["random_web_btn"]
    x11_btn = action_buttons["x11_btn"]
    random_classic_btn = action_buttons["random_classic_btn"]
    random_btn = action_buttons["random_btn"]
    save_btn = action_buttons["save_btn"]
    cancel_btn = action_buttons["cancel_btn"]


    slider_canvas = palette_ui.create_palette_slider_canvas(
        tkinter_module=tkinter,
        master=frame_slider,
        height=hsize,
        width=layout.canvas_width,
        canvas_grid_options={"row": 0, "column": 1, "padx": 10, "pady": 5},
        scrollbar_grid_options={"row": 0, "column": 0, "sticky": "ns"},
    )
    canvas_slider = slider_canvas.canvas
    frame_canvas = slider_canvas.frame
    slider_scroll = slider_canvas.scrollbar

    slider_list = palette_ui.create_palette_sliders(
        palette_count=Palette_nbr,
        scale_factory=Tk_Gen_Scale_Plte,
        master=frame_canvas,
        before=Before_New,
        after=After_New,
        height=hsize,
        width=basewidth,
        slider_length=layout.slider_length,
    )
    palette_ui.set_palette_state_sliders(palette_state, slider_list)
    Sync_Palette_Legacy_State()


    canvas_slider.bind("<Configure>", Tk_update_scrollregion_Plte)
    window.mainloop()


def SmashBruteBrawl(
    File,
    ChunkName,
    ChunkLength,
    DataOffset,
    FromError,
    EditMode="Replace",
    BfMode="Brutus",
    BruteCrc=True,
    BruteLength=True,
    OldCrc=False,
):
    global SideNotes
    global CRASH
    global DIFF
    global TmpImgLst
    global ETA

    Candy("Title", "Attempting Bruteforce To Repair Corrupted Chunk Data:")
    try:
        ChunkName = ChunkName.encode(errors="ignore")
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        if DEBUG is True:
            PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))


    def BuildAttempt(LN, payload_data, crc_data, before, after):
        return bruteforce.prepare_candidate_attempt(
            ChunkName,
            LN,
            payload_data,
            crc_data,
            before,
            after,
            brute_length=BruteLength,
            brute_crc=BruteCrc,
            old_crc=OldCrc,
        )

    def LoadSpec(request):
        return GetSpec(
            ChunkName,
            request.mode,
            **bruteforce.spec_request_kwargs(request),
        )

    def ShowPng(bpng,ndx):
            global DIFF
            global TmpImgLst

            f = io.BytesIO()

            with stderr_redirector(f):
                try:
                    cv2.imdecode(np.frombuffer(bpng, np.uint8), -1)
                except:
                    pass
            result = "{0}".format(f.getvalue().decode("utf-8"))
#            print("Result:",result)
#            print("bryte:",ToBryte)
#            print("bvaluehex:",bvalue.hex())
#            input("hold")
            ViewerCandidate = bruteforce.viewer_candidate_decision(result, LIBPNG_ERR)
            if ViewerCandidate.acceptable:


                with stderr_redirector(f):
                    try:
                         TmpI = Image.open(io.BytesIO(bpng))
                         TmpIW,TmpIH = TmpI.size
                         TmpI.show()
                    except Exception as e:
                         if bruteforce.has_libpng_error(str(e), LIBPNG_ERR):
                             if not TmpI.mode == 'RGB':
                                #print("bvalue:%s fullnewdatax:%s error:%s immode:%s"%(bvalue.hex(),fullnewdatax.hex(),str(e),str(TmpI.mode)),end="\r")
                                TmpI = TmpI.convert('RGB')
                                TmpIW,TmpIH = TmpI.size
                                TmpI.show()
                         elif DEBUG:
                                print("bvalue:%s ndx:%s error:%s immode:%s"%(bvalue.hex(),ndx.hex(),str(e),str(TmpI.mode)),end="\r")
#                         print("bvalue:%s fullnewdatax:%s error:%s immode:%s"%(bvalue.hex(),fullnewdatax.hex(),str(e),str(TmpI.mode)),end="\r")
                PRINT("")
#                bla = cv2.imdecode(np.frombuffer(wanabyte, np.uint8), -1)
#                cv2.imshow('bla',bla)
#                TmpI.show()

                PRINT("-Waiting for Image viewer to launch.")
                bruteforce.wait_for_tmp_png_viewer(psutil.process_iter, time.sleep)

                Candy("Cowsay", "Ah ! Iv got One !", "good")
                TryNumber = bruteforce.viewer_try_number(n)
                PRINT("-Tmp Image Number %s"%str(TryNumber))
                PRINT("-Tmp Image Width: %s"%TmpIW)
                PRINT("-Tmp Image Height: %s"%TmpIH)
                Summarise(
                    bruteforce.viewer_found_summary(
                        TryNumber,
                        TmpIW,
                        TmpIH,
                        datetime.now().strftime('%y-%m-%d:%H:%M:%S'),
                    )
                )
                PRINT("")
                Candy("Cowsay", "Does it looks good or should i keep trying ?", "com")
                try:
#                   Answer = Question(None, True)
                    Answer = decisions.ask_yes_no(
                        lambda prompt: inputimeout(prompt=prompt, timeout=23),
                        "Answer(yes/no) auto answer in 23s:",
                    )
                    Summarise(bruteforce.viewer_user_choice_summary(Answer, TryNumber))
                except EOFError as e:
                    print(e)
                    Candy("Cowsay", "Aouch my head ...Didn't see that one coming..", "bad")
                    Candy("Cowsay", "Please close this terminal and open it again.", "com")
                    Candy("Cowsay", "Then Launch Chunklate again like you did before,", "com")
                    Candy("Cowsay", "But add --crash %s at the end of the argument."%(str(TryNumber)), "com")
                    Candy("Cowsay", "And Everything would be fine i think!", "good")
                    TheEnd()
                except :
                   Answer = False
                   name, dir = Naming(FILE_Origin)

                   PRINT("\n-Skipped No input given within time limit.\n")
                   SaveResult = bruteforce.save_viewer_timeout_image(
                       TmpI.save,
                       dir,
                       name,
                       TmpIW,
                       TmpIH,
                       datetime.now().strftime('-%y%m%d%H%M%S-'),
                       TryNumber,
                   )
                   if SaveResult.saved:
                       Candy("Cowsay", "I took the liberty to save a copy of that image just in case.", "com")
                       PRINT("-Image saved at:%s\n"%SaveResult.path)
                       TmpImgLst.append(SaveResult.path)
                       Summarise(SaveResult.summary)

                   else:
                       Betterror(SaveResult.error, inspect.stack()[0][3])
                       PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", SaveResult.error))
                       Summarise(SaveResult.summary)
                if Answer is True:

                    DIFF = bruteforce.accepted_candidate_diff(DATAX, DataOffset, ndx)
                    return(True)


                else:
                    bruteforce.kill_tmp_png_viewers(psutil.process_iter())
                    Candy("Cowsay", "Ok back to work..", "bad")
                    return(False)

            return(False)





    CNamex_New = hex(int.from_bytes(ChunkName, byteorder="big")).replace("0x", "")

    BrawlState = bruteforce.BruteForceMatchState()
    fullnewdatax = b""
    wanabyte = b""
    TmpSkip = True
    TmpImgLst = []
    result = "bad result"

    def ValidateAttempt(attempt, edit_kind=None, bonus=False):
        nonlocal BrawlState, fullnewdatax, wanabyte

        viewer_ok = True
        if not OldCrc:
            fullnewdatax = attempt.full_new_data
            wanabyte = attempt.png_bytes
            viewer_ok = ShowPng(wanabyte, fullnewdatax)

        applied_attempt = bruteforce.apply_validated_candidate_attempt(
            BrawlState,
            attempt,
            edit_kind,
            bonus=bonus,
            old_crc=OldCrc,
            viewer_ok=viewer_ok,
        )
        if applied_attempt is None:
            return False

        BrawlState = applied_attempt.state
        fullnewdatax = applied_attempt.full_new_data
        wanabyte = applied_attempt.png_bytes
        return True


    bruteforce.register_image_viewers(ImageShow)



    OldCrc = bruteforce.normalize_old_crc(OldCrc)

    RuntimePlan = bruteforce.prepare_runtime_plan(
        BfMode,
        ChunkName,
        PandoraBox,
        LoadSpec,
    )
    BfMode = RuntimePlan.mode
    Sti = RuntimePlan.struct_indexes
    if RuntimePlan.side_note is not None:
        SideNotes.append(RuntimePlan.side_note)

    LengthRange = RuntimePlan.length_range
    maxchunklen = LengthRange.max_length
    minchunklen = LengthRange.min_length
    step = LengthRange.step

    if DEBUG is True:

        max_iter, len_iter, chunklen_spec, chunk_format, chunk_data,color_type = (
            bruteforce.load_iteration_spec(BfMode, Sti, None, LoadSpec)
        )

        PRINT("File:%s"% File)
        PRINT("ChunkName:%s"% ChunkName)
        PRINT("DataOffset:%s"% DataOffset)
        PRINT("ChunkLength:%s"% ChunkLength)
        PRINT("Brute_LvL:%s"% Brute_LvL)
        PRINT("BruteCrc:%s"% BruteCrc)
        PRINT("BruteLength:%s"%BruteLength)
        PRINT("EditMode:%s"% EditMode)
        PRINT("FromError:%s"% FromError)
        PRINT("chunklen_spec:%s"% str(chunklen_spec))
        PRINT("chunk_format:%s"% str(chunk_format))
        PRINT("chunk_data:%s"% str(chunk_data))
        PRINT("max_iter:%s"%max_iter)
        PRINT("maxchunklen:%s"% maxchunklen)
        PRINT("minchunklen:%s"% minchunklen)
        PRINT("step:%s"% step)
        if PAUSEDEBUG is True:
            Pause("Pause:SmashBruteBrawl")

    for n,ln in enumerate(range(minchunklen, maxchunklen, step)):

        Std = datetime.now()
        IterNbr = bruteforce.iter_nbr_for_length(ln, step, n)

        max_iter, len_iter, chunklen_spec, chunk_format, chunk_data,color_type = (
            bruteforce.load_iteration_spec(BfMode, Sti, IterNbr, LoadSpec)
        )

        Loadingbar(
            max_iter, len_iter, None, True
        )



        EditWindow = bruteforce.edit_window(
            DATAX,
            DataOffset,
            ChunkLength,
            EditMode,
            BfMode,
            ln,
        )
        Before_New = EditWindow.before
        ToBrute = EditWindow.to_brute
        ToBryte = EditWindow.to_bryte
        After_New = EditWindow.after

        if EditWindow.replace_flag or EditWindow.insert_flag:
                BrawlState = bruteforce.match_state_from_edit_window(EditWindow)
                Lnx_New = EditWindow.length_bytes

#        print("bfn:",Before_New)
#        print("beforbrute",bytes.fromhex(DATAX[DataOffset+8:DataOffset+32]))
#        print("Tobrute:",ToBrute)


        shuffle = Product(chunk_data,color_type)
        for n, i in enumerate(shuffle):
                   #16581375
#            if n < 16077370:
#            if n < 254:
#                 continue
#            if Brute_LvL == 0:
#                   break

            if CRASH:
                CrashDecision = bruteforce.crash_iteration_decision(n, CRASH)
                CRASH = CrashDecision.crash_value
                if CrashDecision.skip:
                     continue


            if n == 10:
                PRINT("\n\n-BruteForce started at: %s"% Std)
                endat = datetime.now() - Std
                ETA = bruteforce.eta_seconds_after_sample(endat, max_iter)
                timdeta= timedelta(seconds=ETA)
                PRINT("-Bruteforce can last a max of %s"%str(timdeta))

                guess = datetime.now() + timdeta
                PRINT("-Bruteforce ending date time is estimated around %s\n"%str(guess))

            bvalue = bruteforce.build_candidate_bytes(
                i,
                chunk_format,
                BfMode,
                struct_indexes=tuple(Sti),
                to_bryte=ToBryte,
            )

            if BfMode == "TwoBytes":
                bruteforce.run_twobytes_candidate_scan(
                    to_brute=ToBrute,
                    brute_bytes=bvalue,
                    edit_mode=EditMode,
                    chunk_name=ChunkName,
                    brute_level=Brute_LvL,
                    old_crc=OldCrc,
                    before=Before_New,
                    after=After_New,
                    get_state=lambda: BrawlState,
                    build_attempt=BuildAttempt,
                    validate_attempt=ValidateAttempt,
                    progress=lambda: Minibar(Indication="%s/%s"%(n,max_iter)),
                    bonus_message=lambda: print("-Bingo replace bonus stage"),
                )

            else:
                 attempt = BuildAttempt(Lnx_New, bvalue, bvalue, Before_New, After_New)
                 Loadingbar(max_iter, len_iter, n, False)

                 if OldCrc:
    #                  with open("crc.plte","a+") as bd:
    #                         save = "Data:%s Crc:%s"%(str(bvalue.hex()),str(checksum.hex()))
    #                         bd.write(save+"\n")
                      if ValidateAttempt(attempt):
                          break
                      continue

                 else:
                    if ValidateAttempt(attempt):
                       break
                    else:
                       continue

    ###realeta

    ETA = (datetime.now() - Std).seconds

    if BrawlState.bingo is True:


        PRINT(
            "-Bruteforce was %s %s"
            % (Candy("Color", "green", "Successfull!"), Candy("Emoj", "good"))
        )


        if BrawlState.bonus:
                Candy("Cowsay", bruteforce.BRUTE_FORCE_BONUS_NOTE, "bad")
                SideNotes.append(bruteforce.BRUTE_FORCE_BONUS_NOTE)

        for RepairMessage in bruteforce.success_repair_messages(BrawlState, ChunkName, DIFF):
            PRINT(RepairMessage.line_template % Candy("Color", "green", ChunkName))
            SideNotes.append(RepairMessage.side_note)


        PRINT(DIFF)

        Candy("Cowsay", "Wow ...I wasn't sure this would work to be honest !", "good")


        CheckPointRequest = bruteforce.success_checkpoint_request(
            old_crc=OldCrc,
            chunk_name=ChunkName,
            full_new_data_hex=fullnewdatax.hex(),
            png_bytes_hex=wanabyte.hex(),
            data_offset=DataOffset,
            chunk_length=ChunkLength,
            to_brute=ToBrute,
            from_error=FromError,
        )
        return CheckPoint(*CheckPointRequest.as_args())

    else:
        PRINT(
            "\n-Bruteforce has %s %s"
            % (Candy("Color", "red", "Failed!"), Candy("Emoj", "bad"))
        )

        Candy("Cowsay", "I was afraid of this ...", "bad")
        SideNotes.append(bruteforce.BRUTE_FORCE_FAILURE_NOTE)

        if len(TmpImgLst) > 0:
           Candy("Cowsay", "But while you were away i v saved some pictures maybe you should take a look ...", "bad")

           for pic in TmpImgLst:
               PRINT("-Saved Valid Image: %s"%pic)


        CheckPointRequest = bruteforce.failure_checkpoint_request(
            old_crc=OldCrc,
            file=File,
            chunk_name=ChunkName,
            chunk_length=ChunkLength,
            data_offset=DataOffset,
            edit_mode=EditMode,
            bf_mode=BfMode,
            brute_crc=BruteCrc,
            brute_length=BruteLength,
            from_error=FromError,
        )
        return CheckPoint(*CheckPointRequest.as_args())




def FullChunkForcerNoCrc(
    File, Chunk, DataOffset, ChunkLength, FromError
):  ## need to be merged with SmashBruteBrawl
    global SideNotes
    Candy("Title", "Attempting To Repair Corrupted Chunk Data:")
    Chunk = Chunk.encode(errors="ignore")
    Checklist = []
    if DEBUG is True:
        PRINT("file:%s"% File)
        PRINT("chunk:%s"% Chunk)
        PRINT("offd:%s"% DataOffset)
        PRINT("cl:%s"% ChunkLength)
        if PAUSEDEBUG is True:
            Pause("Debug Pause:")

    try:
        with open(Sample, "rb") as f:
            data = f.read()
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))
        TheEnd()

    datax = data.hex()[DataOffset:ChunkLength]  # datax[16:-8]
    Bingo = False
    result = "result is empty"
    needle = 0
    needle2 = 2
    while needle2 <= len(datax) and Bingo is False:
        Minibar()
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
                #                PRINT("dataxt:%s"%datax[:16])
                #                PRINT("newdataxt:%s"%newdatax.hex())
                #                PRINT("checksum:%s"%checksum)
                fullnewdatax = datax[:16] + newdatax.hex() + checksum
                newfilewanabe = DATAX[:DataOffset] + fullnewdatax + DATAX[ChunkLength:]

                #                PRINT(newdatax_copy)
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
                    PRINT(result)
                    pause = input("pause")
                except Exception as e:
                    Betterror(e, inspect.stack()[0][3])
                    PRINT(
                        Candy("Color", "red", "Error FullChunkForcerNoCrc:"),
                        Candy("Color", "yellow", e),
                    )
                    if (PAUSEDEBUG or PAUSEERROR) is True:
                        Pause("Pause Debug")
                if DEBUG is True:
                    PRINT("fullnewdatax:%s"% fullnewdatax)
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
    #            PRINT("needle2 = ",needle2)
    #            Pause("poz2")

    if Bingo is True:
        PRINT(
            "-Bruteforce was %s %s"
            % (Candy("Color", "green", "Successfull!"), Candy("Emoj", "good"))
        )
        PRINT(
            "-Chunk %s has been repaired by changing those bytes:\n"
            % Candy("Color", "green", Chunk)
        )
        PRINT(bad)
        PRINT("\n-With those bytes:\n")
        PRINT(good)
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
            DataOffset + ChunkLength,
            "-Replacing Corrupted %s Data:\n%s\n-With:\n%s"
            % (Chunk.decode(errors="ignore"), datax[16:], fullnewdatax),
            Chunk.decode(errors="ignore"),
            FromError,
        )

    else:
        PRINT(
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




def FindMagic():
    global SideNotes

    Candy("Title", "Looking for magic header:")

    magic = "89504e470d0a1a0a"
    lenmagic = len(magic)
    MagicRecovery = detect_png_signature_recovery(DATA_BYTES)

    if MagicRecovery.action in ("found_at_start", "cut_at_signature"):
        pos = MagicRecovery.signature_hex_offset
        ChunkStory("add", "PNG", pos, pos + lenmagic, int(pos / 2))
        PRINT(
            "-%s is Magic : %s\n"
            % (
                Candy("Color", "white", Sample_Name),
                Candy("Color", "green", DATAX[:lenmagic]),
            )
        )
        PRINT(
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
        if MagicRecovery.action == "cut_at_signature":
            PRINT("-File does not start with a png signature.")
            Candy("Cowsay", " Mkay ...Things just keeps better and better ..", "bad")
            PRINT(
                "-Cutting %s bytes from %s since png header starts at offset %s ."
                % (
                    Candy("Color", "white", Sample_Name),
                    Candy("Color", "blue", int(pos / 2)),
                    Candy("Color", "white", Sample_Name),
                    Candy("Color", "blue", hex(int(pos / 2))),
                )
            )
            return CheckPoint(
                False,
                False,
                "FindMagic",
                "PngSig",
                ["Cutting at Magic"],
                MagicRecovery.fixed_data.hex(),
                hex(int(pos / 2)),
            )

        return CheckPoint(
            False, False, "FindMagic", "PngSig", ["-Found Magic"], pos + lenmagic
        )

    PRINT(
        "-File %s start with valid png signature .%s\n"
        % (Candy("Color", "red", "does not"), Candy("Emoj", "bad"))
    )
    Candy("Cowsay", " This better be a real png or else ....", "bad")

    if MagicRecovery.action == "linefeed_signature_candidate":
        if MagicRecovery.linefeed_pattern == "minor_linefeed_corruption":
            PRINT(
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
            PRINT(Candy("Color", "yellow", "\n-ToDo"))
            # FullChunkForcerWithCrc()
            TheEnd()

        if MagicRecovery.linefeed_pattern == "major_linefeed_corruption":
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
            PRINT(Candy("Color", "yellow", "\n-ToDo"))
            SideNotes.append(
                "-Major Corruption due to line feed conversion\n-File may not be recovered.\n-Not yet implemented."
            )
            PRINT(Candy("Color", "yellow", "\n-ToDo"))
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
        PRINT("\n...\n")
        PRINT("-Done! %s\n" % Candy("Emoj", "good"))
        PRINT(
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
        # PRINT("count:%s"%BestBingoCount)
        # PRINT("score:%s"%BestBingoScore)
        PRINT("\n\n")
        PRINT("\n\n...")
        [PRINT(BingoList[i]) for i in range(0, 20)]
        PRINT(
            "\n\n-Found multiple %s png signatures"
            % Candy("Color", "yellow", "potentials")
        )
        Candy("Cowsay", " Looks like i gonna have to test them all.", "bad")
        PRINT(Candy("Color", "yellow", "\n-ToDo"))
        SideNotes.append(
            "-FindFuckingMagic:Found multiple potentials png signatures\n-Not Implemented yet"
        )
        Candy("Cowsay", "Erf this case is not implemented yet ...", "bad")
        TheEnd()
    else:
        PRINT("\n\n")
        [PRINT(BingoList[i]) for i in range(0, 20)]
        PRINT("\n\n-Matching score :%s"% Candy("Color", "red", "too low"))
        PRINT("\n...\n-Done\n")
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
                    PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))
                    PRINT(
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
                    PRINT(
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
                PRINT("ChunksFound Chunk:%s index:%s" % (ck, ChunksFound[ck]))

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
                    PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))

            if NearestPos - 8 > 0:
                Lenx = DATAX[NearestPos - 8 : NearestPos]
            else:
                Lenx = DATAX[:NearestPos]

            Specheck = SpecLength(NearestChk, Lenx)

            if Specheck != Lenx and type(Specheck) != list:
                Lenx = Specheck
            elif type(Specheck) == list:
                PRINT(Candy("Color", "yellow", "\n-ToDo"))
                pass  # brutefore
            try:
                NearestPosX = hex(int(NearestPos / 2))
            except ZeroDivisionError:
                NearestPosX = hex(int(0))

            Odin = Magic + Lenx + DATAX[NearestPos::]
            if DEBUG is True:
                PRINT("New:")
                PRINT(Odin[: NearestPos + 64])
                PRINT("Old:")
                PRINT(DATAX[: NearestPos + 64])

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
    try:
        Chunk = Chunk.decode(errors="ignore")
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])

    SemanticsResult = ancillary.chunk_name_semantics(Chunk)
    Chunk = SemanticsResult.name
    Semantics = list(SemanticsResult.letters)

    if not SemanticsResult.follows_naming:
        PRINT(
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
        PRINT(
            "-[%s] %s Chunks's naming conventions"
            % (Chunk, Candy("Color", "green", "Seems to be Following"))
        )
        Candy(
            "Cowsay", "If this is a real Chunk this means that %s is :" % Chunk, "good"
        )
        if SemanticsResult.is_critical:
            PRINT(
                "-"
                + Candy("Color", "green", Semantics[0])
                + ":"
                + Candy("Color", "yellow", "Critical")
            )
        else:
            PRINT(
                "-"
                + Candy("Color", "green", Semantics[0])
                + ":"
                + Candy("Color", "yellow", "Not Critical")
            )
        if SemanticsResult.is_private:
            PRINT(
                "-"
                + Candy("Color", "green", Semantics[1])
                + ":"
                + Candy("Color", "yellow", "Private")
            )
        else:
            PRINT(
                "-"
                + Candy("Color", "green", Semantics[1])
                + ":"
                + Candy("Color", "yellow", "Not Private")
            )
        if SemanticsResult.is_reserved_valid:
            PRINT(
                "-"
                + Candy("Color", "green", Semantics[2])
                + ":"
                + Candy("Color", "yellow", "Conform to PNG specifications")
            )
        else:
            PRINT(
                "-"
                + Candy("Color", "green", Semantics[2])
                + ":"
                + Candy("Color", "yellow", "Not Conform to PNG specifications")
            )
        if SemanticsResult.is_unsafe_to_copy:
            PRINT(
                "-"
                + Candy("Color", "green", Semantics[3])
                + ":"
                + Candy("Color", "yellow", "Unsafe to Copy")
            )
        else:
            PRINT(
                "-"
                + Candy("Color", "green", Semantics[3])
                + ":"
                + Candy("Color", "yellow", "Safe to Copy")
            )
        Bad_Ancillary = True


def NullFind(data, search4=None):
    return nearby.null_find(data, search4)


def LibpngCheck(file):
    Candy("Title", "Libpng Returned :%s" % (Candy("Color", "white", Sample_Name)))
    if cv2 is not None:
        f = io.BytesIO()
        with stderr_redirector(f):
            cv2.imread(file)
        result = "{0}".format(f.getvalue().decode("utf-8"))
    elif Image is not None:
        try:
            with Image.open(file) as img:
                img.verify()
            result = ""
        except Exception as e:
            result = "libpng error: %s" % e
    else:
        try:
            with open(file, "rb") as png_file:
                chunks = list(iter_chunks(png_file.read()))
            if not chunks or chunks[-1].chunk_type != b"IEND" or not all(chunk.crc_ok for chunk in chunks):
                result = "libpng error: invalid PNG chunk stream"
            else:
                result = ""
        except (OSError, PngFormatError) as e:
            result = "libpng error: %s" % e
    known_bad_srgb_warning = KnownBadSrgbProfileWarning(file)
    if known_bad_srgb_warning and "known incorrect sRGB profile" not in result:
        result = (result + "\n" if result else "") + known_bad_srgb_warning
    PRINT("Result:%s"%result)
    if not any(s in result for s in LIBPNG_ERR):
        PRINT(
            "-Libpng Check: %s %s"
            % (Candy("Color", "green", "Ok!"), Candy("Emoj", "good"))
        )

        Candy(
            "Cowsay",
            "Good ! The AllMighty Libpng is happy !",
            "good",
        )

        return CheckPoint(
            False, False, "LibpngCheck", file, ["-Libpng dis not found any error"]
        )

    else:
        PRINT(
            "-Libpng Check: %s %s"
            % (Candy("Color", "red", "FAILED!"), Candy("Emoj", "bad"))
        )

        return CheckPoint(True, False, "LibpngCheck", file, ["-" + result])


def KnownBadSrgbProfileWarning(file):
    try:
        with open(file, "rb") as png_file:
            return known_bad_srgb_profile_warning(png_file.read())
    except OSError:
        return ""


def Double_Check(CType, ChunkLen, LastCType):

    Candy("Title", "Double Check:")


    Candy(
        "Cowsay",
        "Or maybe am i missing something ? Just let me double check again just to be sure...",
        "com",
    )
    DoubleCheckFileLength = nearby.double_check_file_length(DATAX)
    if DoubleCheckFileLength.is_too_short:
        PRINT(
            "%s: %s is %s bytes long Png minimum size is 67 bytes ."
            % (
                Candy("Color", "red","-Wrong File Length"),
                Candy("Color", "white", Sample_Name),
                Candy("Color", "red", str(DoubleCheckFileLength.byte_length)),
            )
        )

        Candy(
            "Cowsay",
            "ERrr...There are not enought byte in %s to be a valid png."%(Sample_Name),
            "bad",
        )

        Candy(
            "Cowsay",
            "I can't help you much further sorry.",
            "com",
        )
        TheEnd()

    Candy(
        "Cowsay",
        " But this time let's forget about the usual specifications of png format so This way i will be able to know if a chunk is missing somewhere.",
        "good",
    )

    NearbyChunk(CType, ChunkLen, LastCType, DoubleCheck=True)


def RandomSample(data,colortype,chunk_format):
    return specs.random_sample_hex(data, colortype, chunk_format, random.random)


def DummyChunk(Chunkname, bad_pos, bad_start, bad_end, FromError): ##TODO bad_pos is not used well enough
    Candy("Title", "Creating DummyChunk:")

    #    for c, i in zip(Chunks_History, Chunks_History_Index):
    #        PRINT("chunk:%s index:%s" % (c, i))
    Todo = True


    Candy(
        "Cowsay",
        "Mkay i will need to get some infos on the file before..",
        "com",
    )

    #TODO
    DummyDecision = dummy_chunk.decide_dummy_chunk(Chunkname, DATAX, bad_start)
    if DummyDecision.action in ("strict_ihdr_repair", "partial_idat_blackfill"):
            if DummyDecision.repair is not None:
                SideNotes.append(fixit_felix.repair_note(DummyDecision.repair))
            return CheckPoint(
                True,
                True,
                "DummyChunk",
                Chunkname,
                ["Filling with a dummy chunk"],
                DummyDecision.fixed_data_hex,
                DummyDecision.dummy_data_length,
                bad_pos,
                bad_start,
                bad_end,
                FromError,
            )

    if DummyDecision.action == "complete_iend":
        Candy(
            "Cowsay",
            "Fake datas ready to be served! Bonne appetit !",
            "good",
        )
        return CheckPoint(
            True,
            DummyDecision.solved,
            "DummyChunk",
            Chunkname,
            ["Filling with a dummy chunk"],
            DummyDecision.fixed_data_hex,
            DummyDecision.dummy_data_length,
            bad_pos,
            bad_start,
            bad_end,
            FromError,
        )

    DummyBuild = None
    if Chunkname == b"IHDR":
        DummyBuild = dummy_chunk.build_legacy_ihdr_dummy(
            Chunkname,
            get_spec=GetSpec,
            spec_length=SpecLength,
            random_sample=RandomSample,
        )
        Todo = False


    elif Chunkname == b"IDAT": ##TODO
        pass


    elif Chunkname == b"IEND":
        PRINT(Candy("Color", "yellow", "\n-ToDo"))
        TheEnd()



    if DEBUG is True and not Todo:
        if Chunkname != b"IEND":
            PRINT("chunklen_spec:%s"%str(DummyBuild.chunklen_spec))
            PRINT("chunk_format:%s"%str(DummyBuild.chunk_format))
            PRINT("color_type:%s"%str(DummyBuild.color_type))
        PRINT("dumylen:%s"% DummyBuild.dummy_length)
        PRINT("dumyname:%s"% DummyBuild.dummy_name)
        PRINT("dumydata:%s"% DummyBuild.dummy_data)
        PRINT("dumycrc:%s"% DummyBuild.dummy_crc)
        PRINT("bad_start:%s"% bad_start)
        PRINT("bad_end:%s"% bad_end)
        PRINT("dumdum:%s"% DummyBuild.chunk_hex)
        PRINT("bad pos:%s"% bad_pos)
        PRINT("datax:%s"% DATAX[bad_start:bad_end])

        if PAUSEDEBUG is True:
                Pause("Pause Debug")

#        print("Chunks_History:\n",Chunks_History)
#        TheEnd()

    if not Todo :
        DummyFix = DATAX[:bad_start] + DummyBuild.chunk_hex + DATAX[bad_start:]

        Candy(
            "Cowsay",
            "Fake datas ready to be served! Bonne appetit !",
            "good",
        )

        return CheckPoint(
            True,
            DummyBuild.solved,
            "DummyChunk",
            Chunkname,
            ["Filling with a dummy chunk"],
            DummyFix,
            len(DummyBuild.dummy_data),
            bad_pos,
            bad_start,
            bad_end,
            FromError,
        )
    else:
        PRINT(Candy("Color", "yellow", "\n-ToDo"))
        TheEnd()


def Remove_Extra_Bytes_Before_Chunk(CType, LastCType, Excluded):
    if any(c == CType for c in CHUNKS):
        return None

    data = bytes.fromhex(DATAX)
    current_offset = int(CLoffI / 2)
    candidate = nearby.find_extra_bytes_before_chunk(
        data,
        current_offset=current_offset,
        candidates=set(ALLCHUNKS) - set(Excluded),
    )
    if candidate is not None:
        SolvedMsg = nearby.extra_bytes_solved_message(candidate, LastCType)
        SideNotes.append("-Remove_Extra_Bytes_Before_Chunk:%s" % SolvedMsg)
        return SaveClone("", CLoffI, CLoffI + (candidate.extra_bytes * 2), SolvedMsg)

    return None


def NearbyChunk(CType, ChunkLen, LastCType, DoubleCheck, FromError=None):
    Candy("Title", "Chunk N Destroy:")
    Candy("Cowsay", "Now where shall i start..?", "com")
    if DoubleCheck is False:
        Excluded = CheckChunkOrder(LastCType, "Fix")
    else:
        Candy("Cowsay", " ==Safety Off==", "com")
        Excluded = []

    CleanExtraBytes = Remove_Extra_Bytes_Before_Chunk(CType, LastCType, Excluded)
    if CleanExtraBytes is not None:
        return CleanExtraBytes

    Needle = nearby.initial_search_needle(
        chunk_type=CType,
        known_chunks=CHUNKS,
        current_length_offset=CLoffI,
        chunks_history=Chunks_History,
        chunks_history_index=Chunks_History_Index,
        last_chunk_type=LastCType,
    )

    if DEBUG:
        PRINT("CType:%s"%CType)
        PRINT("LastCtype:%s"%LastCType)
        PRINT("ChunkLen:%s"%ChunkLen)
        PRINT("Orig_CT:%s"%Orig_CT)
        PRINT("Needle:%s"%Needle)
        PRINT("DATAX[N:N+32]:%s"%DATAX[Needle : Needle + 32])

    while Needle < len(DATAX):
        if Needle + 8 > len(DATAX):
           PRINT(Candy("Color", "yellow", "-End of File"))
           break
        scopex = DATAX[Needle : Needle + 8]
        try:
            scope = bytes.fromhex(scopex).lower()
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))
                PRINT(
                    Candy("Color", "red", "Scopex:%s")% Candy("Color", "yellow", scopex)
                )
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            TheEnd()


        NeedleI = int(Needle / 2)
        NeedleX = hex(int(Needle / 2))

        for Chk in CHUNKS:
            if Chk.lower() == scope:
                Candy("Cowsay", " Bingo!!!", "good")
                PRINT(
                    "-Found the closest Chunk to our position:%s at offset %s %s"
                    % (
                        Candy("Color", "green", Chk),
                        Candy("Color", "blue", NeedleX),
                        Candy("Color", "yellow", NeedleI),
                    )
                )
                if Chk in Excluded:
                    PRINT(
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
                    PRINT(Candy("Color", "yellow", "\n-ToDo"))
                    SideNotes.append("-NearbyChunk:Missplaced Chunk")
                    TheEnd()
                else:

                    if not any(c == CType for c in CHUNKS):
                        LengthRepair = nearby.unknown_chunk_length_repair(
                            data_hex=DATAX,
                            display_chunk=CType,
                            checkpoint_length_offset=CLoffI,
                            chunks_history=Chunks_History,
                            chunks_history_index=Chunks_History_Index,
                            last_chunk_type=LastCType,
                            found_chunk=Chk,
                            found_chunk_type_offset=Needle,
                        )
                        if LengthRepair is None:
                            continue
                    else:
                        LengthRepair = nearby.known_chunk_length_repair(
                            display_chunk=Orig_CT,
                            old_length=Orig_CL,
                            current_length_offset=CLoffI,
                            current_length_offset_hex=CLoffX,
                            current_data_offset_byte=CDoffB,
                            found_chunk=Chk,
                            found_chunk_type_offset=Needle,
                        )

                    PRINT(
                        "-Chunk position is %s %s\n"
                        % (Candy("Color", "green", "Valid "), Candy("Emoj", "good"))
                    )
                    PRINT(LengthRepair.print_message)

                    return CheckPoint(
                        True,
                        True,
                        "NearbyChunk",
                        Orig_CT,
                        [LengthRepair.solved_message],
                        LengthRepair.fixed_length,
                        LengthRepair.replace_start,
                        LengthRepair.replace_end,
                        Orig_CT,
                        #                           SolvedMsg,
                        FromError,
                    )

                    return ()
        Needle += 1
    if DoubleCheck is True:
        Candy("Cowsay", " ...??NOTHING AGAIN!?!?!?!?", "bad")
        CheckChunkOrder(LastCType, "Critical")
        if not Bad_Critical:
           Candy("Cowsay", "THEY PLAYED US LIKE A DAMN FIDDLE !!!", "bad")
           Candy(
            "Cowsay",
            " ...??Just Reach the EOF and found nothing!!Can't do much about that sorry ...",
            "com",
           )
           TheEnd()
        else:
            SideNotes.append("-NearbyChunk:Critical Chunk Missing: %s"%Bad_Critical)
            return(FixItFelix(CType))
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

    BadPosition = nearby.parse_history_index(Chunks_History_Index[Missplaced_Chunkpos])
    bad_pos = BadPosition.position
    bad_start = BadPosition.start
    bad_end = BadPosition.end

    for nb, key in enumerate(PandoraBox):
        if "Missplaced" in str(key):
            PRINT("\n-\033[1;31;49mCriticalHit\033[m: %s"%key)

    FixPosition = nearby.find_history_chunk_position(
        Chunks_History,
        Chunks_History_Index,
        ToFix_Chunkname,
    )

    if FixPosition is None:

        PRINT(
            "-Missing Data %s %s"
            % (Candy("Color", "red", "Has Not Been Found"), Candy("Emoj", "bad"))
        )
        Candy("Cowsay", "This is not good..", "bad")
        return CheckPoint(
            True,
            False,
            "TheGoodPlace",
            ToFix_Chunkname,
            ["-Missing Data Has Not Been Found : [%s]" % ToFix_Chunkname],
            ToFix_Chunkname,
            bad_pos,
            bad_start,
            bad_end,
        )

    else:
        PRINT(
            "\n-Found %s:[%s] at Chunk Position:%s Starting at:%s Ending at:%s %s"
            % (
                Candy("Color", "green", "Missing Data"),
                ToFix_Chunkname,
                FixPosition.position,
                FixPosition.start,
                FixPosition.end,
                Candy("Emoj", "good"),
            )
        )
        Candy("Cowsay", "Sounds good to me , where's my rubber tape already ?", "good")
        Rubber_Tape = nearby.relocate_missing_chunk(
            DATAX,
            source_start=FixPosition.start,
            source_end=FixPosition.end,
            target_start=bad_start,
        )
        return CheckPoint(
            True,
            True,
            "TheGoodPlace",
            ToFix_Chunkname,
            [
                "-Found Missing Data:[%s] at Chunk Position:%s Starting at:%s Ending at:%s"
                % (ToFix_Chunkname, FixPosition.position, FixPosition.start, FixPosition.end)
            ],
            Rubber_Tape,
        )

    PRINT("")
    if DEBUG is True:
        PRINT("Missplaced_Chunkname:%s"% Chunks_History[Missplaced_Chunkpos])
        PRINT(
            "Chunks_History_Index[Missplaced_Chunkpos]:%s"%
            Chunks_History_Index[Missplaced_Chunkpos],
        )
        PRINT("ToFix_Chunkname:%s"% ToFix_Chunkname)
        PRINT("Chunk_History and Infos :")
        for a, b in zip(Chunks_History, Chunks_History_Index):
            PRINT("Chunk:%s"% a)
            PRINT("Index Infos:%s"% b)
        #        PRINT(Rubber in DATAX)
        #        PRINT(Rubber in Tape)
        #        PRINT(DATAX[:start])
        #        PRINT("")
        #        PRINT(Rubber)
        #        PRINT("")
        #        PRINT(DATAX[end:])
        #        sys.exit()
        if PAUSEDEBUG is True:
            Pause("Pause Debug")

    TheEnd()


def CheckChunkOrder(lastchunk, mode):
    global Warning
    global SideNotes

    ToFix = []

    try:
        lastchunk = chunk_order.as_chunk_bytes(lastchunk)
    except AttributeError as e:
        Betterror(e, inspect.stack()[0][3])
        #      PRINT(Candy("Color","red","Error:"),Candy("Color","yellow",e))

    if mode == "Critical":

        Candy("Title", "Critical Chunks Check :")
        for chnk in chunk_order.missing_critical_chunks(Chunks_History, MINIMAL_CHUNKS):
            PRINT(
                "-Critical Chunk %s is %s !"
                % (chnk, Candy("Color", "red", "Missing"))
            )
            ToFix.append("-Critical Chunk %s is Missing" % chnk)
        if len(ToFix) > 0:
            CheckPoint(True, False, "CheckChunkOrder", "Critical", ToFix)
            # TheEnd()
        else:
            PRINT(
                "\n-Errors Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )
        return

    if mode == "TheGoodPlace":
        Candy("Title", "Missplaced Chunks Check:")

        Done = False
        Used_Chunks = list(chunk_order.unique_seen_chunks(Chunks_History))
        Excluded = list(chunk_order.unique_chunk_exclusions(Used_Chunks, UNIQUE_CHUNK))
        #        PRINT(Excluded)
        Candy(
            "Cowsay",
            " So far we came across those chunks in "
            + Sample_Name
            + "\n "
            + str([i.decode(errors="ignore") for i in Used_Chunks]),
            "good",
        )

        if chunk_order.legacy_flags_unique_chunk_as_multiple(lastchunk, Excluded, UNIQUE_CHUNK):
            PRINT(
                "-%s chunk %s be used multiple times."
                % (
                    Candy("Color", "red", lastchunk.decode(errors="ignore")),
                    Candy("Color", "red", "cannot"),
                )
            )
            ToFix.append("-Multiple")

        if chunk_order.png_signature_is_misplaced(Chunks_History):
            PRINT(
                "-PNG signature have to be placed %s all the other chunks. %s"
                % (Candy("Color", "red", "Before"), Candy("Emoj", "bad"))
            )
            ToFix.append("-Missplaced")
        if chunk_order.ihdr_is_misplaced(Chunks_History):
            Done = chunk_order.ihdr_misplacement_already_recorded(PandoraBox)

            if Done is False:
                PRINT(
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
                PRINT(
                    "-Already Saved : Missplaced [%s]:Should be IHDR Instead At Chunk Number:%s"
                    % (Chunks_History[-1], str(len(Chunks_History) - 1))
                )
                if PAUSEDEBUG is True:
                    Pause("Pause Debug")

        if chunk_order.must_appear_before_plte(lastchunk, Used_Chunks, BEFORE_PLTE):
            PRINT(
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
            # PRINT(Excluded)
            ToFix.append(
                "-"
                + lastchunk.decode(errors="ignore")
                + " is missplaced must appears before PLTE Chunk"
            )

        if chunk_order.must_appear_before_idat(lastchunk, Used_Chunks, Excluded, BEFORE_IDAT2):
            PRINT(
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
            # PRINT(Excluded)
            ToFix.append("-Missplaced")

        if len(ToFix) > 0:
            CheckPoint(True, False, "CheckChunkOrder", "Missplaced", ToFix)
            PRINT(
                "\n-Missplaced Chunk Check :"
                + Candy("Color", "red", " FAILED ")
                + Candy("Emoj", "bad")
            )
        else:
            PRINT(
                "\n-Missplaced Chunk Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
            )
        return

    if mode == "Fix":

        Candy("Title", "Checking Already Used Chunks :")
        Header_Exclusions = chunk_order.only_ihdr_allowed_after_png_header(Chunks_History, CHUNKS)
        if Header_Exclusions is not None:

            Candy(
                "Cowsay",
                " After Png Header always Follow IHDR this is quite hard to miss..Excluding evrything else",
                "com",
            )
            Excluded = list(Header_Exclusions)
            return Excluded

        Used_Chunks = list(chunk_order.unique_seen_chunks(Chunks_History))
        Excluded = list(chunk_order.unique_chunk_exclusions(Used_Chunks, UNIQUE_CHUNK))
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
                Excluded.append(forbid) for forbid in CHUNKS if forbid in BEFORE_IDAT and forbid not in Excluded
            ]

#            print("Excluded:",Excluded)

            if int(IHDR_Color) == 3:
                print("excluded:\n",Excluded)
                if Used_Chunks[Used_Chunks.index(b"IDAT")-1] != b"PLTE":

                    Candy(
                        "Cowsay",
                        " AH ! I knew this day would come ...You See when Image Header color type is set to 3 (Indexed Colors)..",
                        "com",
                    )

                    Candy(
                        "Cowsay",
                        "PLTE chunk must be placed before any IDAT chunks so that only means one thing ..",
                        "com",
                    )

                    Candy(
                        "Cowsay",
                        "More code to write for me.",
                        "bad",
                    )
                    PRINT(Candy("Color", "yellow", "\n-ToDo"))
                    TheEnd()

            elif (
                (int(IHDR_Color) == 2)
                or (int(IHDR_Color) == 6)
                and (
                    b"PLTE" not in Chunks_History
                    and b"sPLT" not in Chunks_History
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
                            Candy("Color", "yellow", "Missing"),
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



def NameShift():
    Candy("Title", "Checking around Chunk's position:")
    ToFix = []
    Shifted = False
    last_chunk_nbr = ""
    last_chunk_start = ""
    last_chunk_end = ""
    last_chunk_len = ""
    good_offset = False

    if DEBUG is True:
        for c, i in zip(Chunks_History, Chunks_History_Index):
            PRINT("\nCame accross that chunk: %s"% c)
            PRINT("With those index: %s"% i)
        if PAUSEDEBUG is True:
            Pause("-Debug Pause Press Return to continue:")
    for i in range(0,32):
         ioff = CToffI-8+i
         value = bytes.fromhex(DATAX[ioff:CToffI+i])
         if value in ALLCHUNKS:
              PRINT("\n-Current value of chunkname at offset %s : %s"%(str(CToffI),bytes.fromhex(DATAX[CToffI:CToffI+8])))
              SideNotes.append("-NameShift: Found correct chunkname i:%s Offset:%s data: %s"%(str(i),str(ioff),value))
              if ioff < CToffI:
                  good_offset = CToffI-ioff
                  PRINT(Candy("Color", "green", "-Found valid chunkname %s at exactly %s bytes before.")%(value,str( int((good_offset)/2) )))
              elif ioff > CToffI:
                  good_offset = ioff-CToffI
                  PRINT(Candy("Color", "green", "-Found valid chunkname %s at exactly %s bytes after.")%(value,str( int((good_offset)/2) )))
              Shifted = True
              break
    if Shifted :

        Candy("Cowsay", "Mokay ..Maybe some bytes are missing somewhere ..", "com")

        lenioff = DATAX[ioff-8:ioff]
        reallen = SpecLength(value, lenioff)

        if lenioff != reallen:

             Candy("Cowsay", "I knew there was something odd..", "bad")
#             Candy("Cowsay", "The good news is we wont have to bruteforce all the previous chunk...", "com")
             Candy("Cowsay", "That error seems to come from the length part .", "good")
             datpart = int.from_bytes(bytes.fromhex(reallen), byteorder="big")*2
             Ctype = value
             Cdata = bytes.fromhex(DATAX[ioff+8:ioff+8+datpart])
             Crc = hex(int.from_bytes(bytes.fromhex(DATAX[ioff+8+datpart:ioff+8+datpart+8]), byteorder="big"))
             checksum = hex(binascii.crc32(Ctype + Cdata))
             if DEBUG:
                 PRINT("-Crc from file: %s"%(str(checksum)))
                 PRINT("-Actual Crc: %s\n"%(str(Crc)))

             if checksum == Crc:
                 PRINT(
                "-Crc Check :"
                + Candy("Color", "green", " OK ")
                + Candy("Emoj", "good")
                + "\n"
                )

                 Candy("Cowsay", "Found the culprit!", "good")
                 SideNotes.append("-NameShift:Crc check is valid.")
                 fixed = reallen + value.hex() + DATAX[ioff+8:ioff+8+datpart] + Crc.replace("0x","")

                 if ioff > CToffI:
                      for c, i in zip(Chunks_History, Chunks_History_Index):
                          if int(i.split(":")[2]) < CToffI:
                                    last_chunk_nbr = i.split(":")[0]
                                    last_chunk_start = int(i.split(":")[1])
                                    last_chunk_end = int(i.split(":")[2])
                                    last_chunk_len = int(i.split(":")[3])
                          else:
                              break

                      if len(last_chunk_nbr) > 0:
#                          print("last_chunk_nbr:",last_chunk_nbr)
#                          print("last_chunk_start:",last_chunk_start)
#                          print("last_chunk_end:",last_chunk_end)
#                          print("last_chunk_len:",last_chunk_len)

                          if ioff == last_chunk_end + 8 + good_offset:
#                             print(last_chunk_end + 8 + good_offset)
                             SideNotes.append("-NameShift: Extra bytes has been found.")
                             Candy("Cowsay", "Found some extra bytes for some reason.. let's fix this now .", "good")
                             return([fixed,len(fixed)+good_offset,CToffI - 8])
                          else:
                             print("bad")
                             print(last_chunk_end + 8 + good_offset)
                             PRINT(Candy("Color", "yellow", "\n-ToDo"))
                             TheEnd()
                 else:
                     Candy("Cowsay", "So there was some missing bytes after all let's fix this now .", "good")
                     SideNotes.append("-NameShift: Missing bytes found.")
                     return([fixed,len(fixed)-good_offset,CToffI - 8])

             else:
                PRINT(
                    "-Crc Check :" + Candy("Color", "red", " FAILED! ") + Candy("Emoj", "bad")
                )
                if len(Crc) == 0 or len(checksum) == 0:
                    PRINT("\nMonkey wanted Banana :%s"%Candy("Color", "green", checksum))
                    PRINT("Monkey got Pullover :%s"%Candy("Color", "red", Crc))
                    Candy("Cowsay", " Hold on a sec ... Must have missed something...", "com")
                    PRINT(Candy("Color", "yellow", "\n-ToDo"))
                    TheEnd()

                if len(checksum) < 10:
                    checksum = "0x" + (checksum[2::].zfill(8))
                    PRINT("\nMonkey wanted Banana :%s"%Candy("Color", "green", checksum))
                    PRINT("Monkey got Pullover :%s"%Candy("Color", "red", Crc))
                    PRINT(Candy("Color", "yellow", "\n-ToDo"))
                    TheEnd()

             SideNotes.append("-NameShift: Length part of %s was corrupted"%value)

        else:
             PRINT(Candy("Color", "yellow", "\n-ToDo"))
             TheEnd()
    else:
        if Shifted:
            Candy("Cowsay", "Something went wrong sorry ..", "bad")
            PRINT(Candy("Color", "yellow", "\n-ToDo"))
            TheEnd()
        return False

    TheEnd()


def BruteChunk_Crc_Matches(candidates):
    try:
        chunk_data = bytes.fromhex(Raw_Data)
        stored_crc = int(Raw_Crc, 16)
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        return []

    return chunk_type_crc_matches(chunk_data, stored_crc, candidates)


def BruteChunk_Save_Auto_Name(CType, FromError, ChunkName, reason):
    if type(CType) == bytes:
        CTypeBytes = CType
    else:
        CTypeBytes = str(CType).encode(errors="ignore")

    Bchanged = sum(1 for old, new in zip(CTypeBytes, ChunkName) if old != new)
    ChunkNameText = ChunkName.decode(errors="ignore")
    SolvedMsg = (
        "-Found Chunk[%s] has wrong name at offset: %s but BruteChunk changed %s bytes "
        "turning it into a valid Chunk name: %s (%s)"
        % (Orig_CT, CToffX, Bchanged, ChunkNameText, reason)
    )

    return CheckPoint(
        True,
        True,
        "CheckChunkName",
        Orig_CT,
        [SolvedMsg],
        ChunkName.hex(),
        CToffI,
        CToffI + 8,
        Orig_CT,
        SolvedMsg,
        FromError,
    )


def BruteChunk(CType, LastCType, ChunkLen, FromError):
    Candy("Title", "Chunk Scrabble Solver:")
    ErrorA = False
    BingoLst = []
    ToFix = []
    if DEBUG is True:
        PRINT(CType)
        PRINT(LastCType)
        PRINT(ChunkLen)
        PRINT(FromError)
        if PAUSEDEBUG is True:
            Pause("Pause:Debug")

    if type(CType) == bytes:
        CTypeLst = [i.lower() for i in CType.decode(errors="ignore")]
    else:
        CTypeLst = [i.lower() for i in CType]


    Candy(
        "Cowsay", "Before going any further i need to check something real quick...", "com"
    )

    Shifted_Bit = NameShift()

    if Shifted_Bit:
        SolvedMsg = "-Chunk length has been corrupted due to some missing bytes."
        Fixed = Shifted_Bit[0]
        FixedLn = Shifted_Bit[1]
        FixedOff = Shifted_Bit[2]
        return CheckPoint(
            True,
            True,
            "CheckChunkName",
            Orig_CT,
            [SolvedMsg],
            Fixed,
            FixedLn,
            FixedOff,
            SolvedMsg,
            FromError,
        )

    Candy(
        "Cowsay", " Maybe it's name got corrupted somehow. Let's see about that.", "com"
    )

    Excluded = CheckChunkOrder(LastCType, "Fix")
    Candidates = [name for name in CHUNKS if name not in Excluded]
    CrcMatches = BruteChunk_Crc_Matches(Candidates)
    if len(CrcMatches) == 1:
        ChunkName = CrcMatches[0]
        PRINT(
            "-"
            + str(Candy("Color", "green", "CRC Solved."))
            + str(Candy("Emoj", "good"))
        )
        Candy(
            "Cowsay",
            " Stored CRC matches chunk name: %s" % Candy("Color", "green", ChunkName.decode(errors="ignore")),
            "good",
        )
        return BruteChunk_Save_Auto_Name(CType, FromError, ChunkName, "stored CRC matched candidate chunk name")

    for name in Candidates:
        if name not in Excluded:
            Bingo = 0
            ChkLst = [i.lower() for i in name.decode(errors="ignore")]

            for i, j in zip(CTypeLst, ChkLst):
                if i == j:
                    Bingo += 1
            BingoLst.append(str(Bingo) + " " + name.decode(errors="ignore"))

    # [PRINT(i) for i in BingoLst]

    BingoLst.sort(key=SplitDigits)
    BingoLst = BingoLst[::-1]

    BestBingoScore = BingoLst[0].split(" ")[0]
    BestBingoName = BingoLst[0].split(" ")[1]

    BestBingoCount = len(
        [b.count(BestBingoScore) for b in BingoLst if int(b.count(BestBingoScore)) > 0]
    )

    if BestBingoCount <= 2 and int(BestBingoScore) >= 2:

        PRINT(
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
        UnknownPrivateCriticalRemoval = FixItFelix_Try_Unknown_Private_Critical_Removal()
        if UnknownPrivateCriticalRemoval is not None:
            return UnknownPrivateCriticalRemoval

        Candy("Title", "WHO'S THAT POKEMON !?:")
        Candy("Cowsay", " Arg that's all gibberish ...", "com")
        PRINT(
            "\nI need you to choose something looking a like [%s] that is actually a real chunk name can you help ?\nOk Please select the right name for the chunk:\n"
            % Candy("Color", "purple", str(CType))
        )

        for i, j in enumerate(BingoLst):
            PRINT(
                "Score %s ,if you choose this name enter number: %s"
                % (Candy("Color", "green", j), Candy("Color", "yellow", i))
            )

        PRINT(
            "\nIf you feel as lost as me then this might be a Length Problem type : wtf"
        )
        PRINT("\nOr Type quit to ...quit.\n")
        PokemonChoice = prompts.ask_pokemon_choice(
            input,
            len(BingoLst),
            on_invalid=lambda choice: PRINT("choice:%s"% choice),
        )
        if PokemonChoice.action == "select":
            answer = BingoLst[PokemonChoice.index].split(" ")[1]
            SaveClone(
                answer.encode().hex(),
                CToffI,
                CToffI+8,
                "-Found Chunk[%s] has wrong name at offset: %s\n-Chunk seems corrupted user has decided to choose Chunk[%s] as a replacement."
                % (Orig_CT, CToffX, BingoLst[PokemonChoice.index].encode()),
            )
            return ()
        if PokemonChoice.action == "quit":
            Candy("Cowsay", " Take Care Bye !", "good")
            TheEnd()
        if PokemonChoice.action == "length":
            Candy("Cowsay", " Fine , time to investigate that length..", "com")
            NearbyChunk(CType, ChunkLen, LastCType, False)
            return ()


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
                PRINT(
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
                PRINT(
                    "\n-Chunk name:"
                    + Candy("Color", "red", " FAILED! ")
                    + Candy("Emoj", "bad")
                )
                PRINT("\nMonkey wanted Banana :%s"%Candy("Color", "green", name))
                PRINT("Monkey got Pullover :%s"%Candy("Color", "red", CType))
                PRINT("")
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

    PRINT("\n-Chunk name:" + Candy("Color", "red", " FAILED! ") + Candy("Emoj", "bad"))
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


def SpecLength(chunk_name, chunk_length=None):
    global SideNotes

    if chunk_length:
        Candy("Title", "Get Length from Spec:")
        Candy("Cowsay", "Kay ..Just Checking if the length part is legit..", "com")


    chunklen_spec = GetSpec(chunk_name,"Spec",Fields=["Length"])[0]

    if type(chunklen_spec) == tuple:
          PRINT(Candy("Color", "yellow", "\n-ToDotuple"))
          TheEnd()
    else:
          real_length = hex(int(chunklen_spec/2)).replace("0x", "").zfill(8)
          if not chunk_length:
                return real_length

          PRINT("-Real %s Length: %s " % (chunk_name, real_length))
          if real_length == chunk_length:
                Candy(
                    "Cowsay",
                    "Looks good to me !",
                    "good",
                    )
                SideNotes.append(
                    "-SpecLength:Giving correct length:  %s -"
                    % chunk_length
                    )
                return chunk_length
          else:
                PRINT(
                    "-Given %s Length was : %s "
                    % (chunk_name, chunk_length)
                    )
                Candy(
                       "Cowsay",
                       "Length part is corrupted!",
                       "bad",
                        )
                SideNotes.append(
                    "-SpecLength:Giving correct length:  %s -" % real_length
                    )
                PRINT("\n-Returning correct fixed length :%s"% real_length)
                return real_length

                                # PRINT("Chunk:%s"%key)
                                # PRINT("name:%s value:%s"%(name,value))
                                # PRINT("min:%s, max:%s"%(value[0],value[1]))
    PRINT(Candy("Color", "yellow", "\n-Requested Spec %s has not been found."%chunk_name))
    PRINT(Candy("Color", "yellow", "\n-ToDo"))
    TheEnd()


def CheckLength(Cdata, Clen, Ctype):

    Candy("Title", "Checking Data Length:", Candy("Color", "white", str(Clen)))
    LengthDecision = legacy_length_decision(
        DATA_BYTES,
        CLoffI,
        previous_chunk=Chunks_History[-1],
        idat_average_length=IDAT_Avg_Len,
    )

    Candy(
        "Cowsay",
        " So ..The length part is saying that data is %s bytes long."
        % Candy("Color", "yellow", LengthDecision.declared_length),
        "com",
    )

    #    ToBitstory(int(Clen, 16))

    if LengthDecision.is_huge:
        Candy("Cowsay", " Really!? That much ?", "com")

    if LengthDecision.idat_length_differs:
        Candy(
            "Cowsay", "Weird why does the length is not the same as before ?", "com"
        )

    if LengthDecision.checkpoint_error:
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
            [LengthDecision.checkpoint_info],
            Ctype,
            Clen,
            Chunks_History[-1],
        )
    else:
        Candy(
            "Cowsay",
            " ..So depending on that the next chunk seems to be : "
            + Candy("Color", "yellow", LengthDecision.next_chunk_type),
            "com",
        )
        return CheckPoint(
            False, False, "CheckLength", Ctype, [LengthDecision.checkpoint_info], Clen
        )




def Question(id=None,idhash=None, skipauto=False):
    runtime = question_runtime.QuestionRuntime(
        history=IFOP,
        nodialogue=NODIALOGUE,
        auto=AUTO,
        debug=DEBUG,
        pause_debug=PAUSEDEBUG,
        offset=CLoffI,
        asker=input,
        candy=Candy,
        emit=PRINT,
        pause=Pause,
        end=TheEnd,
    )
    return question_runtime.ask_question(runtime, id, idhash, skipauto=skipauto)


def Checksum(Ctype, Cdata, Crc, next=None):
    Candy("Title", "Check Crc Validity:")
    CrcDecision = legacy_crc_decision(Ctype, Cdata, Crc)
    Ctype = CrcDecision.chunk_type
    Cdata = CrcDecision.chunk_data
    Crc = CrcDecision.stored_crc_hex
    checksum = CrcDecision.computed_crc_hex
    if DEBUG:
                 PRINT("-Crc from file: %s"%(str(checksum)))
                 PRINT("-Actual Crc: %s\n"%(str(Crc)))

    if CrcDecision.ok:
        PRINT(
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
        PRINT(
            "-Crc Check :" + Candy("Color", "red", " FAILED! ") + Candy("Emoj", "bad")
        )
        if len(Crc) == 0 or len(checksum) == 0:
            PRINT("\nMonkey wanted Banana :%s"%Candy("Color", "green", checksum))
            PRINT("Monkey got Pullover :%s"%Candy("Color", "red", Crc))
            Candy("Cowsay", " Hold on a sec ... Must have missed something...", "com")
            PRINT("")
            TheEnd()

        checksum = CrcDecision.normalized_computed_crc
        PRINT("\nMonkey wanted Banana :%s"%Candy("Color", "green", checksum))
        PRINT("Monkey got Pullover :%s"%Candy("Color", "red", Crc))

        if next == None:
            ##TODO tmpworkaround need to fix wrong behavor due to this line below
            ChunkStory("add", Ctype, CLoffI, CrcoffI + 8, int(Orig_CL, 16))

        return CheckPoint(
            True,
            False,
            "Checksum",
            Ctype,
            ["-Wrong Crc %s"%str(Ctype)],
            CrcDecision.normalized_computed_crc_no_prefix,
            CrcoffI,
            CrcoffI + 8,
            Orig_CT,
            CrcoffX,
            Orig_CRC,
            int(Orig_CL, 16),
            CDoffI,
        )


def RemoveChunk(start,length,infos):
    Candy("Title", "Removing Chunk")
    end = length - start
    Before = DATAX[:start]
    After = DATAX[start+end:]
    Fix = Before + After
    WriteClone(Fix,infos)

def SaveClone(DataFix, start, end, infos):
    global Show_Must_Go_On
    Show_Must_Go_On = True

    Candy("Title", "Saving Clone")
    try:
        PRINT("-Data : %s\n" % bytes.fromhex(DataFix))
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])


    Before = DATAX[:start]
    After = DATAX[end:]
    Fix = Before + DataFix + After
    WriteClone(Fix,infos)


def WriteClone(data,infos):
    global Sample
    global Have_A_KitKat
    global SideNotes
    global SAVE_COUNT

    Pandemonium_Remember_Current_Sample()

    try:
        clone_plan = writer.prepare_clone_write(
            FILE_Origin,
            FILE_DIR,
            data,
            SAVE_COUNT,
            MAX_SAVES,
        )
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        TheEnd()

    target = clone_plan.target

    PRINT(Candy("Color", "green", "-Saving to : %s")% target.path)

    SideNotes.append("-Saving to : %s"% target.path)

    try:
       writer.write_prepared_clone(clone_plan)
       Sample = target.path
       SAVE_COUNT = clone_plan.save_count
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])
        PRINT(
                    Candy("Color", "red", "Error WriteClone:%s")%
                    Candy("Color", "yellow", e),
                )
        TheEnd()
    Have_A_KitKat = True

    if PAUSE is True:
        Pause("-Saved Press Return to continue:")

    Summarise(infos)

    if clone_plan.max_saves_reached:
        PRINT("-Max saves reached: %s" % MAX_SAVES)
        sys.exit(0)

    return None


def Relics_Runtime():
    return relics_runtime.RelicsRuntime(
        save_clone=SaveClone,
        smash_brute_brawl=SmashBruteBrawl,
        full_chunk_forcer_no_crc=FullChunkForcerNoCrc,
        tk_manual_plte=Tk_Manual_Plte,
        remove_chunk=RemoveChunk,
        ask_choice=lambda prompt, choices, retry_prompt: decisions.ask_choice(
            input,
            prompt,
            choices,
            retry_prompt,
        ),
    )


def Relics(FromError):
    Candy("Title", "Opening the Ark Of The Covenant :")

    RelicsRuntime = Relics_Runtime()
    relics_ui.emit_debug_state(
        debug=DEBUG,
        pandemonium=Pandemonium,
        pandora_box=PandoraBox,
        chunks_history=Chunks_History,
        chunks_history_index=Chunks_History_Index,
        pause_debug=PAUSEDEBUG,
        emit=PRINT,
        pause=Pause,
    )

    if len(Pandemonium) >= 1:
        relics_ui.emit_pandemonium_summary(
            relics.pandemonium_summary(Pandemonium),
            emit=PRINT,
            candy=Candy,
        )

        ##Find a more efficient way to sort error by severity and behave procedurally
        ##tmp workaround
        for PolicyStep in relics.pandemonium_policy_steps(len(Pandemonium)):
            if PolicyStep.action == "current_wrong_crc":
                should_return, result = relics_runtime.handle_current_wrong_crc_flow(
                    RelicsRuntime,
                    relics,
                    relics_ui,
                    relics.current_wrong_crc_prompt_contexts(
                        PandoraBox,
                        Cornucopia,
                        ALLCHUNKS,
                    ),
                    ask=Question,
                    emit=PRINT,
                    candy=Candy,
                )
                if should_return:
                    return result

            elif PolicyStep.action == "remembered_idat_wrong_crc":
                relics_runtime.handle_remembered_idat_wrong_crc_flow(
                    RelicsRuntime,
                    relics_ui,
                    relics.remembered_idat_wrong_crc_brawl_requests(
                        Pandemonium,
                        ALLCHUNKS,
                        target_file=FILE_Origin,
                        from_error=FromError,
                    ),
                    candy=Candy,
                )

            elif PolicyStep.action == "plte":
                PlteFinding = relics.first_current_plte_repair_finding(
                    PandoraBox,
                    Cornucopia,
                    skip_bad_current_name=Skip_Bad_Current_Name,
                    skip_bad_infos=Skip_Bad_Infos,
                    skip_bad_critical=Skip_Bad_Critical,
                )
                if PlteFinding is not None:
                    should_return, result = relics_runtime.handle_plte_repair_flow(
                        RelicsRuntime,
                        relics,
                        relics_ui,
                        has_bad_crc=Bad_Crc,
                        chunks_history=Chunks_History,
                        chunks_history_index=Chunks_History_Index,
                        target_file=Sample_Name,
                        old_crc=DATAX[CrcoffI:CrcoffI+8] if Bad_Crc else None,
                        ask_fallback=Question,
                        add_side_note=SideNotes.append,
                        the_end=TheEnd,
                        candy=Candy,
                    )
                    if should_return:
                        return result

            elif PolicyStep.action == "single_pandemonium":
                return relics_runtime.handle_single_pandemonium_flow(
                    RelicsRuntime,
                    relics_ui,
                    relics.single_pandemonium_decisions(
                        Pandemonium,
                        known_chunks=ALLCHUNKS,
                        file_origin=FILE_Origin,
                        current_sample=Sample,
                        from_error=FromError,
                    ),
                    debug=DEBUG,
                    pause_debug=PAUSEDEBUG,
                    pause_error=PAUSEERROR,
                    pause=Pause,
                    the_end=TheEnd,
                    candy=Candy,
                )

            elif PolicyStep.action == "remembered_dummy_chunks":
                return relics_runtime.handle_remembered_dummy_chunk_flow(
                    RelicsRuntime,
                    relics,
                    relics_ui,
                    relics.first_remembered_dummy_chunk_repair_request(
                        Pandemonium,
                        ALLCHUNKS,
                        CRITICAL_CHUNKS,
                    ),
                    from_error=FromError,
                    ask=Question,
                    show_todo=lambda: relics_ui.emit_todo(emit=PRINT, candy=Candy),
                    the_end=TheEnd,
                    candy=Candy,
                )

        return None

    RelicsPolicy = None
    PromptContext = None
    if len(PandoraBox) > 0:
        RelicsPolicy = relics.no_pandemonium_policy(PandoraBox, CRITICAL_CHUNKS, ALLCHUNKS)
        PromptContext = relics.no_pandemonium_prompt_context(
            RelicsPolicy,
            PandoraBox,
        )

    return relics_runtime.handle_no_pandemonium_flow(
        RelicsRuntime,
        relics,
        relics_ui,
        policy=RelicsPolicy,
        prompt_context=PromptContext,
        chunks_history=Chunks_History,
        chunks_history_index=Chunks_History_Index,
        target_file=Sample_Name,
        from_error=FromError,
        chunks_len_not_fixed=CHUNKS_LEN_NOT_FIXED,
        skip_bad_crc=Skip_Bad_Crc,
        ask=Question,
        emit=PRINT,
        candy=Candy,
        the_end=TheEnd,
    )


def Naming(filename):

    target = output.next_clone_target(filename, FILE_DIR)
    return (target.name, target.directory)

def LockDown():
    Candy("Title", "LockDown: ", Candy("Color", "white", Chunk))

    folder = output.clone_folder(FILE_Origin, FILE_DIR)
    PRINT(folder)
    folder = folder + "/"
    PRINT(folder)


def FixItFelix_Wrong_Crc(key, chkd, PandoraBox_len):
    global Old_Bad_Crc
    global Skip_Bad_Crc

    CrcDecision = fixit_felix.wrong_crc_decision(
        key,
        solved=str(key) in Cornucopia,
        pandora_box_len=PandoraBox_len,
    )

    if CrcDecision.action != "already_in_cornucopia":
        PRINT("\n-\033[1;31;49mCriticalHit\033[m: %s"% key)
        CrcTools = relics.wrong_crc_tools(PandoraBox[key], chkd)

        if CrcDecision.action == "ask_easy_crc_fix":
            Candy("Cowsay", "Crc checksum is not valid !!!", "bad")
            Candy(
                "Cowsay",
                "This looks like an easy fix since there is no real errors beside the Crc issue.Do you wish to try to fix it ?",
                "com",
            )
            uniqh = relics.question_hash(PandoraBox, key, chkd)
            Answer = Question(id=key,idhash=uniqh)
            if Answer is True:
                return True, relics_runtime.run_save_clone_plan(Relics_Runtime(),
                    relics.wrong_crc_save_clone_plan(CrcTools)
                )
            else:
                Skip_Bad_Crc = None
        else:
            Candy(
                "Cowsay",
                "Crc checksum is not valid and there are %s other errors !"
                % CrcDecision.other_error_count,
                "bad",
            )

            Candy(
                "Cowsay",
                "We may want to fix them first before jumping on that Crc what do you think ?",
                "com",
            )
        uniqh = relics.question_hash(PandoraBox, key, chkd)
        Answer = Question(id=key,idhash=uniqh)
        if Answer is False:
            return True, relics_runtime.run_save_clone_plan(Relics_Runtime(),
                relics.wrong_crc_save_clone_plan(CrcTools)
            )
        else:
            ChunkStory(
                "add",
                CrcTools.chunk,
                CLoffI,
                CrcoffI + 8,
                int(Orig_CL, 16),
            )
            #                    ChunkStory("add", Ctype, CLoffI, PandoraBox[key][chkd + "2"],PandoraBox[key][chkd + "6"])
            # return CheckPoint(
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
            Old_Bad_Crc = CrcTools.old_crc
            Skip_Bad_Crc = True

    else:
        PRINT("\n-\033[1;31;49mCriticalHit\033[m: %s"% key)
        if DEBUG is True:
            if PAUSEDEBUG is True:
                PRINT("-Cornucopia is True")

    return False, None


def FixItFelix_Libpng_Print_Critical(key):
    PRINT("\n-\033[1;31;49mCriticalHit\033[m: %s"% key)


def FixItFelix_Libpng_Not_Enough_Image_Data(decision, key, chkd):
    FixItFelix_Libpng_Print_Critical(key)
    Candy("Cowsay", "Well this is as far as i could get for now. ", "bad")
    Candy("Cowsay", "At least i was able to get some pixels out of it ..", "com")
    PRINT(Candy("Color", "yellow", "\n-ToDo"))
    TheEnd()


def FixItFelix_Libpng_Ask_Relics(decision, key, chkd):
    global Skip_Bad_Libpng

    FixItFelix_Libpng_Print_Critical(key)
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
    uniqh = relics.question_hash(PandoraBox, key, chkd)
    Answer = Question(id=key,idhash=uniqh)
    if Answer is True:
        Skip_Bad_Libpng = True
        return True, Relics(str(key))

    Candy("Cowsay", "See You Space Cowboy....", "good")
    TheEnd()


def FixItFelix_Libpng_Skip(decision, key, chkd):
    FixItFelix_Libpng_Print_Critical(key)
    return False, None


def FixItFelix_Libpng_Save_Existing_Solution(decision, key, chkd):
    PRINT("\n-\033[1;32;49mSolved\033[m: %s"% relics.tool_value(Cornucopia[key], chkd, 3))
    SaveClone(
        relics.tool_value(Cornucopia[key], chkd, 0),
        relics.tool_value(Cornucopia[key], chkd, 1),
        relics.tool_value(Cornucopia[key], chkd, 2),
        relics.tool_value(Cornucopia[key], chkd, 3),
    )
    return True, GroundhogDay(Sample)


FIXIT_FELIX_LIBPNG_ERROR_HANDLERS = {
    "not_enough_image_data": FixItFelix_Libpng_Not_Enough_Image_Data,
    "ask_relics": FixItFelix_Libpng_Ask_Relics,
    "skip": FixItFelix_Libpng_Skip,
    "save_existing_solution": FixItFelix_Libpng_Save_Existing_Solution,
}


def FixItFelix_Libpng_Error(key, chkd):
    LibpngDecision = fixit_felix.libpng_error_decision(
        key,
        solved=str(key) in Cornucopia,
        skip_bad_libpng=Skip_Bad_Libpng,
    )

    handler = FIXIT_FELIX_LIBPNG_ERROR_HANDLERS.get(LibpngDecision.action)
    if handler is None:
        raise ValueError("Unknown FixItFelix libpng action: %s" % LibpngDecision.action)
    return handler(LibpngDecision, key, chkd)


def FixItFelix_Wrong_Chunk_Name(key, chkd):
    global Skip_Bad_Current_Name
    global Skip_Bad_Next_Name

    if Skip_Bad_Current_Name is False:

        NameDecision = fixit_felix.wrong_chunk_name_decision(
            key,
            solved=str(key) in Cornucopia,
            bad_crc=Bad_Crc,
        )

        if NameDecision.action != "save_existing_solution":
            PRINT("\n-\033[1;31;49mCriticalHit\033[m: %s"% key)
            NameTools = relics.wrong_chunk_name_tools(PandoraBox[key], chkd)
            Ancillary(NameTools.chunk_type)

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

            if NameDecision.action == "ask_length_probe":
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
                uniqh = relics.question_hash(PandoraBox, key, chkd)
                Answer = Question(id=key,idhash=uniqh)
                if Answer is True:

                    return True, NearbyChunk(
                        NameTools.chunk_type,
                        NameTools.chunk_length,
                        NameTools.chunk_type_offset,
                        False,
                        key,
                    )

                else:
                    Skip_Bad_Next_Name = True
                    #Pause("Else")
            if NameDecision.bad_crc is False:
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
            uniqh = relics.question_hash(PandoraBox, key, chkd)
            Answer = Question(id=key,idhash=uniqh)
            if Answer is True:
                return True, BruteChunk(
                    NameTools.chunk_type,
                    NameTools.previous_chunk,
                    NameTools.chunk_length,
                    str(key),
                )

            else:
                Skip_Bad_Current_Name = True
        else:
            PRINT("\n-\033[1;32;49mSolved\033[m: %s"% relics.tool_value(Cornucopia[key], chkd, 4))
            return True, SaveClone(
                relics.tool_value(Cornucopia[key], chkd, 0),
                relics.tool_value(Cornucopia[key], chkd, 1),
                relics.tool_value(Cornucopia[key], chkd, 2),
                relics.tool_value(Cornucopia[key], chkd, 3),
            )
            pass

    return False, None


def FixItFelix_No_NextChunk_Print_Critical(key):
    PRINT("\n-\033[1;31;49mCriticalHit\033[m: %s"% key)


def FixItFelix_No_NextChunk_Discard_False_Positive():
    global Skip_Bad_No_Next_Chunk

    for pandora_key in list(PandoraBox):
        if "No NextChunk" in str(pandora_key):
            Candy(
                "Cowsay",
                "That one is a false positive im removing it ..",
                "good",
            )
            relics.discard_pandora_error(PandoraBox, pandora_key)
            SideNotes.append("-Found False-Positive :[Error:-No NextChunk].")
            Skip_Bad_No_Next_Chunk = True
            break


def FixItFelix_No_NextChunk_Missplaced_Tools():
    for pandora_key in PandoraBox:
        if "Missplaced" in str(pandora_key) and EOF is True:
            return list(PandoraBox[pandora_key].values())
    return None


def FixItFelix_No_NextChunk_Mark_IEND_Reached():
    global EOF

    CheckChunkOrder(b"IEND", "Critical")
    Candy("Cowsay", "We have reached the end of file.", "good")
    EOF = True
    SideNotes.append("-Reached the end of file.")


def FixItFelix_No_NextChunk_Handle_False_Positive_IEND(decision, key, chkd, Chunk, NoNextTools):
    FixItFelix_No_NextChunk_Discard_False_Positive()
    ChunkStory("add", b"IEND", CLoffI, CrcoffI + 8, int(Orig_CL, 16))

    FalsePositiveDecision = fixit_felix.no_next_false_positive_iend_decision(
        DATAX,
        bad_missplaced=Bad_Missplaced,
        has_missplaced_finding=any("Missplaced" in str(pandora_key) for pandora_key in PandoraBox),
    )

    if FalsePositiveDecision.action in ("libpng_check", "the_good_place", "continue"):
        FixItFelix_No_NextChunk_Mark_IEND_Reached()

        if FalsePositiveDecision.action == "libpng_check":
            Candy("Cowsay", "Ok let's feed the Kraken now..", "com")
            return True, LibpngCheck(Sample)

        if FalsePositiveDecision.action == "the_good_place":
            rustine = FixItFelix_No_NextChunk_Missplaced_Tools()
            if rustine is not None:
                Candy("Cowsay", "But the fun isnt over yet..", "com")
                return True, TheGoodPlace(rustine[0], rustine[1], rustine[2])

        return False, None

    if FalsePositiveDecision.action == "write_clean_iend_cut":
        cleancut = bytes.fromhex(FalsePositiveDecision.cut_hex)
        SideNotes.append("-FixitFelix:Removing extra bytes after IEND chunk.")
        return True, WriteClone(cleancut, "-Saved")

    if FalsePositiveDecision.action == "end_not_regular_iend":
        PRINT(Candy("Color", "yellow", "Not ending with regular IEND\n-ToDo"))
        SideNotes.append("-Not ending with regular IEND Chunk")
        PRINT("-Exceptation: %s"%(str(fixit_felix.GOOD_IEND_HEX)))
        PRINT("-Reality: %s"%(str(DATAX[-len(fixit_felix.GOOD_IEND_HEX) :])))
        TheEnd()
        return False, None

    raise ValueError("Unknown no-next false-positive IEND action: %s" % FalsePositiveDecision.action)


def FixItFelix_No_NextChunk_Handle_Wrong_IEND_Length(decision, key, chkd, Chunk, NoNextTools):
    PRINT(
        "-%s length for IEND %s "
        % (Candy("Color", "red", "Wrong"), Candy("Emoj", "bad"))
    )
    PRINT(Candy("Color", "yellow", "\n-ToDo"))
    SideNotes.append("-Wrong length for IEND")  # TODO
    TheEnd()
    return False, None


def FixItFelix_No_NextChunk_Print_Append_Debug():
    if DEBUG:
        print("CrcoffI:",CrcoffI)
        print("Raw_Crc:",Raw_Crc)
        print("DATAX[crc]:",DATAX[CrcoffI:CrcoffI+8])
        if PAUSEDEBUG is True or PAUSEERROR is True:
            Pause("Pause Debug")


def FixItFelix_No_NextChunk_Report_Exceeding(exceeding):
    if len(exceeding) <= 0:
        return

    if int(len(exceeding)/2) == 0:
        Candy("Cowsay", "Ah there is one bit left after the Crc ..", "com")
    else:
        Candy("Cowsay", "Ah there are %s bytes left after the Crc .."%(str(int(len(exceeding)/2))), "com")
    SideNotes.append("-Extra bits detected:%s"%str(exceeding))


def FixItFelix_No_NextChunk_Handle_Append_Missing_IEND(decision, key, chkd, Chunk, NoNextTools):
    Candy("Cowsay", "Well it seems that i need to add that IEND chunk myself after all ..", "bad")
    FixItFelix_No_NextChunk_Print_Append_Debug()

    AppendDecision = fixit_felix.no_next_append_iend_decision(
        DATAX,
        crc_offset=CrcoffI,
    )
    exceeding = AppendDecision.exceeding
    FixItFelix_No_NextChunk_Report_Exceeding(exceeding)

    if AppendDecision.action == "end_iend_inside_exceeding":
        Candy("Cowsay", "And it seems that the IEND chunk is inside it  ..", "com")
        print("-iendsample:",fixit_felix.GOOD_IEND_HEX) #TODO use PRINT()
        print("-exceeding:",exceeding)
        SideNotes.append("-Part or full IEND chunk detected:%s"%(str(exceeding)))
        PRINT(Candy("Color", "yellow", "\n-ToDo"))
        TheEnd()
        return False, None

    if AppendDecision.action == "dummy_at_crc_tail":
        if len(exceeding) > len(fixit_felix.GOOD_IEND_HEX):
            Candy("Cowsay", "But i don't know what to do with those bytes  ..", "com")
            Candy("Cowsay", "So..Im just going to append an IEND chunk there for the moment ..", "com")
        else:
            Candy("Cowsay", "It doesn't looks like and IEND chunk ..", "bad")
            Candy("Cowsay", "And i don't know what to do with those bytes  ..", "com")
            Candy("Cowsay", "So..Im just going to append an IEND chunk there for the moment ..", "com")
        print("-exceeding:",exceeding)
        return True, DummyChunk(b"IEND", CrcoffI+8, CrcoffI+8, CrcoffI+8, str(key))

    if AppendDecision.action == "dummy_at_eof":
        if exceeding:
            Candy("Cowsay", "And it seems that it matches with some part of IEND chunk ..", "com")
            Candy("Cowsay", "I don't think this is a coincidence.", "good")
            SideNotes.append("-Part or full IEND chunk detected:%s"%(str(exceeding)))
            print("-iendsample:",fixit_felix.GOOD_IEND_HEX)
            print("-exceeding:",exceeding)
        return True, DummyChunk(b"IEND", len(DATAX), len(DATAX), len(DATAX), str(key))

    raise ValueError("Unknown no-next append-IEND action: %s" % AppendDecision.action)


def FixItFelix_No_NextChunk_Handle_Ask_Length_Probe(decision, key, chkd, Chunk, NoNextTools):
    PRINT(
        "\n-End of File Reached but IEND Chunk is %s ! %s"
        % (Candy("Color", "red", " MISSING! "), Candy("Emoj", "bad"))
    )
    SideNotes.append("-End of File Reached but IEND Chunk is missing")
    Candy(
        "Cowsay",
        "A length error maybe ? Do you want me to have a look ?",
        "com",
    )
    uniqh = relics.question_hash(PandoraBox, key, chkd)
    Answer = Question(id=key,idhash=uniqh)
    if Answer is True:
        return True, NearbyChunk(
            NoNextTools.chunk_type,
            NoNextTools.chunk_length,
            NoNextTools.previous_chunk,
            False,
            key,
        )

    TheEnd()
    return False, None


FIXIT_FELIX_NO_NEXT_CHUNK_HANDLERS = {
    "false_positive_iend": FixItFelix_No_NextChunk_Handle_False_Positive_IEND,
    "wrong_iend_length": FixItFelix_No_NextChunk_Handle_Wrong_IEND_Length,
    "append_missing_iend": FixItFelix_No_NextChunk_Handle_Append_Missing_IEND,
    "ask_length_probe": FixItFelix_No_NextChunk_Handle_Ask_Length_Probe,
}


def FixItFelix_Apply_No_NextChunk_Decision(decision, key, chkd, Chunk, NoNextTools):
    handler = FIXIT_FELIX_NO_NEXT_CHUNK_HANDLERS.get(decision.action)
    if handler is None:
        raise ValueError("Unknown FixItFelix no-next-chunk action: %s" % decision.action)
    return handler(decision, key, chkd, Chunk, NoNextTools)


def FixItFelix_No_NextChunk(key, chkd, Chunk):
    global Skip_Bad_No_Next_Chunk

    if Skip_Bad_No_Next_Chunk is False:
        FixItFelix_No_NextChunk_Print_Critical(key)
        NoNextTools = relics.no_next_chunk_tools(PandoraBox[key], chkd)
        NoNextDecision = fixit_felix.no_next_chunk_decision(
            current_chunk=Chunk,
            chunk_type=NoNextTools.chunk_type,
            chunk_length=NoNextTools.chunk_length,
            bad_critical=Bad_Critical,
        )
        return FixItFelix_Apply_No_NextChunk_Decision(
            NoNextDecision,
            key,
            chkd,
            Chunk,
            NoNextTools,
        )

    return False, None


def FixItFelix_Gama_Zero(key):
    GamaDecision = fixit_felix.gama_zero_decision(key)
    if GamaDecision.action == "discard_false_positive":
        Candy("Cowsay", "Bah that's just a warning who cares ?! !", "good") ##ME !!!
        relics.discard_pandora_error(PandoraBox, GamaDecision.false_positive.finding)
        SideNotes.append(GamaDecision.false_positive.note)
        return True, FixItFelix

    raise ValueError("Unknown FixItFelix gAMA action: %s" % GamaDecision.action)


def FixItFelix_Critical_Miss(key):
    CriticalMissDecision = fixit_felix.critical_miss_decision(
        key,
        debug=DEBUG,
        pause_debug=PAUSEDEBUG,
    )
    PRINT("\n-\033[1;31;49mCriticalMiss\033[m: %s"%key)
    if CriticalMissDecision.action == "pause_debug":
        Pause("Pause:Debug")
    return False, None


def FixItFelix_Apply_Repair(repair):
    AppliedRepair = fixit_felix.applied_repair(repair)
    SideNotes.append(AppliedRepair.note)
    WriteClone(AppliedRepair.data_hex, AppliedRepair.save_suffix)
    return True


def FixItFelix_Try_Automatic_Repair(name):
    repair = fixit_felix.automatic_repair(
        name,
        DATA_BYTES,
        PandoraBox,
        known_chunk_types=ALLCHUNKS,
        auto=AUTO,
        nodialogue=NODIALOGUE,
        max_saves=MAX_SAVES,
    )
    if repair is None:
        return None

    return FixItFelix_Apply_Repair(repair)


def FixItFelix_Handle_Wrong_Crc(work_item, chkd, pandora_box_len, Chunk):
    return FixItFelix_Wrong_Crc(work_item.finding, chkd, pandora_box_len)


def FixItFelix_Handle_Libpng_Error(work_item, chkd, pandora_box_len, Chunk):
    return FixItFelix_Libpng_Error(work_item.finding, chkd)


def FixItFelix_Handle_Wrong_Chunk_Name(work_item, chkd, pandora_box_len, Chunk):
    return FixItFelix_Wrong_Chunk_Name(work_item.finding, chkd)


def FixItFelix_Handle_No_NextChunk(work_item, chkd, pandora_box_len, Chunk):
    return FixItFelix_No_NextChunk(work_item.finding, chkd, Chunk)


def FixItFelix_Handle_Gama_Zero(work_item, chkd, pandora_box_len, Chunk):
    return FixItFelix_Gama_Zero(work_item.finding)


def FixItFelix_Handle_Critical_Miss(work_item, chkd, pandora_box_len, Chunk):
    return FixItFelix_Critical_Miss(work_item.finding)


FIXIT_FELIX_FINDING_HANDLERS = {
    "wrong_crc": FixItFelix_Handle_Wrong_Crc,
    "libpng_error": FixItFelix_Handle_Libpng_Error,
    "wrong_chunk_name": FixItFelix_Handle_Wrong_Chunk_Name,
    "no_next_chunk": FixItFelix_Handle_No_NextChunk,
    "gama_zero": FixItFelix_Handle_Gama_Zero,
    "critical_miss": FixItFelix_Handle_Critical_Miss,
}


def FixItFelix_Apply_Finding_Work_Item(work_item, chkd, pandora_box_len, Chunk):
    handler = FIXIT_FELIX_FINDING_HANDLERS.get(work_item.handler)
    if handler is None:
        raise ValueError("Unknown FixItFelix finding handler: %s" % work_item.handler)
    return handler(work_item, chkd, pandora_box_len, Chunk)


def FixItFelix_Runtime():
    return fixit_felix.FixItFelixRuntime(
        try_automatic_repair=FixItFelix_Try_Automatic_Repair,
        apply_finding_work_item=FixItFelix_Apply_Finding_Work_Item,
    )


def FixItFelix(Chunk=None):
    Candy("Title", "Fix It Felix: ", Candy("Color", "white", Chunk))
    ##TODOFIND A WAY TO MAKE IT READABLE

    global Skip_Bad_Current_Name
    global Skip_Bad_Ancillary
    global Skip_Bad_No_Next_Chunk
    global Skip_Bad_Next_Name
    global Skip_Bad_Next_Ancillary
    global Skip_Bad_Infos
    global Skip_Bad_Length
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
        chkd = fixit_felix.tool_prefix_for_chunk(Chunk)

    if DEBUG is True:
        PRINT("EOF:%s"% EOF)
        PRINT("Bad_Current_Name:%s"% Bad_Current_Name)
        PRINT("Bad_Ancillary:%s"% Bad_Ancillary)
        PRINT("Bad_No_Next_Chunk:%s"% Bad_No_Next_Chunk)
        PRINT("Bad_Next_Name:%s"% Bad_Next_Name)
        PRINT("Bad_Next_Ancillary:%s"% Bad_Next_Ancillary)
        PRINT("Bad_Length:%s"% Bad_Length)
        PRINT("Bad_Infos:%s"% Bad_Infos)
        PRINT("Bad_Crc:%s"% Bad_Crc)
        PRINT("Bad_Critical:%s"% Bad_Critical)
        PRINT("Bad_Missplaced:%s"% Bad_Missplaced)
        PRINT("Bad_Libpng:%s"% Bad_Libpng)
        PRINT("Skip_Bad_Current_Name:%s"% Skip_Bad_Current_Name)
        PRINT("Skip_Bad_Ancillary:%s"% Skip_Bad_Ancillary)
        PRINT("Skip_Bad_No_Next_Chunk:%s"% Skip_Bad_No_Next_Chunk)
        PRINT("Skip_Bad_Next_Name:%s"% Skip_Bad_Next_Name)
        PRINT("Skip_Bad_Next_Ancillary:%s"% Skip_Bad_Next_Ancillary)
        PRINT("Skip_Bad_Length:%s"% Skip_Bad_Length)
        PRINT("Skip_Bad_Infos:%s"% Skip_Bad_Infos)
        PRINT("Skip_Bad_Crc:%s"% Skip_Bad_Crc)
        PRINT("Skip_Bad_Critical:%s"% Skip_Bad_Critical)
        PRINT("Skip_Bad_Missplaced:%s"% Skip_Bad_Missplaced)
        PRINT("Skip_Bad_Libpng:%s"% Skip_Bad_Libpng)
        PRINT("")
        PRINT("PandoraBox:\n%s"% PandoraBox)

        for nb, key in enumerate(PandoraBox):

            PRINT("Len PandoraBox:%s"% len(PandoraBox))
            for toolkey, keyvalue in PandoraBox[key].items():
                PRINT("PandoraBox toolkey:%s"% toolkey)
                PRINT("PandoraBox keyvalue:%s"% keyvalue)

        PRINT("")
        PRINT("Cornucopia:")
        for nb, key in enumerate(Cornucopia):
            PRINT("Len Cornucopia:%s"% len(Cornucopia))
            for toolkey, keyvalue in Cornucopia[key].items():
                PRINT("Cornucopia toolkey:%s"% toolkey)
                PRINT("Cornucopia keyvalue:%s"% keyvalue)

        if PAUSEDEBUG is True:
            Pause("FixItFelix Debug Pause:")

    PandoraBox_len = fixit_felix.effective_pandora_box_len(
        PandoraBox,
        bad_next_name=Bad_Next_Name,
    )

    RunResult = fixit_felix.run_repair_work_items(
        FixItFelix_Runtime(),
        fixit_felix.repair_work_items(
            PandoraBox,
            skip_bad_crc=Skip_Bad_Crc,
        ),
        chkd=chkd,
        pandora_box_len=PandoraBox_len,
        chunk=Chunk,
    )
    if RunResult.should_return:
        return RunResult.result

    Show_Must_Go_On = True

def CheckPoint(error, fixed, function, chunk, infos, *ToolKit):
    global Bad_Current_Name
    global Bad_Ancillary
    global Bad_No_Next_Chunk
    global Bad_Next_Name
    global Bad_Next_Ancillary
    global Bad_Infos
    global Bad_Length
    global Bad_Crc
    global Bad_Missplaced
    global Bad_Critical
    global Bad_Libpng
    global Brute_LvL
    global SideNotes
    global ERRORSFLAG
    global Cornucopia
    global PandoraBox

    Candy("Title", "CheckPoint")
    PRINT(
        r"""
   ( (
    ) )
  ........
  |      |]
  \      /
   `----'"""
    )

    if DEBUG is True:
        checkpoint_runtime.emit_checkpoint_debug(
            PRINT,
            error=error,
            fixed=fixed,
            function=function,
            infos=infos,
            chunk=chunk,
            toolkit=ToolKit,
            pandora_keys=tuple(PandoraBox),
        )

        if PAUSEDEBUG is True:
            Pause("Checkpoint pause")

    return checkpoint_runtime.run_checkpoint_loop(
        checkpoint_runtime.CheckPointLoopRuntime(
            record_finding=CheckPoint_Record_Finding,
            apply_action=CheckPoint_Apply_Action_Decision,
            pause_error=Pause,
        ),
        checkpoint_runtime.CheckPointLoopContext(
            error=error,
            fixed=fixed,
            function=function,
            chunk=chunk,
            infos=tuple(infos),
            toolkit=ToolKit,
            brute_level=Brute_LvL,
            libpng_errors=tuple(LIBPNG_ERR),
            libpng_finished_at_iend=(
                bool(Chunks_History) and Chunks_History[-1] == b"IEND" and EOF is True
            ),
            pause_error_enabled=PAUSEERROR,
        ),
    )


def Pause(msg):
    prompts.pause_with_legacy_eof_report(
        input,
        msg,
        error_emit=print,
        stderr_redirector=stderr_redirector,
        stream_factory=io.BytesIO,
    )
    return ()

def PRINT(msg):
    ui.emit_printable_message(print, msg, max_columns=MAXCHAR, no_dialogue=NODIALOGUE)

#    else:
#        print("-not print-")
#        print(msg)

def main():
    global IDAT_Bytes_Len
    global IBN
    global IDAT_Datastream
    global idatcounter
    global FirStart
    global FILE_Origin
    global CLEAR
    global CRASH
    global PAUSE
    global DEBUG
    global PAUSEDEBUG
    global PAUSEERROR
    global PAUSEDIALOGUE
    global NODIALOGUE
    global AUTO
    global CLONESWAR
    global Bad_Ancillary
    global FILE_DIR
    global DATAX
    global DATA_BYTES
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
    global Bad_Length
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
    global Skip_Bad_Length
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
    global StopBar
    global MAX_SAVES
    global SAVE_COUNT

    parser = cli.configure_parser(ArgumentParser())

    Args, unknown = parser.parse_known_args()
    LegacyUnknown = cli.parse_legacy_unknown_options(unknown)
    if LegacyUnknown.cloneswar is not None:
        CLONESWAR = LegacyUnknown.cloneswar
    if LegacyUnknown.crash_error is not None:
        print(LegacyUnknown.crash_error)
        sys.exit(1)
    if LegacyUnknown.crash is not None:
        CRASH = LegacyUnknown.crash

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    if Args.FILENAME is None:
        print("-f,--filename arguments is missing.")
        sys.exit(1)
    MaxSavesError = cli.max_saves_error(Args.MAX_SAVES)
    if MaxSavesError is not None:
        print(MaxSavesError)
        sys.exit(1)

    FILE_Origin = Args.FILENAME
    FILE_DIR = cli.output_file_dir(Args.OUTPUT_DIR, abspath=os.path.abspath, join=os.path.join)
    if FILE_DIR:
        os.makedirs(FILE_DIR, exist_ok=True)
    RuntimeFlags = cli.runtime_flags_from_args(Args)
    CLEAR = RuntimeFlags.clear
    PAUSE = RuntimeFlags.pause
    PAUSEDEBUG = RuntimeFlags.pause_debug
    PAUSEERROR = RuntimeFlags.pause_error
    PAUSEDIALOGUE = RuntimeFlags.pause_dialogue
    NODIALOGUE = RuntimeFlags.nodialogue
    DEBUG = RuntimeFlags.debug
    AUTO = RuntimeFlags.auto
    MAX_SAVES = Args.MAX_SAVES
    SAVE_COUNT = 0
    Sample = FILE_Origin

    while True:

        ClearDecision = cli.clear_screen_decision(
            clear=CLEAR,
            fir_start=FirStart,
            os_name=os.name,
        )
        FirStart = ClearDecision.fir_start
        if ClearDecision.action == "ansi_reset":
            sys.stderr.write("\033c")
        elif ClearDecision.action == "cls":
            os.system("cls")
        globals().update(runtime_state.main_loop_scan_reset_values())
        CHUNK_INFO_STATE.reset_idat()
        Sync_Chunk_Info_Legacy_State("idat")
        globals().update(runtime_state.main_loop_error_reset_values())
        TmpFixIHDR = False
        globals().update(runtime_state.main_loop_history_reset_values())
        CHUNK_INFO_STATE.reset_idat()
        Sync_Chunk_Info_Legacy_State("idat")
        # IFOP = []
        Chunklate(1)

        SampleSelection = runtime_state.select_sample(
            Sample,
            CLONESWAR,
            basename=os.path.basename,
        )
        Sample = SampleSelection.sample
        Sample_Name = SampleSelection.sample_name
        CLONESWAR = SampleSelection.cloneswar

        print("-Proceeding with: %s"% Candy("Color", "white", Sample_Name))
        try:
            LoadedSample = runtime_state.load_sample_data(Sample, opener=open)
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))
            sys.exit(1)

        DATA_BYTES = LoadedSample.data_bytes
        DATAX = LoadedSample.data_hex

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

                Offset = runtime_state.next_chunk_offset(
                    Offset,
                    Raw_Length,
                    Raw_Type,
                    Raw_Data,
                    Raw_Crc,
                )

                BreakLoop, Have_A_KitKat = runtime_state.kitkat_break_decision(Have_A_KitKat)
                if BreakLoop is True:
                    break

        # print("Reached End of %s\n"%Sample_Name)
        # CheckChunkOrder(b'IEND',"Critical")
        # TheEnd()


###


###

MINIMAL_CHUNKS = list(specs.MINIMAL_CHUNKS)
CRITICAL_CHUNKS = list(specs.CRITICAL_CHUNKS)
CHUNKS = list(specs.CHUNKS)
PRIVATE_CHUNKS = list(specs.PRIVATE_CHUNKS)
BEFORE_PLTE = list(specs.BEFORE_PLTE)
AFTER_PLTE = list(specs.AFTER_PLTE)
BEFORE_IDAT = list(specs.BEFORE_IDAT)
BEFORE_IDAT2 = list(specs.BEFORE_IDAT2)
UNIQUE_CHUNK = list(specs.UNIQUE_CHUNK)
NO_ORDER_CHUNKS = list(specs.NO_ORDER_CHUNKS)
CHUNKS_LEN_NOT_FIXED = list(specs.CHUNKS_LEN_NOT_FIXED)
ALLCHUNKS = list(specs.ALLCHUNKS)
LIBPNG_ERR = list(specs.LIBPNG_ERR)



IFOP = []
Chunks_History = []
IDAT_Bytes_Len_History = []
Chunks_History_Index = []
pCAL_Param = []
PLTE_R = []
PLTE_G = []
PLTE_B = []
Plte_Blst = []
palette_state = None
slider_list = []
wanabyte = b""
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
ThksForTheFish = []
SideNotes = []
ERRORSFLAG = []

PandoraBox = {}
Cornucopia = {}
ArkOfCovenant = {}
Pandemonium = {}
CHUNK_INFO_STATE = chunk_state.ChunkInfoState()


MAXCHAR = shutil.get_terminal_size(fallback=(120, 24)).columns - 1
# TMPFIX = False

FirStart = True
Switch = False
GoBack = False
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
Bad_Length = False
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
Skip_Bad_Length = False
Skip_Bad_Infos = False
Skip_Bad_Crc = False
Skip_Bad_Critical = False
Skip_Bad_Missplaced = False
Skip_Bad_Libpng = False
EOF = False
Show_Must_Go_On = False
CLEAR = False
CRASH = False
PAUSE = False
DEBUG = False
PAUSEDEBUG = False
PAUSEERROR = False
PAUSEDIALOGUE = False
NODIALOGUE = False
AUTO = False
CLONESWAR = False
MAX_SAVES = None
SAVE_COUNT = 0

FishPos = 0
LenFishList = 0
Brute_LvL = 0
IBN = 0
IDAT_Bytes_Len = 0
IDAT_Datastream = ""
idatcounter = 0
ETA = 0
Old_Bad_Crc = ""
IDAT_Avg_Len = ""
FILE_Origin = ""
FILE_DIR = ""
Loading_txt = ""
DATAX = ""
DATA_BYTES = b""
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
IHDR_Height = 0
IHDR_Width = 0
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
eXIf_endian = ""

Web_Safe_Colors =['000000', '000033', '000066', '000099', '0000cc', '0000ff', '003300', '003333', '003366', '003399', '0033cc', '0033ff', '006600', '006633', '006666', '006699', '0066cc', '0066ff', '009900', '009933', '009966', '009999', '0099cc', '0099ff', '00cc00', '00cc33', '00cc66', '00cc99', '00cccc', '00ccff', '00ff00', '00ff33', '00ff66', '00ff99', '00ffcc', '00ffff', '330000', '330033', '330066', '330099', '3300cc', '3300ff', '333300', '333333', '333366', '333399', '3333cc', '3333ff', '336600', '336633', '336666', '336699', '3366cc', '3366ff', '339900', '339933', '339966', '339999', '3399cc', '3399ff', '33cc00', '33cc33', '33cc66', '33cc99', '33cccc', '33ccff', '33ff00', '33ff33', '33ff66', '33ff99', '33ffcc', '33ffff', '660000', '660033', '660066', '660099', '6600cc', '6600ff', '663300', '663333', '663366', '663399', '6633cc', '6633ff', '666600', '666633', '666666', '666699', '6666cc', '6666ff', '669900', '669933', '669966', '669999', '6699cc', '6699ff', '66cc00', '66cc33', '66cc66', '66cc99', '66cccc', '66ccff', '66ff00', '66ff33', '66ff66', '66ff99', '66ffcc', '66ffff', '990000', '990033', '990066', '990099', '9900cc', '9900ff', '993300', '993333', '993366', '993399', '9933cc', '9933ff', '996600', '996633', '996666', '996699', '9966cc', '9966ff', '999900', '999933', '999966', '999999', '9999cc', '9999ff', '99cc00', '99cc33', '99cc66', '99cc99', '99cccc', '99ccff', '99ff00', '99ff33', '99ff66', '99ff99', '99ffcc', '99ffff', 'cc0000', 'cc0033', 'cc0066', 'cc0099', 'cc00cc', 'cc00ff', 'cc3300', 'cc3333', 'cc3366', 'cc3399', 'cc33cc', 'cc33ff', 'cc6600', 'cc6633', 'cc6666', 'cc6699', 'cc66cc', 'cc66ff', 'cc9900', 'cc9933', 'cc9966', 'cc9999', 'cc99cc', 'cc99ff', 'cccc00', 'cccc33', 'cccc66', 'cccc99', 'cccccc', 'ccccff', 'ccff00', 'ccff33', 'ccff66', 'ccff99', 'ccffcc', 'ccffff', 'ff0000', 'ff0033', 'ff0066', 'ff0099', 'ff00cc', 'ff00ff', 'ff3300', 'ff3333', 'ff3366', 'ff3399', 'ff33cc', 'ff33ff', 'ff6600', 'ff6633', 'ff6666', 'ff6699', 'ff66cc', 'ff66ff', 'ff9900', 'ff9933', 'ff9966', 'ff9999', 'ff99cc', 'ff99ff', 'ffcc00', 'ffcc33', 'ffcc66', 'ffcc99', 'ffcccc', 'ffccff', 'ffff00', 'ffff33', 'ffff66', 'ffff99', 'ffffcc', 'ffffff']

X11_Colors =[
  "000000",
  "800000",
  "008000",
  "808000",
  "000080",
  "800080",
  "008080",
  "c0c0c0",
  "808080",
  "ff0000",
  "00ff00",
  "ffff00",
  "0000ff",
  "ff00ff",
  "00ffff",
  "ffffff",
  "000000",
  "00005f",
  "000087",
  "0000af",
  "0000d7",
  "0000ff",
  "005f00",
  "005f5f",
  "005f87",
  "005faf",
  "005fd7",
  "005fff",
  "008700",
  "00875f",
  "008787",
  "0087af",
  "0087d7",
  "0087ff",
  "00af00",
  "00af5f",
  "00af87",
  "00afaf",
  "00afd7",
  "00afff",
  "00d700",
  "00d75f",
  "00d787",
  "00d7af",
  "00d7d7",
  "00d7ff",
  "00ff00",
  "00ff5f",
  "00ff87",
  "00ffaf",
  "00ffd7",
  "00ffff",
  "5f0000",
  "5f005f",
  "5f0087",
  "5f00af",
  "5f00d7",
  "5f00ff",
  "5f5f00",
  "5f5f5f",
  "5f5f87",
  "5f5faf",
  "5f5fd7",
  "5f5fff",
  "5f8700",
  "5f875f",
  "5f8787",
  "5f87af",
  "5f87d7",
  "5f87ff",
  "5faf00",
  "5faf5f",
  "5faf87",
  "5fafaf",
  "5fafd7",
  "5fafff",
  "5fd700",
  "5fd75f",
  "5fd787",
  "5fd7af",
  "5fd7d7",
  "5fd7ff",
  "5fff00",
  "5fff5f",
  "5fff87",
  "5fffaf",
  "5fffd7",
  "5fffff",
  "870000",
  "87005f",
  "870087",
  "8700af",
  "8700d7",
  "8700ff",
  "875f00",
  "875f5f",
  "875f87",
  "875faf",
  "875fd7",
  "875fff",
  "878700",
  "87875f",
  "878787",
  "8787af",
  "8787d7",
  "8787ff",
  "87af00",
  "87af5f",
  "87af87",
  "87afaf",
  "87afd7",
  "87afff",
  "87d700",
  "87d75f",
  "87d787",
  "87d7af",
  "87d7d7",
  "87d7ff",
  "87ff00",
  "87ff5f",
  "87ff87",
  "87ffaf",
  "87ffd7",
  "87ffff",
  "af0000",
  "af005f",
  "af0087",
  "af00af",
  "af00d7",
  "af00ff",
  "af5f00",
  "af5f5f",
  "af5f87",
  "af5faf",
  "af5fd7",
  "af5fff",
  "af8700",
  "af875f",
  "af8787",
  "af87af",
  "af87d7",
  "af87ff",
  "afaf00",
  "afaf5f",
  "afaf87",
  "afafaf",
  "afafd7",
  "afafff",
  "afd700",
  "afd75f",
  "afd787",
  "afd7af",
  "afd7d7",
  "afd7ff",
  "afff00",
  "afff5f",
  "afff87",
  "afffaf",
  "afffd7",
  "afffff",
  "d70000",
  "d7005f",
  "d70087",
  "d700af",
  "d700d7",
  "d700ff",
  "d75f00",
  "d75f5f",
  "d75f87",
  "d75faf",
  "d75fd7",
  "d75fff",
  "d78700",
  "d7875f",
  "d78787",
  "d787af",
  "d787d7",
  "d787ff",
  "d7af00",
  "d7af5f",
  "d7af87",
  "d7afaf",
  "d7afd7",
  "d7afff",
  "d7d700",
  "d7d75f",
  "d7d787",
  "d7d7af",
  "d7d7d7",
  "d7d7ff",
  "d7ff00",
  "d7ff5f",
  "d7ff87",
  "d7ffaf",
  "d7ffd7",
  "d7ffff",
  "ff0000",
  "ff005f",
  "ff0087",
  "ff00af",
  "ff00d7",
  "ff00ff",
  "ff5f00",
  "ff5f5f",
  "ff5f87",
  "ff5faf",
  "ff5fd7",
  "ff5fff",
  "ff8700",
  "ff875f",
  "ff8787",
  "ff87af",
  "ff87d7",
  "ff87ff",
  "ffaf00",
  "ffaf5f",
  "ffaf87",
  "ffafaf",
  "ffafd7",
  "ffafff",
  "ffd700",
  "ffd75f",
  "ffd787",
  "ffd7af",
  "ffd7d7",
  "ffd7ff",
  "ffff00",
  "ffff5f",
  "ffff87",
  "ffffaf",
  "ffffd7",
  "ffffff",
  "080808",
  "121212",
  "1c1c1c",
  "262626",
  "303030",
  "3a3a3a",
  "444444",
  "4e4e4e",
  "585858",
  "606060",
  "666666",
  "767676",
  "808080",
  "8a8a8a",
  "949494",
  "9e9e9e",
  "a8a8a8",
  "b2b2b2",
  "bcbcbc",
  "c6c6c6",
  "d0d0d0",
  "dadada",
  "e4e4e4",
  "eeeeee"
]


if __name__ == "__main__":
    main()
