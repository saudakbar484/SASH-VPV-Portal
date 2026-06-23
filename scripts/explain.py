import runpy

import _bootstrap  # noqa: F401

if __name__ == "__main__":
    runpy.run_module("palm_vein.explainability", run_name="__main__")
