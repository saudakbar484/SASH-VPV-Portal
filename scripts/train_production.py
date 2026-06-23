"""Stage 2: production training — all 244 classes, deployment checkpoint."""
import _bootstrap  # noqa: F401

from palm_vein.config import CHECKPOINT_PRODUCTION
from palm_vein.train import main

if __name__ == "__main__":
    main(
        max_epochs=60,
        batch_size=16,
        held_out_fold=None,
        checkpoint_path=CHECKPOINT_PRODUCTION,
    )
