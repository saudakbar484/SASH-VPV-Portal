"""CPU smoke-test training run (small subset)."""
import _bootstrap  # noqa: F401

from palm_vein.train import main

if __name__ == "__main__":
    main(max_epochs=2, batch_size=4, max_train_rows=40, max_val_rows=20)
