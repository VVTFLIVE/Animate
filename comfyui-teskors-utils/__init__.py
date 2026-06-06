"""Backward-compatible shim — all logic now lives in NEW-UTILS."""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_NEW_UTILS_DIR = os.path.join(_REPO_ROOT, "NEW-UTILS")

for _p in (_REPO_ROOT, _NEW_UTILS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from save_load_pose import TSSavePoseDataAsPickle, TSLoadPoseDataPickle  # noqa: E402
from openpose_smoother import KPSSmoothPoseDataAndRender  # noqa: E402
from load_video_batch import LoadVideoBatchListFromDir  # noqa: E402
from rename_files import RenameFilesInDir  # noqa: E402

NODE_CLASS_MAPPINGS = {
    "TSSavePoseDataAsPickle": TSSavePoseDataAsPickle,
    "TSLoadPoseDataPickle": TSLoadPoseDataPickle,
    "TSPoseDataSmoother": KPSSmoothPoseDataAndRender,
    "TSLoadVideoBatchListFromDir": LoadVideoBatchListFromDir,
    "TSRenameFilesInDir": RenameFilesInDir,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TSSavePoseDataAsPickle": "TS Save Pose Data (PKL)",
    "TSLoadPoseDataPickle": "TS Load Pose Data (PKL)",
    "TSPoseDataSmoother": "TS Pose Data Smoother",
    "TSLoadVideoBatchListFromDir": "TS Load Video Batch List From Dir",
    "TSRenameFilesInDir": "TS Rename Files In Dir",
}
