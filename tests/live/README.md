# Live capture testing

Drop your real-time NIR palm photos here before running `scripts/live_test.py`.

```
tests/live/
├── enroll/     # 2–3 enrollment captures per identity
└── probe/      # verification / identification probe image(s)
```

Supported format: grayscale or color PNG/JPG from the same NIR sensor pipeline (480×640 typical).

In the next step, provide full paths to your photos and we will run verification against `checkpoint_production_full.pt`.
