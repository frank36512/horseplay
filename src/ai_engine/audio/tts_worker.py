import pyttsx3
import sys
import os

import hashlib

def generate(text, output_path, voice_id=None):
    try:
        engine = pyttsx3.init()
        
        # Default settings
        base_rate = 150
        engine.setProperty('volume', 0.9)
        
        voice_found = False
        if voice_id:
            # 1. Try exact/partial match with system voices
            voices = engine.getProperty('voices')
            for voice in voices:
                # Check ID or Name
                if (voice_id in voice.id) or (voice_id in voice.name):
                    engine.setProperty('voice', voice.id)
                    print(f"Selected system voice: {voice.name}")
                    voice_found = True
                    break
            
            if not voice_found:
                print(f"Voice '{voice_id}' not found in system. Applying simulated variation.")
                # 2. Simulate variation based on voice_id hash
                # Generate a deterministic modifier for rate based on voice_id
                # Hash string to int
                hash_val = int(hashlib.sha256(voice_id.encode('utf-8')).hexdigest(), 16)
                # Map to range -30 to +30
                rate_mod = (hash_val % 61) - 30 
                new_rate = base_rate + rate_mod
                engine.setProperty('rate', new_rate)
                print(f"Applied simulated voice rate: {new_rate} (Base: {base_rate})")
        else:
            engine.setProperty('rate', base_rate)
        
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        print(f"SUCCESS: {output_path}")
    except Exception as e:
        print(f"ERROR: {e}")

def list_voices():
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for voice in voices:
            # Print in a parseable format
            print(f"VOICE|{voice.id}|{voice.name}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_voices()
        sys.exit(0)

    if len(sys.argv) < 3:
        print("Usage: python tts_worker.py <output_path> <text> [voice_id]")
        print("       python tts_worker.py --list")
        sys.exit(1)
        
    output_path = sys.argv[1]
    text = sys.argv[2]
    voice_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    generate(text, output_path, voice_id)
