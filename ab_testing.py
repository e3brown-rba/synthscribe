"""
ab_testing.py - A/B Testing framework for prompt optimization

This module implements:
- Deterministic user assignment to variants
- Statistical significance testing
- Experiment tracking and reporting
- Automatic winner selection
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import random
import math
from collections import defaultdict


class ExperimentStatus(Enum):
    """Status of an A/B test experiment"""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class Variant:
    """Represents a variant in an A/B test"""

    name: str
    description: str
    config: Dict[str, Any]
    metrics: Dict[str, float] = field(
        default_factory=lambda: {
            "impressions": 0,
            "successes": 0,
            "conversion_rate": 0.0,
            "avg_feedback_score": 0.0,
            "total_feedback_score": 0.0,
            "feedback_count": 0,
        }
    )

    def record_impression(self):
        """Record that this variant was shown"""
        self.metrics["impressions"] += 1
        self._update_conversion_rate()

    def record_success(self):
        """Record a successful outcome"""
        self.metrics["successes"] += 1
        self._update_conversion_rate()

    def record_feedback(self, score: float):
        """Record user feedback score"""
        self.metrics["total_feedback_score"] += score
        self.metrics["feedback_count"] += 1
        self.metrics["avg_feedback_score"] = (
            self.metrics["total_feedback_score"] / self.metrics["feedback_count"]
        )

    def _update_conversion_rate(self):
        """Update conversion rate metric"""
        if self.metrics["impressions"] > 0:
            self.metrics["conversion_rate"] = (
                self.metrics["successes"] / self.metrics["impressions"]
            )


@dataclass
class Experiment:
    """Represents an A/B test experiment"""

    name: str
    description: str
    variants: List[Variant]
    status: ExperimentStatus = ExperimentStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    min_sample_size: int = 100  # Per variant
    confidence_level: float = 0.95

    def get_variant_names(self) -> List[str]:
        """Get list of variant names"""
        return [v.name for v in self.variants]

    def get_variant(self, name: str) -> Optional[Variant]:
        """Get variant by name"""
        for variant in self.variants:
            if variant.name == name:
                return variant
        return None

    def is_significant(self) -> Tuple[bool, Optional[str], float]:
        """
        Check if results are statistically significant
        Returns: (is_significant, winning_variant, p_value)
        """
        if len(self.variants) != 2:
            # For simplicity, only handle A/B tests (2 variants)
            return False, None, 1.0

        v1, v2 = self.variants

        # Check minimum sample size
        if (
            v1.metrics["impressions"] < self.min_sample_size
            or v2.metrics["impressions"] < self.min_sample_size
        ):
            return False, None, 1.0

        # Calculate z-score for conversion rate difference
        p1 = v1.metrics["conversion_rate"]
        p2 = v2.metrics["conversion_rate"]
        n1 = v1.metrics["impressions"]
        n2 = v2.metrics["impressions"]

        # Pooled probability
        p_pooled = (v1.metrics["successes"] + v2.metrics["successes"]) / (n1 + n2)

        # Standard error
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1 / n1 + 1 / n2))

        if se == 0:
            return False, None, 1.0

        # Z-score
        z = (p1 - p2) / se

        # P-value (two-tailed test)
        p_value = 2 * (1 - self._normal_cdf(abs(z)))

        # Determine if significant
        alpha = 1 - self.confidence_level
        is_significant = p_value < alpha

        # Determine winner if significant
        winner = None
        if is_significant:
            winner = v1.name if p1 > p2 else v2.name

        return is_significant, winner, p_value

    @staticmethod
    def _normal_cdf(z: float) -> float:
        """Approximate normal CDF using error function"""
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))


class ABTestingManager:
    """Manages A/B testing experiments"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".synthscribe" / "experiments"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.experiments: Dict[str, Experiment] = {}
        self._load_experiments()

    def create_experiment(
        self, name: str, description: str, variants: List[Dict[str, Any]]
    ) -> Experiment:
        """Create a new experiment"""
        variant_objects = []
        for v in variants:
            variant_objects.append(
                Variant(
                    name=v["name"],
                    description=v.get("description", ""),
                    config=v.get("config", {}),
                )
            )

        experiment = Experiment(
            name=name, description=description, variants=variant_objects
        )

        self.experiments[name] = experiment
        self._save_experiments()

        return experiment

    def get_user_variant(self, experiment_name: str, user_id: str) -> Optional[str]:
        """
        Get variant assignment for a user
        Uses deterministic hashing for consistent assignment
        """
        experiment = self.experiments.get(experiment_name)
        if not experiment or experiment.status != ExperimentStatus.ACTIVE:
            return None

        # Create deterministic hash
        hash_input = f"{experiment_name}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

        # Assign to variant based on hash
        variant_index = hash_value % len(experiment.variants)
        variant = experiment.variants[variant_index]

        # Record impression
        variant.record_impression()
        self._save_experiments()

        return variant.name

    def record_success(self, experiment_name: str, variant_name: str):
        """Record a successful outcome for a variant"""
        experiment = self.experiments.get(experiment_name)
        if not experiment:
            return

        variant = experiment.get_variant(variant_name)
        if variant:
            variant.record_success()
            experiment.updated_at = datetime.now()
            self._save_experiments()

    def record_feedback(self, experiment_name: str, variant_name: str, score: float):
        """Record user feedback for a variant"""
        experiment = self.experiments.get(experiment_name)
        if not experiment:
            return

        variant = experiment.get_variant(variant_name)
        if variant:
            variant.record_feedback(score)
            experiment.updated_at = datetime.now()
            self._save_experiments()

    def get_experiment_results(self, experiment_name: str) -> Dict[str, Any]:
        """Get comprehensive results for an experiment"""
        experiment = self.experiments.get(experiment_name)
        if not experiment:
            return {}

        is_significant, winner, p_value = experiment.is_significant()

        results = {
            "name": experiment.name,
            "status": experiment.status.value,
            "created_at": experiment.created_at.isoformat(),
            "updated_at": experiment.updated_at.isoformat(),
            "variants": [],
            "statistical_significance": {
                "is_significant": is_significant,
                "winner": winner,
                "p_value": p_value,
                "confidence_level": experiment.confidence_level,
            },
        }

        for variant in experiment.variants:
            results["variants"].append(
                {
                    "name": variant.name,
                    "metrics": variant.metrics,
                    "config": variant.config,
                }
            )

        return results

    def complete_experiment(self, experiment_name: str):
        """Mark an experiment as completed"""
        experiment = self.experiments.get(experiment_name)
        if experiment:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.updated_at = datetime.now()
            self._save_experiments()

    def _save_experiments(self):
        """Save experiments to disk"""
        data = {}
        for name, exp in self.experiments.items():
            data[name] = {
                "name": exp.name,
                "description": exp.description,
                "status": exp.status.value,
                "created_at": exp.created_at.isoformat(),
                "updated_at": exp.updated_at.isoformat(),
                "min_sample_size": exp.min_sample_size,
                "confidence_level": exp.confidence_level,
                "variants": [
                    {
                        "name": v.name,
                        "description": v.description,
                        "config": v.config,
                        "metrics": v.metrics,
                    }
                    for v in exp.variants
                ],
            }

        with open(self.storage_dir / "experiments.json", "w") as f:
            json.dump(data, f, indent=2)

    def _load_experiments(self):
        """Load experiments from disk"""
        exp_file = self.storage_dir / "experiments.json"
        if not exp_file.exists():
            return

        try:
            with open(exp_file, "r") as f:
                data = json.load(f)

            for name, exp_data in data.items():
                variants = []
                for v_data in exp_data["variants"]:
                    variant = Variant(
                        name=v_data["name"],
                        description=v_data["description"],
                        config=v_data["config"],
                        metrics=v_data["metrics"],
                    )
                    variants.append(variant)

                experiment = Experiment(
                    name=exp_data["name"],
                    description=exp_data["description"],
                    variants=variants,
                    status=ExperimentStatus(exp_data["status"]),
                    created_at=datetime.fromisoformat(exp_data["created_at"]),
                    updated_at=datetime.fromisoformat(exp_data["updated_at"]),
                    min_sample_size=exp_data.get("min_sample_size", 100),
                    confidence_level=exp_data.get("confidence_level", 0.95),
                )

                self.experiments[name] = experiment

        except Exception as e:
            print(f"Error loading experiments: {e}")


