import os
import subprocess
import sys
import requests
import json
from core.config.config_manager import ConfigManager

class TTSClient:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        # Resolve path to pronunciation dictionary
        # src/ai_engine/audio/tts_client.py -> ... -> root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.pronunciation_dict_path = os.path.join(base_dir, "resources", "config", "pronunciation_dict.json")

    def _get_provider_config(self):
        # Find the TTS configuration
        # Assuming config structure has a list of APIs or a specific TTS section
        # For now, we look for an API config with type="TTS"
        # Note: SettingsWindow saves to "api_configs"
        apis = self.config.get("api_configs", [])
        
        # First pass: check for default
        for api in apis:
            if api.get("type") == "TTS" and api.get("is_default"):
                return api
                
        # Second pass: return first found
        for api in apis:
            if api.get("type") == "TTS":
                return api
        return None

    def _preprocess_text(self, text):
        """
        Preprocesses text to fix common pronunciation issues.
        Loads corrections from resources/config/pronunciation_dict.json
        """
        corrections = {}
        if os.path.exists(self.pronunciation_dict_path):
            try:
                with open(self.pronunciation_dict_path, 'r', encoding='utf-8') as f:
                    corrections = json.load(f)
            except Exception as e:
                print(f"Error loading pronunciation dict: {e}")
        
        # Apply corrections
        for original, replacement in corrections.items():
            text = text.replace(original, replacement)
        return text

    def generate_audio(self, text, voice_id, output_path):
        """
        Generates audio based on the configured provider.
        """
        # Preprocess text for pronunciation fixes
        text = self._preprocess_text(text)

        print(f"Generating audio for: {text}")
        
        tts_config = self._get_provider_config()
        provider = tts_config.get("provider", "system").lower() if tts_config else "system"
        
        if provider == "xiaoai":
            return self._generate_xiaoai(text, voice_id, output_path, tts_config)
        elif provider == "openai":
            return self._generate_openai(text, voice_id, output_path, tts_config)
        elif provider == "veo":
            return self._generate_veo(text, voice_id, output_path, tts_config)
        else:
            return self._generate_system(text, voice_id, output_path)

    def _generate_veo(self, text, voice_id, output_path, config):
        """
        Generates audio using Veo 3.1 API.
        """
        from ai_engine.veo_service import VeoService
        
        base_url = config.get("base_url", "https://api.veo.ai/v1")
        api_key = config.get("api_key", "")
        model = config.get("model", "veo-audio-3.1")
        # Default to Chinese if not specified, as this is likely a Chinese project context
        language = config.get("language", "zh")
        
        if not api_key:
            print("Error: Veo API Key not configured.")
            return None
            
        veo = VeoService(api_key, base_url)
        return veo.generate_audio(text, voice_id, output_path, model=model, language=language)

    def _generate_openai(self, text, voice_id, output_path, config):
        """
        Generates audio using OpenAI TTS API.
        """
        try:
            base_url = config.get("base_url", "https://api.openai.com/v1")
            api_key = config.get("api_key", "")
            model = config.get("model", "tts-1")
            
            if not api_key:
                print("Error: OpenAI API Key not configured.")
                return None

            url = f"{base_url.rstrip('/')}/audio/speech"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # Default to 'alloy' if voice_id is invalid or missing
            valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
            if voice_id not in valid_voices:
                voice_id = "alloy"

            payload = {
                "model": model,
                "input": text,
                "voice": voice_id,
                "response_format": "wav"
            }
            
            print(f"Calling OpenAI TTS: {url} with voice {voice_id}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"OpenAI TTS Success: {output_path}")
                return output_path
            else:
                print(f"OpenAI TTS Failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"OpenAI TTS Error: {e}")
            return None

    def _generate_system(self, text, voice_id, output_path):
        """
        Generates audio from text using offline TTS (pyttsx3) via a subprocess.
        This avoids COM threading issues in PyQt applications.
        """
        try:
            # Path to the worker script
            worker_path = os.path.join(os.path.dirname(__file__), "tts_worker.py")
            
            # Run subprocess
            # Use the same python interpreter
            cmd = [sys.executable, worker_path, output_path, text]
            if voice_id:
                cmd.append(voice_id)
            
            # Run and wait
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"TTS Success: {output_path}")
                return output_path
            else:
                print(f"TTS Failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"TTS Error: {e}")
            return None

    def _generate_xiaoai(self, text, voice_id, output_path, config):
        """
        Generates audio using the XiaoAi TTS API (Generic HTTP Interface).
        """
        try:
            base_url = config.get("base_url", "")
            api_key = config.get("api_key", "")
            
            if not base_url:
                print("Error: XiaoAi TTS Base URL not configured.")
                return None

            # Example API structure - adjust according to actual API docs
            # POST /tts
            # Body: { "text": "...", "voice_id": "..." }
            url = f"{base_url.rstrip('/')}/tts"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            payload = {
                "text": text,
                "voice_id": voice_id,
                "format": "wav"
            }
            
            print(f"Calling XiaoAi TTS: {url}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"XiaoAi TTS Success: {output_path}")
                return output_path
            else:
                print(f"XiaoAi TTS Failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"XiaoAi TTS Error: {e}")
            return None

    def get_available_voices(self):
        """
        Retrieves available voices based on the configured provider.
        """
        tts_config = self._get_provider_config()
        provider = tts_config.get("provider", "system").lower() if tts_config else "system"
        
        if provider == "xiaoai":
            return self._get_voices_xiaoai(tts_config)
        elif provider == "openai":
            return self._get_voices_openai()
        else:
            return self._get_voices_system()

    def _get_voices_openai(self):
        """
        Returns standard OpenAI voices.
        """
        return [
            {'id': 'alloy', 'name': 'Alloy (Neutral)'},
            {'id': 'echo', 'name': 'Echo (Male)'},
            {'id': 'fable', 'name': 'Fable (British)'},
            {'id': 'onyx', 'name': 'Onyx (Deep Male)'},
            {'id': 'nova', 'name': 'Nova (Female)'},
            {'id': 'shimmer', 'name': 'Shimmer (Clear Female)'}
        ]

    def _get_voices_system(self):
        try:
            worker_path = os.path.join(os.path.dirname(__file__), "tts_worker.py")
            cmd = [sys.executable, worker_path, "--list"]
            
            # Create startupinfo to hide console window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', startupinfo=startupinfo)
            
            voices = []
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith("VOICE|"):
                        parts = line.split("|")
                        if len(parts) >= 3:
                            voices.append({'id': parts[1], 'name': parts[2]})
            return voices
        except Exception as e:
            print(f"Error fetching voices: {e}")
            return []

    def _get_voices_xiaoai(self, config):
        try:
            base_url = config.get("base_url", "")
            api_key = config.get("api_key", "")
            
            if not base_url:
                return [{'id': 'error', 'name': 'Error: Base URL not set'}]

            # Example API structure
            # GET /voices
            url = f"{base_url.rstrip('/')}/voices"
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            print(f"Fetching XiaoAi Voices: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            voices = []
            if response.status_code == 200:
                data = response.json()
                # Assuming data is a list of dicts or has a 'voices' key
                voice_list = data.get('voices', data) if isinstance(data, dict) else data
                
                for v in voice_list:
                    # Adapt to API response format
                    v_id = v.get('id') or v.get('voice_id')
                    v_name = v.get('name') or v.get('voice_name')
                    if v_id and v_name:
                        voices.append({'id': v_id, 'name': v_name})
            else:
                print(f"XiaoAi Voices Failed: {response.status_code}")
                
            return voices
        except Exception as e:
            print(f"XiaoAi Voices Error: {e}")
            return [{'id': 'error', 'name': f'Connection Error: {e}'}]
