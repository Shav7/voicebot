#!/usr/bin/env python3

import pyaudio
import wave
import numpy as np
import time
import sys
import os
import alsaaudio

def set_volume():
    """Set volume for the USB audio device"""
    try:
        # Find the USB audio card
        cards = alsaaudio.cards()
        card_index = None
        for i, card in enumerate(cards):
            if 'UAC' in card:
                card_index = i
                break
        
        if card_index is not None:
            # Set master volume to 100%
            mixer = alsaaudio.Mixer(control='PCM', cardindex=card_index)
            mixer.setvolume(100)
            print("Set USB speaker volume to 100%")
    except Exception as e:
        print(f"Note: Could not set volume automatically: {e}")

def list_audio_devices():
    """List all available audio devices"""
    p = pyaudio.PyAudio()
    print("\nAvailable Audio Devices:")
    print("------------------------")
    
    # Find USB audio device
    target_device_index = None
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info['maxOutputChannels'] > 0:  # Only show output devices
            print(f"Device {i}: {dev_info['name']}")
            print(f"  Max Output Channels: {dev_info['maxOutputChannels']}")
            print(f"  Default Sample Rate: {dev_info['defaultSampleRate']}")
            if "USB" in dev_info['name']:
                target_device_index = i
                print("  *** This appears to be your USB speaker ***")
            print()
    
    p.terminate()
    return target_device_index

def play_wav_file(device_index=None):
    """Play the WAV file through the specified device"""
    p = pyaudio.PyAudio()
    
    # Open the WAV file
    wav_path = "/home/holly/quickstart/tests/recordings/police.wav"
    if not os.path.exists(wav_path):
        print(f"Error: WAV file not found at {wav_path}")
        return False
        
    try:
        print("\nPlaying police.wav...")
        wf = wave.open(wav_path, 'rb')
        
        # Open stream
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                       channels=wf.getnchannels(),
                       rate=wf.getframerate(),
                       output=True,
                       output_device_index=device_index)
        
        # Read data in chunks and play
        chunk_size = 1024
        data = wf.readframes(chunk_size)
        
        while data:
            stream.write(data)
            data = wf.readframes(chunk_size)
        
        # Cleanup
        stream.stop_stream()
        stream.close()
        wf.close()
        print("Playback completed.")
        return True
        
    except Exception as e:
        print(f"Error playing WAV file: {e}")
        return False
        
    finally:
        p.terminate()

def main():
    print("USB Speaker Test")
    print("===============")
    
    # Set volume first
    set_volume()
    
    # List available devices
    device_index = list_audio_devices()
    
    if device_index is None:
        print("\nNo USB audio device found!")
        print("Please check:")
        print("1. Is the USB speaker properly connected?")
        print("2. Has the system recognized the USB device?")
        print("3. Try unplugging and plugging the speaker back in")
        sys.exit(1)
    
    print(f"\nFound USB audio device at index {device_index}")
    print("Playing WAV file in 3 seconds...")
    time.sleep(3)
    
    success = play_wav_file(device_index)
    if success:
        print("\nTest completed successfully!")
        print("If you didn't hear anything, check:")
        print("1. Is the speaker volume turned up?")
        print("2. Is the system volume turned up?")
        print("3. Try running 'alsamixer' to check volume levels")
    else:
        print("\nTest failed. Please check your audio settings.")

if __name__ == "__main__":
    main()