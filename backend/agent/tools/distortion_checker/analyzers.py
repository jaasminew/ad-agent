"""Analyzers for detecting distortions in hand, pose, and face landmarks."""

from typing import List, Optional, Tuple
import numpy as np

from .models import (
    HandLandmarks,
    PoseLandmarks,
    FaceLandmarks,
    Distortion,
    BoundingBox,
)
from .utils import calculate_bounding_box, calculate_distance, calculate_angle


# MediaPipe landmark indices
FINGER_TIPS = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
PALM_LANDMARKS = [0, 5, 9, 13, 17]  # Wrist and base of each finger


class HandAnalyzer:
    """Analyzes hand landmarks for distortions."""
    
    def __init__(
        self,
        max_hands: int = 2,
        max_fingers_per_hand: int = 5,
        finger_distance_threshold: float = 0.03,
        palm_ratio_min: float = 0.6,
        palm_ratio_max: float = 1.8,
        enable_extra_hand_check: bool = False,
    ):
        """
        Initialize hand analyzer.
        
        Args:
            max_hands: Maximum anatomically correct number of hands
            max_fingers_per_hand: Maximum fingers per hand
            finger_distance_threshold: Minimum distance between finger tips
            palm_ratio_min: Minimum palm aspect ratio
            palm_ratio_max: Maximum palm aspect ratio
            enable_extra_hand_check: Whether to surface a distortion when more
                than ``max_hands`` hands are detected.
        """
        self.max_hands = max_hands
        self.max_fingers_per_hand = max_fingers_per_hand
        self.finger_distance_threshold = finger_distance_threshold
        self.palm_ratio_min = palm_ratio_min
        self.palm_ratio_max = palm_ratio_max
        self.enable_extra_hand_check = enable_extra_hand_check
    
    def analyze(
        self,
        hands: List[HandLandmarks],
        image_width: int,
        image_height: int
    ) -> List[Distortion]:
        """
        Analyze hands for distortions.
        
        Args:
            hands: List of detected hands
            image_width: Image width in pixels
            image_height: Image height in pixels
            
        Returns:
            List of detected distortions
        """
        distortions = []
        
        # Check for extra hands
        if self.enable_extra_hand_check and len(hands) > self.max_hands:
            all_landmarks = []
            for hand in hands:
                for lm in hand.landmarks:
                    all_landmarks.append((lm.x, lm.y))
            
            bbox_dict = calculate_bounding_box(all_landmarks, image_width, image_height)
            bbox = BoundingBox(**bbox_dict)
            
            distortions.append(Distortion(
                label="extra_hands",
                confidence=0.95,
                bounding_box=bbox,
                details=f"Detected {len(hands)} hands (expected ≤ {self.max_hands})"
            ))
        
        # Analyze each hand
        for i, hand in enumerate(hands):
            hand_distortions = self._analyze_single_hand(
                hand, image_width, image_height, i
            )
            distortions.extend(hand_distortions)
        
        return distortions
    
    def _analyze_single_hand(
        self,
        hand: HandLandmarks,
        image_width: int,
        image_height: int,
        hand_index: int
    ) -> List[Distortion]:
        """Analyze a single hand for distortions."""
        distortions = []
        landmarks = hand.landmarks
        
        # Get landmark positions
        hand_points = [(lm.x, lm.y) for lm in landmarks]
        
        # Calculate bounding box
        bbox_dict = calculate_bounding_box(hand_points, image_width, image_height)
        bbox = BoundingBox(**bbox_dict)
        
        # Check for extra fingers
        finger_tips = [landmarks[i] for i in FINGER_TIPS]
        clustered_tips = self._count_clustered_tips(finger_tips)
        
        if clustered_tips > self.max_fingers_per_hand:
            distortions.append(Distortion(
                label="extra_fingers",
                confidence=0.90,
                bounding_box=bbox,
                details=f"Detected {clustered_tips} finger tips on {hand.handedness} hand (expected {self.max_fingers_per_hand})"
            ))
        
        # Check palm geometry
        palm_distortion = self._check_palm_geometry(landmarks, image_width, image_height)
        if palm_distortion:
            distortions.append(palm_distortion)
        
        return distortions
    
    def _count_clustered_tips(self, finger_tips: List) -> int:
        """Count distinct finger tips based on distance clustering."""
        if not finger_tips:
            return 0
        
        # Simple counting - check if tips are too close together
        positions = [(tip.x, tip.y) for tip in finger_tips]
        
        # Count unique positions (tips far enough apart)
        unique_tips = []
        for pos in positions:
            is_unique = True
            for unique_pos in unique_tips:
                if calculate_distance(pos, unique_pos) < self.finger_distance_threshold:
                    is_unique = False
                    break
            if is_unique:
                unique_tips.append(pos)
        
        return len(unique_tips)
    
    def _check_palm_geometry(
        self,
        landmarks: List,
        image_width: int,
        image_height: int
    ) -> Optional[Distortion]:
        """Check if palm geometry is anatomically correct."""
        palm_points = [(landmarks[i].x, landmarks[i].y) for i in PALM_LANDMARKS]
        
        # Calculate palm dimensions
        x_coords = [p[0] for p in palm_points]
        y_coords = [p[1] for p in palm_points]
        
        palm_width = max(x_coords) - min(x_coords)
        palm_height = max(y_coords) - min(y_coords)
        
        if palm_height < 1e-6:
            return None
        
        aspect_ratio = palm_width / palm_height
        
        if aspect_ratio < self.palm_ratio_min or aspect_ratio > self.palm_ratio_max:
            bbox_dict = calculate_bounding_box(palm_points, image_width, image_height, padding=0.2)
            bbox = BoundingBox(**bbox_dict)
            
            return Distortion(
                label="warped_hand",
                confidence=0.85,
                bounding_box=bbox,
                details=f"Palm aspect ratio {aspect_ratio:.2f} outside normal range [{self.palm_ratio_min}, {self.palm_ratio_max}]"
            )
        
        return None


