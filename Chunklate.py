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

from chunklate import ancillary, bruteforce, checkpoint, checkpoint_actions_runtime, checkpoint_runtime, chunk_info, chunk_name_runtime, chunk_order, chunk_order_runtime, chunk_report, chunk_scanner, chunk_state, chunk_state_runtime, chunk_story, chunk_validation_runtime, cli, decisions, dummy_chunk, dummy_chunk_runtime, error_log, fixit_felix, fixit_felix_runtime, full_chunk_forcer, getinfo_runtime, getspec_runtime, history, libpng_check, libpng_runtime, magic_runtime, main_runtime, name_shift, name_shift_runtime, nearby, nearby_runtime, output, palette, palette_runtime, palette_ui, prompts, question_runtime, relics, relics_runtime, relics_ui, runtime_state, smash_bruteforce, sorting, spec_length_runtime, specs, stdio, ui, ui_runtime, writer, writer_runtime, youshallpass_runtime
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
    return IBN



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
    return getspec_runtime.run_getspec(
        getspec_runtime.GetSpecRuntime(
            emit=PRINT,
            candy=Candy,
            betterror=Betterror,
            pause=Pause,
            end=TheEnd,
            max_resolution=Max_Res,
            refresh_idat_byte_count=IDAT_Bytes_Nbr,
            current_year=lambda: datetime.now().year,
        ),
        getspec_runtime.GetSpecContext(
            idat_byte_count=IBN,
            brute_level=Brute_LvL,
            ihdr_color=IHDR_Color,
            ihdr_height=IHDR_Height,
            ihdr_width=IHDR_Width,
            pandora_box=PandoraBox,
            cornucopia=Cornucopia,
            pandemonium=Pandemonium,
            allchunks=tuple(ALLCHUNKS),
            skip_bad_crc=Skip_Bad_Crc,
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
            pause_error=PAUSEERROR,
        ),
        GetChunk,
        Mode,
        Fields,
        StructIndex,
        IterNbr,
    )


def Sync_Chunk_Info_Legacy_State(section=None):
    return chunk_state_runtime.sync_state_to_legacy(globals(), CHUNK_INFO_STATE, section)


