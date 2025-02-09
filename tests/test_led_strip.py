# INFO
# If you run into the problem that you cant install 'sysv-ipc' then do: sudo apt-get install python3-sysv-ipc
# The adaruit neopixel library doesnt work on the PI5, someone wrote this: https://pypi.org/project/Pi5Neo/
# use the MOSI pin (GPIO10) on PI5 for this script to work.
# NOTE: the neopixel strips are directional, they have an input direction and output direction. Check your wiring.
# NOTE: the Pi5Neo library is not working well, i had to patch it, in its source for the update_led function, theres a time.sleep(0.1), i just made that 0.01

from pi5neo import Pi5Neo
import time

def rainbow_cycle(neo, delay=1.0):  # Increased delay to 1 second
    colors = [
        (255, 0, 0),  # Red
        (255, 127, 0),  # Orange
        (255, 255, 0),  # Yellow
        (0, 255, 0),  # Green
        (0, 0, 255),  # Blue
        (75, 0, 130),  # Indigo
        (148, 0, 211)  # Violet
    ]
    
    print("Starting rainbow cycle...")
    for i, color in enumerate(colors):
        print(f"Setting color {i+1}/7: RGB{color}")
        neo.fill_strip(*color)
        neo.update_strip()
        time.sleep(delay)
        print(f"Color {i+1} displayed for {delay} seconds")

print("Initializing LED strip...")
try:
    neo = Pi5Neo('/dev/spidev0.0', 15, 800)
    print("LED strip initialized successfully")
    print("Starting color sequence...")
    rainbow_cycle(neo)
    print("Color sequence completed")
except Exception as e:
    print(f"Error: {e}")
    print("Please check:")
    print("1. Is the LED strip connected to GPIO10 (MOSI)?")
    print("2. Is the LED strip oriented correctly (check arrow direction)?")
    print("3. Is the power supply connected and adequate?")
    print("4. Are all ground connections secure?")
