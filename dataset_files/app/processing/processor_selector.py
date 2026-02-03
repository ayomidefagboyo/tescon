"""Intelligent processor selection for optimal background removal."""
import time
import os
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from io import BytesIO

class ProcessorType(Enum):
    """Available background removal processors."""
    ENHANCED_REMBG = "enhanced_rembg"
    PICWISH = "picwish"
    FALLBACK_REMBG = "fallback_rembg"


@dataclass
class ProcessorPerformance:
    """Performance metrics for a processor."""
    avg_processing_time: float  # seconds
    success_rate: float  # 0.0 to 1.0
    quality_score: float  # 0.0 to 1.0 (estimated)
    cost_per_image: float  # USD
    last_updated: float  # timestamp


class IntelligentProcessorSelector:
    """Intelligent selection of background removal processor based on requirements."""

    def __init__(self):
        self.performance_history: Dict[ProcessorType, ProcessorPerformance] = {}
        self._initialize_default_metrics()

    def _initialize_default_metrics(self):
        """Initialize with default performance metrics."""
        # Enhanced REMBG (our optimized version)
        self.performance_history[ProcessorType.ENHANCED_REMBG] = ProcessorPerformance(
            avg_processing_time=0.35,  # GPU BiRefNet
            success_rate=0.95,
            quality_score=0.88,
            cost_per_image=0.002,  # Infrastructure cost only
            last_updated=time.time()
        )

        # PicWish API
        self.performance_history[ProcessorType.PICWISH] = ProcessorPerformance(
            avg_processing_time=3.0,  # Network latency
            success_rate=0.97,
            quality_score=0.90,
            cost_per_image=0.10,  # API cost
            last_updated=time.time()
        )

        # Fallback REMBG (original implementation)
        self.performance_history[ProcessorType.FALLBACK_REMBG] = ProcessorPerformance(
            avg_processing_time=0.8,  # CPU IS-Net
            success_rate=0.92,
            quality_score=0.82,
            cost_per_image=0.001,  # Infrastructure cost only
            last_updated=time.time()
        )

    def get_optimal_processor(
        self,
        requirements: Optional[Dict[str, Any]] = None
    ) -> ProcessorType:
        """
        Select the optimal processor based on requirements and current conditions.

        Args:
            requirements: Dict with keys like 'priority', 'budget_limit', 'max_time', etc.

        Returns:
            Best processor type for the requirements
        """
        if requirements is None:
            requirements = {}

        priority = requirements.get('priority', 'balanced')  # 'speed', 'quality', 'cost', 'balanced'
        budget_limit = requirements.get('budget_limit', 0.05)  # USD per image
        max_time = requirements.get('max_time', 5.0)  # seconds per image
        min_success_rate = requirements.get('min_success_rate', 0.9)
        batch_size = requirements.get('batch_size', 1)

        # Check processor availability
        available_processors = self._check_processor_availability()

        # Filter by constraints
        valid_processors = []
        for proc_type in available_processors:
            perf = self.performance_history[proc_type]

            if (perf.cost_per_image <= budget_limit and
                perf.avg_processing_time <= max_time and
                perf.success_rate >= min_success_rate):
                valid_processors.append(proc_type)

        if not valid_processors:
            # Relax constraints and pick best available
            print("⚠ No processor meets all constraints, selecting best available")
            valid_processors = available_processors

        # Score processors based on priority
        scores = {}
        for proc_type in valid_processors:
            perf = self.performance_history[proc_type]

            if priority == 'speed':
                # Prioritize speed
                scores[proc_type] = (
                    (1.0 / perf.avg_processing_time) * 0.6 +
                    perf.success_rate * 0.3 +
                    (1.0 - perf.cost_per_image / 0.10) * 0.1
                )
            elif priority == 'quality':
                # Prioritize quality
                scores[proc_type] = (
                    perf.quality_score * 0.6 +
                    perf.success_rate * 0.3 +
                    (1.0 / perf.avg_processing_time) * 0.1
                )
            elif priority == 'cost':
                # Prioritize cost
                scores[proc_type] = (
                    (1.0 - perf.cost_per_image / 0.10) * 0.6 +
                    perf.success_rate * 0.3 +
                    (1.0 / perf.avg_processing_time) * 0.1
                )
            else:  # balanced
                # Balanced scoring
                time_score = 1.0 / perf.avg_processing_time
                cost_score = 1.0 - (perf.cost_per_image / 0.10)

                scores[proc_type] = (
                    time_score * 0.3 +
                    perf.quality_score * 0.25 +
                    perf.success_rate * 0.25 +
                    cost_score * 0.2
                )

        # Special handling for large batches
        if batch_size > 1000:
            # For large batches, strongly favor cost efficiency
            for proc_type in scores:
                perf = self.performance_history[proc_type]
                if proc_type == ProcessorType.ENHANCED_REMBG:
                    scores[proc_type] *= 1.5  # Boost local processing for large batches
                elif proc_type == ProcessorType.PICWISH:
                    scores[proc_type] *= 0.5  # Penalize expensive API for large batches

        # Return highest scoring processor
        best_processor = max(scores.items(), key=lambda x: x[1])[0]

        print(f"🎯 Selected processor: {best_processor.value} (priority: {priority}, batch: {batch_size})")
        return best_processor

    def _check_processor_availability(self) -> List[ProcessorType]:
        """Check which processors are currently available."""
        available = []

        # Check Enhanced REMBG
        try:
            from app.processing.rembg_processor import is_model_loaded
            if is_model_loaded() or True:  # Can be initialized
                available.append(ProcessorType.ENHANCED_REMBG)
        except Exception as e:
            print(f"Enhanced REMBG not available: {str(e)}")

        # Check PicWish API
        try:
            from app.processing.picwish_processor import check_api_available
            if check_api_available():
                available.append(ProcessorType.PICWISH)
        except Exception as e:
            print(f"PicWish API not available: {str(e)}")

        # Fallback REMBG should always be available
        available.append(ProcessorType.FALLBACK_REMBG)

        return available

    def update_performance(
        self,
        processor_type: ProcessorType,
        processing_time: float,
        success: bool,
        estimated_quality: Optional[float] = None
    ):
        """Update performance metrics based on actual usage."""
        if processor_type not in self.performance_history:
            return

        perf = self.performance_history[processor_type]

        # Exponential moving average for processing time
        alpha = 0.2  # Learning rate
        perf.avg_processing_time = (
            alpha * processing_time +
            (1 - alpha) * perf.avg_processing_time
        )

        # Update success rate
        perf.success_rate = (
            alpha * (1.0 if success else 0.0) +
            (1 - alpha) * perf.success_rate
        )

        # Update quality score if provided
        if estimated_quality is not None:
            perf.quality_score = (
                alpha * estimated_quality +
                (1 - alpha) * perf.quality_score
            )

        perf.last_updated = time.time()

    def get_processor_instance(self, processor_type: ProcessorType):
        """Get an instance of the specified processor."""
        if processor_type == ProcessorType.ENHANCED_REMBG:
            from app.processing import rembg_processor
            return rembg_processor
        elif processor_type == ProcessorType.PICWISH:
            from app.processing import picwish_processor
            return picwish_processor
        elif processor_type == ProcessorType.FALLBACK_REMBG:
            from app.processing import rembg_processor
            # Use original settings for fallback
            return rembg_processor
        else:
            raise ValueError(f"Unknown processor type: {processor_type}")

    def estimate_batch_cost(
        self,
        processor_type: ProcessorType,
        num_images: int
    ) -> Dict[str, float]:
        """Estimate cost for processing a batch of images."""
        perf = self.performance_history[processor_type]

        total_cost = num_images * perf.cost_per_image
        total_time = num_images * perf.avg_processing_time

        return {
            "total_cost_usd": total_cost,
            "cost_per_image": perf.cost_per_image,
            "estimated_time_seconds": total_time,
            "estimated_time_hours": total_time / 3600,
            "processor": processor_type.value
        }

    def get_recommendations_for_batch(self, num_images: int) -> Dict[str, Any]:
        """Get processor recommendations for a specific batch size."""
        recommendations = {}

        for priority in ['speed', 'quality', 'cost', 'balanced']:
            requirements = {
                'priority': priority,
                'batch_size': num_images,
                'budget_limit': 0.05 if priority != 'cost' else 0.01,
                'max_time': 10.0 if priority != 'speed' else 2.0
            }

            best_processor = self.get_optimal_processor(requirements)
            cost_estimate = self.estimate_batch_cost(best_processor, num_images)

            recommendations[priority] = {
                "processor": best_processor.value,
                "cost_estimate": cost_estimate,
                "performance": self.performance_history[best_processor].__dict__
            }

        return recommendations


# Global selector instance
_processor_selector = IntelligentProcessorSelector()


def get_processor_selector() -> IntelligentProcessorSelector:
    """Get the global processor selector instance."""
    return _processor_selector


def select_optimal_processor(**requirements) -> ProcessorType:
    """Convenience function to select optimal processor."""
    return _processor_selector.get_optimal_processor(requirements)


def process_with_optimal_selection(
    image_bytes: bytes,
    requirements: Optional[Dict[str, Any]] = None,
    **kwargs
) -> BytesIO:
    """Process image with automatically selected optimal processor."""
    processor_type = select_optimal_processor(**(requirements or {}))
    processor_module = _processor_selector.get_processor_instance(processor_type)

    start_time = time.time()
    try:
        result = processor_module.process_image(image_bytes, **kwargs)
        processing_time = time.time() - start_time

        # Update performance metrics
        _processor_selector.update_performance(
            processor_type, processing_time, success=True
        )

        return result
    except Exception as e:
        processing_time = time.time() - start_time
        _processor_selector.update_performance(
            processor_type, processing_time, success=False
        )
        raise