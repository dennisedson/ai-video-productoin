import os, sys, tempfile, shutil, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
sys.path.insert(0, STUDIO)


def temp_root():
    """A temporary repo root with an empty videos/ folder; core reads STUDIO_ROOT."""
    d = tempfile.mkdtemp(prefix="studio-test-")
    os.makedirs(os.path.join(d, "videos"))
    os.environ["STUDIO_ROOT"] = d
    import core
    importlib.reload(core)
    return d, core


def cleanup(d):
    shutil.rmtree(d, ignore_errors=True)
    os.environ.pop("STUDIO_ROOT", None)
