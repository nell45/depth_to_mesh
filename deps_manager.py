import importlib
import subprocess
import sys

# (import_name, pip_name) pairs
PACKAGES = [
    ("PIL",             "Pillow"),
    ("transformers",    "transformers"),
    ("huggingface_hub", "huggingface_hub"),
    ("safetensors",     "safetensors"),
    ("timm",            "timm"),
    ("accelerate",      "accelerate"),
]


def is_installed(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def all_installed() -> bool:
    return all(is_installed(name) for name, _ in PACKAGES)


def install_all() -> tuple[bool, str]:
    """
    Run pip to install all required packages.
    Returns (success, log_text).
    Blocks until pip exits — expected to be called from an operator.
    """
    pip_names = [pip for _, pip in PACKAGES]
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install"] + pip_names,
        capture_output=True,
        text=True,
    )
    importlib.invalidate_caches()
    log = result.stdout + result.stderr
    return result.returncode == 0, log
