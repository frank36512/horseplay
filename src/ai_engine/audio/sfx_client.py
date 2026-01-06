import os
from core.config.config_manager import ConfigManager

class SFXClient:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

    def _get_provider_config(self):
        apis = self.config.get("api_configs", [])
        for api in apis:
            if api.get("type") == "SFX":
                return api
        # Fallback to Veo if configured elsewhere or default
        for api in apis:
            if api.get("type") == "Veo": # Or generic Veo config
                return api
        return None

    def generate_sfx(self, prompt, output_path, duration=5.0):
        """
        Generates sound effects.
        """
        print(f"Generating SFX for: {prompt}")
        
        config = self._get_provider_config()
        if not config:
            print("No SFX provider configured.")
            return None
            
        provider = config.get("provider", "veo").lower()
        
        if provider == "veo":
            return self._generate_veo(prompt, output_path, duration, config)
        
        print(f"Unknown SFX provider: {provider}")
        return None

    def _generate_veo(self, prompt, output_path, duration, config):
        from ai_engine.veo_service import VeoService
        
        base_url = config.get("base_url", "https://api.veo.ai/v1")
        api_key = config.get("api_key", "")
        
        if not api_key:
            print("Error: Veo API Key not configured.")
            return None
            
        veo = VeoService(api_key, base_url)
        return veo.generate_sfx(prompt, output_path, duration)
