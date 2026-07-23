# ASL data sources and pose pipelines

SignOra targets **American Sign Language (ASL)** → English. The datasets and pose tools serve different roles.

## Sign language data (what miners learn from)

| Source | Language | Content | Role in SignOra |
|--------|----------|---------|-----------------|
| **WLASL** | **ASL** | 2,000 word-level glosses, real Deaf signers on video | Stage 1–2 vocabulary, corpus anchor, Comp B training |
| **YouTube-ASL** | **ASL** | Open-domain ASL ↔ English parallel captions | Stage 3+ phrases, broader coverage |
| **Layer 2 captures** | **ASL** | Known-plaintext Signer recordings | Live challenges, ground truth |

WLASL glosses are ASL sign labels (e.g. `thank_you` = the ASL sign for “thank you”). English text in training pairs is the **translation target**, not the signed language.

## Pose pipelines (how motion is measured)

These are **not** sign-language models. They track **hands, face, and body** in video — which is exactly what ASL encoding requires (handshapes + facial grammar).

| Pipeline | ASL-specific? | What it detects | SignOra use |
|----------|-----------------|-----------------|-------------|
| **MediaPipe Holistic** | No (general CV) | 21 hand landmarks × 2, face mesh, body | Miners (Comp A), optional reference |
| **Optical flow** | No | Pseudo hand landmarks from motion | Cheap second reference |
| **DWPose** | No (whole-body pose) | Body + **hands (21 pts)** + face keypoints | Validator **reference ensemble** — independent of MediaPipe |

### Why DWPose for a sign language subnet?

DWPose does not “understand” ASL. It estimates **where the hands and face are** in each frame — the raw signal ASL is made of. We use it in the **validator reference ensemble** so scoring is not circular (miners all running MediaPipe vs validators also using only MediaPipe).

For ASL specifically, the important DWPose outputs are:

- **Left/right hand keypoints** (finger configuration, movement)
- **Face keypoints** (eyebrow raise, mouth morphemes — grammatical in ASL)

Body pose matters for spatial grammar and role shift in dialogue signing.

### What would be ASL-specific?

Future improvements (not in v0.8):

- ASL-trained pose or recognition models (e.g. fine-tuned on WLASL/How2Sign)
- Signer attestation and M2 human validation (already in mechanism paper)
- Known-plaintext Layer 2 captures from certified ASL Signers

## Quick answers

**Is WLASL sign language?** Yes — American Sign Language word-level video.

**Is YouTube-ASL sign language?** Yes — ASL with English captions.

**Is DWPose sign language?** No — general human pose estimation, used here because ASL is expressed through **visible hand and face motion**, which DWPose detects.
