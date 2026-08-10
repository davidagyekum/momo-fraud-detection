# Model Card — image-mobilenetv3-controlled-v1

Controlled MobileNetV3Small tamper detector. Human review is required.
It must not be described as provider-wide, calibrated or production-ready.
The configured acceptance gate failed. This artifact must not be registered or activated.

- Training commit: `02d8967136853c5c46eaa0babe44a7327c843a32`
- Artifact SHA-256: `3d074298835a28a9af92fca8b50cc618dc8eb67585e2b312c261121f43a70046`
- Preprocessing SHA-256: `8510a396d3115887f8ebff88414f75f9ea5b353f375d93cfdf65f488d55df616`
- Held-out samples/groups: `2` / `1`
- Held-out macro F1: `0.333333`
- Acceptance minimum/status: `0.85` / `FAILED`
- Threshold selected on validation: `0.05`
- CPU median/p95 ms: `110.137` / `171.081`

The evidence corpus contains only six generic controlled source groups.
Both held-out images were predicted `CONTROLLED_TAMPERED`; the result is preserved only as failed experimental pipeline evidence.