class PoseAnalyzer:
    """Analyzes pose landmarks for distortions."""
    
    def __init__(
        self,
        limb_ratio_threshold: float = 2.5,
        elongation_threshold: float = 3.0,
    ):
        """
        Initialize pose analyzer.
        
        Args:
            limb_ratio_threshold: Maximum ratio between left/right limbs
            elongation_threshold: Maximum limb-to-torso ratio
        """
        self.limb_ratio_threshold = limb_ratio_threshold
        self.elongation_threshold = elongation_threshold
    
    def analyze(
        self,
        pose: Optional[PoseLandmarks],
        image_width: int,
        image_height: int
    ) -> List[Distortion]:
        """
        Analyze pose for distortions.
        
        Args:
            pose: Detected pose landmarks
            image_width: Image width in pixels
            image_height: Image height in pixels
            
        Returns:
            List of detected distortions
        """
        if not pose or not pose.landmarks:
            return []
        
        distortions = []
        landmarks = pose.landmarks
        
        # Check limb proportions
        limb_distortion = self._check_limb_proportions(landmarks, image_width, image_height)
        if limb_distortion:
            distortions.append(limb_distortion)
        
        # Check for elongation
        elongation_distortion = self._check_elongation(landmarks, image_width, image_height)
        if elongation_distortion:
            distortions.append(elongation_distortion)
        
        return distortions
    
    def _check_limb_proportions(
        self,
        landmarks: List,
        image_width: int,
        image_height: int
    ) -> Optional[Distortion]:
        """Check if limb proportions are anatomically correct."""
        # MediaPipe pose landmark indices
        # 11, 12: shoulders, 13, 14: elbows, 15, 16: wrists
        # 23, 24: hips, 25, 26: knees, 27, 28: ankles
        
        if len(landmarks) < 33:
            return None
        
        # Calculate arm lengths
        left_arm = calculate_distance(
            (landmarks[11].x, landmarks[11].y),
            (landmarks[15].x, landmarks[15].y)
        )
        right_arm = calculate_distance(
            (landmarks[12].x, landmarks[12].y),
            (landmarks[16].x, landmarks[16].y)
        )
        
        # Check arm symmetry
        if min(left_arm, right_arm) > 0:
            arm_ratio = max(left_arm, right_arm) / min(left_arm, right_arm)
            
            if arm_ratio > self.limb_ratio_threshold:
                # Get affected landmarks
                affected_points = [
                    (landmarks[i].x, landmarks[i].y)
                    for i in [11, 12, 13, 14, 15, 16]
                ]
                bbox_dict = calculate_bounding_box(affected_points, image_width, image_height)
                bbox = BoundingBox(**bbox_dict)
                
                return Distortion(
                    label="warped_limbs",
                    confidence=0.88,
                    bounding_box=bbox,
                    details=f"Arm length asymmetry ratio {arm_ratio:.2f} exceeds threshold {self.limb_ratio_threshold}"
                )
        
        return None
    
    def _check_elongation(
        self,
        landmarks: List,
        image_width: int,
        image_height: int
    ) -> Optional[Distortion]:
        """Check for unnaturally elongated limbs."""
        if len(landmarks) < 33:
            return None
        
        # Calculate torso length (shoulder to hip)
        torso_length = calculate_distance(
            (landmarks[11].x, landmarks[11].y),
            (landmarks[23].x, landmarks[23].y)
        )
        
        # Calculate leg length
        leg_length = calculate_distance(
            (landmarks[23].x, landmarks[23].y),
            (landmarks[27].x, landmarks[27].y)
        )
        
        if torso_length < 1e-6:
            return None
        
        leg_to_torso_ratio = leg_length / torso_length
        
        if leg_to_torso_ratio > self.elongation_threshold:
            affected_points = [
                (landmarks[i].x, landmarks[i].y)
                for i in [23, 24, 25, 26, 27, 28]
            ]
            bbox_dict = calculate_bounding_box(affected_points, image_width, image_height)
            bbox = BoundingBox(**bbox_dict)
            
            return Distortion(
                label="elongated_limbs",
                confidence=0.87,
                bounding_box=bbox,
                details=f"Leg-to-torso ratio {leg_to_torso_ratio:.2f} exceeds threshold {self.elongation_threshold}"
            )
        
        return None


