#!/usr/bin/env python3

import sys
import os
import time
from datetime import datetime
import pyaudio
import wave
import numpy as np
import paho.mqtt.client as mqtt
from openai import OpenAI
from lib.led_feedback import LEDFeedback
import subprocess
import threading

# OpenAI setup
client = OpenAI()  # This will use OPENAI_API_KEY environment variable

# MQTT setup
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"

# Initialize MQTT client with newer API version
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
try:
    mqtt_client.connect(MQTT_BROKER_ADDRESS)
    mqtt_client.loop_start()
    print("Connected to MQTT broker")
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")
    print("Make sure node_drive.py is running first!")
    sys.exit(1)

class RobotSession:
    def __init__(self):
        self.active = False
        self.last_command_time = None
        self.timeout_seconds = 120  # Increased to 2 minutes
        self.warning_threshold = 30  # Warning when 30 seconds remaining
        self.led = LEDFeedback()  # Initialize LED feedback
        self.led.end()  # Start with LEDs off
    
    def start(self):
        self.active = True
        self.last_command_time = time.time()
        print("\n=== Session Started ===")
        print("Robot will now accept movement commands")
        print("Session will timeout after 2 minutes of inactivity")
        print("Say 'end session' or 'stop session' to stop")
        # Send initial stop command to ensure clean state
        mqtt_client.publish(MQTT_TOPIC, "stop")
        self.led.active()  # Green when session is active
    
    def end(self):
        if self.active:
            self.active = False
            self.last_command_time = None
            print("\n=== Session Ended ===")
            print("Robot will not accept movement commands")
            print("Say 'start session' or 'begin session' to start a new session")
            # Send stop command when ending session
            mqtt_client.publish(MQTT_TOPIC, "stop")
            self.led.end()  # Turn off LEDs when session ends
    
    def check_timeout(self):
        if self.active and self.last_command_time:
            elapsed = time.time() - self.last_command_time
            remaining = self.timeout_seconds - elapsed
            
            if elapsed > self.timeout_seconds:
                print(f"\n⚠️  Session timed out after {self.timeout_seconds} seconds of inactivity")
                self.end()
            elif remaining <= self.warning_threshold and remaining > (self.warning_threshold - 1):
                # Warning when 30 seconds remaining
                print(f"\n⚠️  Warning: Session will timeout in {int(remaining)} seconds")
                print("Issue any command or say 'start session' to reset the timer")
            elif remaining <= 10 and remaining > 9:
                # Final warning at 10 seconds
                print(f"\n⚠️  Final Warning: Session will end in {int(remaining)} seconds!")
    
    def update_last_command_time(self):
        self.last_command_time = time.time()
        remaining = self.timeout_seconds
        print(f"\n⏰ Session time reset. {remaining} seconds until timeout")

def play_siren():
    """Play the police siren sound"""
    siren_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings", "police.wav")
    try:
        subprocess.run(["aplay", "-D", "plughw:2,0", siren_path])
    except Exception as e:
        print(f"Error playing siren: {e}")

def play_siren_loop():
    """Play the police siren sound in a loop"""
    siren_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings", "police.wav")
    start_time = time.time()
    duration = 5  # Match LED duration
    
    while time.time() - start_time < duration:
        try:
            subprocess.run(["aplay", "-D", "plughw:2,0", siren_path], check=True)
        except Exception as e:
            print(f"Error playing siren: {e}")
            break

