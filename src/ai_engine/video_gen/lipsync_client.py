import os
from core.config.config_manager import ConfigManager

class LipSyncClient:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

    def _get_provider_config(self):
        apis = self.config.get("api_configs", [])
        for api in apis:
            if api.get("type") == "LipSync":
                return api
        # Fallback
        for api in apis:
            if api.get("type") == "Veo":
                return api
        return None

    def sync_lips(self, video_path, audio_path, output_path):
        """
        Syncs video lips to audio.
        """
        print(f"Syncing lips for {video_path} with {audio_path}")
        
        config = self._get_provider_config()
        if not config:
            print("No LipSync provider configured.")
            return None
            
        provider = config.get("provider", "veo").lower()
        
        if provider == "veo":
            return self._sync_veo(video_path, audio_path, output_path, config)
        
        print(f"Unknown LipSync provider: {provider}")
        return None

    def _sync_veo(self, video_path, audio_path, output_path, config):
        from ai_engine.veo_service import VeoService
        
        base_url = config.get("base_url", "https://api.veo.ai/v1")
        api_key = config.get("api_key", "")
        
        if not api_key:
            print("Error: Veo API Key not configured.")
            return None
            
        veo = VeoService(api_key, base_url)
        # VeoService handles base64 encoding for local files if paths are passed
        return veo.sync_lips(video_path=video_path, audio_path=audio_path, output_path=output_path)
