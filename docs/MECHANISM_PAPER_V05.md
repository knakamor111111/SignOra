# SignOra Mechanism Architecture — v0.5

**Mining & Validation Mechanism Paper · June 2026**

> Converted from *SignOra Mechanism Paper v05* for the SignOra repository.

| Field | Value |
|-------|-------|
| Version | v0.5 — Final Draft |
| Date | June 2026 |
| Status | For TBD investors & technical partners |
| Dev partner | Vocence · SN78 |
| Protocol | Bittensor v3.4.6 |
| Mechanisms | M1 (computational miners) + M2 (human Signers) |

## Contents

1. [The Core Problem](#1-the-core-problem--motion-to-meaning-is-not-a-lookup)
2. [Sign Language as a Technical Problem](#2-sign-language-as-a-technical-problem--what-miners-are-actually-solving)
3. [Data Architecture](#3-data-architecture--four-layers-one-principle)
4. [Corpus Linguistics](#4-corpus-linguistics--defining-what-miners-are-trained-to-translate)
5. [Two-Competition Split](#5-the-two-competition-split--how-mining-actually-works)
6. [Ground Truth Architecture](#6-ground-truth-architecture--how-we-know-it-is-right)
7. [Security Architecture (DBCP)](#7-security-architecture--the-dual-blind-commitment-protocol-dbcp)
8. [Emission Architecture](#8-emission-architecture--boolean-gate-compliance-from-day-one)
9. [Cold Start Protocol & Residual Risks](#9-cold-start-protocol--residual-risks)

---


## Abstract

SignOra is a Bittensor subnet that translates sign language motion into spoken and written language in real time. The initial target is ASL-to-English — the highest-volume, best-resourced language pair globally. BabelBit SN59's multilingual API then routes English output to any spoken language, meaning ASL users can communicate with speakers of any of the world's 7,000 spoken languages. Additional sign languages — Indian Sign Language, BSL, LSF, and others — are added as separate mining competition tracks in priority order by market size, each requiring their own training corpus and Signer validator community. This paper specifies the complete mechanism — how miners receive challenges, what they compute and submit, how validators score submissions, how ground truth is established and kept fresh, how gaming is prevented, and how the system proves genuine translation capability rather than answer memorization. The core insight: proof of understanding requires testing on video that did not exist when the model was built. Every architectural decision flows from this principle. The mechanism draws directly from Score SN44's proven lightweight validation pattern, Vocence SN78's model-submission architecture, corpus linguistics research on conversational frequency, and the Dual-Blind Commitment Protocol — a novel application of cryptographic commitment schemes that eliminates the two attacks that have killed other subnets.


#### Especially Timely — June 2026

This week the Opentensor Foundation deployed Bittensor v3.4.6, ceasing emissions on 60+ subnets with no active mining mechanism. The boolean gate is now chain law. SignOra was designed to pass it from the first tempo of the first block — not as a retrofit, but as a foundational requirement. The network just eliminated its weakest participants. We were designed for what remains. Implementation scaffold (miner/validator, pose gate, DBCP, calibration): github.com/knakamor111111/SignOra


## 1. THE CORE PROBLEM — MOTION TO MEANING IS NOT A LOOKUP

The fundamental challenge in building a sign language translation system is not technical complexity alone. It is epistemic: how do you prove the system actually understands sign language motion versus memorizing answers to questions you already know?


#### The Central Principle

If you test a model only on video it was trained on, you have proven nothing.

A model that has memorized 10,000 labeled signing clips will score perfectly on those clips and fail completely on new video from a real human it has never seen. The only honest proof of genuine translation capability is accuracy on continuously fresh, never-before-seen signing video. This single principle determines every architectural decision in this paper.

This is not a theoretical concern. It is the central failure mode that separates a real translation system from a sophisticated lookup table. The mechanism is designed from the ground up so that fresh, ungameable challenge data is structurally guaranteed at every tempo — not promised, not monitored, but guaranteed by protocol.

What "understanding" means in this context: A miner's model genuinely understands ASL if and only if it can correctly translate a new video, from a person it has never seen, signing a phrase in their own individual style with natural regional and personal variation — and produce the correct English meaning. Everything in this mechanism is designed to test exactly that, and only that.


## 2. SIGN LANGUAGE AS A TECHNICAL PROBLEM — WHAT MINERS ARE ACTUALLY SOLVING


### 2.1 The Asymmetry of the Two Directions

SignOra is bidirectional — sign language to speech for deaf patients, and speech to text for the deaf person to read. These two directions are not equally hard.

Hard Direction — The Primary Problem Sign Language → Text / Any Spoken Language Requires the machine to genuinely understand physical motion — hand skeleton geometry, finger joint angles, wrist rotation, facial grammar markers, body pose — and map it to meaning. SignOra trains first on ASL-to-English — the highest-volume, best-resourced starting point. BabelBit SN59's multilingual routing API then delivers that English output to any spoken language.

Important distinction: BabelBit bridges spoken languages, not sign languages. Each sign language (Indian Sign Language, BSL, LSF, and others) requires its own dedicated training corpus and Signer validator community — added as separate mining competition tracks in market-size priority order after ASL is proven.

Easy Direction — Already Solved Speech → Text (for deaf person to read) Handled by Vocence SN78's existing speech-to-text SDK and API. This is a mature, solved problem. Text can also be rendered as a signing avatar via Vidaio SN85 as an optional enhancement — useful but not a technical barrier. This direction requires no novel mining competition.

All mechanism design in this paper focuses on the hard direction: sign language video → English text. That is the problem no existing system has solved at scale, and the problem that determines whether SignOra has genuine value.


### 2.2 Why Sign Language Is Harder Than Other Vision Tasks

Score SN44 solves object detection in football video — identifying where players and balls are on a pitch. That task has a ground truth that is visually unambiguous. Sign language is harder in three specific ways that shape the entire mechanism design:

Facial expression is grammar, not decoration. In ASL, a raised eyebrow changes the grammatical type of an entire clause. A furrowed brow with a specific head tilt modifies sentence meaning. A model that ignores the face produces systematically wrong translations, not just imprecise ones.

Regional and individual variation is real and significant. ASL has regional dialects comparable to spoken English accents. Two fluent native signers may produce measurably different skeletal patterns for the same concept. A model that only knows "standard" signing will fail on real humans from different communities.

Continuous signing is not isolated signs stitched together. The movement between signs — coarticulation — carries grammatical information. Transition patterns, spatial grammar, role-shifting all require the model to understand sequences, not individual frames. A model trained only on dictionary-style isolated sign clips will fail on real conversational signing.

Each of these properties directly shapes a specific architectural decision in the mechanism that follows.


## 3. DATA ARCHITECTURE — FOUR LAYERS, ONE PRINCIPLE

The challenge data miners receive must simultaneously be: abundant enough to run continuous competition, real enough to capture genuine signing variation, fresh enough that memorization is structurally impossible, and verifiable enough that validators can check answers cheaply.

No single data source satisfies all four constraints. The mechanism uses four layers that each solve a different constraint — and together produce something none could achieve alone.


### LAYER 1 — BOOTSTRAP CORPUS

Licensed Dictionary & Open Source Video Resources like HandSpeak, ASL University, Lifeprint, and the ASL Signbank provide existing video clips of individual signs. Ample public and open-source ASL content exists across web dictionaries, educational platforms, and community resources. These form the starting line — used to train the open-source base miner model that every miner downloads on Day 1. Critically: this layer is never used for live challenge scoring. It is the textbook, not the test.


### LAYER 2 — KNOWN-PLAINTEXT HUMAN CAPTURES

The Primary Live Challenge Source Real human signers read a text script and sign it to a camera. The script — the "plaintext" — is encrypted and separated from the video immediately. Miners receive only the video and must recover the meaning.

The encrypted script is the ground truth, committed on-chain before the challenge is sent. This is called known-plaintext capture in cryptographic annotation methodology. It is real, naturalistic, continuously fresh, and the script cannot be reverse-engineered from the video alone.


### LAYER 3 — SKELETAL POSE REPLAY

Real Motion, Infinite Variation Every real human capture (Layer 2) is processed by MediaPipe Holistic to extract a full skeletal pose sequence — hand landmarks, facial action units, body pose, frame by frame. That pose sequence is stored permanently and can be replayed through any renderer (including Vidaio SN85 for avatar output) to generate visually different representations of the same underlying authentic signing motion. The signing is always real — captured from a real human. Only the visual rendering varies. This eliminates dependency on generative synthesis while providing replay variation. One real human capture yields multiple rendered variants without degrading motion authenticity.


### LAYER 3B — RESEARCH CORPUS (WLASL + YOUTUBE-ASL)

Substantial Existing Coverage WLASL (Word-Level American Sign Language dataset) contains 2,000 ASL words with real human signing video — the largest publicly available word-level ASL dataset. YouTube-ASL provides a large-scale open-domain ASL-English parallel corpus. These are real human signing videos available for research use, providing substantial Stage 1-2 vocabulary coverage without requiring new human captures. Combined with pose replay, WLASL's 2,000 labeled videos serve a second critical function:

they are the reference anchor for Track A corpus mining validation — allowing the cross-reference validator to check Stage 1-2 submissions against a known correct reference without requiring a bootstrap model or external human reviewers.


### LAYER 4 — ADVERSARIAL CANARY CLIPS

Gaming Detection Layer A controlled percentage of each challenge batch contains adversarial canaries — clips designed to look like common signs on the surface but are structurally different under genuine skeletal analysis. A miner patternmatching against memorized common signs will fail canaries systematically. A miner running genuine pose estimation will catch the distinction. Canaries are generated by native Signer advisors specifically to target known shortcut patterns. They rotate every 3 tempos from a secret pool.

On generative text-to-sign models (T2S-GPT, SignLLM): Research-grade text-to-sign generation models exist but are not yet production-ready for continuous conversational signing challenge generation — current error rates on novel sentences would corrupt the training signal. They are not used as challenge data sources. They are referenced as an emerging capability that SignOra's own mining competition will eventually surpass, validating the subnet's core value proposition. The pose replay approach is preferred precisely because it preserves real human motion authenticity.

The domain shift problem — acknowledged honestly: A model trained primarily on avatar-generated video may perform worse on real human signing than on avatars — a known computer vision problem called domain shift. The mechanism mitigates this by ensuring a minimum 40% of every live challenge batch is real human captures (Layer 2), not synthetic. This percentage increases as the human Signer capture community grows. It is monitored on the held-out benchmark and flagged if model performance diverges between avatar and human-capture clips.


## 4. CORPUS LINGUISTICS — DEFINING WHAT MINERS ARE TRAINED TO TRANSLATE

Mining should not attempt to cover all possible signing from day one. The challenge corpus is built using corpus linguistics — the scientific study of language as it actually occurs in real communication — to identify and prioritize what matters most.


### 4.1 The Conversational Frequency Principle

Research in corpus linguistics consistently shows that approximately 1,000 word families cover roughly 90% of everyday spoken conversation. The Corpus of Contemporary American English (COCA) — one billion words of real spoken and written American English — quantifies which words, phrases, and transitions appear most frequently in actual human communication. This is the core training target: not all possible language, but the high-frequency core that makes 90% of real conversations work.


#### COVERAGE TARGET

Top 1,000 word families → ~90% of everyday spoken conversation Top 500 common phrase patterns → core conversational transitions Medical communication corpus → clinical domain-specific vocabulary Source: Corpus of Contemporary American English (COCA), Nation (2001) vocabulary frequency research, medical communication corpora from clinical linguistics literature. This is not a complete language model — it is a high-coverage practical communication layer.


### 4.2 The Four-Stage Curriculum

Mining competition is structured in four progressive stages. Miners are scored across all active stages, but new miners must demonstrate competence at Stages 1-2 before their Stage 3-4 submissions carry significant emission weight. This prevents low-quality miners from polluting the hardest, most valuable signal.


#### STAGE


#### CONTENT


#### DATA SOURCE


#### WHY THIS ORDER


#### EMISSION


#### WEIGHT

Stage 1 Alphabet & Numbers ASL fingerspelling — 26 handshapes plus numbers 0–9. Discrete, unambiguous ground truth.

Layer 1 bootstrap + Layer 3 avatar. High-volume, easy to generate.

Establishes pose estimation baseline.

Similar handshapes (M/N/S) are natural adversarial canary candidates. Failure here means the miner's vision pipeline does not work at all.

10% Stage 2 Core Vocabulary Top 1,000 ASL signs corresponding to the 1,000 highest-frequency English word families. Single signs, isolated.

Layer 1 licensed dictionary + Layer 2 human captures of individual signs. 10 variant captures per sign target.

Builds the high-coverage vocabulary core. This is where regional variation first appears significantly — the same word signed differently by different people.

20% Stage 3 Common Phrases & Transitions Top 500 conversational phrase patterns — greetings, questions, common requests, transitions. Continuous signing of 3-8 sign sequences.

Layer 2 human known-plaintext captures as primary. Layer 3 avatar as supplement. Corpus linguistics frequency data defines which phrases.

Introduces coarticulation — the movement between signs — and facial grammar. A model that handles isolated signs but fails on transitions has not learned the language, only a vocabulary list.

35% Stage 4 Domain- Specific Professional Two parallel domain tracks running simultaneously: (1) Medical — chief complaints, symptom descriptions, informed consent, discharge instructions, medication guidance. (2) Financial & Business — loan applications, insurance terms, real estate and escrow transactions, employment contracts, legal proceedings, banking interactions. Both domains share the "greater than 5 minutes, high consequence" characteristic that defines the ADA Title III obligation for these industries.

Layer 2 human captures exclusively. Medical communication corpora + financial/legal communication corpora define vocabulary.

Domain-specific Signer validators for each track. Financial domain corpus drawn from CFPB consumer communication research and plain-language financial disclosure standards.

Clinical and financial accuracy are equally mission-critical. A deaf patient misunderstanding discharge instructions and a deaf person misunderstanding loan terms face comparable real-world harm. Both domains are primary revenue targets.

Stage 4 accuracy in both tracks is the benchmark that validates the full healthcare and business market strategy.

35% Scope check — this is tractable: Stage 2: 10 human capture variants × 1,000 signs = 10,000 clips. Stage 3: 10 variants × 500 phrases = 5,000 clips. Stage 4 medical: 2,000 domain-specific clips. Stage 4 financial/business: 2,000 domain-specific clips. Total: approximately 19,000 high-quality human captures for meaningful core coverage. WLASL and YouTube-ASL provide substantial immediate vocabulary coverage via pose replay, reducing new capture requirements significantly at Stage 2. This is a real, fundable, executable data collection task — not an infinite research project.


## 5. THE TWO-COMPETITION SPLIT — HOW MINING ACTUALLY WORKS

The mining architecture is split into two separate, sequential competitions. This split solves the core validation problem: how do you check a miner's translation answer cheaply, without running a full translation pipeline yourself, and without the validator already having done all the work?


#### The Key Architectural Insight — Borrowed From Score SN44

Miners do not submit translation guesses. They submit structured data that proves they ran genuine computation.

Score SN44 does not ask miners "who won the football match?" It asks miners to return a JSON file of player coordinates, bounding boxes, and keypoint positions — data that can only be produced by actually running computer vision on the video. You cannot fake correct keypoint coordinates without genuinely processing the image. SignOra applies this exact pattern to sign language: Competition A asks miners to return skeletal pose data. The submission format itself prevents shortcut gaming.


### 5.1 Competition A — Skeletal Extraction

What it is: Miners receive a signing video clip and return a structured JSON containing the 3D coordinates of all hand joints, finger positions, facial action units, and body pose — frame by frame across the clip. No translation. No English text. Raw pose data only.

What technology miners use: Open-source pose estimation libraries — primarily MediaPipe Holistic (Google's production-grade hand, face, and body tracking library) or equivalent alternatives. MediaPipe Holistic runs in real time on a standard consumer GPU, produces exactly the keypoint output required, and is freely available. The base miner package wraps MediaPipe into the Bittensor submission format. Miners compete by building better, faster, more accurate variants of this pipeline.


#### Competition A — Miner Submission Format

Input: MP4 video clip (5–15 seconds), received from validator Process: MediaPipe Holistic or equivalent pose estimation, run frame by frame Output: JSON containing per-frame arrays of —

- 21 hand landmarks per hand (x, y, z coordinates + confidence)
- 468 facial mesh landmarks (subset: 52 action-unit-relevant points)
- 33 full-body pose landmarks
- Frame timestamp
- Miner confidence score
Submission: JSON + miner commitment hash (DBCP — see Section 7) Quality gate: Aggregate MediaPipe landmark confidence score must reach ≥0.75 across the hand landmark set before Competition B receives this data. Submissions below threshold receive zero score for that clip. Threshold is a starting parameter — calibrated on testnet before mainnet registration. Applied to the revealed skeletal JSON, auditable on-chain.

How validators check it cheaply: Validators do not re-run full pose estimation on every clip. They maintain a hybrid-generated reference — exactly Score SN44's proven pattern — where a trusted frontier-quality pose estimation pipeline was run once on each challenge clip to generate a reference keypoint set, spot-checked by a small certified team. Validators compare miner submissions against this reference using a lightweight geometric distance metric. This is computationally cheap: comparing two JSON arrays of coordinates requires milliseconds, not GPU compute.


### 5.2 Competition B — Meaning Translation

What it is: A separate pool of miners (or the same miners with a different model component) receives the verified skeletal sequences from Competition A and produces the English text translation. This is the sequence-to-meaning model: a transformer-architecture neural network trained to map skeletal coordinate sequences to English sentences.

Why split from Competition A: Competition A and Competition B miners are blind to each other's scoring criteria by structural design. A Competition A miner trying to game skeletal extraction scores never sees the meaning-scoring criteria. A Competition B miner trying to game translation never sees the raw video — they receive only the verified skeletal data from Competition A. Neither competition can be gamed by reverse-engineering the other's evaluation criteria, because those criteria operate on different data types.


#### Competition B — Miner Submission Format

Input: Verified skeletal JSON sequence from Competition A (no raw video) Process: Sequence transformer model — maps coordinate sequences to English text Output: English text translation + confidence score Scored against: Known-plaintext ground truth (encrypted at capture time, revealed post-commit) + Signer human validation consensus (M2 layer)


### 5.3 How the Pipeline Connects

```
CHALLENGE (Video Clip, raw MP4)
    → COMP A (Skeletal Extraction: MediaPipe → JSON)
    → GATE (Multi-signal gate — pass or discard)
    → COMP B (Meaning Translation: sequence → English)
    → SCORING (Known-plaintext ground truth + M2 Signers)
```

SN59 (BabelBit) and SN85 (Vidaio) decoupled from consensus liveness: These subnets handle output delivery — translating English to other spoken languages (SN59) and rendering signing avatars (SN85). They are called at product delivery time, after mining consensus is complete. A degradation or outage in either subnet does not affect miner scoring, validator weight submission, or Yuma consensus calculation. The consensus mechanism runs exclusively on Competition A and Competition B. Subnet liveness is never dependent on downstream delivery services.

The Multi-Signal Confidence Gate — protecting Competition B from Competition A errors: A single aggregate confidence threshold is insufficient for sign language video. Fast fingerspelling, two-hand signs, and close-to-face signing often produce lower MediaPipe confidence scores even when the motion is valid. Facial grammar (eyebrows, head tilt) requires separate coverage checks from hand landmarks. The gate uses five independent signals, all of which must pass before skeletal data is forwarded to Competition B:

Hand landmark coverage: Stage-specific threshold — τ_hand ≥ 0.72–0.75 for Stages 1–2 (discrete signs, controlled motion), τ_hand ≥ 0.65 for Stages 3–4 (continuous signing, higher variation expected) Facial grammar coverage: Independent confidence check on eyebrow, head tilt, and mouth morpheme landmarks — required because facial grammar is syntactically meaningful in ASL and cannot be inferred from hand data alone Temporal continuity: Frame-to-frame landmark position delta within physically plausible bounds — rejects corrupted or dropped-frame sequences Geometric score vs. reference ensemble: Submission compared against a reference pose ensemble using a different MediaPipe configuration than the one miners use — prevents gaming the gate by optimizing for the validator's specific detector Two-hand coverage: Both hands detected for two-handed signs; single hand verified for one-handed signs based on stage and sign type Calibration target: Gate parameters calibrated on approximately 500 real human ASL captures before mainnet. Target: 75–90% pass rate for honest miners. Parameters published on-chain at registration and subject to governance update post-calibration. Implementation led by Vocence engineering team.


#### 5B. Corpus Mining — Phase 1B Competition (Days 30–60)

The translation mining competitions (Sections 5 and 6) depend on a continuously growing corpus of verified signing video. Corpus Mining is a separate, dedicated competition that pays miners to build that corpus — making data generation a network-incentivized activity rather than a centralized cost.


#### The Problem It Solves

The network pays for its own training data.

Rather than requiring upfront capital to hire human signers, Corpus Mining emissions incentivize community Signers to record scripts on camera.

Every clip submitted and validated enters the permanent challenge corpus. More corpus = better miners = better translation = more enterprise revenue = more emissions. The loop is self-sustaining from the moment corpus mining activates.


### 5b.1 How Corpus Mining Works

Corpus miners are attested Signers (same attestation requirement as M2 validators) who receive text script assignments and submit signed video. The script is drawn from the corpus linguistics frequency framework — common, unambiguous phrases from the target vocabulary set.

The miner signs the script on camera, submits the raw video plus their skeletal pose extraction (MediaPipe Holistic output), and commits to the submission hash via DBCP before revealing.


### 5b.2 Validation Without a Pre-Existing Corpus — Cross-Referencing

This is the key design challenge: how do you validate corpus submissions when there is no pre-existing translation model to check them against? The answer does not require a translation model. It requires independent consensus across multiple signers producing pose data for the same script.

Cross-Reference Validation Protocol — Dual Check Assignment: Each script is assigned to 5 independent corpus miners simultaneously. No miner sees any other's submission.

Track A — Known Vocabulary (Stage 1 & 2):

For signs and phrases where a verified reference exists in WLASL or the bootstrap corpus, the validator runs a dual check:

(1) Compare each submission's skeletal JSON against the WLASL reference sequence using MediaPipe geometric distance metric (2) Compare submissions against each other for cross-miner consistency Both checks must pass. This closes the cartel loophole — a group of miners who all sign the same wrong thing consistently will fail the WLASL reference check regardless of their internal agreement.

Track B — Stage 3 Common Phrases (consensus-only):

No WLASL reference exists for novel phrase combinations. Cross-miner consistency alone is used. WLASL anchoring intentionally excluded here — penalizing valid regional variation in continuous signing would corrupt the corpus rather than protect it. Scripts drawn from high-frequency corpus linguistics vocabulary where systematic misunderstanding is unlikely.

Track C — Stage 4 Clinical and Professional Domains (consensus + domain review):

Cross-miner consensus as primary signal. Domain-specific Signer validators from the M2 pool provide secondary review for medical and financial terminology where mistranslation carries real clinical or legal consequence.

Scoring (both tracks):

- 4 or 5 submissions pass → full emissions, clips enter corpus
- 3 of 5 pass → partial emissions, 3 clips enter corpus, outliers flagged
- Fewer than 3 pass → batch discarded, no emissions, scripts reassigned
- Persistent outlier pattern → trust weight review, potential attestation suspension
WLASL provides 2,000 real labeled signing videos as reference anchors — available for research use, no bootstrap capital required. This is the primary reference source for Stage 1-2 vocabulary validation.

Why this works without a translation model: The validator is not asking "is this correct ASL?" It is asking "do independent signers produce consistent skeletal patterns for this script?" Consistency across independent signers who cannot see each other's submissions is a reliable proxy for accuracy. A miner who signs the wrong thing produces skeletal patterns that diverge from honest signers' consensus.

The validator detects divergence using pose geometry — computationally cheap, no model required.

On WLASL as a reference anchor — used with appropriate caution: WLASL provides reference skeletal sequences for 2,000 ASL words and is used as one input to Stage 1–2 validation, not as an absolute ground truth. WLASL reflects specific regional and individual signing styles and does not capture the full range of valid ASL variation. Submissions that diverge from the WLASL reference are not automatically rejected — they are flagged for cross-reference review. High cross-reference consensus can override a WLASL divergence flag, accommodating legitimate regional variation. For Stage 3–4 where no WLASL reference exists, cross-reference consensus is the sole validation method. WLASL anchoring is a supporting signal, not a hard gate.

The one honest limitation: Cross-referencing catches individual malicious or careless submissions but cannot catch systematic error where all signers misunderstood the same script. Mitigation: scripts are drawn exclusively from high-frequency, unambiguous corpus linguistics vocabulary. Ambiguous or idiom-heavy scripts are excluded from corpus mining assignments until the translation model is mature enough to provide a secondary quality check.

5b.3 Emission Structure for Corpus Mining

#### Corpus Mining Emission Allocation

- Phase 1b allocation: **5%** of total subnet emission → Corpus Mining pool
- Corpus miner earnings ∝ verified clips submitted × quality score
- Quality score = consensus agreement rate across cross-reference group
- **0–5,000 clips:** 5% allocation (bootstrap phase)
- **5,000–15,000:** 8% allocation (growth phase)
- **15,000+:** 3% allocation (maintenance phase, corpus largely complete)

Emission weight scales with need — highest during bootstrap when corpus gaps are largest, decreasing as the corpus matures.


### 5b.4 How the Three Security Layers Interlock

The three validation mechanisms introduced in Sections 5, 5b, and 6 are designed as a unified system — each one reinforces the others:

WLASL reference anchoring (Section 5b) closes the corpus cartel attack by providing an external ground truth for Stage 1–2 vocabulary that no cartel of miners can fake their way past.

The confidence gate at 0.75 (Section 5.3) ensures only high-quality skeletal data reaches Competition B — protecting translation miners from being penalized for upstream errors and keeping the corpus clean.

The TEE-protected benchmark with multi-sig governance (Section 6.3) ensures the SOTA measurement is tamper-proof and auditable — by anyone, at any time, including Yuma.

Together these three mechanisms close the bootstrap validation loop without requiring centralized human review, external capital, or a preexisting translation model. The corpus builds itself, the pipeline self-filters, and the benchmark self-protects.


### 5b.5 Activation and Ordering

| Phase | What activates | Timing | Why this order |
|-------|----------------|--------|----------------|
| **Phase 1 — Day 0** | Competition A + B using bootstrap corpus (WLASL, etc.) | Registration day | Boolean gate requires active mining immediately |
| **Phase 1b — Day 30–60** | Corpus Mining; cross-reference validation | Signer cohort ≥ 30 | Minimum cohort for statistically meaningful consensus |
| **Phase 2 — Day 60+** | M2 Signer validation on translation competition | Post Signer onboarding | M2 requires corpus clips to validate against |


## 6. GROUND TRUTH ARCHITECTURE — HOW WE KNOW IT IS RIGHT


### 6.1 The Known-Plaintext Capture Protocol

For real human capture clips, the ground truth is established before the clip is ever used as a challenge, through a three-step protocol:

Script generation: Text prompts drawn from the corpus linguistics frequency framework — words, phrases, and sentences from the target vocabulary set — are selected as signing targets.

Encrypted separation: The plaintext script is hashed and committed on-chain before the signing session begins. The Signer sees the script, signs it on camera, and the video is captured. The script is then encrypted and stored separately from the video. Miners who receive the video challenge never have access to the script.

Commit-reveal at scoring: After all miners have submitted their Translation Competition B responses (also committed via DBCP), the encrypted plaintext is revealed on-chain. Scoring is deterministic from the revealed plaintext. Any observer can verify the ground truth was set before the challenge was issued.

Why this proves genuine translation: The Signer who recorded the video knew the script. The validator who issued the challenge committed the hash of the script before sending. The miners who received the video had no access to the script. A miner who returns the correct translation has proven their model can extract meaning from visual motion alone — there is no other path to the correct answer.

1. **Script generation** — prompts from the corpus linguistics frequency framework
2. **Encrypted separation** — hash committed on-chain before signing; script stored separately from video
3. **Commit-reveal at scoring** — plaintext revealed after miner DBCP commits; scoring is deterministic


### 6.2 Distributional Ground Truth — Disagreement as Signal

For human validation scoring (the M2 Signer layer), the mechanism uses distributional ground truth rather than naive majority vote. This is grounded in published annotation science demonstrating that for language tasks with inherent variation, "the standard practice of minimizing disagreement between annotators results in data that fails to account for the ambiguity inherent in language" (CrowdTruth, Dumitrache et al., 2017).

Sign language variation is exactly this kind of task. When five Signers review a translation and three score it fully correct while two flag a regional variant nuance — that 3-2 split is real linguistic data, not noise to be eliminated. It is recorded as a Normalized Distribution of Annotations (NDA) and used to:

Score miners on capturing the full valid range of interpretation, not just the majority answer Identify genuine regional variation in the training data (high disagreement = genuine dialectal ambiguity worth flagging) Detect systematic Signer bias (a Signer who always disagrees with everyone else is flagged for review)


### 6.3 The Held-Out Benchmark — TEE-Secured, Multi-Sig Governed

A permanently withheld validation set is maintained separately from all challenge data. This set — new signing video from real humans, continuously captured, never exposed to miners for training — is the only honest measurement of whether models are improving at genuine translation versus memorizing challenge clips.

The centralization problem and its solution: A benchmark controlled by any single person — including the founders — is not credible thirdparty verification. "The team controls the benchmark that proves their technology works" undermines the entire proof. SignOra solves this using infrastructure already in the stack.

Benchmark clips are encrypted and stored in Targon's Intel TDX Trusted Execution Environment. No individual — not the founders, not Yuma, not any single party — can access the plaintext clips. The TEE runs the evaluation pipeline internally and returns only the accuracy score to the public chain. The underlying clips are never exposed. Access to add new clips requires a multi-signature transaction from three defined keyholders: SignOra, Vocence SN78, and one independent technical party. No single party can tamper with or update the benchmark unilaterally.

Each evaluation cycle, every registered miner model is run against the current held-out benchmark inside the TEE. The accuracy score is posted on-chain — publicly auditable, reproducible, and verifiable by any observer without requiring access to the benchmark clips themselves.

Targon's TEE infrastructure (the same layer providing HIPAA-compliant inference for the clinical product) is the implementation foundation for this benchmark security.


#### Sota Benchmark Definition

SOTA_score(t) = accuracy( model_best(t), held_out_set(t) ) where: held_out_set(t) contains only video captured AFTER tempo t-N and: model_best(t) is the highest-ranked miner model at tempo t The held-out set grows continuously with new captures. A model cannot improve its held-out score by memorizing training data because the test videos literally did not exist when the model was last trained. Improvement is only possible by building a better translation model.


## 7. SECURITY ARCHITECTURE — THE DUAL-BLIND COMMITMENT PROTOCOL (DBCP)


#### The Core Security Insight

You cannot cheat a game where you must commit to your answer before you see anyone else's.

The two attacks that have killed other Bittensor subnets — weight copying and validator-miner collusion — both require one party to see another's committed answer before submitting their own. The DBCP prevents this structurally: both miner and validator commit cryptographically before either reveals. Zero new cryptographic primitives. Zero new infrastructure. One hash function and a block delay. Eight attack vectors neutralized.


### 7.1 The DBCP Protocol — Step by Step

**Per-tempo DBCP flow:**

1. **Block B+0:** Validator computes challenge batch using private rotating salt.  
   `V_commit = SHA256(clip_ids ‖ reference_answers ‖ salt ‖ block_hash_t)` — posted on-chain; reference answers locked.
2. **Block B+1:** Validator sends encrypted challenge packet to miners (clips only, no answers).
3. **Block B+2:** Miners process clips;  
   `M_commit = SHA256(translations ‖ miner_nonce ‖ block_hash_t)` — posted before deadline.
4. **Block B+3:** Simultaneous reveal; chain verifies `SHA256(revealed_data) == commit` for both parties.
5. **Block B+4:** Scoring runs; weights computed and submitted to Yuma.

Block hash inclusion forces liveness — pre-computed answers from prior tempos fail.


### 7.2 Salt Rotation — Preventing Temporal Correlation


#### Per-Tempo Salt Rotation

salt_t+1 = SHA256( salt_t ‖ block_hash_t ) The validator's private salt rotates every tempo using the current block hash. Even if one tempo's salt were somehow leaked, the next tempo's salt is immediately different and unrelated. The miner cannot predict which clips any validator will select because the salt is private until after both commitments are locked.


### 7.3 Complete Attack Vector Table


#### ATTACK


#### HOW IT WORKS


#### SEVERITY


#### How Signora Eliminates It

Weight Copying Lazy validator copies honest validator's weights without doing evaluation work High — killed SN30 Commit Reveal: weights encrypted until reveal window closes. Nothing to copy during submission window.

Validator-Miner Collusion Validator leaks challenge answers to miner before miner commits High — killed SN33 DBCP: validator's answers locked on-chain before miner commits. Leaking gains nothing — miner still must commit before seeing validator's reveal.

Corpus Memorization Miner scrapes all challenge data offline, caches answers, returns lookup results High Known-plaintext capture: new human-signed video continuously, never pre-existing. Avatar clips seeded by block hash. Cannot pre-compute answers to clips that don't exist yet.

UID Slot Monopolization Script acquires all UID slots during immunity period, blocks legitimate miners High — killed SN33 Minimum stake requirement for registration.

Open-source base miner released 2 weeks prelaunch. Hyperparameter-tuned registration burn.

Stage Gaming Miner only competes on easy Stage 1-2 challenges, ignores hard Stage 3-4 Medium Emission weighting: Stage 3-4 carries 70% of emission weight. Optimizing for Stage 1-2 only yields minimal returns.

Signer Sybil One person registers multiple Signer identities to control M2 consensus Medium One attestation per coldkey, on-chain enforced.

Trust weight bound to coldkey. Multiple wallets detectable by issuing organization.

Lazy Validator Replay Validator pre-computes all reference answers once, replays indefinitely High — novel, not addressed elsewhere V_commit includes current block_hash_t. Cached answers from prior tempos fail hash verification — they were computed without this tempo's block hash. Liveness enforced cryptographically.

Anchor Clip Identification Signer identifies calibration clips statistically over many tempos, games them Medium 800–1,000+ clip rotating anchor pool with decoy clips. Refreshed every 3 tempos. No anchor repeats within 12-tempo window. Identification requires 100+ tempos — trust weight collapses first.

Slow Signer Cartel Group of Signers farms trust score honestly then coordinates to corrupt M2 Medium Trust cap 1.50 max. Passive decay −0.01/tempo always. −0.25/tempo as outlier. Patient farming of 30 tempos (+0.90 gain) wiped out in 4 tempos of bad scoring.

Temporal Correlation Miner reverse-engineers clip selection from public block hash Medium Per-validator private salt: VRF seed = SHA256(block_hash + salt_t). Salt never revealed on-chain. Rotates every tempo.


## 8. EMISSION ARCHITECTURE — BOOLEAN GATE COMPLIANCE FROM DAY ONE


#### Chain Emission Formula — Bittensor V3.4.6 (June 2026)

e_i ∝ ( root_prop_i × price_EMA_i ) × ( 1 − miner_burn_i )


#### └── Linear Term ───────────────┘ └── Boolean Gate ──┘

SignOra: miner_burn = 0 (by construction — zero owner hotkeys in miner emission pool) price_EMA driven by enterprise revenue → real alpha token demand root_prop advantage: new entrant on-ramp deliberately designed into protocol Early-phase emission smoothing (Days 0–90): longer EMA window (30 tempos vs. standard 10) applied to price term to prevent extreme swings from thin alpha pool liquidity during launch period. Automatically resets to standard after tempo 1,800.


#### BOOLEAN GATE


#### REQUIREMENT


#### Signora Implementation


#### STATUS

Active mining mechanism Competition A: validators send challenge clips every tempo. Automated. Cannot stop without explicit action.

Day 1 Real miner distribution All miner emission flows to registered miners via Yuma score. Zero to owner hotkey.

Day 1 Active validator set Vocence SN78 team runs bootstrap validators. Validator code open-sourced. Any staker can run.

Day 1 M2 Signer layer active Activates when ≥30 attested Signers from ≥5 sources are registered. M1 runs at 100% emission until then.

Day 30–60 No emission cycling Price-based emission is symmetric — no buy/sell arbitrage cycle possible. Enterprise revenue creates organic demand.

Protocol guaranteed Subtensor Multi-Mechanism ID Mapping: Bittensor's native multi-mechanism support assigns each mechanism a unique on-chain identifier within the subnet slot. M1 (Computational Miners), M2 (Human Signers), and Corpus Mining (Phase 1b) each map to distinct subtensor mechanism IDs. Emission splits, weight matrices, and bond pools are tracked independently per mechanism ID on-chain.

Implementation of the exact mechanism ID registration follows subtensor's native multi-mechanism API — led by Vocence engineering team per protocol specification.


#### Emission Split — Dual Mechanism

Phase 1 (launch): M1 = 100%, M2 = 0% (until Signer cohort ≥30) Phase 2 (steady): M1 = 70%, M2 = 30% Within M1: 50% to miners (by Yuma composite score), 50% to validators Within M2: 70% to Signers (by trust weight × consensus agreement), 30% to M2 validators Owner: 18% of total subnet emission (standard protocol allocation) M1↔M2 Alignment Bonus: miners whose translations receive consistently high Signer agreement receive +6% weight bonus on M1 composite score for that tempo.


## 9. COLD START PROTOCOL & RESIDUAL RISKS


### 9.1 Cold Start — Day Zero Through Day Thirty


#### DAY


#### ACTION


#### WHO


#### PURPOSE


#### D−14

Open-source base miner package released. Includes MediaPipe Holistic wrapper, basic sequence translation model trained on bootstrap corpus, full documentation.

Vocence dev team Miners test and optimize locally for 2 weeks before mainnet. Score SN44 pattern.


#### D−7

Recruit 3 independent mining teams. 2 independent validator operators (not Vocence, no prior SignOra relationship) commit to Day-0 launch. Bootstrap validator coldkeys published in genesis document.

Michael / specialK Prevents bootstrap capture. Validator independence enforced by disclosure.


#### D+0

Subnet registers. Vocence runs bootstrap miners only — not validators. M1 active at 100% emission. Challenge batch begins immediately.

All Boolean gate satisfied from tempo 1.


#### D+14

First Signer cohort onboarding — California School for the Deaf pilot. Target: 30+ attested Signers from ≥5 organizations.

SignOra / NAD / CAD M2 minimum cohort threshold.


#### D+21–

30 M2 activates. Split moves to 70/30. First hospital pilot deployment begins. First real enterprise revenue → first alpha token demand.

SignOra sales Linear emission term begins building.


### 9.2 Residual Risks — Named Honestly

Risk 1 — Low-Medium (mitigated) Avatar-to-Real-Human Domain Shift A model trained heavily on avatar-generated video may not immediately generalize to real human signing variation — a known computer vision problem. Mitigation: minimum 40% of live challenges are real human captures from launch. Held-out benchmark monitors divergence between avatar and humancapture performance explicitly.

Risk 2 — Medium Human Capture Supply Dependency Known-plaintext human captures depend on Signers being available and willing. If human participation is lower than projected, avatar-generated clips carry more weight than ideal.

Mitigation: avatar supply is infinite via Vidaio SN85. Avatar clips have lower scoring weight but keep mining active. Human capture percentage targets increase gradually as community builds.

Risk 3 — Low Coarticulation Learning Gap Models trained primarily on isolated sign clips may underperform on continuous signing. The Stage 3-4 curriculum directly targets this, but early-stage models may lag on clinical-grade translation.

This is an expected phase of development, not a design flaw.

Stage weighting ensures miners are rewarded for improving here.

Risk 4 — Low Alpha Pool Liquidity at Launch New subnets start with near-zero alpha pool depth. Small staking events cause large price swings. Mitigation: early-phase emission smoothing (30-tempo EMA window). Yuma accelerator staking provides structured pool depth. Enterprise contracts provide persistent organic buy pressure once live.


#### Why This Mechanism Deserves A Slot

Real work that cannot be faked. Skeletal extraction via MediaPipe requires genuine computer vision — the submission format prevents shortcut gaming. DBCP closes collusion and weight copying. Canaries catch patternmatching.

Continuously advancing technology. Knownplaintext captures and the held-out benchmark ensure miners improve at genuine translation — not a fixed test set. Fresh data every tempo.

Boolean-native by design. Active mechanism from Day 1. Zero owner hotkeys. Enterprise revenue drives real alpha demand. The new emission formula rewards exactly what SignOra is.

v0.5 — June 2026 · SignOra · For TBD investors, Vocence SN78, and technical advisors · Not for public distribution · Implementation parameters subject to testnet calibration · References: Bittensor v3.4.6-421 · Score SN44 (github.com/score-technologies/score-vision) · MediaPipe Holistic (google.github.io/mediapipe) · COCA (corpus.byu.edu/coca) · WLASL dataset · CrowdTruth (Dumitrache et al., 2017) · Nation (2001) vocabulary frequency research
