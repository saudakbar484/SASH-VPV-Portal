# Model checkpoints

| File | Purpose |
|------|---------|
| `production/checkpoint_production_full.pt` | **Deploy this** — trained on all 244 classes |
| `validation/checkpoint_validation_fold0_held_out.pt` | Open-set validation run (metrics reference) |
| `legacy/checkpoint.pt` | Original CPU 40-class baseline |

Load in code:

```python
from palm_vein.config import CHECKPOINT_PRODUCTION
from palm_vein.deployment import PalmVeinBiometricSystem

system = PalmVeinBiometricSystem(CHECKPOINT_PRODUCTION)
```