class FaceAnalyzer:
    """Analyzes face mesh landmarks for distortions."""
    
    def __init__(
        self,
        face_ratio_min: float = 1.2,
        face_ratio_max: float = 2.0,
        eye_symmetry_threshold: float = 0.15,
    ):
        """
        Initialize face analyzer.
        
        Args:
            face_ratio_min: Minimum face aspect ratio
            face_ratio_max: Maximum face aspect ratio
            eye_symmetry_threshold: Maximum eye size difference
        """
        self.face_ratio_min = face_ratio_min
        self.face_ratio_max = face_ratio_max
        self.eye_symmetry_threshold = eye_symmetry_threshold
    
    def analyze(
        self,
        face: Optional[FaceLandmarks],
        image_width: int,
        image_height: int
    ) -> List[Distortion]:
        """
        Analyze face for distortions.
        
        Args:
            face: Detected face landmarks
            image_width: Image width in pixels
            image_height: Image height in pixels
            
        Returns:
            List of detected distortions
        """
        if not face or not face.landmarks:
            return []
        
        distortions = []
        landmarks = face.landmarks
        
        # Check face proportions
        face_distortion = self._check_face_proportions(landmarks, image_width, image_height)
        if face_distortion:
            distortions.append(face_distortion)
        
        # Check eye symmetry
        eye_distortion = self._check_eye_symmetry(landmarks, image_width, image_height)
        if eye_distortion:
            distortions.append(eye_distortion)
        
        return distortions
    
    def _check_face_proportions(
        self,
        landmarks: List,
        image_width: int,
        image_height: int
    ) -> Optional[Distortion]:
        """Check if face proportions are normal."""
        if len(landmarks) < 468:
            return None
        
        # Get face outline points
        face_points = [(lm.x, lm.y) for lm in landmarks]
        
        x_coords = [p[0] for p in face_points]
        y_coords = [p[1] for p in face_points]
        
        face_width = max(x_coords) - min(x_coords)
        face_height = max(y_coords) - min(y_coords)
        
        if face_width < 1e-6:
            return None
        
        aspect_ratio = face_height / face_width
        
        if aspect_ratio < self.face_ratio_min or aspect_ratio > self.face_ratio_max:
            bbox_dict = calculate_bounding_box(face_points, image_width, image_height)
            bbox = BoundingBox(**bbox_dict)
            
            return Distortion(
                label="deformed_face",
                confidence=0.82,
                bounding_box=bbox,
                details=f"Face aspect ratio {aspect_ratio:.2f} outside normal range [{self.face_ratio_min}, {self.face_ratio_max}]"
            )
        
        return None
    
    def _check_eye_symmetry(
        self,
        landmarks: List,
        image_width: int,
        image_height: int
    ) -> Optional[Distortion]:
        """Check if eyes are symmetric."""
        if len(landmarks) < 468:
            return None
        
        # Simplified eye landmarks (approximate indices)
        # Left eye: ~130-159, Right eye: ~359-386
        left_eye_indices = range(130, 145)
        right_eye_indices = range(359, 374)
        
        left_eye_points = [(landmarks[i].x, landmarks[i].y) for i in left_eye_indices if i < len(landmarks)]
        right_eye_points = [(landmarks[i].x, landmarks[i].y) for i in right_eye_indices if i < len(landmarks)]
        
        if not left_eye_points or not right_eye_points:
            return None
        
        # Calculate eye widths
        left_eye_width = max([p[0] for p in left_eye_points]) - min([p[0] for p in left_eye_points])
        right_eye_width = max([p[0] for p in right_eye_points]) - min([p[0] for p in right_eye_points])
        
        if min(left_eye_width, right_eye_width) < 1e-6:
            return None
        
        size_diff = abs(left_eye_width - right_eye_width) / max(left_eye_width, right_eye_width)
        
        if size_diff > self.eye_symmetry_threshold:
            all_eye_points = left_eye_points + right_eye_points
            bbox_dict = calculate_bounding_box(all_eye_points, image_width, image_height, padding=0.3)
            bbox = BoundingBox(**bbox_dict)
            
            return Distortion(
                label="deformed_face",
                confidence=0.78,
                bounding_box=bbox,
                details=f"Eye size asymmetry {size_diff:.2%} exceeds threshold {self.eye_symmetry_threshold:.2%}"
            )
        
        return None