def process_command(text, session):
    """Process transcribed text for commands"""
    text = text.lower().strip()
    print(f"\nProcessing text: {text}")
    
    # Session control commands
    if "start" in text:
        session.start()
        return True
    elif any(cmd in text for cmd in ["end", "terminate"]):
        session.end()
        return True
    
    # Only process movement commands if session is active
    if not session.active:
        if any(cmd in text for cmd in ["go", "back up", "left", "right", "stop", "halt", "emergency"]):
            print("\n⚠️  No active session. Say 'start' first!")
            session.led.waiting()  # Blue light to indicate waiting for session start
        return False
    
    # Check for emergency command first
    if "emergency" in text:
        print("\n🚨 EMERGENCY MODE ACTIVATED 🚨")
        mqtt_client.publish(MQTT_TOPIC, "stop")  # Stop the robot
        
        # Start siren in a separate thread
        siren_thread = threading.Thread(target=play_siren_loop)
        siren_thread.start()
        
        # Flash LEDs
        session.led.emergency()
        
        session.update_last_command_time()
        return True
    
    # Command mapping with more precise matching
    commands = {
        "go": "forward",
        "back up": "back",
        "turn left": "left",
        "turn right": "right",
        "stop": "stop",
        "halt": "stop"
    }
    
    # Check for exact command matches
    words = text.split()
    for trigger, command in commands.items():
        trigger_words = trigger.split()
        # Only match if all words are present in sequence
        for i in range(len(words) - len(trigger_words) + 1):
            if words[i:i+len(trigger_words)] == trigger_words:
                print(f"\nExecuting command: {command}")
                mqtt_client.publish(MQTT_TOPIC, command)
                session.update_last_command_time()
                if command == "stop":
                    session.led.stopped()  # Red flash for stop
                else:
                    session.led.moving()  # White for movement
                return True
    
    return False

def record_and_transcribe():
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Set up the output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    recordings_dir = os.path.join(script_dir, "recordings")
    os.makedirs(recordings_dir, exist_ok=True)
    
    # Audio parameters
    RATE = 44100
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RECORD_SECONDS = 3  # Record in 3-second chunks
    
    try:
        # Open audio stream using pulse audio
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        print("\nReady for voice commands!")
        print("\n=== Session Control ===")
        print("1. Say 'start' to begin controlling the robot")
        print("2. Say 'end' or 'terminate' to stop controlling the robot")
        print("   (Session will automatically end after 2 minutes of inactivity)")
        print("\n=== Movement Commands ===")
        print("(Only work when session is active)")
        print("- 'go' - Move forward")
        print("- 'stop' or 'halt' - Stop moving")
        print("- 'turn left' - Turn left")
        print("- 'turn right' - Turn right")
        print("- 'back up' - Move backward")
        print("- 'emergency' - Activate emergency mode with siren")
        print("\nListening... (Press Ctrl+C to exit)")
        
        # Initialize session
        session = RobotSession()
        print("\n⚠️  No active session. Say 'start' first!")
        session.led.waiting()  # Start with blue light (waiting for session)
        
        while True:
            # Check for session timeout
            session.check_timeout()
            
            # Record audio chunk
            frames = []
            print("\nRecording...", end="\r")
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                except Exception as e:
                    print(f"\nWarning during recording: {e}")
                    continue
            
            # Save temporary WAV file
            temp_wav = os.path.join(recordings_dir, "temp.wav")
            wf = wave.open(temp_wav, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            # Transcribe using OpenAI Whisper API
            try:
                with open(temp_wav, "rb") as audio_file:
                    result = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                        language="en",  # Specify English for better accuracy
                        temperature=0.3  # Lower temperature for more focused responses
                    )
                    if result:
                        print(f"\nTranscribed: {result}")
                        # Clean up the text and check for commands
                        text = result.lower().strip()
                        # Remove punctuation and normalize spacing
                        text = ' '.join(text.replace('!', ' ').replace('.', ' ').replace('?', ' ').split())
                        process_command(text, session)
            except Exception as e:
                print(f"\nTranscription error: {e}")
                continue
            
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Cleanup
        stream.stop_stream()
        stream.close()
        p.terminate()
        mqtt_client.publish(MQTT_TOPIC, "stop")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        if 'session' in locals():
            session.led.end()  # Make sure LEDs are off

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set")
        print("Please set it with: export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    record_and_transcribe()