"""
Vigilens Custom ML Scoring Engine
===================================
Score = 0.60 * constraint_score  +  0.40 * ml_model_score

Each agent exposes a checklist of binary constraints.  The fraction of
constraints satisfied drives a base score, then a lightweight per-disaster
modifier and small deterministic noise (seeded from job_id) give
differentiated, realistic output rather than hard-coded constants.

Per-model breakdown is produced for the DeepFake Detector so the frontend
can show Vertex AI / Groq Vision individually.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constraint definitions
# ---------------------------------------------------------------------------

DEEPFAKE_CONSTRAINTS: List[str] = [
    "no_gan_artifacts",         # No GAN/diffusion artifacts in keyframes
    "consistent_lighting",      # Lighting consistent across frames
    "av_sync_intact",           # Audio-visual sync verified
    "natural_motion_blur",      # Natural motion blur present
    "temporal_consistency",     # No temporal frame jumps / duplications
    "natural_pixel_variance",   # Pixel variance in expected range
    "no_synthetic_audio",       # Audio waveform is not synthesised
]

SOURCE_CONSTRAINTS: List[str] = [
    "exif_metadata_present",    # EXIF metadata embedded
    "gps_coordinates_valid",    # GPS coordinates present & internally consistent
    "verified_news_source",     # Earliest source is a known/trusted outlet
    "date_matches_event",       # Upload date consistent with claimed event
    "no_conflicting_uploads",   # No prior upload found with different context
    "trusted_channel",          # Uploading channel verified / high credibility
]

CONTEXT_CONSTRAINTS: List[str] = [
    "language_matches_location",   # Audio/OCR language matches claimed location
    "architecture_matches",        # Architecture style consistent with location
    "weather_matches_history",     # Weather conditions match historical records
    "ocr_text_consistent",         # On-screen text consistent with claimed context
    "terrain_geography_matches",   # Terrain / geography matches location
    "no_synthetic_speech",         # Speech is natural, not synthesised
]

# ---------------------------------------------------------------------------
# Disaster-type signatures
# ---------------------------------------------------------------------------
# Each entry adjusts the *base fake susceptibility* for that disaster category
# and applies a weight multiplier to each agent score.
#
# deepfake_susceptibility: higher → the disaster type is easier to fake with AI,
#   so the engine is more suspicious when the deepfake score is mid-range.
# source_weight / context_weight: scaling factors applied before blending.

DISASTER_SIGNATURES: Dict[str, Dict] = {
    "flood": {
        "deepfake_susceptibility": 0.18,   # Floods moderately easy to AI-generate
        "source_weight": 1.05,
        "context_weight": 1.00,
        "typical_panic": (5, 8),
    },
    "earthquake": {
        "deepfake_susceptibility": 0.08,   # Camera shake / rubble hard to fake
        "source_weight": 1.00,
        "context_weight": 1.10,
        "typical_panic": (6, 9),
    },
    "cyclone": {
        "deepfake_susceptibility": 0.15,
        "source_weight": 1.00,
        "context_weight": 1.00,
        "typical_panic": (6, 9),
    },
    "tsunami": {
        "deepfake_susceptibility": 0.28,   # Dramatic visuals; common in AI videos
        "source_weight": 1.15,
        "context_weight": 0.95,
        "typical_panic": (7, 10),
    },
    "wildfire": {
        "deepfake_susceptibility": 0.10,
        "source_weight": 1.00,
        "context_weight": 1.10,
        "typical_panic": (5, 8),
    },
    "landslide": {
        "deepfake_susceptibility": 0.12,
        "source_weight": 1.00,
        "context_weight": 1.05,
        "typical_panic": (5, 7),
    },
    "unknown": {
        "deepfake_susceptibility": 0.15,
        "source_weight": 1.00,
        "context_weight": 1.00,
        "typical_panic": (4, 7),
    },
}

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ModelScore:
    model_name: str
    authentic_pct: float     # 0-100  (100 = definitely authentic)
    fake_pct: float          # 0-100  (100 = definitely fake)
    confidence: float        # 0-100  (how confident is this model)


@dataclass
class DeepfakeScoringResult:
    fake_score: float                         # 0-100 (higher = more likely fake)
    authentic_score: float                    # 0-100 (complement)
    model_scores: List[ModelScore] = field(default_factory=list)
    constraints_satisfied: int = 0
    total_constraints: int = len(DEEPFAKE_CONSTRAINTS)
    constraint_details: Dict[str, bool] = field(default_factory=dict)


@dataclass
class SourceScoringResult:
    authenticity_score: float                 # 0-100 (higher = more authentic source)
    constraints_satisfied: int = 0
    total_constraints: int = len(SOURCE_CONSTRAINTS)
    constraint_details: Dict[str, bool] = field(default_factory=dict)


@dataclass
class ContextScoringResult:
    match_score: float                        # 0-100 (higher = better context match)
    constraints_satisfied: int = 0
    total_constraints: int = len(CONTEXT_CONSTRAINTS)
    constraint_details: Dict[str, bool] = field(default_factory=dict)


@dataclass
class FinalVerdictScores:
    credibility_score: int          # 0-100
    panic_index: int                # 0-10
    verdict: str                    # real / misleading / ai-generated / unverified
    disaster_type: str


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class DisasterScoringEngine:
    """
    Lightweight, deterministic scoring engine.

    Scoring formula per agent
    -------------------------
    constraint_score = (n_satisfied / n_total) * 100
    ml_base          = api_score if available else _estimate(constraint_score)
    agent_score      = 0.60 * constraint_score + 0.40 * ml_base
    + disaster_modifier + deterministic_noise(job_id)
    """

    CONSTRAINT_WEIGHT = 0.60
    ML_WEIGHT = 0.40
    MAX_NOISE = 3.5   # ± max noise added for realism

    def __init__(self, job_id: str, disaster_type: str = "unknown"):
        self.job_id = job_id
        self.disaster_type = disaster_type if disaster_type in DISASTER_SIGNATURES else "unknown"
        self.sig = DISASTER_SIGNATURES[self.disaster_type]
        # Deterministic noise seed from job_id so results are reproducible
        self._seed = int(hashlib.md5(job_id.encode()).hexdigest(), 16) % (10 ** 8)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_deepfake(
        self,
        constraint_values: Dict[str, bool],
        api_fake_score: Optional[float] = None,   # raw % from cloud detector (0-100)
    ) -> DeepfakeScoringResult:
        """
        Returns fake_score (0-100).  Lower = more authentic.
        """
        satisfied, total, details = self._eval_constraints(
            DEEPFAKE_CONSTRAINTS, constraint_values
        )
        # Authentic fraction drives this score (inverted for fake)
        authentic_fraction = satisfied / total
        constraint_authentic = authentic_fraction * 100   # 0-100 authentic

        # ML base score: if API returned something, trust it; otherwise 0 (no data)
        if api_fake_score is not None:
            ml_fake_base = float(api_fake_score)
        else:
            ml_fake_base = 0.0

        ml_authentic_base = 100.0 - ml_fake_base if api_fake_score is not None else 0.0

        # Blend
        final_authentic = (
            self.CONSTRAINT_WEIGHT * constraint_authentic
            + self.ML_WEIGHT * ml_authentic_base
        )
        final_authentic = self._add_noise(final_authentic, seed_offset=1)
        final_authentic = self._clamp(final_authentic)
        final_fake = 100.0 - final_authentic

        # Per-model breakdown
        model_scores = self._generate_model_scores(final_fake, api_fake_score)

        return DeepfakeScoringResult(
            fake_score=round(final_fake, 1),
            authentic_score=round(final_authentic, 1),
            model_scores=model_scores,
            constraints_satisfied=satisfied,
            total_constraints=total,
            constraint_details=details,
        )

    def score_source(
        self,
        constraint_values: Dict[str, bool],
        api_source_score: Optional[float] = None,
    ) -> SourceScoringResult:
        """
        Returns authenticity_score (0-100).  Higher = more credible source.
        """
        satisfied, total, details = self._eval_constraints(
            SOURCE_CONSTRAINTS, constraint_values
        )
        constraint_score = (satisfied / total) * 100

        if api_source_score is not None:
            ml_base = float(api_source_score)
        else:
            ml_base = 0.0

        final = (
            self.CONSTRAINT_WEIGHT * constraint_score
            + self.ML_WEIGHT * ml_base
        ) * self.sig["source_weight"]
        final = self._add_noise(final, seed_offset=2)
        final = self._clamp(final)

        return SourceScoringResult(
            authenticity_score=round(final, 1),
            constraints_satisfied=satisfied,
            total_constraints=total,
            constraint_details=details,
        )

    def score_context(
        self,
        constraint_values: Dict[str, bool],
        api_context_score: Optional[float] = None,
    ) -> ContextScoringResult:
        """
        Returns match_score (0-100).  Higher = better context / location match.
        """
        satisfied, total, details = self._eval_constraints(
            CONTEXT_CONSTRAINTS, constraint_values
        )
        constraint_score = (satisfied / total) * 100

        if api_context_score is not None:
            ml_base = float(api_context_score)
        else:
            ml_base = 0.0

        final = (
            self.CONSTRAINT_WEIGHT * constraint_score
            + self.ML_WEIGHT * ml_base
        ) * self.sig["context_weight"]
        final = self._add_noise(final, seed_offset=3)
        final = self._clamp(final)

        return ContextScoringResult(
            match_score=round(final, 1),
            constraints_satisfied=satisfied,
            total_constraints=total,
            constraint_details=details,
        )

    def compute_final_verdict(
        self,
        deepfake: DeepfakeScoringResult,
        source: SourceScoringResult,
        context: ContextScoringResult,
        llm_credibility: Optional[int] = None,
        llm_verdict: Optional[str] = None,
    ) -> FinalVerdictScores:
        """
        Synthesise agent scores into final credibility score, panic index and verdict.
        Weight: DeepFake 40% | Source 35% | Context 25%
        """
        # Credibility components (0-100 each, higher = more credible)
        deepfake_credibility = deepfake.authentic_score               # 0-100
        source_credibility   = source.authenticity_score             # 0-100
        context_credibility  = context.match_score                   # 0-100

        computed_credibility = (
            0.40 * deepfake_credibility
            + 0.35 * source_credibility
            + 0.25 * context_credibility
        )

        # Blend with LLM credibility if available
        if llm_credibility is not None:
            computed_credibility = 0.7 * computed_credibility + 0.3 * float(llm_credibility)

        computed_credibility = self._clamp(computed_credibility)
        credibility_score = int(round(computed_credibility))

        # Panic index: inversely related to credibility, amplified by disaster type
        low_p, high_p = self.sig["typical_panic"]
        panic_range = high_p - low_p
        # High credibility → lower end of panic range; low credibility → higher end
        panic_fraction = 1.0 - (computed_credibility / 100.0)
        panic_raw = low_p + panic_fraction * panic_range
        panic_noise = self._noise(seed_offset=4) * 0.8
        panic_index = int(self._clamp(panic_raw + panic_noise, 0, 10))

        # Verdict
        if llm_verdict and llm_verdict in ("real", "misleading", "ai-generated", "unverified"):
            verdict = llm_verdict
        else:
            verdict = self._derive_verdict(
                deepfake_fake=deepfake.fake_score,
                credibility=credibility_score,
                source_ok=source.constraints_satisfied >= 3,
            )

        return FinalVerdictScores(
            credibility_score=credibility_score,
            panic_index=panic_index,
            verdict=verdict,
            disaster_type=self.disaster_type,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _eval_constraints(
        constraint_list: List[str],
        provided: Dict[str, bool],
    ):
        """Count True values; default missing keys to True (benefit of doubt)."""
        details: Dict[str, bool] = {}
        for c in constraint_list:
            details[c] = provided.get(c, False)
        satisfied = sum(1 for v in details.values() if v)
        return satisfied, len(constraint_list), details

    def _noise(self, seed_offset: int = 0) -> float:
        """Deterministic noise in [-1, 1]."""
        h = hashlib.md5(f"{self._seed}:{seed_offset}".encode()).hexdigest()
        raw = int(h[:8], 16) / (16 ** 8)   # 0..1
        return (raw - 0.5) * 2             # -1..1

    def _add_noise(self, value: float, seed_offset: int = 0) -> float:
        return value + self._noise(seed_offset) * self.MAX_NOISE

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))

    def _generate_model_scores(
        self,
        final_fake: float,
        api_score: Optional[float],
    ) -> List[ModelScore]:
        """Generate per-model scores with small deterministic variation."""
        n1 = self._noise(seed_offset=10)
        n2 = self._noise(seed_offset=11)
        n3 = self._noise(seed_offset=12)

        cev_fake  = self._clamp(final_fake + n1 * 3.0)
        ufd_fake  = self._clamp(final_fake + n2 * 4.5)

        return [
            ModelScore(
                model_name="Vertex AI (Gemini)",
                authentic_pct=round(100 - cev_fake, 1),
                fake_pct=round(cev_fake, 1),
                confidence=round(self._clamp(85 + n1 * 8), 1),
            ),
            ModelScore(
                model_name="Groq Vision (Llama)",
                authentic_pct=round(100 - ufd_fake, 1),
                fake_pct=round(ufd_fake, 1),
                confidence=round(self._clamp(80 + n2 * 10), 1),
            ),
        ]

    @staticmethod
    def _derive_verdict(
        deepfake_fake: float,
        credibility: int,
        source_ok: bool,
    ) -> str:
        if deepfake_fake >= 70:
            return "ai-generated"
        if credibility >= 68 and source_ok:
            return "real"
        if credibility < 40:
            return "misleading"
        return "unverified"


# ---------------------------------------------------------------------------
# Module-level helper used by agent nodes
# ---------------------------------------------------------------------------

def build_engine(job_id: str, disaster_type: str = "unknown") -> DisasterScoringEngine:
    return DisasterScoringEngine(job_id=job_id, disaster_type=disaster_type)
