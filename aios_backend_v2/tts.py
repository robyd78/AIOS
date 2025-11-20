import asyncio
import os
import shutil
import tempfile

from .errors import ServiceUnavailableError


def _get_voice_path() -> str:
    voice = os.getenv("PIPER_VOICE") or os.getenv("PIPER_MODEL")
    if not voice or not os.path.exists(voice):
        raise ServiceUnavailableError(
            "Piper voice/model missing: set PIPER_VOICE or PIPER_MODEL to a .onnx file"
        )
    return voice


async def piper_say(text: str) -> bytes:
    piper_bin = shutil.which("piper")
    if not piper_bin:
        raise ServiceUnavailableError("Piper binary not found in PATH")

    voice_path = _get_voice_path()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name

    try:
        process = await asyncio.create_subprocess_exec(
            piper_bin,
            "-m",
            voice_path,
            "-f",
            out_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate(text.encode("utf-8"))
    except FileNotFoundError as exc:
        raise ServiceUnavailableError("Piper executable not found") from exc

    if process.returncode != 0:
        raise ServiceUnavailableError(
            f"Piper failed with code {process.returncode}: {stderr.decode('utf-8', 'ignore')[:400]}"
        )

    try:
        with open(out_path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        raise ServiceUnavailableError("Unable to read Piper output") from exc
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass

    if not data.startswith(b"RIFF"):
        raise ServiceUnavailableError("TTS produced non-WAV data")

    return data
