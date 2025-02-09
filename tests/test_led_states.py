#!/usr/bin/env python3

import sys
import os
import time

# Add the lib directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.led_feedback import LEDFeedback

def test_states():
    print("Testing LED states...")
    led = LEDFeedback()
    
    try:
        print("1. Blue - Waiting for session")
        led.waiting()
        time.sleep(2)
        
        print("2. Green - Session active")
        led.active()
        time.sleep(2)
        
        print("3. White - Moving")
        led.moving()
        time.sleep(2)
        
        print("4. Red flashing - Stopped (watch for 3 red flashes)")
        led.stopped()
        time.sleep(3)  # Give more time to see the red flashes and green
        
        print("5. Off - Session ended")
        led.end()
        
        print("\nTest complete!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
        led.end()
    except Exception as e:
        print(f"Error: {e}")
        led.end()

if __name__ == "__main__":
    test_states() 