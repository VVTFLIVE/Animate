import os
import time
import pickle
import glob
import folder_paths


# ---------------------------------------------------------------------------
# Restricted unpickler — prevents arbitrary code execution from .pkl files
# ---------------------------------------------------------------------------
_ALLOWED_MODULES = frozenset({
    "numpy", "numpy.core", "numpy.core.multiarray", "numpy.core.numeric",
    "numpy._core", "numpy._core.multiarray", "numpy._core.numeric",
    "numpy._globals",
    "torch", "torch._utils",
    "collections", "builtins", "_codecs",
})

_ALLOWED_GLOBALS = frozenset({
    ("numpy", "ndarray"), ("numpy", "dtype"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy.core.multiarray", "scalar"),
    ("numpy.core.numeric", "_frombuffer"),
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy._core.numeric", "_frombuffer"),
    ("torch", "FloatStorage"), ("torch", "LongStorage"),
    ("torch", "IntStorage"), ("torch", "DoubleStorage"),
    ("torch", "HalfStorage"), ("torch", "BFloat16Storage"),
    ("torch._utils", "_rebuild_tensor_v2"),
    ("collections", "OrderedDict"),
    ("builtins", "set"), ("builtins", "frozenset"),
    ("_codecs", "encode"),
})


class _RestrictedUnpickler(pickle.Unpickler):
    """Only allow known-safe numpy/torch types to be deserialized."""

    def find_class(self, module: str, name: str):
        # Remap numpy._core -> numpy.core (version compat)
        if module.startswith("numpy._core"):
            module = module.replace("numpy._core", "numpy.core", 1)
        if module.startswith("numpy._globals"):
            module = module.replace("numpy._globals", "numpy", 1)

        if (module, name) in _ALLOWED_GLOBALS:
            return super().find_class(module, name)

        # Allow any attribute access within allowed modules for dtype etc.
        if module in _ALLOWED_MODULES:
            return super().find_class(module, name)

        raise pickle.UnpicklingError(
            f"Restricted unpickler refused to load: {module}.{name}"
        )


def _safe_pickle_load(f):
    """Load a pickle file with restricted deserialization."""
    return _RestrictedUnpickler(f).load()


# ---------------------------------------------------------------------------
# Path safety helpers
# ---------------------------------------------------------------------------
def _validate_path_within(path: str, allowed_root: str) -> str:
    """Resolve path and ensure it stays within allowed_root. Raises ValueError on escape."""
    resolved = os.path.realpath(path)
    root = os.path.realpath(allowed_root)
    if not resolved.startswith(root + os.sep) and resolved != root:
        raise ValueError(
            f"Path traversal blocked: '{path}' resolves outside allowed directory."
        )
    return resolved


def _ensure_output_dir():
    out_dir = folder_paths.get_output_directory()
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


# -------------------------
# UI: list PKL/PT under input/** (recursive)
# -------------------------
def _list_all_pkl_under_input():
    inp = folder_paths.get_input_directory()
    exts = (".pkl", ".pickle", ".pt")

    files = []
    for ext in exts:
        pattern = os.path.join(inp, "**", f"*{ext}")
        files.extend(glob.glob(pattern, recursive=True))

    rel = []
    for f in files:
        if os.path.isfile(f):
            r = os.path.relpath(f, inp).replace("\\", "/")
            rel.append(r)

    rel = sorted(set(rel))
    return rel if rel else [""]


def _abs_from_input(rel_path: str) -> str:
    inp = folder_paths.get_input_directory()
    candidate = os.path.join(inp, rel_path).replace("\\", "/")
    return _validate_path_within(candidate, inp)


def _make_unique_path(base_path: str) -> str:
    """
    If file exists, append incremental suffix:
    pose_data.pkl
    pose_data_0001.pkl
    pose_data_0002.pkl
    """
    if not os.path.exists(base_path):
        return base_path

    directory = os.path.dirname(base_path)
    name = os.path.basename(base_path)
    base, ext = os.path.splitext(name)

    idx = 1
    while True:
        new_name = f"{base}_{idx:04d}{ext}"
        new_path = os.path.join(directory, new_name)
        if not os.path.exists(new_path):
            return new_path
        idx += 1


def _default_filename(prefix: str, ext: str):
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}{ext}"


class TSSavePoseDataAsPickle:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pose_data": ("POSEDATA",),
                "filename": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_path",)
    FUNCTION = "save"
    CATEGORY = "save"

    def save(self, pose_data, filename=""):
        out_dir = _ensure_output_dir()
        filename = (filename or "").strip()
        if not filename:
            filename = _default_filename("pose_data", ".pkl")
        if not filename.lower().endswith((".pkl", ".pickle")):
            filename += ".pkl"

        # Block path traversal in user-provided filename
        candidate = os.path.join(out_dir, filename)
        _validate_path_within(candidate, out_dir)
        abs_path = _make_unique_path(candidate)

        with open(abs_path, "wb") as f:
            pickle.dump(pose_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        return (abs_path,)


class TSLoadPoseDataPickle:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # dropdown + Upload, recursive input/**
                "file": (_list_all_pkl_under_input(),),
            }
        }

    RETURN_TYPES = ("POSEDATA",)
    RETURN_NAMES = ("pose_data",)
    FUNCTION = "load"
    CATEGORY = "load"

    def load(self, file):
        if not isinstance(file, str) or not file.strip():
            raise ValueError("TS PoseData Pickle: Please select a .pkl/.pt file.")

        abs_path = _abs_from_input(file)
        if not os.path.isfile(abs_path):
            raise ValueError(f"TS PoseData Pickle: File not found: {abs_path}")

        with open(abs_path, "rb") as f:
            pose_data = _safe_pickle_load(f)

        return (pose_data,)