# Prompt variants for testing
PROMPT_VARIANTS = {
    "zero_shot": {
        "name": "zero_shot",
        "description": "Basic zero-shot prompt",
        "config": {
            "template": """You are SynthScribe, a music recommendation expert.
Suggest 4 music genres/artists for: "{description}"
Format each as:
- Genre: [name]
  Artists: [names]
  Note: [reason]"""
        },
    },
    "few_shot": {
        "name": "few_shot",
        "description": "Few-shot learning with examples",
        "config": {
            "template": """Examples:
Input: "coding late at night"
Output:
- Genre: Lofi Hip Hop
  Artists: Nujabes, J Dilla
  Note: Relaxing beats for focus

Input: "morning workout"
Output:
- Genre: Electronic/EDM
  Artists: The Prodigy, Pendulum
  Note: High energy for motivation

Now suggest music for: "{description}"
Follow the same format."""
        },
    },
    "persona_based": {
        "name": "persona_based",
        "description": "AI persona with context",
        "config": {
            "template": """You are Nova, an empathetic AI music curator.
{context}

The user needs music for: "{description}"

Provide 4 thoughtful suggestions that balance their preferences with discovery.
Format each as:
- Genre: [name]
  Artists: [names]
  Note: [personalized insight]"""
        },
    },
}


