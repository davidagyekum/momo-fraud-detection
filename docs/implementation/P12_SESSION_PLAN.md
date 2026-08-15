# P12 Session Plan — CNN receipt-tampering classifier

Base: `main` at `2a9f1eb0aebff4770d4a1717db42d09ead91f97b`

Scope boundary:

1. Define and test the exact 224×224 RGB preprocessing and train-only augmentation policy.
2. Implement the TensorFlow/Keras MobileNetV3Small training, evaluation, packaging and Colab workflow without executing reportable training locally.
3. Implement a private, hash-verified image-model adapter with explicit unavailable/error states and ADMIN-only lifecycle integration.
4. Preserve P10 source-group splits, controlled-only labels and immutable provenance.
5. Stop and notify the project owner before the first reportable P12 training cell is run in Google Colab.

Out of scope before owner approval: measured CNN metrics, model acceptance, activation, `.keras` artifact evidence, production/provider accuracy claims and P13 aggregation.
