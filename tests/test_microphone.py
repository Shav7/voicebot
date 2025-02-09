#!/usr/bin/env python3

import pyaudio
import wave
import sys
import time
import os

def test_microphone():
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Set up the output file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    recordings_dir = os.path.join(script_dir, "recordings")
    os.makedirs(recordings_dir, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(recordings_dir, f"recording_{timestamp}.wav")
    print(f"\nWill save audio to: {output_file}")
    
    # Print available audio devices
    print("\nAvailable Audio Input Devices:")
    target_device_index = None
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info['maxInputChannels'] > 0:  # Only show input devices
            print(f"Device {i}: {dev_info['name']}")
            print(f"  Max Input Channels: {dev_info['maxInputChannels']}")
            print(f"  Default Sample Rate: {dev_info['defaultSampleRate']}")
            if "USB PnP Sound Device" in dev_info['name']:
                target_device_index = i
                device_info = dev_info
    
    if target_device_index is None:
        print("Error: USB PnP Sound Device not found!")
        return False
    
    print(f"\nUsing USB PnP Sound Device (index {target_device_index})")
    
    # Set recording parameters
    CHUNK = 1024  # Smaller chunk size
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 5
    
    try:
        # Open audio stream
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       input_device_index=target_device_index,
                       frames_per_buffer=CHUNK)
        
        print("Recording 5 seconds of audio...")
        
        # Record audio
        frames = []
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            except Exception as e:
                print(f"Warning during recording chunk {i}: {e}")
                continue
            
        print("Finished recording")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Save the recorded data as a WAV file
        try:
            wf = wave.open(output_file, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            print(f"Successfully saved audio to {output_file}")
            print(f"File exists: {os.path.exists(output_file)}")
            if os.path.exists(output_file):
                print(f"File size: {os.path.getsize(output_file)} bytes")
            return True
        except Exception as e:
            print(f"Error saving audio file: {e}")
            return False
            
    except Exception as e:
        print(f"Error recording audio: {e}")
        return False
    finally:
        # Terminate PyAudio
        p.terminate()

if __name__ == "__main__":
    success = test_microphone()
    sys.exit(0 if success else 1)
