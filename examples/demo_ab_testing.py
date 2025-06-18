#!/usr/bin/env python3
"""
Demo script showing A/B testing capabilities in SynthScribe

This demonstrates how the system can test different prompt strategies
to optimize recommendation quality.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ab_testing import ABTestingManager, PROMPT_VARIANTS
from config import Config, LLMProvider
from logger import get_logger
import random
import time


def simulate_user_session(ab_manager: ABTestingManager, user_id: str, mood: str):
    """Simulate a user getting recommendations and providing feedback"""
    logger = get_logger()

    # Get variant assignment
    variant = ab_manager.get_user_variant("prompt_optimization", user_id)
    if not variant:
        print(f"No active experiment for {user_id}")
        return

    print(f"\n{'='*50}")
    print(f"User: {user_id}")
    print(f"Mood: {mood}")
    print(f"Variant: {variant}")
    print(f"{'='*50}")

    # Simulate getting recommendations (in real app, this would use the variant's prompt)
    with logger.performance(f"generate_recommendations_{variant}"):
        time.sleep(random.uniform(0.5, 1.5))  # Simulate API call

        # Simulate recommendations
        recommendations = [
            {"genre": "Lofi Hip Hop", "quality": random.uniform(3, 5)},
            {"genre": "Ambient", "quality": random.uniform(3, 5)},
            {"genre": "Jazz", "quality": random.uniform(3, 5)},
            {"genre": "Classical", "quality": random.uniform(3, 5)},
        ]

    print("\nRecommendations generated:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['genre']} (Quality: {rec['quality']:.1f})")

    # Simulate user interaction
    # Higher quality = more likely to interact
    avg_quality = sum(r["quality"] for r in recommendations) / len(recommendations)
    interaction_probability = avg_quality / 5.0  # Convert to 0-1 probability

    # Add variant-specific bias (simulating that some prompts perform better)
    if variant == "persona_based":
        interaction_probability *= 1.2  # 20% better
    elif variant == "few_shot":
        interaction_probability *= 1.1  # 10% better

    # Ensure probability stays in valid range
    interaction_probability = min(interaction_probability, 0.95)

    # Simulate user action
    if random.random() < interaction_probability:
        print("✓ User saved/liked recommendations")
        ab_manager.record_success("prompt_optimization", variant)

        # Simulate feedback
        feedback_score = random.uniform(avg_quality - 0.5, min(avg_quality + 0.5, 5))
        ab_manager.record_feedback("prompt_optimization", variant, feedback_score)
        print(f"✓ User feedback: {feedback_score:.1f}/5")
    else:
        print("✗ User didn't interact with recommendations")


def main():
    """Run A/B testing demonstration"""
    print("SynthScribe A/B Testing Demo")
    print("=" * 60)

    # Initialize A/B testing manager
    ab_manager = ABTestingManager()

    # Create experiment if it doesn't exist
    if "prompt_optimization" not in ab_manager.experiments:
        print("Creating new experiment: Prompt Optimization")
        ab_manager.create_experiment(
            name="prompt_optimization",
            description="Testing different prompt strategies for better recommendations",
            variants=[
                PROMPT_VARIANTS["zero_shot"],
                PROMPT_VARIANTS["few_shot"],
                PROMPT_VARIANTS["persona_based"],
            ],
        )

    # Test moods
    test_moods = [
        "coding late at night",
        "morning workout",
        "relaxing after work",
        "focusing on deep work",
        "weekend party vibes",
        "studying for exams",
        "cooking dinner",
        "rainy day mood",
    ]

    # Simulate multiple users
    print("\nSimulating user interactions...")
    num_users = 30  # Reduced for demo

    for i in range(num_users):
        user_id = f"demo_user_{i:03d}"
        mood = random.choice(test_moods)
        simulate_user_session(ab_manager, user_id, mood)
        time.sleep(0.1)  # Small delay for readability

    # Show results
    print("\n" + "=" * 60)
    print("EXPERIMENT RESULTS")
    print("=" * 60)

    results = ab_manager.get_experiment_results("prompt_optimization")

    print(f"\nExperiment: {results['name']}")
    print(f"Status: {results['status']}")

    print(
        "\n%-15s %10s %10s %12s %12s"
        % ("Variant", "Shown", "Successes", "Conversion", "Avg Rating")
    )
    print("-" * 65)

    for variant in results["variants"]:
        metrics = variant["metrics"]
        print(
            "%-15s %10d %10d %11.1f%% %12.2f"
            % (
                variant["name"],
                metrics["impressions"],
                metrics["successes"],
                metrics["conversion_rate"] * 100,
                metrics["avg_feedback_score"] or 0,
            )
        )

    # Statistical significance
    sig = results["statistical_significance"]
    print(f"\nStatistical Analysis:")
    print(f"  Confidence Level: {sig['confidence_level']:.0%}")
    print(f"  P-value: {sig['p_value']:.4f}")
    print(f"  Statistically Significant: {sig['is_significant']}")

    if sig["winner"]:
        print(f"  🏆 Winner: {sig['winner']}")
        print("\n✅ Recommendation: Deploy the winning variant to all users")
    else:
        print("\n⏳ Need more data for statistical significance")
        print("   Continue running the experiment...")

    # Show what would happen in production
    print("\n" + "=" * 60)
    print("PRODUCTION IMPLICATIONS")
    print("=" * 60)

    if sig["winner"]:
        winning_variant = next(
            v for v in results["variants"] if v["name"] == sig["winner"]
        )
        baseline = next(v for v in results["variants"] if v["name"] == "zero_shot")

        improvement = (
            (
                winning_variant["metrics"]["conversion_rate"]
                - baseline["metrics"]["conversion_rate"]
            )
            / baseline["metrics"]["conversion_rate"]
            * 100
        )

        print(f"\nDeploying '{sig['winner']}' variant would result in:")
        print(f"  • {improvement:+.1f}% improvement in user engagement")
        print(
            f"  • Better recommendation quality ({winning_variant['metrics']['avg_feedback_score']:.2f} vs {baseline['metrics']['avg_feedback_score']:.2f})"
        )

        # Cost implications
        if sig["winner"] != "zero_shot":
            print(f"  • Slightly higher token usage (~10-20% more)")
            print(f"  • Worth it for {improvement:.1f}% engagement boost")


if __name__ == "__main__":
    main()
