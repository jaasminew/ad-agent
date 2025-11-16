"""Main distortion checker pipeline."""

import time
from typing import Union, List

from .models import DetectionResult, Distortion
from .detectors import HandDetector, PoseDetector, FaceDetector
from .analyzers import HandAnalyzer, PoseAnalyzer, FaceAnalyzer
from .utils import load_image


class DistortionChecker:
    """
    Main distortion checker that coordinates detection and analysis.
    """
    
    def __init__(self):
        """Initialize detectors and analyzers."""
        # Initialize detectors (lazy loading)
        self._hand_detector = None
        self._pose_detector = None
        self._face_detector = None
        
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
        
        # Build result
        result = DetectionResult(
            has_distortion=len(all_distortions) > 0,
            distortions=all_distortions,
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

