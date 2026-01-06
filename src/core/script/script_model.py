import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional

@dataclass
class Dialogue:
    role: str
    content: str
    action: str = ""
    expression: str = ""

@dataclass
class Scene:
    scene_id: str
    location: str
    time: str  # Day/Night
    description: str
    dialogues: List[Dialogue] = field(default_factory=list)
    environment_image: str = ""
    scene_library_id: str = "" # Link to Scene Library ID

@dataclass
class Script:
    title: str
    genre: str
    summary: str = ""
    scenes: List[Scene] = field(default_factory=list)
    
    def to_json(self):
        return json.dumps(asdict(self), indent=4, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        scenes_data = data.pop('scenes', [])
        
        # Filter data to only include fields defined in the dataclass
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        
        script = cls(**filtered_data)
        
        for s_data in scenes_data:
            dialogues_data = s_data.pop('dialogues', [])
            
            # Filter scene data
            scene_valid_keys = set(Scene.__dataclass_fields__.keys())
            scene_filtered_data = {k: v for k, v in s_data.items() if k in scene_valid_keys}
            
            scene = Scene(**scene_filtered_data)
            
            # Filter dialogue data
            dialogue_valid_keys = set(Dialogue.__dataclass_fields__.keys())
            
            scene.dialogues = []
            for d in dialogues_data:
                d_filtered = {k: v for k, v in d.items() if k in dialogue_valid_keys}
                scene.dialogues.append(Dialogue(**d_filtered))
                
            script.scenes.append(scene)
        return script

    def save(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
