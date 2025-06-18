"""
Test A/B testing framework
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from ab_testing import ABTestingManager, Variant, Experiment, PROMPT_VARIANTS


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for tests"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_variant_metrics():
    """Test variant metrics tracking"""
    variant = Variant(
        name="test_variant",
        description="Test variant",
        config={"template": "test template"}
    )
    
    # Test initial state
    assert variant.metrics["impressions"] == 0
    assert variant.metrics["successes"] == 0
    assert variant.metrics["conversion_rate"] == 0.0
    
    # Test impression recording
    variant.record_impression()
    assert variant.metrics["impressions"] == 1
    
    # Test success recording
    variant.record_success()
    assert variant.metrics["successes"] == 1
    assert variant.metrics["conversion_rate"] == 1.0
    
    # Test feedback
    variant.record_feedback(4.5)
    assert variant.metrics["feedback_count"] == 1
    assert variant.metrics["avg_feedback_score"] == 4.5


def test_ab_testing_manager(temp_storage):
    """Test A/B testing manager functionality"""
    manager = ABTestingManager(storage_dir=temp_storage)
    
    # Test experiment creation
    experiment = manager.create_experiment(
        name="test_experiment",
        description="Test experiment",
        variants=[
            {"name": "variant_a", "description": "Variant A", "config": {"test": "a"}},
            {"name": "variant_b", "description": "Variant B", "config": {"test": "b"}}
        ]
    )
    
    assert experiment.name == "test_experiment"
    assert len(experiment.variants) == 2
    assert "test_experiment" in manager.experiments
    
    # Test user assignment
    variant_a = manager.get_user_variant("test_experiment", "user_1")
    variant_b = manager.get_user_variant("test_experiment", "user_1")
    
    # Same user should get same variant (deterministic)
    assert variant_a == variant_b
    assert variant_a in ["variant_a", "variant_b"]
    
    # Test success recording
    manager.record_success("test_experiment", variant_a)
    
    # Test results
    results = manager.get_experiment_results("test_experiment")
    assert results["name"] == "test_experiment"
    assert len(results["variants"]) == 2


def test_prompt_variants():
    """Test that prompt variants are properly defined"""
    assert "zero_shot" in PROMPT_VARIANTS
    assert "few_shot" in PROMPT_VARIANTS
    assert "persona_based" in PROMPT_VARIANTS
    
    for variant_name, variant_data in PROMPT_VARIANTS.items():
        assert "name" in variant_data
        assert "description" in variant_data
        assert "config" in variant_data
        assert "template" in variant_data["config"]


def test_deterministic_assignment():
    """Test that user assignment is deterministic"""
    manager = ABTestingManager()
    
    # Create test experiment
    manager.create_experiment(
        name="deterministic_test",
        description="Test deterministic assignment",
        variants=[
            {"name": "a", "description": "A", "config": {}},
            {"name": "b", "description": "B", "config": {}}
        ]
    )
    
    # Same user should always get same variant
    user_id = "test_user_123"
    variant1 = manager.get_user_variant("deterministic_test", user_id)
    variant2 = manager.get_user_variant("deterministic_test", user_id)
    variant3 = manager.get_user_variant("deterministic_test", user_id)
    
    assert variant1 == variant2 == variant3 