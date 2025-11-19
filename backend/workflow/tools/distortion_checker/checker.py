"""Main distortion checker pipeline."""

import logging
import os
import time
from typing import Union, List, Optional

from .models import DetectionResult, Distortion
from .detectors import HandDetector, PoseDetector, FaceDetector
from .analyzers import HandAnalyzer, PoseAnalyzer, FaceAnalyzer
from .utils import load_image


logger = logging.getLogger(__name__)

DEFAULT_MIN_CONFIDENCE = 0.82
ENV_VAR_MIN_CONFIDENCE = "DISTORTION_CHECKER_MIN_CONFIDENCE"


def _resolve_min_confidence(explicit: Optional[float]) -> float:
    """
    Resolve the minimum confidence threshold, preferring an explicit value,
    then the environment variable, and falling back to the default.
    """
    if explicit is not None:
        return explicit

    env_value = os.getenv(ENV_VAR_MIN_CONFIDENCE)
    if env_value is None:
        return DEFAULT_MIN_CONFIDENCE

    try:
        parsed = float(env_value)
    except ValueError:
        logger.warning(
            "Invalid %s=%r (must be a float). Falling back to default %.2f.",
            ENV_VAR_MIN_CONFIDENCE,
            env_value,
            DEFAULT_MIN_CONFIDENCE,
        )
        return DEFAULT_MIN_CONFIDENCE

    if not 0.0 <= parsed <= 1.0:
        logger.warning(
            "%s must be between 0 and 1. Got %.2f; using default %.2f instead.",
            ENV_VAR_MIN_CONFIDENCE,
            parsed,
            DEFAULT_MIN_CONFIDENCE,
        )
        return DEFAULT_MIN_CONFIDENCE

    logger.info(
        "Using %s=%.2f for distortion checker confidence threshold.",
        ENV_VAR_MIN_CONFIDENCE,
        parsed,
    )
    return parsed


class DistortionChecker:
    """
    Main distortion checker that coordinates detection and analysis.
    """
    
    def __init__(self, min_distortion_confidence: Optional[float] = None):
        """
        Initialize detectors and analyzers.
        
        Args:
            min_distortion_confidence: Minimum confidence required for a detected
                distortion to be surfaced in the final result. If not provided,
                the checker will look for the `DISTORTION_CHECKER_MIN_CONFIDENCE`
                environment variable before falling back to the default of 0.82.
        """
        # Initialize detectors (lazy loading)
        self._hand_detector = None
        self._pose_detector = None
        self._face_detector = None
        self.min_distortion_confidence = _resolve_min_confidence(min_distortion_confidence)
        
        # Initialize analyzers
        self.hand_analyzer = HandAnalyzer()
        self.pose_analyzer = PoseAnalyzer()
        self.face_analyzer = FaceAnalyzer()
    
    @property
    def hand_detector(self):
        """Lazy load hand detector."""
        if self._hand_detector is None:
            self._hand_detector = HandDetector()
        return self._hand_detector
    
    @property
    def pose_detector(self):
        """Lazy load pose detector."""
        if self._pose_detector is None:
            self._pose_detector = PoseDetector()
        return self._pose_detector
    
    @property
    def face_detector(self):
        """Lazy load face detector."""
        if self._face_detector is None:
            self._face_detector = FaceDetector()
        return self._face_detector
    
    def check_image(self, image_input: Union[str, bytes]) -> DetectionResult:
        """
        Check an image for distortions.
        
        Args:
            image_input: Image as file path, base64 string, or bytes
            
        Returns:
            DetectionResult with all detected distortions
        """
        start_time = time.time()
        
        # Load image
        image, width, height = load_image(image_input)
        
        # Run all detections
        all_distortions: List[Distortion] = []
        
        # 1. Hand detection and analysis
        try:
            hands = self.hand_detector.detect(image)
            hand_distortions = self.hand_analyzer.analyze(hands, width, height)
            all_distortions.extend(hand_distortions)
        except Exception as e:
            print(f"Hand detection error: {e}")
        
        # 2. Pose detection and analysis
        try:
            pose = self.pose_detector.detect(image)
            pose_distortions = self.pose_analyzer.analyze(pose, width, height)
            all_distortions.extend(pose_distortions)
        except Exception as e:
            print(f"Pose detection error: {e}")
        
        # 3. Face detection and analysis
        try:
            face = self.face_detector.detect(image)
            face_distortions = self.face_analyzer.analyze(face, width, height)
            all_distortions.extend(face_distortions)
        except Exception as e:
            print(f"Face detection error: {e}")
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Filter low-confidence distortions before building the result
        filtered_distortions = [
            distortion for distortion in all_distortions
            if distortion.confidence >= self.min_distortion_confidence
        ]
        
        # Build result
        result = DetectionResult(
            has_distortion=len(filtered_distortions) > 0,
            distortions=filtered_distortions,
            processing_time_ms=processing_time,
            image_width=width,
            image_height=height
        )
        
        return result
    
    def cleanup(self):
        """Clean up resources."""
        if self._hand_detector:
            self._hand_detector.close()
            self._hand_detector = None
        if self._pose_detector:
            self._pose_detector.close()
            self._pose_detector = None
        if self._face_detector:
            self._face_detector.close()
            self._face_detector = None
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.cleanup()
        except Exception:
            # Ignore cleanup errors during garbage collection
            pass