def Sync_Chunk_Info_State_From_Legacy(section=None):
    return chunk_state_runtime.sync_legacy_to_state(CHUNK_INFO_STATE, globals(), section)


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
    return palette_runtime.sync_palette_legacy_state(globals(), palette_state)


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
    return palette_runtime.guess_palette_count(
        palette_runtime.PaletteCountGuessRuntime(
            cv2=cv2,
            numpy=np,
            image=Image,
            imagehash=imagehash,
            stderr_redirector=stderr_redirector,
            betterror=Betterror,
            emit=PRINT,
            candy=Candy,
            end=TheEnd,
            raw_print=print,
            side_notes=SideNotes,
        ),
        palette_runtime.PaletteCountGuessContext(
            x11_colors=tuple(X11_Colors),
            libpng_errors=tuple(LIBPNG_ERR),
            ihdr_depth=IHDR_Depht,
        ),
        bfn,
        afn,
    )



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

    PaletteSetup = palette_runtime.create_manual_palette_setup(
        palette_runtime.ManualPaletteSetupRuntime(
            candy=Candy,
            emit=PRINT,
            betterror=Betterror,
            cv2=cv2,
            numpy=np,
            image=Image,
            guess_palette_count=Guess_Palettes_Nbr,
        ),
        palette_runtime.ManualPaletteSetupContext(
            file=File,
            chunk_name=ChunkName,
            chunk_length=ChunkLength,
            data_offset=DataOffset,
            data_hex=DATAX,
            debug=DEBUG,
        ),
    )
    PaletteSession = PaletteSetup.session
    Before_New = PaletteSession.before
    After_New = PaletteSession.after
    wanabyte = PaletteSession.wanabyte
    Palette_nbr = PaletteSession.palette_count

    palette_state = PaletteSession.state
    Plte_Blst = palette_state.values

    im = PaletteSetup.image_array
    pil_image = PaletteSetup.pil_image

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
    return smash_bruteforce.run_legacy_smash_brute_brawl_from_namespace(
        globals(),
        File,
        ChunkName,
        ChunkLength,
        DataOffset,
        FromError,
        EditMode,
        BfMode,
        BruteCrc,
        BruteLength,
        OldCrc,
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
    return magic_runtime.run_find_magic(
        magic_runtime.FindMagicRuntime(
            candy=Candy,
            emit=PRINT,
            checkpoint=CheckPoint,
            end=TheEnd,
            betterror=Betterror,
            pause=Pause,
            spec_length=SpecLength,
            minibar=Minibar,
            side_notes=SideNotes,
            chunk_story=ChunkStory,
        ),
        magic_runtime.FindMagicContext(
            data_bytes=DATA_BYTES,
            data_hex=DATAX,
            chunks=tuple(CHUNKS),
            before_idat=tuple(BEFORE_IDAT),
            sample_name=Sample_Name,
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
            pause_error=PAUSEERROR,
        ),
    )


def FindFuckingMagic():
    return magic_runtime.run_find_fucking_magic(
        magic_runtime.FindMagicRuntime(
            candy=Candy,
            emit=PRINT,
            checkpoint=CheckPoint,
            end=TheEnd,
            betterror=Betterror,
            pause=Pause,
            spec_length=SpecLength,
            minibar=Minibar,
            side_notes=SideNotes,
        ),
        magic_runtime.FindMagicContext(
            data_bytes=DATA_BYTES,
            data_hex=DATAX,
            chunks=tuple(CHUNKS),
            before_idat=tuple(BEFORE_IDAT),
            sample_name=Sample_Name,
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
            pause_error=PAUSEERROR,
        ),
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
    return libpng_runtime.run_libpng_check(
        libpng_runtime.LibpngCheckRuntime(
            candy=Candy,
            emit=PRINT,
            checkpoint=CheckPoint,
        ),
        libpng_runtime.LibpngCheckContext(
            sample_name=Sample_Name,
            libpng_errors=LIBPNG_ERR,
            cv2_module=cv2,
            image_module=Image,
            stderr_redirector=stderr_redirector,
            warning_reader=KnownBadSrgbProfileWarning,
        ),
        file,
    )


def KnownBadSrgbProfileWarning(file):
    return libpng_runtime.run_known_bad_srgb_profile_warning(file)


def Double_Check(CType, ChunkLen, LastCType):
    return nearby_runtime.run_double_check(
        nearby_runtime.DoubleCheckRuntime(
            candy=Candy,
            emit=PRINT,
            end=TheEnd,
            nearby_chunk=NearbyChunk,
        ),
        nearby_runtime.DoubleCheckContext(
            data_hex=DATAX,
            sample_name=Sample_Name,
        ),
        CType,
        ChunkLen,
        LastCType,
    )


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
    return nearby_runtime.run_remove_extra_bytes_before_chunk(
        nearby_runtime.RemoveExtraBytesRuntime(
            save_clone=SaveClone,
            side_notes=SideNotes,
        ),
        nearby_runtime.RemoveExtraBytesContext(
            data_hex=DATAX,
            current_length_offset=CLoffI,
            known_chunks=tuple(CHUNKS),
            all_chunks=tuple(ALLCHUNKS),
        ),
        CType,
        LastCType,
        Excluded,
    )


def NearbyChunk(CType, ChunkLen, LastCType, DoubleCheck, FromError=None):
    return nearby_runtime.run_nearby_chunk(
        nearby_runtime.NearbyChunkRuntime(
            candy=Candy,
            emit=PRINT,
            checkpoint=CheckPoint,
            check_chunk_order=CheckChunkOrder,
            clean_extra_bytes=Remove_Extra_Bytes_Before_Chunk,
            double_check=Double_Check,
            fix_it_felix=FixItFelix,
            betterror=Betterror,
            pause=Pause,
            end=TheEnd,
            get_bad_critical=lambda: Bad_Critical,
            side_notes=SideNotes,
        ),
        nearby_runtime.NearbyChunkContext(
            data_hex=DATAX,
            chunks=tuple(CHUNKS),
            all_chunks=tuple(ALLCHUNKS),
            current_length_offset=CLoffI,
            current_length_offset_hex=CLoffX,
            current_data_offset_byte=CDoffB,
            chunks_history=tuple(Chunks_History),
            chunks_history_index=tuple(Chunks_History_Index),
            original_chunk_type=Orig_CT,
            original_chunk_length=Orig_CL,
            sample_name=Sample_Name,
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
            pause_error=PAUSEERROR,
        ),
        CType,
        ChunkLen,
        LastCType,
        DoubleCheck,
        FromError,
    )


def TheGoodPlace(Missplaced_Chunkname, Missplaced_Chunkpos, ToFix_Chunkname):
    return chunk_order_runtime.run_the_good_place(
        chunk_order_runtime.TheGoodPlaceRuntime(
            candy=Candy,
            emit=PRINT,
            checkpoint=CheckPoint,
            pause=Pause,
            end=TheEnd,
        ),
        chunk_order_runtime.TheGoodPlaceContext(
            data_hex=DATAX,
            chunks_history=tuple(Chunks_History),
            chunks_history_index=tuple(Chunks_History_Index),
            pandora_box=PandoraBox,
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
        ),
        Missplaced_Chunkname,
        Missplaced_Chunkpos,
        ToFix_Chunkname,
    )


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
    return name_shift_runtime.run_name_shift(
        name_shift_runtime.NameShiftRuntime(
            candy=Candy,
            emit=PRINT,
            pause=Pause,
            end=TheEnd,
            spec_length=SpecLength,
            side_notes=SideNotes,
            raw_print=print,
        ),
        name_shift_runtime.NameShiftContext(
            name_shift_context=runtime_state.name_shift_runtime_context(
                DATAX,
                CToffI,
                Chunks_History_Index,
                ALLCHUNKS,
            ),
            chunks_history=tuple(Chunks_History),
            debug=DEBUG,
            pause_debug=PAUSEDEBUG,
        ),
    )


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


def ChunkName_Runtime():
    return chunk_name_runtime.ChunkNameRuntime(
        candy=Candy,
        emit=PRINT,
        checkpoint=CheckPoint,
        pause=Pause,
        end=TheEnd,
        betterror=Betterror,
        name_shift=NameShift,
        check_chunk_order=CheckChunkOrder,
        nearby_chunk=NearbyChunk,
        save_clone=SaveClone,
        crc_matches=BruteChunk_Crc_Matches,
        save_auto_name=BruteChunk_Save_Auto_Name,
        unknown_private_critical_removal=lambda: FixItFelix_Try_Automatic_Repair(
            "unknown_private_critical_removal"
        ),
        ask_pokemon_choice=lambda count, on_invalid: prompts.ask_pokemon_choice(
            input,
            count,
            on_invalid=on_invalid,
        ),
    )


def ChunkName_Context():
    return chunk_name_runtime.ChunkNameContext(
        chunks=tuple(CHUNKS),
        all_chunks=tuple(ALLCHUNKS),
        chunks_history=tuple(Chunks_History),
        original_chunk_type=Orig_CT,
        original_chunk_length=Orig_CL,
        current_type_offset=CToffI,
        current_type_offset_hex=CToffX,
        idat_average_length=IDAT_Avg_Len,
        original_next_chunk=Orig_NC,
        next_chunk_offset=NCoffI,
        debug=DEBUG,
        pause_debug=PAUSEDEBUG,
    )


def BruteChunk(CType, LastCType, ChunkLen, FromError):
    return chunk_name_runtime.run_brute_chunk(
        ChunkName_Runtime(),
        ChunkName_Context(),
        CType,
        LastCType,
        ChunkLen,
        FromError,
    )


def CheckChunkName(ChunkType, ChunkLen, LastCType, Next=None):
    return chunk_name_runtime.run_check_chunk_name(
        ChunkName_Runtime(),
        ChunkName_Context(),
        ChunkType,
        ChunkLen,
        LastCType,
        Next,
    )


def SpecLength(chunk_name, chunk_length=None):
    return spec_length_runtime.run_spec_length(
        spec_length_runtime.SpecLengthRuntime(
            candy=Candy,
            emit=PRINT,
            end=TheEnd,
            get_spec=GetSpec,
            side_notes=SideNotes,
        ),
        chunk_name,
        chunk_length,
    )


def CheckLength(Cdata, Clen, Ctype):
    return chunk_validation_runtime.run_check_length(
        chunk_validation_runtime.ChunkValidationRuntime(
            candy=Candy,
            emit=PRINT,
            checkpoint=CheckPoint,
            end=TheEnd,
            chunk_story_add_if_no_next=chunk_story.add_if_no_next,
        ),
        chunk_validation_runtime.CheckLengthContext(
            data_bytes=DATA_BYTES,
            current_length_offset=CLoffI,
            previous_chunk=Chunks_History[-1],
            idat_average_length=IDAT_Avg_Len,
        ),
        Cdata,
        Clen,
        Ctype,
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
    return chunk_validation_runtime.run_checksum(
        chunk_validation_runtime.ChunkValidationRuntime(
            candy=Candy,
            emit=PRINT,
            checkpoint=CheckPoint,
            end=TheEnd,
            chunk_story_add_if_no_next=chunk_story.add_if_no_next,
        ),
        chunk_validation_runtime.ChecksumContext(
            current_length_offset=CLoffI,
            crc_offset=CrcoffI,
            crc_offset_hex=CrcoffX,
            original_chunk_type=Orig_CT,
            original_crc=Orig_CRC,
            original_length=Orig_CL,
            current_data_offset=CDoffI,
            chunks_history=Chunks_History,
            chunks_history_index=Chunks_History_Index,
            debug=DEBUG,
        ),
        Ctype,
        Cdata,
        Crc,
        next,
    )


def RemoveChunk(start,length,infos):
    return writer_runtime.run_remove_chunk(
        writer_runtime.ClonePatchRuntime(
            data_hex=DATAX,
            candy=Candy,
            emit=PRINT,
            betterror=Betterror,
            write_clone=WriteClone,
            set_show_must_go_on=lambda value: globals().__setitem__("Show_Must_Go_On", value),
        ),
        start,
        length,
        infos,
    )

def SaveClone(DataFix, start, end, infos):
    return writer_runtime.run_save_clone(
        writer_runtime.ClonePatchRuntime(
            data_hex=DATAX,
            candy=Candy,
            emit=PRINT,
            betterror=Betterror,
            write_clone=WriteClone,
            set_show_must_go_on=lambda value: globals().__setitem__("Show_Must_Go_On", value),
        ),
        DataFix,
        start,
        end,
        infos,
    )


def WriteClone(data,infos):
    return writer_runtime.run_write_clone(
        writer_runtime.build_write_clone_runtime(
            namespace=globals(),
            remember_current_sample=Pandemonium_Remember_Current_Sample,
            betterror=Betterror,
            end=TheEnd,
            candy=Candy,
            emit=PRINT,
            pause=Pause,
            summarise=Summarise,
            exit_process=sys.exit,
            side_notes=SideNotes,
        ),
        writer_runtime.build_write_clone_context(globals()),
        data,
        infos,
    )


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
    return checkpoint_runtime.run_checkpoint(
        checkpoint_runtime.CheckPointEntryRuntime(
            candy=Candy,
            emit=PRINT,
            pause_debug=Pause,
            record_finding=CheckPoint_Record_Finding,
            apply_action=CheckPoint_Apply_Action_Decision,
            pause_error=Pause,
        ),
        checkpoint_runtime.CheckPointEntryContext(
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
            pandora_keys=tuple(PandoraBox),
            debug=DEBUG,
            pause_debug_enabled=PAUSEDEBUG,
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
    MainOptions = main_runtime.apply_main_cli_options(
        main_runtime.build_cli_options_runtime(
            print_error=print,
            exit_process=sys.exit,
            make_dirs=os.makedirs,
            abspath=os.path.abspath,
            join=os.path.join,
            stderr=sys.stderr,
        ),
        Args,
        unknown,
        argv_len=len(sys.argv),
        parser=parser,
        current_cloneswar=CLONESWAR,
        current_crash=CRASH,
    )
    if MainOptions is None:
        return
    globals().update(main_runtime.legacy_globals_from_main_cli_options(MainOptions))

    while True:

        ClearScreenState = main_runtime.run_main_clear_screen(
            main_runtime.build_clear_screen_runtime(
                stderr_write=sys.stderr.write,
                system=os.system,
                os_name=os.name,
            ),
            main_runtime.MainClearScreenContext(
                clear=CLEAR,
                fir_start=FirStart,
            ),
        )
        FirStart = ClearScreenState.fir_start
        MainLoopReset = main_runtime.reset_main_loop_state(
            main_runtime.build_loop_reset_runtime(
                namespace=globals(),
                reset_chunk_info_idat=CHUNK_INFO_STATE.reset_idat,
                sync_chunk_info_legacy_state=Sync_Chunk_Info_Legacy_State,
                banner=Chunklate,
            )
        )
        TmpFixIHDR = MainLoopReset.tmp_fix_ihdr
        # IFOP = []

        LoadedMainSample = main_runtime.load_main_sample(
            main_runtime.build_sample_runtime(
                basename=os.path.basename,
                load_sample_data=lambda sample: runtime_state.load_sample_data(sample, opener=open),
                raw_print=print,
                candy=Candy,
                emit=PRINT,
                betterror=Betterror,
                exit_process=sys.exit,
            ),
            main_runtime.MainSampleContext(
                sample=Sample,
                cloneswar=CLONESWAR,
            ),
        )
        if LoadedMainSample is None:
            return
        Sample = LoadedMainSample.sample
        Sample_Name = LoadedMainSample.sample_name
        CLONESWAR = LoadedMainSample.cloneswar
        DATA_BYTES = LoadedMainSample.data_bytes
        DATAX = LoadedMainSample.data_hex
        Offset = FindMagic()
        main_runtime.run_main_chunk_walk(
            main_runtime.build_chunk_walk_runtime(
                namespace=globals(),
                chunk_by_chunk=ChunkbyChunk,
                check_length=CheckLength,
                check_chunk_name=CheckChunkName,
                get_info=GetInfo,
                checksum=Checksum,
                fix_it_felix=FixItFelix,
            ),
            main_runtime.MainChunkWalkContext(
                offset=Offset,
                data_hex=DATAX,
            ),
        )

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
