from __future__ import annotations

from typing import Any


def normalize_sections(section: str | list[str] | tuple[str, ...] | set[str] | None) -> tuple[bool, set[str]]:
    if section is None:
        return True, set()
    if isinstance(section, str):
        return False, {section}
    return False, set(section or ())


def legacy_values_from_state(state: Any, section: Any = None) -> dict[str, Any]:
    sync_all, sections = normalize_sections(section)
    values: dict[str, Any] = {}

    if sync_all or "ihdr" in sections:
        values.update(
            IHDR_Width=state.ihdr_width,
            IHDR_Height=state.ihdr_height,
            IHDR_Depht=state.ihdr_depth,
            IHDR_Color=state.ihdr_color,
            IHDR_Method=state.ihdr_method,
            IHDR_Filter=state.ihdr_filter,
            IHDR_Interlace=state.ihdr_interlace,
        )

    if sync_all or "idat" in sections:
        values.update(
            IDAT_Bytes_Len=state.idat_bytes_len,
            IDAT_Datastream=state.idat_datastream,
            idatcounter=state.idat_counter,
            IDAT_Bytes_Len_History=list(state.idat_bytes_len_history),
            IDAT_Avg_Len=state.idat_avg_len,
        )

    if sync_all or "plte" in sections:
        values.update(
            PLTE_R=list(state.plte_r),
            PLTE_G=list(state.plte_g),
            PLTE_B=list(state.plte_b),
        )

    if sync_all or "splt" in sections:
        values.update(
            sPLT_Name=list(state.splt_name),
            sPLT_Depht=list(state.splt_depth),
            sPLT_Red=list(state.splt_red),
            sPLT_Green=list(state.splt_green),
            sPLT_Blue=list(state.splt_blue),
            sPLT_Alpha=list(state.splt_alpha),
            sPLT_Freq=list(state.splt_freq),
        )

    if sync_all or "trns" in sections:
        values["tRNS_Index"] = list(state.trns_index)

    if sync_all or "pcal" in sections:
        values.update(
            pCAL_Param=list(state.pcal_param),
            pCAL_Key=state.pcal_key,
            pCAL_Zero=state.pcal_zero,
            pCAL_Max=state.pcal_max,
            pCAL_Eq=state.pcal_eq,
            pCAL_PNBR=state.pcal_pnbr,
        )

    if sync_all or "chrm" in sections:
        values.update(
            cHRM_WhiteX=state.chrm_white_x,
            cHRM_WhiteY=state.chrm_white_y,
            cHRM_Redx=state.chrm_red_x,
            cHRM_Redy=state.chrm_red_y,
            cHRM_Greenx=state.chrm_green_x,
            cHRM_Greeny=state.chrm_green_y,
            cHRM_Bluex=state.chrm_blue_x,
            cHRM_Bluey=state.chrm_blue_y,
        )

    if sync_all or "iccp" in sections:
        values.update(
            iCCP_Name=state.iccp_name,
            iCCP_Method=state.iccp_method,
            iCCP_Profile=state.iccp_profile,
        )

    if sync_all or "sbit" in sections:
        values.update(
            sBIT_Gray=state.sbit_gray,
            sBIT_TrueR=state.sbit_true_r,
            sBIT_TrueG=state.sbit_true_g,
            sBIT_TrueB=state.sbit_true_b,
            sBIT_GrayScale=state.sbit_gray_scale,
            sBIT_GrayAlpha=state.sbit_gray_alpha,
            sBIT_TrueAlphaR=state.sbit_true_alpha_r,
            sBIT_TrueAlphaG=state.sbit_true_alpha_g,
            sBIT_TrueAlphaB=state.sbit_true_alpha_b,
            sBIT_TrueAlpha=state.sbit_true_alpha,
        )

    if sync_all or "gifg" in sections:
        values.update(
            gIFgM=state.gifg_disposal_method,
            gIFgU=state.gifg_user_input_flag,
            gIFgT=state.gifg_delay_time,
        )

    if sync_all or "gifx" in sections:
        values.update(
            gIFID=state.gifx_application_identifier,
            gIFCD=state.gifx_authentication_code,
            gIFDT=state.gifx_application_data,
        )

    if sync_all or "ster" in sections:
        values["sTER"] = state.ster_mode

    if sync_all or "text" in sections:
        values.update(
            tEXt_Key_List=list(state.text_key_list),
            tEXt_Str_List=list(state.text_str_list),
            tEXt_Key=state.text_key,
            tEXt_Text=state.text_text,
        )

    if sync_all or "ztxt" in sections:
        values.update(
            zTXt_Key_List=list(state.ztxt_key_list),
            zTXt_Str_List=list(state.ztxt_str_list),
            zTXt_Key=state.ztxt_key,
            zTXt_Text=state.ztxt_text,
        )

    if sync_all or "itxt" in sections:
        values.update(
            iTXt_Key_List=list(state.itxt_key_list),
            iTXt_String_List=list(state.itxt_string_list),
            iTXt_Key=state.itxt_key,
            iTXt_String=state.itxt_string,
        )

    if sync_all or "exif" in sections:
        values["eXIf_endian"] = state.exif_endian

    return values


def sync_state_to_legacy(namespace: dict[str, Any], state: Any, section: Any = None) -> None:
    namespace.update(legacy_values_from_state(state, section))


def sync_legacy_to_state(state: Any, namespace: dict[str, Any], section: Any = None) -> None:
    sync_all, sections = normalize_sections(section)

    if sync_all or "ihdr" in sections:
        state.set_ihdr_legacy(
            height=namespace["IHDR_Height"],
            width=namespace["IHDR_Width"],
            depth=namespace["IHDR_Depht"],
            color=namespace["IHDR_Color"],
            method=namespace["IHDR_Method"],
            filter_method=namespace["IHDR_Filter"],
            interlace=namespace["IHDR_Interlace"],
        )

    if sync_all or "plte" in sections:
        state.set_plte_legacy(
            namespace["PLTE_R"],
            namespace["PLTE_G"],
            namespace["PLTE_B"],
        )

    if sync_all or "splt" in sections:
        state.set_splt_legacy(
            names=namespace["sPLT_Name"],
            depths=namespace["sPLT_Depht"],
            red=namespace["sPLT_Red"],
            green=namespace["sPLT_Green"],
            blue=namespace["sPLT_Blue"],
            alpha=namespace["sPLT_Alpha"],
            freq=namespace["sPLT_Freq"],
        )
