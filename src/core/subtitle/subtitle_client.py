import os
from core.config.config_manager import ConfigManager

class SubtitleClient:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

    def _get_provider_config(self):
        apis = self.config.get("api_configs", [])
        for api in apis:
            if api.get("type") == "Subtitle":
                return api
        for api in apis:
            if api.get("type") == "Veo":
                return api
        return None

    def generate_subtitles(self, audio_path, output_path):
        """
        Generates subtitles (SRT) from audio using API.
        """
        print(f"Generating subtitles for {audio_path}")
        
        config = self._get_provider_config()
        if not config:
            print("No Subtitle provider configured.")
            return None
            
        provider = config.get("provider", "veo").lower()
        
        if provider == "veo":
            return self._generate_veo(audio_path, output_path, config)
        
        print(f"Unknown Subtitle provider: {provider}")
        return None

    def _generate_veo(self, audio_path, output_path, config):
        from ai_engine.veo_service import VeoService
        
        base_url = config.get("base_url", "https://api.veo.ai/v1")
        api_key = config.get("api_key", "")
        
        if not api_key:
            print("Error: Veo API Key not configured.")
            return None
            
        veo = VeoService(api_key, base_url)
        return veo.generate_subtitles(audio_path=audio_path, output_path=output_path)
