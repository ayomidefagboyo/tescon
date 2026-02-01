#!/usr/bin/env python3
"""
Test script for Enhanced REMBG implementation.
This script tests the new optimizations and measures performance for 20k+ image processing.
"""

import asyncio
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any
import tempfile
from PIL import Image
import io

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Import our enhanced modules
try:
    from app.processing.rembg_processor import (
        initialize_processor,
        get_performance_stats,
        estimate_processing_time,
        optimize_for_large_dataset,
        process_image
    )
    from app.processing.processor_selector import get_processor_selector, ProcessorType
    from app.processing.batch_manager import create_optimized_processor_for_large_dataset

    print("✅ Successfully imported enhanced REMBG modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)


def create_test_image(width: int = 512, height: int = 512) -> bytes:
    """Create a simple test image for processing."""
    # Create a simple test image with a colored rectangle on white background
    img = Image.new('RGB', (width, height), 'white')
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    # Draw a blue rectangle that should be easy to segment
    draw.rectangle([width//4, height//4, 3*width//4, 3*height//4], fill='blue')

    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


async def test_processor_selection():
    """Test the intelligent processor selection system."""
    print("\n🧠 Testing Intelligent Processor Selection")
    print("=" * 50)

    selector = get_processor_selector()

    # Test different scenarios
    scenarios = [
        {"name": "Small batch (100 images)", "batch_size": 100, "priority": "balanced"},
        {"name": "Medium batch (1,000 images)", "batch_size": 1000, "priority": "cost"},
        {"name": "Large batch (20,000 images)", "batch_size": 20000, "priority": "cost"},
        {"name": "Quality priority", "batch_size": 500, "priority": "quality"},
        {"name": "Speed priority", "batch_size": 500, "priority": "speed"},
    ]

    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")

        requirements = {
            'priority': scenario['priority'],
            'batch_size': scenario['batch_size']
        }

        recommended_processor = selector.get_optimal_processor(requirements)
        cost_estimate = selector.estimate_batch_cost(recommended_processor, scenario['batch_size'])

        print(f"   Recommended: {recommended_processor.value}")
        print(f"   Total cost: ${cost_estimate['total_cost_usd']:.2f}")
        print(f"   Time estimate: {cost_estimate['estimated_time_hours']:.1f}h")


def test_performance_estimation():
    """Test processing time estimation for large datasets."""
    print("\n📊 Testing Performance Estimation")
    print("=" * 50)

    test_sizes = [100, 1000, 5000, 10000, 20651]  # Including our exact dataset size

    for size in test_sizes:
        estimate = estimate_processing_time(size)

        print(f"\n📈 Estimate for {size:,} images:")
        print(f"   Total time: {estimate['total_hours']:.1f}h ({estimate['total_minutes']:.0f}m)")
        print(f"   Per image: {estimate['per_image_ms']:.0f}ms")
        print(f"   Device: {estimate['device']}")
        print(f"   Model: {estimate['model']}")


async def test_enhanced_rembg_processing():
    """Test the enhanced REMBG processing with a sample image."""
    print("\n🖼️ Testing Enhanced REMBG Processing")
    print("=" * 50)

    try:
        # Initialize the processor
        print("🚀 Initializing enhanced REMBG processor...")
        initialize_processor()

        # Get performance stats
        stats = get_performance_stats()
        print(f"📊 System stats: {stats}")

        # Create test image
        print("🎨 Creating test image...")
        test_image_bytes = create_test_image()

        # Test different optimization levels
        optimization_levels = ["fast", "balanced", "quality"]

        for level in optimization_levels:
            print(f"\n⚡ Testing {level} optimization:")

            start_time = time.time()
            try:
                result = process_image(
                    test_image_bytes,
                    optimization_level=level,
                    white_background=True
                )
                processing_time = (time.time() - start_time) * 1000

                print(f"   ✅ Success in {processing_time:.0f}ms")
                print(f"   📦 Output size: {len(result.getvalue())} bytes")

            except Exception as e:
                print(f"   ❌ Failed: {str(e)}")

    except Exception as e:
        print(f"❌ Enhanced REMBG test failed: {e}")
        return False

    return True


def test_large_dataset_optimization():
    """Test optimizations specifically for large datasets."""
    print("\n🏭 Testing Large Dataset Optimization")
    print("=" * 50)

    # Test the optimization function
    print("🔧 Optimizing system for large dataset...")
    optimize_for_large_dataset()

    # Test optimized batch processor creation
    num_images = 20651  # Our exact dataset size
    print(f"📦 Creating optimized processor for {num_images:,} images...")

    optimized_processor = create_optimized_processor_for_large_dataset(num_images)

    # Get recommendations
    recommendations = optimized_processor.get_processing_recommendations(num_images)

    print(f"\n💡 Recommendations for {num_images:,} images:")
    for priority, rec in recommendations.items():
        cost = rec['cost_estimate']['total_cost_usd']
        time_hours = rec['cost_estimate']['estimated_time_hours']
        processor = rec['processor']

        print(f"   {priority.capitalize()}: {processor}")
        print(f"     💰 Cost: ${cost:.2f}")
        print(f"     ⏱️  Time: {time_hours:.1f}h")
        print(f"     💾 Model: {rec['performance'].get('current_model', 'N/A')}")
        print()


async def run_comprehensive_test():
    """Run all tests comprehensively."""
    print("🧪 Enhanced REMBG Comprehensive Test Suite")
    print("=" * 60)
    print(f"🐍 Python: {sys.version}")
    print(f"📂 Working directory: {os.getcwd()}")
    print()

    # Test 1: Enhanced REMBG processing
    success = await test_enhanced_rembg_processing()
    if not success:
        print("⚠️ Enhanced REMBG test failed, continuing with other tests...")

    # Test 2: Processor selection
    await test_processor_selection()

    # Test 3: Performance estimation
    test_performance_estimation()

    # Test 4: Large dataset optimization
    test_large_dataset_optimization()

    print("\n🎉 All tests completed!")
    print("\n📋 Summary for 20,651 images:")

    # Final summary for our specific use case
    selector = get_processor_selector()
    requirements = {'priority': 'cost', 'batch_size': 20651}
    best_processor = selector.get_optimal_processor(requirements)
    cost_estimate = selector.estimate_batch_cost(best_processor, 20651)

    print(f"   🎯 Recommended processor: {best_processor.value}")
    print(f"   💰 Total cost: ${cost_estimate['total_cost_usd']:.2f}")
    print(f"   ⏱️  Processing time: {cost_estimate['estimated_time_hours']:.1f} hours")
    print(f"   💸 Cost savings vs PicWish (~$2,065): ${2065 - cost_estimate['total_cost_usd']:.2f} (${2065 - cost_estimate['total_cost_usd']:.0f})")


if __name__ == "__main__":
    print("🚀 Starting Enhanced REMBG Test Suite...")

    # Check if we can import torch for GPU info
    try:
        import torch
        if torch.cuda.is_available():
            print(f"🔥 GPU detected: {torch.cuda.get_device_name(0)}")
            print(f"💾 GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
        else:
            print("💻 Using CPU (no GPU detected)")
    except ImportError:
        print("⚠️ PyTorch not available")

    print()

    # Run the tests
    asyncio.run(run_comprehensive_test())