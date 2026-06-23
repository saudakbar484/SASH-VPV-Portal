"""Stage 1: validation training — fold 0 held out for open-set evaluation."""
import _bootstrap  # noqa: F401

from palm_vein.config import CHECKPOINT_VALIDATION
from palm_vein.train import main

if __name__ == "__main__":
    main(
        max_epochs=60,
        batch_size=16,
        held_out_fold=0,
        checkpoint_path=CHECKPOINT_VALIDATION,
    )