# Example usage
if __name__ == "__main__":
    # Initialize manager
    ab_manager = ABTestingManager()

    # Create an experiment
    experiment = ab_manager.create_experiment(
        name="prompt_optimization_v1",
        description="Testing different prompt strategies for better recommendations",
        variants=[PROMPT_VARIANTS["zero_shot"], PROMPT_VARIANTS["few_shot"]],
    )

    print(f"Created experiment: {experiment.name}")

    # Simulate user interactions
    users = [f"user_{i}" for i in range(200)]

    for user_id in users:
        # Get variant assignment
        variant = ab_manager.get_user_variant("prompt_optimization_v1", user_id)
        print(f"{user_id} -> {variant}")

        # Simulate success (simplified - in reality based on user action)
        if random.random() > 0.4:  # 60% success rate
            ab_manager.record_success("prompt_optimization_v1", variant)

            # Simulate feedback
            feedback_score = random.uniform(3, 5)
            ab_manager.record_feedback(
                "prompt_optimization_v1", variant, feedback_score
            )

    # Get results
    results = ab_manager.get_experiment_results("prompt_optimization_v1")

    print("\n" + "=" * 50)
    print("EXPERIMENT RESULTS")
    print("=" * 50)
    print(f"Experiment: {results['name']}")
    print(f"Status: {results['status']}")

    print("\nVariant Performance:")
    for variant in results["variants"]:
        print(f"\n{variant['name']}:")
        print(f"  Impressions: {variant['metrics']['impressions']}")
        print(f"  Successes: {variant['metrics']['successes']}")
        print(f"  Conversion Rate: {variant['metrics']['conversion_rate']:.2%}")
        print(f"  Avg Feedback: {variant['metrics']['avg_feedback_score']:.2f}")

    print("\nStatistical Analysis:")
    sig = results["statistical_significance"]
    print(f"  Significant: {sig['is_significant']}")
    print(f"  P-value: {sig['p_value']:.4f}")
    if sig["winner"]:
        print(f"  Winner: {sig['winner']}")

    # Complete the experiment
    if sig["is_significant"]:
        ab_manager.complete_experiment("prompt_optimization_v1")
        print("\nExperiment completed!")
