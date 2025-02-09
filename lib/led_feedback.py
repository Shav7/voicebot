from pi5neo import Pi5Neo
import time
import threading

class LEDFeedback:
    def __init__(self, num_leds=15):
        self.neo = Pi5Neo('/dev/spidev0.0', num_leds, 800)
        
    def waiting(self):
        """Blue color - waiting for session to start"""
        self.neo.fill_strip(0, 0, 255)  # Blue
        self.neo.update_strip()
        
    def active(self):
        """Green color - session is active"""
        self.neo.fill_strip(0, 255, 0)  # Green
        self.neo.update_strip()
        
    def moving(self):
        """White color - robot is moving"""
        self.neo.fill_strip(255, 255, 255)  # White
        self.neo.update_strip()
        
    def stopped(self):
        """Red color - robot has stopped"""
        # Flash red three times
        for _ in range(3):
            self.neo.fill_strip(255, 0, 0)  # Bright red
            self.neo.update_strip()
            time.sleep(0.5)  # On for longer
            self.neo.fill_strip(0, 0, 0)  # Off
            self.neo.update_strip()
            time.sleep(0.2)  # Brief off
        self.active()  # Return to green (active state)
        
    def end(self):
        """Turn off LEDs - session ended"""
        self.neo.fill_strip(0, 0, 0)  # Off
        self.neo.update_strip()
        
    def emergency(self):
        """Police-style flashing red and blue"""
        # Flash between red and blue continuously for about 5 seconds
        start_time = time.time()
        duration = 5  # Run for 5 seconds
        
        while time.time() - start_time < duration:
            # Red flash
            self.neo.fill_strip(255, 0, 0)  # Bright red
            self.neo.update_strip()
            time.sleep(0.3)
            # Blue flash
            self.neo.fill_strip(0, 0, 255)  # Bright blue
            self.neo.update_strip()
            time.sleep(0.3)
            
        self.active()  # Return to green (active state) only at the very end 