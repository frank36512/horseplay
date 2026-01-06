import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict

@dataclass
class Scene:
    id: str
    name: str
    description: str          # Detailed visual description
    time_of_day: str = ""     # e.g., "Day", "Night", "Sunset"
    weather: str = ""         # e.g., "Sunny", "Rainy", "Foggy"
    style: str = ""           # e.g., "Cyberpunk", "Realistic", "Anime"
    image_path: str = ""      # Path to reference image
    project_id: str = ""      # ID of the project this scene belongs to
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
