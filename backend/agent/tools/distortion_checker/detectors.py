"""MediaPipe detector wrappers for hands, pose, and face detection."""

from typing import List, Optional
import numpy as np

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None

from .models import HandLandmarks, PoseLandmarks, FaceLandmarks, LandmarkData


class HandDetector:
    """Wrapper for MediaPipe Hands detector."""
    
    def __init__(self, max_num_hands: int = 20, min_detection_confidence: float = 0.01):
        """
        Initialize hand detector.
        
        Args:
            max_num_hands: Maximum number of hands to detect
            min_detection_confidence: Minimum confidence for detection
        """
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("mediapipe is not installed. Install with: pip install mediapipe")
        
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=True,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
        )
    
    def detect(self, image: np.ndarray) -> List[HandLandmarks]:
        """
        Detect hands in image.
        
        Args:
            image: RGB image as numpy array
        
        Returns:
            List of HandLandmarks objects
        """
        results = self.hands.process(image)
        
        if not results.multi_hand_landmarks:
            return []
        
        hands = []
        for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
            # Get handedness
            handedness = results.multi_handedness[i].classification[0].label
            score = results.multi_handedness[i].classification[0].score
            
            # Convert landmarks
            landmarks = [
                LandmarkData(x=lm.x, y=lm.y, z=lm.z)
                for lm in hand_landmarks.landmark
            ]
            
            hands.append(HandLandmarks(
                landmarks=landmarks,
                handedness=handedness,
                score=score
            ))
        
        return hands
    
    def close(self):
        """Release resources."""
        if self.hands:
            self.hands.close()


class PoseDetector:
    """Wrapper for MediaPipe Pose detector."""
    
    def __init__(self, min_detection_confidence: float = 0.5):
        """
        Initialize pose detector.
        
        Args:
            min_detection_confidence: Minimum confidence for detection
        """
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("mediapipe is not installed. Install with: pip install mediapipe")
        
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=True,
            min_detection_confidence=min_detection_confidence,
        )
    
    def detect(self, image: np.ndarray) -> Optional[PoseLandmarks]:
        """
        Detect pose in image.
        
        Args:
            image: RGB image as numpy array
        
        Returns:
            PoseLandmarks object or None if no pose detected
        """
        results = self.pose.process(image)
        
        if not results.pose_landmarks:
            return None
        
        # Convert landmarks
        landmarks = [
            LandmarkData(
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibility=lm.visibility
            )
            for lm in results.pose_landmarks.landmark
        ]
        
        # Calculate average visibility as score
        avg_visibility = np.mean([lm.visibility for lm in landmarks])
        
        return PoseLandmarks(landmarks=landmarks, score=float(avg_visibility))
    
    def close(self):
        """Release resources."""
        if self.pose:
            self.pose.close()


class FaceDetector:
    """Wrapper for MediaPipe Face Mesh detector."""
    
    def __init__(self, min_detection_confidence: float = 0.5):
        """
        Initialize face detector.
        
        Args:
            min_detection_confidence: Minimum confidence for detection
        """
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("mediapipe is not installed. Install with: pip install mediapipe")
        
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            min_detection_confidence=min_detection_confidence,
        )
    
    def detect(self, image: np.ndarray) -> Optional[FaceLandmarks]:
        """
        Detect face in image.
        
        Args:
            image: RGB image as numpy array
        
        Returns:
            FaceLandmarks object or None if no face detected
        """
        results = self.face_mesh.process(image)
        
        if not results.multi_face_landmarks:
            return None
        
        # Take first face only
        face_landmarks = results.multi_face_landmarks[0]
        
        # Convert landmarks
        landmarks = [
            LandmarkData(x=lm.x, y=lm.y, z=lm.z)
            for lm in face_landmarks.landmark
        ]
        
        return FaceLandmarks(landmarks=landmarks, score=1.0)
    
    def close(self):
        """Release resources."""
        if self.face_mesh:
            self.face_mesh.close()

