import os
import sys

class SubtitleAligner:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                import whisper
                print("Loading Whisper model (base)...")
                cls._model = whisper.load_model("base")
            except ImportError:
                print("Whisper not installed. Please run: pip install openai-whisper")
                return None
            except Exception as e:
                print(f"Error loading Whisper model: {e}")
                return None
        return cls._model

    @staticmethod
    def transcribe(audio_path, api_key=None, base_url=None):
        """
        Returns the full transcription result:
        {
            "text": "Full text",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Segment 1"},
                ...
            ]
        }
        """
        import imageio_ffmpeg
        
        # 1. Try API if key provided
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=base_url)
                print("Transcribing using OpenAI API...")
                with open(audio_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file, 
                        response_format="verbose_json"
                    )
                
                # Convert API response to standard format
                return {
                    "text": transcript.text,
                    "segments": [
                        {"start": s.start, "end": s.end, "text": s.text}
                        for s in transcript.segments
                    ]
                }
            except Exception as e:
                print(f"API Transcription failed: {e}")
                # Fallback to local

        # 2. Try Local Whisper
        model = SubtitleAligner.get_model()
        if not model:
            return None

        try:
            # Load audio manually to avoid ffmpeg PATH issues
            import numpy as np
            import wave
            
            audio_data = None
            try:
                with wave.open(audio_path, 'rb') as wf:
                    if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                        print(f"Warning: Audio format mismatch. Whisper expects 16kHz mono.")
                        audio_data = None
                    else:
                        frames = wf.readframes(wf.getnframes())
                        audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            except Exception as e:
                print(f"Error reading WAV manually: {e}")
                audio_data = None

            if audio_data is not None:
                print("Transcribing with Local Whisper (manual load)...")
                result = model.transcribe(audio_data, no_speech_threshold=0.1, logprob_threshold=None)
            else:
                print("Transcribing with Local Whisper (ffmpeg load)...")
                result = model.transcribe(audio_path, no_speech_threshold=0.1, logprob_threshold=None)

            return result
            
        except Exception as e:
            print(f"Error transcribing: {e}")
            return None

    @staticmethod
    def get_speech_timing(audio_path, api_key=None, base_url=None):
        """
        Legacy wrapper for backward compatibility.
        """
        result = SubtitleAligner.transcribe(audio_path, api_key, base_url)
        
        # Get total duration for fallback
        total_duration = 0.0
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            total_duration = len(audio) / 1000.0
        except:
            pass

        if not result or not result.get("segments"):
            # Try VAD fallback if local whisper failed to find segments
            # (Logic from previous edit moved here or simplified)
            return 0.0, total_duration

        segments = result["segments"]
        start_time = segments[0]["start"]
        end_time = segments[-1]["end"]
        
        # Safety check
        if end_time > total_duration and total_duration > 0:
            end_time = total_duration
            
        return start_time, end_time
