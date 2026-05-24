#!/usr/bin/env python3
from argparse import ArgumentParser, SUPPRESS
from datetime import datetime
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

import sys, os, random, time, zlib, io, inspect, types, collections, itertools, shutil

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

from chunklate import ancillary, bruteforce, checkpoint, checkpoint_actions_runtime, checkpoint_runtime, chunk_info, chunk_order, chunk_order_runtime, chunk_report, chunk_scanner, chunk_state, chunk_story, cli, decisions, dummy_chunk, dummy_chunk_runtime, error_log, fixit_felix, fixit_felix_runtime, full_chunk_forcer, getinfo_runtime, history, libpng_check, name_shift, nearby, output, palette, palette_runtime, palette_ui, prompts, question_runtime, relics, relics_runtime, relics_ui, runtime_state, smash_bruteforce, sorting, specs, stdio, ui, ui_runtime, writer, youshallpass_runtime
from chunklate.png import (
    chunk_type_crc_matches,
    detect_png_signature_recovery,
    legacy_crc_checkpoint_args,
    legacy_crc_decision,
    legacy_crc_debug_lines,
    legacy_crc_monkey_lines,
    legacy_find_magic_checkpoint_args,
    legacy_length_checkpoint_args,
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


def CheckPoint_Set_Brute_LvL(value):
    global Brute_LvL

    Brute_LvL = value


def CheckPoint_Action_Runtime():
    return checkpoint_actions_runtime.CheckPointActionRuntime(
        checkpoint=CheckPoint_Runtime(),
        side_notes=SideNotes,
        apply_flags=CheckPoint_Apply_Flags,
        raw_next_chunk=Raw_NextChunk,
        get_brute_level=lambda: Brute_LvL,
        set_brute_level=CheckPoint_Set_Brute_LvL,
        eta=ETA,
        ihdr_interlace=IHDR_Interlace,
    )

def CheckPoint_Apply_Action_Decision(decision, chunk, info, toolkit):
    return checkpoint_actions_runtime.apply_action_decision(
        CheckPoint_Action_Runtime(),
        decision,
        chunk,
        info,
        toolkit,
    )


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
def GetInfo_Set_Legacy(**values):
    globals().update(values)


def GetInfo_Runtime():
    return getinfo_runtime.GetInfoRuntime(
        chunk_state=CHUNK_INFO_STATE,
        set_legacy=GetInfo_Set_Legacy,
        sync_legacy=Sync_Chunk_Info_Legacy_State,
        max_resolution=Max_Res,
        checkpoint=CheckPoint,
        emit=PRINT,
        candy=Candy,
        color=Chunk_Report_Color,
        emoji=Chunk_Report_Emoji,
        raw_length=Raw_Length,
        orig_cl=Orig_CL,
        ihdr_color=IHDR_Color,
        ihdr_depth=IHDR_Depht,
        chunks_history=tuple(Chunks_History),
        private_chunks=tuple(PRIVATE_CHUNKS),
        allchunks=tuple(ALLCHUNKS),
    )


def GetInfo(Chunk, data, Dummy=False):
    globals().update(
        iCCP_Name="",
        iTXt_String="",
        iTXt_Key="",
        zTXt_Key="",
        tEXt_Text="",
        tEXt_Key="",
    )

    getinfo_runtime.run_getinfo(GetInfo_Runtime(), Chunk, data)

    if Dummy is False:
        CheckChunkOrder(Chunk, "TheGoodPlace")
    return


####


def YouShallPass_Runtime():
    return youshallpass_runtime.YouShallPassRuntime(
        chunk_state=CHUNK_INFO_STATE,
        sync_state=Sync_Chunk_Info_State_From_Legacy,
        chunks_history=tuple(Chunks_History),
        orig_cl=Orig_CL,
    )


def YouShallPass(Chunk, data):
    return youshallpass_runtime.youshallpass(YouShallPass_Runtime(), Chunk, data)


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

    TmpImgLst = []

    def LoadSpec(request):
        return GetSpec(
            ChunkName,
            request.mode,
            **bruteforce.spec_request_kwargs(request),
        )

    def SaveViewerError(error, def_name):
        return Betterror(error, def_name)

    def SyncLegacyState(crash, eta_seconds, diff):
        global CRASH
        global DIFF
        global ETA
        CRASH = crash
        ETA = eta_seconds
        if diff:
            DIFF = diff

    return smash_bruteforce.run_legacy_smash_brute_brawl(
        smash_bruteforce.SmashBruteBrawlLegacyRuntime(
            load_spec=LoadSpec,
            product=Product,
            loadingbar=Loadingbar,
            minibar=Minibar,
            image_show=ImageShow,
            cv2=cv2,
            numpy=np,
            image=Image,
            psutil=psutil,
            stderr_redirector=stderr_redirector,
            sleep=time.sleep,
            ask_timeout=inputimeout,
            naming=Naming,
            emit=PRINT,
            candy=Candy,
            summarise=Summarise,
            save_error=SaveViewerError,
            end=TheEnd,
            checkpoint=CheckPoint,
            side_notes=SideNotes,
            pause=Pause,
            sync_state=SyncLegacyState,
        ),
        smash_bruteforce.SmashBruteBrawlLegacyContext(
            file=File,
            chunk_name=ChunkName,
            chunk_length=ChunkLength,
            data_offset=DataOffset,
            from_error=FromError,
            data_hex=DATAX,
            pandora_box=PandoraBox,
            libpng_errors=tuple(LIBPNG_ERR),
            tmp_image_paths=TmpImgLst,
            file_origin=FILE_Origin,
            current_diff=DIFF,
            edit_mode=EditMode,
            bf_mode=BfMode,
            brute_crc=BruteCrc,
            brute_length=BruteLength,
            old_crc=OldCrc,
            brute_level=Brute_LvL,
            crash=CRASH,
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
        ),
    )




def FullChunkForcerNoCrc(
    File, Chunk, DataOffset, ChunkLength, FromError
):  ## need to be merged with SmashBruteBrawl
    global SideNotes
    Candy("Title", "Attempting To Repair Corrupted Chunk Data:")
    Chunk = Chunk.encode(errors="ignore")
    return full_chunk_forcer.run_legacy_full_chunk_forcer_no_crc(
        full_chunk_forcer.FullChunkForcerRuntime(
            emit=PRINT,
            candy=Candy,
            checkpoint=CheckPoint,
            side_notes=SideNotes,
            minibar=Minibar,
            pause=Pause,
            end=TheEnd,
            save_error=lambda error, def_name: Betterror(error, def_name),
            cv2=cv2,
            numpy=np,
            stderr_redirector=stderr_redirector,
        ),
        full_chunk_forcer.FullChunkForcerContext(
            file=File,
            chunk=Chunk,
            data_offset=DataOffset,
            chunk_length=ChunkLength,
            from_error=FromError,
            sample_path=Sample,
            data_hex=DATAX,
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
            pause_error=PAUSEERROR,
        ),
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
            return CheckPoint(*legacy_find_magic_checkpoint_args(MagicRecovery, lenmagic))

        return CheckPoint(*legacy_find_magic_checkpoint_args(MagicRecovery, lenmagic))

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
    return CheckPoint(*legacy_find_magic_checkpoint_args(MagicRecovery, lenmagic))


def FindFuckingMagic():
    global SideNotes

    Candy("Title", "Looking harder for magic header:")
    Candy("Cowsay", " This may take me sometimes please wait ..", "com")
    Magic = "89504e470d0a1a0a"
    FullMagic = "89504e470d0a1a0a0000000d49484452"
    MagicScan = chunk_scanner.magic_bingo_scan(DATAX, FullMagic, progress=Minibar)
    BingoList = MagicScan.bingo_list
    BestBingoScore = MagicScan.best_score
    BestBingoSig = MagicScan.best_signature
    BestBingoCount = MagicScan.best_count
    MagicBingoAction = chunk_scanner.magic_bingo_action(MagicScan)

    if MagicBingoAction == "single_candidate":
        BestMagicRebuild = chunk_scanner.rebuild_from_best_magic(DATAX, FullMagic, BestBingoSig)
        PRINT("\n...\n")
        PRINT("-Done! %s\n" % Candy("Emoj", "good"))
        PRINT(
            "-Found at offset %s with a score of %s/32 :\n %s\n"
            % (
                Candy("Color", "blue", BestMagicRebuild.offset_hex),
                Candy("Color", "green", BestBingoScore),
                Candy("Color", "purple", BestBingoSig),
            )
        )
        Candy(
            "Cowsay",
            " I think this is a good start to work with.Lets see where that leads us...",
            "good",
        )

        return CheckPoint(
            False,
            False,
            "FindFuckingMagic",
            "PngSig",
            ["-Cutting at Magic"],
            BestMagicRebuild.data_hex,
            BestMagicRebuild.offset_hex,
        )

    elif MagicBingoAction == "multiple_candidates":
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

        try:
            KnownChunkScan = chunk_scanner.scan_known_chunks_until_idat(DATAX, CHUNKS)
        except Exception as e:
            Betterror(e, inspect.stack()[0][3])
            if DEBUG is True:
                PRINT(Candy("Color", "red", "Error:%s")% Candy("Color", "yellow", e))
                if PAUSEDEBUG is True or PAUSEERROR is True:
                    Pause("Pause Debug")
            TheEnd()

        ChunksFound = KnownChunkScan.chunks_found
        CheckIdat = KnownChunkScan.found_idat

        for Hit in KnownChunkScan.hits:
            Candy("Cowsay", " Bingo!!!", "good")
            PRINT(
                "-Found the closest Chunk to our position:%s at offset %s %s"
                % (
                    Candy("Color", "green", Hit.chunk),
                    Candy("Color", "blue", Hit.offset_hex),
                    Candy("Color", "yellow", Hit.offset_byte),
                )
            )
            if Hit.is_idat:
                Candy(
                    "Cowsay",
                    "No need to go any further i think i have enough data now...",
                    "com",
                )

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

            if chunk_scanner.missing_chunks_before_idat(ChunksFound, BEFORE_IDAT):
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
            NearestChunk = chunk_scanner.nearest_found_chunk(DATAX, ChunksFound)
            NearestPos = NearestChunk.offset
            NearestChk = NearestChunk.chunk
            Lenx = NearestChunk.preceding_length

            Specheck = SpecLength(NearestChk, Lenx)

            if Specheck != Lenx and type(Specheck) != list:
                Lenx = Specheck
            elif type(Specheck) == list:
                PRINT(Candy("Color", "yellow", "\n-ToDo"))
                pass  # brutefore
            NearestPosX = NearestChunk.offset_hex

            Odin = chunk_scanner.prepend_magic_before_nearest(DATAX, Magic, Lenx, NearestPos)
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
        for Letter, Label in ancillary.semantic_labels(SemanticsResult):
            PRINT(
                "-"
                + Candy("Color", "green", Letter)
                + ":"
                + Candy("Color", "yellow", Label)
            )
        Bad_Ancillary = True


def NullFind(data, search4=None):
    return nearby.null_find(data, search4)


def LibpngCheck(file):
    Candy("Title", "Libpng Returned :%s" % (Candy("Color", "white", Sample_Name)))
    result = libpng_check.libpng_result(
        file,
        cv2_module=cv2,
        image_module=Image,
        stderr_redirector=stderr_redirector,
        warning_reader=KnownBadSrgbProfileWarning,
    )
    PRINT("Result:%s"%result)
    if not libpng_check.result_has_error(result, LIBPNG_ERR):
        PRINT(
            "-Libpng Check: %s %s"
            % (Candy("Color", "green", "Ok!"), Candy("Emoj", "good"))
        )

        Candy(
            "Cowsay",
            "Good ! The AllMighty Libpng is happy !",
            "good",
        )

        return CheckPoint(*libpng_check.checkpoint_args(file, result, LIBPNG_ERR))

    else:
        PRINT(
            "-Libpng Check: %s %s"
            % (Candy("Color", "red", "FAILED!"), Candy("Emoj", "bad"))
        )

        return CheckPoint(*libpng_check.checkpoint_args(file, result, LIBPNG_ERR))


def KnownBadSrgbProfileWarning(file):
    return libpng_check.known_bad_srgb_profile_warning_for_file(file)


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


def DummyChunk_Runtime():
    return dummy_chunk_runtime.DummyChunkRuntime(
        data_hex=DATAX,
        side_notes=SideNotes,
        candy=Candy,
        emit=PRINT,
        checkpoint=CheckPoint,
        end=TheEnd,
        pause=Pause,
        get_spec=GetSpec,
        spec_length=SpecLength,
        random_sample=RandomSample,
        repair_note=fixit_felix.repair_note,
        debug=DEBUG,
        pause_debug=PAUSEDEBUG,
    )


def DummyChunk(Chunkname, bad_pos, bad_start, bad_end, FromError): ##TODO bad_pos is not used well enough
    return dummy_chunk_runtime.run_dummy_chunk(
        DummyChunk_Runtime(),
        Chunkname,
        bad_pos,
        bad_start,
        bad_end,
        FromError,
    )


def Remove_Extra_Bytes_Before_Chunk(CType, LastCType, Excluded):
    candidate = nearby.extra_bytes_before_chunk_candidate(
        DATAX,
        current_length_offset=CLoffI,
        chunk_type=CType,
        known_chunks=CHUNKS,
        all_chunks=ALLCHUNKS,
        excluded_chunks=Excluded,
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
        for DebugLine in nearby.nearby_debug_lines(
            CType,
            LastCType,
            ChunkLen,
            Orig_CT,
            Needle,
            DATAX,
        ):
            PRINT(DebugLine)

    while Needle < len(DATAX):
        if Needle + 8 > len(DATAX):
           PRINT(Candy("Color", "yellow", "-End of File"))
           break
        scopex = DATAX[Needle : Needle + 8]
        try:
            scope = nearby.decode_scope(scopex)
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
            if nearby.scope_matches_chunk(scope, Chk):
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
            *chunk_order.the_good_place_missing_checkpoint_args(
                ToFix_Chunkname,
                bad_pos,
                bad_start,
                bad_end,
            )
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
            *chunk_order.the_good_place_found_checkpoint_args(
                ToFix_Chunkname,
                FixPosition,
                Rubber_Tape,
            )
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
    def set_warning(value):
        global Warning
        Warning = value

    context = chunk_order_runtime.CheckChunkOrderContext(
        chunk_order_context=runtime_state.chunk_order_runtime_context(
            Sample_Name,
            Chunks_History,
            UNIQUE_CHUNK,
        ),
        minimal_chunks=tuple(MINIMAL_CHUNKS),
        pandora_box=PandoraBox,
        before_plte=tuple(BEFORE_PLTE),
        before_idat2=tuple(BEFORE_IDAT2),
        chunks=tuple(CHUNKS),
        after_plte=tuple(AFTER_PLTE),
        before_idat=tuple(BEFORE_IDAT),
        ihdr_color=IHDR_Color,
        no_order_chunks=tuple(NO_ORDER_CHUNKS),
        debug=DEBUG,
        pause_debug=PAUSEDEBUG,
    )
    runtime = chunk_order_runtime.CheckChunkOrderRuntime(
        candy=Candy,
        emit=PRINT,
        checkpoint=CheckPoint,
        pause=Pause,
        end=TheEnd,
        betterror=Betterror,
        get_warning=lambda: Warning,
        set_warning=set_warning,
        raw_print=print,
    )
    return chunk_order_runtime.run_check_chunk_order(runtime, context, lastchunk, mode)



def NameShift():
    Candy("Title", "Checking around Chunk's position:")
    Shifted = False
    good_offset = False

    if DEBUG is True:
        for c, i in zip(Chunks_History, Chunks_History_Index):
            PRINT("\nCame accross that chunk: %s"% c)
            PRINT("With those index: %s"% i)
        if PAUSEDEBUG is True:
            Pause("-Debug Pause Press Return to continue:")
    NameShiftContext = runtime_state.name_shift_runtime_context(
        DATAX,
        CToffI,
        Chunks_History_Index,
        ALLCHUNKS,
    )
    ShiftCandidate = name_shift.find_shifted_chunk_name(
        NameShiftContext.data_hex,
        NameShiftContext.current_type_offset,
        NameShiftContext.known_chunks,
    )
    if ShiftCandidate is not None:
         i = ShiftCandidate.search_index
         ioff = ShiftCandidate.type_offset
         value = ShiftCandidate.chunk_name
         PRINT(
             name_shift.current_chunk_value_line(
                 NameShiftContext.current_type_offset,
                 name_shift.current_chunk_value(
                     NameShiftContext.data_hex,
                     NameShiftContext.current_type_offset,
                 ),
             )
         )
         SideNotes.append(name_shift.found_chunk_note(i, ioff, value))
         if ShiftCandidate.is_before:
             good_offset = ShiftCandidate.good_offset
             PRINT(Candy("Color", "green", name_shift.valid_chunk_before_line(value, good_offset)))
         elif ShiftCandidate.is_after:
             good_offset = ShiftCandidate.good_offset
             PRINT(Candy("Color", "green", name_shift.valid_chunk_after_line(value, good_offset)))
         Shifted = True
    if Shifted :

        Candy("Cowsay", "Mokay ..Maybe some bytes are missing somewhere ..", "com")

        lenioff = NameShiftContext.data_hex[ioff-8:ioff]
        reallen = SpecLength(value, lenioff)

        if name_shift.length_part_is_corrupted(lenioff, reallen):

             Candy("Cowsay", "I knew there was something odd..", "bad")
#             Candy("Cowsay", "The good news is we wont have to bruteforce all the previous chunk...", "com")
             Candy("Cowsay", "That error seems to come from the length part .", "good")
             CrcView = name_shift.shifted_chunk_crc_view(NameShiftContext.data_hex, ioff, value, reallen)
             Crc = CrcView.file_crc
             checksum = CrcView.checksum
             if DEBUG:
                 PRINT("-Crc from file: %s"%(str(checksum)))
                 PRINT("-Actual Crc: %s\n"%(str(Crc)))

             if CrcView.crc_matches:
                 PRINT(
                    name_shift.crc_ok_line(
                        Candy("Color", "green", " OK "),
                        Candy("Emoj", "good"),
                    )
                )

                 Candy("Cowsay", "Found the culprit!", "good")
                 SideNotes.append(name_shift.crc_valid_note())
                 fixed = CrcView.fixed_hex

                 if ioff > CToffI:
                      LastChunkBeforeOffset = name_shift.last_history_chunk_before_offset(
                          NameShiftContext.chunks_history_index,
                          NameShiftContext.current_type_offset,
                      )

                      if LastChunkBeforeOffset is not None:
#                          print("last_chunk_nbr:",LastChunkBeforeOffset.number)
#                          print("last_chunk_start:",LastChunkBeforeOffset.start)
#                          print("last_chunk_end:",LastChunkBeforeOffset.end)
#                          print("last_chunk_len:",LastChunkBeforeOffset.length)

                          if name_shift.extra_bytes_align_with_previous_chunk(
                              ioff,
                              LastChunkBeforeOffset.end,
                              good_offset,
                          ):
#                             print(name_shift.extra_bytes_expected_offset(LastChunkBeforeOffset.end, good_offset))
                             SideNotes.append(name_shift.extra_bytes_found_note())
                             Candy("Cowsay", "Found some extra bytes for some reason.. let's fix this now .", "good")
                             return name_shift.extra_bytes_repair_result(
                                 fixed,
                                 good_offset,
                                 NameShiftContext.current_type_offset,
                             )
                          else:
                             print("bad")
                             print(name_shift.extra_bytes_expected_offset(LastChunkBeforeOffset.end, good_offset))
                             PRINT(Candy("Color", "yellow", "\n-ToDo"))
                             TheEnd()
                 else:
                     Candy("Cowsay", "So there was some missing bytes after all let's fix this now .", "good")
                     SideNotes.append(name_shift.missing_bytes_found_note())
                     return name_shift.missing_bytes_repair_result(
                         fixed,
                         good_offset,
                         NameShiftContext.current_type_offset,
                     )

             else:
                PRINT(
                    name_shift.crc_failed_line(
                        Candy("Color", "red", " FAILED! "),
                        Candy("Emoj", "bad"),
                    )
                )
                if name_shift.crc_value_is_empty(Crc, checksum):
                    PRINT(name_shift.monkey_wanted_line(Candy("Color", "green", checksum)))
                    PRINT(name_shift.monkey_got_line(Candy("Color", "red", Crc)))
                    Candy("Cowsay", name_shift.missed_something_message(), "com")
                    PRINT(Candy("Color", "yellow", "\n-ToDo"))
                    TheEnd()

                if name_shift.checksum_needs_legacy_padding(checksum):
                    checksum = name_shift.legacy_pad_checksum(checksum)
                    PRINT(name_shift.monkey_wanted_line(Candy("Color", "green", checksum)))
                    PRINT(name_shift.monkey_got_line(Candy("Color", "red", Crc)))
                    PRINT(Candy("Color", "yellow", "\n-ToDo"))
                    TheEnd()

             SideNotes.append(name_shift.corrupted_length_note(value))

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
          LengthCheck = specs.check_spec_length(chunklen_spec, chunk_length)
          real_length = LengthCheck.real_length
          if not LengthCheck.has_provided_length:
                return LengthCheck.returned_length

          PRINT("-Real %s Length: %s " % (chunk_name, real_length))
          if LengthCheck.matches:
                Candy(
                    "Cowsay",
                    "Looks good to me !",
                    "good",
                    )
                SideNotes.append(
                    "-SpecLength:Giving correct length:  %s -"
                    % chunk_length
                    )
                return LengthCheck.returned_length
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
                return LengthCheck.returned_length

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
        return CheckPoint(*legacy_length_checkpoint_args(LengthDecision, Ctype, Clen, Chunks_History[-1]))
    else:
        Candy(
            "Cowsay",
            " ..So depending on that the next chunk seems to be : "
            + Candy("Color", "yellow", LengthDecision.next_chunk_type),
            "com",
        )
        return CheckPoint(*legacy_length_checkpoint_args(LengthDecision, Ctype, Clen, Chunks_History[-1]))




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
        for DebugLine in legacy_crc_debug_lines(CrcDecision):
            PRINT(DebugLine)

    if CrcDecision.ok:
        PRINT(
            "-Crc Check :"
            + Candy("Color", "green", " OK ")
            + Candy("Emoj", "good")
            + "\n"
        )
        chunk_story.add_if_no_next(
            Chunks_History,
            Chunks_History_Index,
            next,
            Ctype,
            CLoffI,
            CrcoffI + 8,
            int(Orig_CL, 16),
        )
        return CheckPoint(
            *legacy_crc_checkpoint_args(
                CrcDecision,
                CrcoffI,
                Orig_CT,
                CrcoffX,
                Orig_CRC,
                Orig_CL,
                CDoffI,
            )
        )
    else:
        PRINT(
            "-Crc Check :" + Candy("Color", "red", " FAILED! ") + Candy("Emoj", "bad")
        )
        if len(Crc) == 0 or len(checksum) == 0:
            MonkeyWanted, MonkeyGot = legacy_crc_monkey_lines(
                Candy("Color", "green", checksum),
                Candy("Color", "red", Crc),
            )
            PRINT(MonkeyWanted)
            PRINT(MonkeyGot)
            Candy("Cowsay", " Hold on a sec ... Must have missed something...", "com")
            PRINT("")
            TheEnd()

        checksum = CrcDecision.normalized_computed_crc
        MonkeyWanted, MonkeyGot = legacy_crc_monkey_lines(
            Candy("Color", "green", checksum),
            Candy("Color", "red", Crc),
        )
        PRINT(MonkeyWanted)
        PRINT(MonkeyGot)

        ##TODO tmpworkaround need to fix wrong behavor due to this line below
        chunk_story.add_if_no_next(
            Chunks_History,
            Chunks_History_Index,
            next,
            Ctype,
            CLoffI,
            CrcoffI + 8,
            int(Orig_CL, 16),
        )

        return CheckPoint(
            *legacy_crc_checkpoint_args(
                CrcDecision,
                CrcoffI,
                Orig_CT,
                CrcoffX,
                Orig_CRC,
                Orig_CL,
                CDoffI,
            )
        )


def RemoveChunk(start,length,infos):
    Candy("Title", "Removing Chunk")
    Fix = writer.remove_hex_range(DATAX, start, length)
    WriteClone(Fix,infos)

def SaveClone(DataFix, start, end, infos):
    global Show_Must_Go_On
    Show_Must_Go_On = True

    Candy("Title", "Saving Clone")
    try:
        PRINT("-Data : %s\n" % bytes.fromhex(DataFix))
    except Exception as e:
        Betterror(e, inspect.stack()[0][3])


    Fix = writer.replace_hex_range(DATAX, DataFix, start, end)
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
    return relics_runtime.build_relics_runtime(
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


def Relics_Context(FromError):
    return runtime_state.relics_runtime_context(
        from_error=FromError,
        pandemonium=Pandemonium,
        pandora_box=PandoraBox,
        cornucopia=Cornucopia,
        side_notes=SideNotes,
        all_chunks=ALLCHUNKS,
        critical_chunks=CRITICAL_CHUNKS,
        chunks_history=Chunks_History,
        chunks_history_index=Chunks_History_Index,
        file_origin=FILE_Origin,
        sample=Sample,
        sample_name=Sample_Name,
        data_hex=DATAX,
        crc_offset=CrcoffI,
        bad_crc=Bad_Crc,
        skip_bad_current_name=Skip_Bad_Current_Name,
        skip_bad_infos=Skip_Bad_Infos,
        skip_bad_critical=Skip_Bad_Critical,
        skip_bad_crc=Skip_Bad_Crc,
        chunks_len_not_fixed=CHUNKS_LEN_NOT_FIXED,
        debug=DEBUG,
        pause_debug=PAUSEDEBUG,
        pause_error=PAUSEERROR,
    )


def Relics(FromError):
    Candy("Title", "Opening the Ark Of The Covenant :")

    return relics_runtime.handle_relics_context_flow(
        Relics_Runtime(),
        relics,
        relics_ui,
        Relics_Context(FromError),
        ask=Question,
        emit=PRINT,
        pause=Pause,
        show_todo=lambda: relics_ui.emit_todo(emit=PRINT, candy=Candy),
        candy=Candy,
        the_end=TheEnd,
    )


def Naming(filename):

    target = output.next_clone_target(filename, FILE_DIR)
    return (target.name, target.directory)

def LockDown():
    Candy("Title", "LockDown: ", Candy("Color", "white", Chunk))

    for folder in output.lockdown_folder_lines(FILE_Origin, FILE_DIR):
        PRINT(folder)


def FixItFelix_Set_Skip_Bad_Crc(value):
    global Skip_Bad_Crc

    Skip_Bad_Crc = value


def FixItFelix_Set_Old_Bad_Crc(value):
    global Old_Bad_Crc

    Old_Bad_Crc = value


def FixItFelix_Wrong_Crc_Runtime():
    return fixit_felix_runtime.WrongCrcRuntime(
        emit=PRINT,
        candy=Candy,
        question=Question,
        save_clone=SaveClone,
        chunk_story=ChunkStory,
        set_skip_bad_crc=FixItFelix_Set_Skip_Bad_Crc,
        set_old_bad_crc=FixItFelix_Set_Old_Bad_Crc,
        pandora_box=PandoraBox,
        cl_offset=CLoffI,
        crc_offset=CrcoffI,
        original_chunk_length_hex=Orig_CL,
        debug=DEBUG,
        pause_debug=PAUSEDEBUG,
    )


def FixItFelix_Wrong_Crc(key, chkd, PandoraBox_len):
    CrcDecision = fixit_felix.wrong_crc_decision(
        key,
        solved=str(key) in Cornucopia,
        pandora_box_len=PandoraBox_len,
    )

    CrcTools = None
    if CrcDecision.action != "already_in_cornucopia":
        CrcTools = relics.wrong_crc_tools(PandoraBox[key], chkd)

    return fixit_felix_runtime.apply_wrong_crc(
        FixItFelix_Wrong_Crc_Runtime(),
        CrcDecision,
        chkd,
        CrcTools,
    )


def FixItFelix_Set_Skip_Bad_Libpng(value):
    global Skip_Bad_Libpng

    Skip_Bad_Libpng = value


def FixItFelix_Libpng_Error_Runtime():
    return fixit_felix_runtime.LibpngErrorRuntime(
        emit=PRINT,
        candy=Candy,
        question=Question,
        the_end=TheEnd,
        run_relics=Relics,
        save_clone=SaveClone,
        groundhog_day=GroundhogDay,
        set_skip_bad_libpng=FixItFelix_Set_Skip_Bad_Libpng,
        pandora_box=PandoraBox,
        cornucopia=Cornucopia,
        sample=Sample,
    )


def FixItFelix_Libpng_Error(key, chkd):
    return fixit_felix_runtime.apply_libpng_error(
        FixItFelix_Libpng_Error_Runtime(),
        fixit_felix.libpng_error_decision(
            key,
            solved=str(key) in Cornucopia,
            skip_bad_libpng=Skip_Bad_Libpng,
        ),
        chkd,
    )


def FixItFelix_Set_Skip_Bad_Next_Name(value):
    global Skip_Bad_Next_Name

    Skip_Bad_Next_Name = value


def FixItFelix_Set_Skip_Bad_Current_Name(value):
    global Skip_Bad_Current_Name

    Skip_Bad_Current_Name = value


def FixItFelix_Wrong_Chunk_Name_Runtime():
    return fixit_felix_runtime.WrongChunkNameRuntime(
        emit=PRINT,
        candy=Candy,
        question=Question,
        ancillary=Ancillary,
        nearby_chunk=NearbyChunk,
        brute_chunk=BruteChunk,
        save_clone=SaveClone,
        set_skip_bad_next_name=FixItFelix_Set_Skip_Bad_Next_Name,
        set_skip_bad_current_name=FixItFelix_Set_Skip_Bad_Current_Name,
        bad_ancillary=lambda: Bad_Ancillary,
        pandora_box=PandoraBox,
        cornucopia=Cornucopia,
    )


def FixItFelix_Wrong_Chunk_Name(key, chkd):
    if Skip_Bad_Current_Name is False:
        NameDecision = fixit_felix.wrong_chunk_name_decision(
            key,
            solved=str(key) in Cornucopia,
            bad_crc=Bad_Crc,
        )

        NameTools = None
        if NameDecision.action != "save_existing_solution":
            NameTools = relics.wrong_chunk_name_tools(PandoraBox[key], chkd)

        return fixit_felix_runtime.apply_wrong_chunk_name(
            FixItFelix_Wrong_Chunk_Name_Runtime(),
            NameDecision,
            chkd,
            NameTools,
        )

    return False, None


def FixItFelix_Set_Skip_Bad_No_Next_Chunk(value):
    global Skip_Bad_No_Next_Chunk

    Skip_Bad_No_Next_Chunk = value


def FixItFelix_Set_EOF(value):
    global EOF

    EOF = value


def FixItFelix_No_NextChunk_Runtime():
    return fixit_felix_runtime.NoNextChunkRuntime(
        emit=PRINT,
        candy=Candy,
        question=Question,
        side_notes=SideNotes,
        pandora_box=PandoraBox,
        sample=Sample,
        data_hex=DATAX,
        cl_offset=CLoffI,
        crc_offset=CrcoffI,
        original_chunk_length_hex=Orig_CL,
        raw_crc=Raw_Crc,
        debug=DEBUG,
        pause_debug=PAUSEDEBUG,
        pause_error=PAUSEERROR,
        bad_missplaced=Bad_Missplaced,
        set_skip_bad_no_next_chunk=FixItFelix_Set_Skip_Bad_No_Next_Chunk,
        set_eof=FixItFelix_Set_EOF,
        eof=lambda: EOF,
        chunk_story=ChunkStory,
        check_chunk_order=CheckChunkOrder,
        libpng_check=LibpngCheck,
        the_good_place=TheGoodPlace,
        write_clone=WriteClone,
        the_end=TheEnd,
        pause=Pause,
        debug_print=print,
        dummy_chunk=DummyChunk,
        nearby_chunk=NearbyChunk,
    )


def FixItFelix_No_NextChunk(key, chkd, Chunk):
    global Skip_Bad_No_Next_Chunk

    if Skip_Bad_No_Next_Chunk is False:
        NoNextTools = relics.no_next_chunk_tools(PandoraBox[key], chkd)
        NoNextDecision = fixit_felix.no_next_chunk_decision(
            current_chunk=Chunk,
            chunk_type=NoNextTools.chunk_type,
            chunk_length=NoNextTools.chunk_length,
            bad_critical=Bad_Critical,
        )
        return fixit_felix_runtime.apply_no_next_chunk(
            FixItFelix_No_NextChunk_Runtime(),
            NoNextDecision,
            key,
            chkd,
            NoNextTools,
        )

    return False, None


def FixItFelix_Gama_Zero_Runtime():
    return fixit_felix_runtime.GamaZeroRuntime(
        candy=Candy,
        pandora_box=PandoraBox,
        side_notes=SideNotes,
        return_value=FixItFelix,
    )


def FixItFelix_Gama_Zero(key):
    return fixit_felix_runtime.apply_gama_zero(
        FixItFelix_Gama_Zero_Runtime(),
        fixit_felix.gama_zero_decision(key),
    )


def FixItFelix_Critical_Miss_Runtime():
    return fixit_felix_runtime.CriticalMissRuntime(
        emit=PRINT,
        pause=Pause,
    )


def FixItFelix_Critical_Miss(key):
    return fixit_felix_runtime.apply_critical_miss(
        FixItFelix_Critical_Miss_Runtime(),
        fixit_felix.critical_miss_decision(
            key,
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
        ),
    )


def FixItFelix_Automatic_Repair_Runtime():
    return fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=SideNotes,
        write_clone=WriteClone,
    )


def FixItFelix_Apply_Repair(repair):
    return fixit_felix_runtime.apply_repair(
        FixItFelix_Automatic_Repair_Runtime(),
        repair,
    )


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


def FixItFelix_Runtime_Callbacks():
    return fixit_felix_runtime.LegacyFixItFelixHandlers(
        wrong_crc=FixItFelix_Wrong_Crc,
        libpng_error=FixItFelix_Libpng_Error,
        wrong_chunk_name=FixItFelix_Wrong_Chunk_Name,
        no_next_chunk=FixItFelix_No_NextChunk,
        gama_zero=FixItFelix_Gama_Zero,
        critical_miss=FixItFelix_Critical_Miss,
    )


def FixItFelix_Runtime():
    return fixit_felix_runtime.runtime(
        try_automatic_repair=FixItFelix_Try_Automatic_Repair,
        callbacks=FixItFelix_Runtime_Callbacks(),
    )


def FixItFelix_Tool_Prefix(Chunk):
    try:
        return Chunk.decode(errors="ignore") + "_Tool_"
    except AttributeError as e:
        Betterror(e, "FixItFelix")
        return fixit_felix.tool_prefix_for_chunk(Chunk)


def FixItFelix(Chunk=None):
    Candy("Title", "Fix It Felix: ", Candy("Color", "white", Chunk))
    ##TODOFIND A WAY TO MAKE IT READABLE

    global Show_Must_Go_On

    chkd = FixItFelix_Tool_Prefix(Chunk)

    if DEBUG is True:
        fixit_felix.emit_debug_report(PRINT, globals(), PandoraBox, Cornucopia)

        if PAUSEDEBUG is True:
            Pause("FixItFelix Debug Pause:")

    RunResult = fixit_felix.run_repair_pipeline(
        FixItFelix_Runtime(),
        PandoraBox,
        skip_bad_crc=Skip_Bad_Crc,
        bad_next_name=Bad_Next_Name,
        chkd=chkd,
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
