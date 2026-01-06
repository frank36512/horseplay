import os
import time
import httpx
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError
from core.config.config_manager import ConfigManager

class LLMClient:
    def __init__(self, api_key=None, base_url=None, model=None):
        self.config_manager = ConfigManager()
        # Priority: Argument > Env Var > Config File > Placeholder
        key = api_key or os.environ.get("OPENAI_API_KEY") or self.config_manager.get("OPENAI_API_KEY") or "sk-placeholder"
        
        # Use httpx.Timeout to set both connect and read timeouts
        # This avoids the need for a custom http_client while ensuring we don't timeout on connection (21s issue)
        self.client = OpenAI(
            api_key=key,
            base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
            timeout=httpx.Timeout(300.0, connect=60.0),
            max_retries=0 # We handle retries manually
        )
        self.model = model or "gpt-4o"

    def generate_script(self, prompt, system_prompt=None):
        if not system_prompt:
            system_prompt = """You are a professional screenwriter. 
            Generate a short drama script in JSON format based on the user's request.
            The JSON structure must be:
            {
                "title": "Script Title",
                "genre": "Genre",
                "scenes": [
                    {
                        "scene_id": "1",
                        "location": "Location Name",
                        "time": "Day/Night",
                        "description": "Scene visual description",
                        "dialogues": [
                            {
                                "role": "Character Name",
                                "content": "Dialogue text",
                                "action": "Character action",
                                "expression": "Facial expression"
                            }
                        ]
                    }
                ]
            }
            Return ONLY the JSON string, no markdown formatting.
            """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                print(f"LLM Request started (Attempt {attempt+1})...") 
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4096 # Prevent infinite loops
                )
                
                duration = time.time() - start_time
                print(f"LLM Request finished in {duration:.2f}s")
                
                return response.choices[0].message.content
            except (APIConnectionError, APITimeoutError, RateLimitError) as e:
                duration = time.time() - start_time
                print(f"LLM Network Error (Attempt {attempt+1}/{max_retries}) after {duration:.2f}s: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1)) # Backoff: 3s, 6s, ...
                else:
                    print(f"LLM Failed after {max_retries} attempts.")
                    return None
            except Exception as e:
                print(f"LLM Error: {e}")
                return None

    def get_embedding(self, text, model=None):
        """Generates embedding for the given text using OpenAI API."""
        try:
            text = text.replace("\n", " ")
            
            # Get model from argument or config, default to text-embedding-3-small
            if not model:
                model = self.config_manager.get("embedding_model", "text-embedding-3-small")
            
            response = self.client.embeddings.create(
                input=[text],
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding Error: {e}")
            # Return a zero vector or None as fallback? 
            # Better to return None and handle it.
            return None
