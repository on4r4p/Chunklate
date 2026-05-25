from __future__ import annotations

from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Any, Callable

from . import specs


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class SpecLengthRuntime:
    candy: LegacyCall
    emit: LegacyCall
    end: LegacyCall
    get_spec: LegacyCall
    side_notes: MutableSequence[str]


def run_spec_length(
    runtime: SpecLengthRuntime,
    chunk_name: bytes,
    chunk_length: str | None = None,
) -> Any:
    if chunk_length:
        runtime.candy("Title", "Get Length from Spec:")
        runtime.candy("Cowsay", "Kay ..Just Checking if the length part is legit..", "com")

    chunklen_spec = runtime.get_spec(chunk_name, "Spec", Fields=["Length"])[0]

    if type(chunklen_spec) == tuple:
        runtime.emit(runtime.candy("Color", "yellow", "\n-ToDotuple"))
        runtime.end()
    else:
        length_check = specs.check_spec_length(chunklen_spec, chunk_length)
        real_length = length_check.real_length
        if not length_check.has_provided_length:
            return length_check.returned_length

        runtime.emit("-Real %s Length: %s " % (chunk_name, real_length))
        if length_check.matches:
            runtime.candy("Cowsay", "Looks good to me !", "good")
            runtime.side_notes.append("-SpecLength:Giving correct length:  %s -" % chunk_length)
            return length_check.returned_length

        runtime.emit("-Given %s Length was : %s " % (chunk_name, chunk_length))
        runtime.candy("Cowsay", "Length part is corrupted!", "bad")
        runtime.side_notes.append("-SpecLength:Giving correct length:  %s -" % real_length)
        runtime.emit("\n-Returning correct fixed length :%s" % real_length)
        return length_check.returned_length

    runtime.emit(runtime.candy("Color", "yellow", "\n-Requested Spec %s has not been found." % chunk_name))
    runtime.emit(runtime.candy("Color", "yellow", "\n-ToDo"))
    runtime.end()
