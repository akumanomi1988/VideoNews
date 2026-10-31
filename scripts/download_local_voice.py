"""Download pinned official Kokoro assets; never load or execute downloaded code."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
ASSETS = {
    "kokoro-v1.0.onnx": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("output/voice_lab/models"))
    target = parser.parse_args().output_dir
    target.mkdir(parents=True, exist_ok=True)
    records = []
    for name, expected in ASSETS.items():
        path = target / name
        if not path.is_file() or checksum(path) != expected:
            temporary = path.with_suffix(path.suffix + ".part")
            try:
                request = Request(BASE + name, headers={"User-Agent": "VideoNews-Voice-Setup"})
                with urlopen(request, timeout=180) as response:
                    with temporary.open("wb") as stream:
                        total = 0
                        while chunk := response.read(1024 * 1024):
                            total += len(chunk)
                            if total > 512 * 1024 * 1024:
                                raise RuntimeError("Voice asset exceeded its download limit")
                            stream.write(chunk)
                if checksum(temporary) != expected:
                    raise RuntimeError(f"Checksum mismatch for {name}")
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        records.append({"file": name, "sha256": expected, "bytes": path.stat().st_size, "url": BASE + name})
    references = {
        "MODEL_CARD.md": "https://huggingface.co/hexgrad/Kokoro-82M/raw/main/README.md",
        "VOICES.md": "https://huggingface.co/hexgrad/Kokoro-82M/raw/main/VOICES.md",
        "RUNTIME_LICENSE.txt": "https://raw.githubusercontent.com/thewh1teagle/kokoro-onnx/main/LICENSE",
        "APACHE-2.0.txt": "https://www.apache.org/licenses/LICENSE-2.0.txt",
    }
    for name, url in references.items():
        with urlopen(Request(url, headers={"User-Agent": "VideoNews-Voice-Setup"}), timeout=30) as response:
            content = response.read(1024 * 1024)
        (target / name).write_bytes(content)
    (target / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps({"models_ready": True, "directory": str(target), "assets": records}))


if __name__ == "__main__":
    main()
