import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict

@dataclass
class Character:
    id: str
    name: str
    age: str
    gender: str
    appearance_features: str  # e.g., "Blue hair, twin tails, mechanical eye"
    style_description: str    # e.g., "Cyberpunk, Anime style"
    voice_id: str = ""        # e.g., "zh_male_xiaoshuai" (TTS ID)
    voice_description: str = "" # e.g., "Deep, raspy male voice" (For Video Gen)
    language: str = "English" # e.g., "English", "Chinese", "Japanese"
    avatar_path: str = ""     # Path to the main avatar image
    project_id: str = ""      # ID (folder name) of the project this character belongs to
    reference_images: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_json(self):
        return json.dumps(asdict(self), indent=4)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(**data)

    def save(self, directory):
        filename = f"{self.name}_{self.id}.json"
        path = os.path.join(directory, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        return path
