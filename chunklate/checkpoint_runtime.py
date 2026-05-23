from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class CheckPointRuntime:
    write_clone: LegacyCall
    dummy_chunk: LegacyCall
    summarise: LegacyCall
    find_fucking_magic: LegacyCall
    check_chunk_name: LegacyCall
    save_clone: LegacyCall
    fix_it_felix: LegacyCall
    relics: LegacyCall
    smash_brute_brawl: LegacyCall
    candy: LegacyCall
    emit: LegacyCall
    end: LegacyCall
    question: LegacyCall
    print_libpng_critical: LegacyCall
    discard_libpng_warning: LegacyCall
    libpng_end_success: LegacyCall


def run_write_clone(runtime: CheckPointRuntime, toolkit: tuple[Any, ...]) -> tuple[bool, Any]:
    return True, runtime.write_clone(toolkit[0], "-About to save.")


def run_dummy_chunk_from_the_good_place(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
    info: Any,
) -> tuple[bool, Any]:
    return True, runtime.dummy_chunk(toolkit[0], toolkit[1], toolkit[2], toolkit[3], info)


def run_return_value(return_value: Any) -> tuple[bool, Any]:
    return True, return_value


def run_summarise_and_write_clone(
    runtime: CheckPointRuntime,
    summary: Any,
    toolkit: tuple[Any, ...],
) -> tuple[bool, Any]:
    runtime.summarise(summary)
    return True, runtime.write_clone(toolkit[0], "-About to save.")


def run_find_fucking_magic(runtime: CheckPointRuntime) -> tuple[bool, Any]:
    return True, runtime.find_fucking_magic()


def run_check_chunk_name(
    runtime: CheckPointRuntime,
    raw_next_chunk: Any,
    chunk: Any,
    toolkit: tuple[Any, ...],
) -> tuple[bool, Any]:
    return True, runtime.check_chunk_name(raw_next_chunk, int(toolkit[0], 16), chunk, True)


def run_save_clone(runtime: CheckPointRuntime, toolkit: tuple[Any, ...]) -> tuple[bool, Any]:
    return True, runtime.save_clone(toolkit[0], toolkit[1], toolkit[2], toolkit[3])


def run_save_clone_missing_bytes(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
) -> tuple[bool, Any]:
    return True, runtime.save_clone(
        toolkit[0],
        toolkit[2],
        toolkit[1] + toolkit[2],
        "Fixing Missing bytes corruption",
    )


def run_fix_it_felix_continue(runtime: CheckPointRuntime, return_value: Any) -> tuple[bool, Any]:
    runtime.fix_it_felix(return_value)
    return False, None


def run_fix_it_felix_return(runtime: CheckPointRuntime, return_value: Any) -> tuple[bool, Any]:
    return True, runtime.fix_it_felix(return_value)


def run_libpng_warning_relics(runtime: CheckPointRuntime, info: Any) -> tuple[bool, Any]:
    runtime.print_libpng_critical(info)
    runtime.candy("Cowsay", "Ah found something !", "good")
    return True, runtime.relics(info)


def run_discard_libpng_warning(
    runtime: CheckPointRuntime,
    action: str,
    info: Any,
) -> tuple[bool, Any]:
    runtime.print_libpng_critical(info)
    runtime.candy("Cowsay", "Bah that's just a warning who cares ?! !", "good")
    runtime.candy("Cowsay", "im removing it ..", "good")
    runtime.discard_libpng_warning()
    if action == "discard_libpng_warning_and_end":
        runtime.libpng_end_success(
            "Well maybe i am missing something but as for my abilities my job is done here!"
        )
    return False, None


def run_libpng_end_success(runtime: CheckPointRuntime) -> tuple[bool, Any]:
    runtime.libpng_end_success(
        "Well maybe i am missing something but as far as my current abilities goes the job is done for me here!"
    )
    return False, None


def run_smash_brute_brawl_relaunch(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
    from_error: Any,
    *,
    bf_mode: Any = None,
    has_old_crc: bool = False,
    old_crc: Any = None,
) -> Any:
    kwargs = {
        "EditMode": toolkit[4],
        "BfMode": bf_mode if bf_mode is not None else toolkit[5],
        "BruteCrc": toolkit[6],
        "BruteLength": toolkit[7],
    }
    if has_old_crc:
        kwargs["OldCrc"] = old_crc
    return runtime.smash_brute_brawl(
        toolkit[0],
        toolkit[1],
        toolkit[2],
        toolkit[3],
        from_error,
        **kwargs,
    )


def run_smash_brute_brawl_retry_ihdr(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
    from_error: Any,
    brute_level: int,
) -> tuple[bool, Any]:
    runtime.candy(
        "Cowsay",
        "One More Try Hang In There ! Increasing Bruteforce Lvl! (%s/3)"
        % brute_level,
        "bad",
    )
    run_smash_brute_brawl_relaunch(runtime, toolkit, from_error)
    return False, None


def ask_smash_brute_brawl_twobytes_retry(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
    *,
    brute_level: int,
    eta: int,
    ihdr_interlace: str,
) -> Any:
    runtime.candy("Cowsay", "Too bad that was the easy way ..", "bad")
    runtime.candy(
        "Cowsay",
        "I may increase the BruteForce Level in case there is another corrupted bytes that iv missed.",
        "com",
    )
    runtime.candy("Cowsay", "But this will take litterally forever...i mean like this :", "bad")
    estimation = eta * toolkit[2]
    if toolkit[1] == b"IDAT":
        estimation *= 3
    from datetime import timedelta

    runtime.emit("-BruteForce Estimated Time : %s\n" % str(timedelta(seconds=estimation)))
    runtime.candy("Cowsay", "And of course this may fail .. Do you still want to try ?", "com")
    if toolkit[1] == b"IDAT" and ihdr_interlace == "1":
        runtime.candy(
            "Cowsay",
            "Since this is an IDAT chunk i may have another solution just answer: 'No' then.",
            "good",
        )

    answer = runtime.question(skipauto=True)
    if answer:
        runtime.candy(
            "Cowsay",
            "One More Try Hang In There ! Increasing Bruteforce Lvl! (%s/1)"
            % brute_level,
            "bad",
        )
    return answer


def ask_smash_brute_brawl_dummy_idat_fallback(runtime: CheckPointRuntime) -> Any:
    runtime.candy(
        "Cowsay",
        "So let's face it ..I wont be able to recover that IDAT before one of us die.",
        "bad",
    )
    runtime.candy("Cowsay", "But i could create another one full of black pixels..", "com")
    runtime.candy("Cowsay", "This way i hope we could end up with a valid png.", "good")
    runtime.candy(
        "Cowsay",
        "At the cost of one beautiful white rectangle in the middle of that image..",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "What do you say ? Otherwise Chunklate is going to exit .",
        "com",
    )
    return runtime.question()


def run_smash_brute_brawl_end_failed_noncustom(
    runtime: CheckPointRuntime,
) -> tuple[bool, Any]:
    runtime.candy(
        "Cowsay",
        "Iv tried everything , im out of option sorry ..",
        "bad",
    )
    runtime.end()
    return False, None


def ask_smash_brute_brawl_custom_brutus(runtime: CheckPointRuntime) -> Any:
    runtime.candy("Cowsay", "Too bad that was the easy way ..", "bad")
    runtime.candy("Cowsay", "Wanna try to bruteforce the entire chunk instead ?", "com")
    return runtime.question()


def run_smash_brute_brawl_end_unhandled(runtime: CheckPointRuntime) -> tuple[bool, Any]:
    runtime.end()
    return False, None
