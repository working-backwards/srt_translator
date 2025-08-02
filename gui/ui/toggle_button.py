"""
Custom Toggle Button with Smooth Rotation Animation
Provides a chevron button that rotates smoothly when toggled
"""

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Property, QTimer
from PySide6.QtWidgets import QPushButton


class AnimatedToggleButton(QPushButton):
    """Toggle button with smooth chevron rotation animation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rotation = 0.0
        self._animation = QPropertyAnimation(self, b"rotation", self)
        self._animation.setDuration(200)  # 200ms animation
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Set initial chevron (pointing right when collapsed)
        self.setText(">")  # Simple right arrow
        self.setObjectName("toggleButton")
        self.setFixedSize(30, 30)
        
    def get_rotation(self):
        """Get current rotation angle"""
        return self._rotation
        
    def set_rotation(self, angle):
        """Set rotation angle and update button text"""
        self._rotation = angle
        # Update the chevron based on rotation
        if angle >= 90:
            self.setText("v")  # Simple down arrow
        else:
            self.setText(">")  # Simple right arrow
    
    # Property for animation
    rotation = Property(float, get_rotation, set_rotation)
    
    def animate_to_expanded(self):
        """Animate to expanded state (rotate 90 degrees)"""
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(90.0)
        self._animation.start()
        
    def animate_to_collapsed(self):
        """Animate to collapsed state (rotate back to 0 degrees)"""
        self._animation.setStartValue(90.0)
        self._animation.setEndValue(0.0)
        self._animation.start()
        
    def set_expanded_state(self, expanded: bool):
        """Set expanded state with animation"""
        if expanded:
            self.animate_to_expanded()
        else:
            self.animate_to_collapsed() 