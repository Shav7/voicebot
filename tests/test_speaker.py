#!/usr/bin/env python3

import os
import subprocess

def play_wav_file():
    """Play the WAV file through the USB speaker"""
    # Open the WAV file
    wav_path = os.path.join(os.path.dirname(__file__), "recordings", "police.wav")
    if not os.path.exists(wav_path):
        print(f"Error: WAV file not found at {wav_path}")
        return False
        
    try:
        print("Playing audio...")
        subprocess.run(["aplay", "-D", "plughw:4,0", wav_path], check=True)
        print("Playback complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error playing audio: {e}")
        return False

if __name__ == "__main__":
    play_wav_file()