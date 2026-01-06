import json
from dataclasses import dataclass, field, asdict
from typing import List

@dataclass
class Panel:
    panel_id: str
    scene_id: str
    description: str
    image_prompt: str
    video_prompt: str = ""
    image_path: str = ""
    history_images: List[str] = field(default_factory=list)
    characters: List[str] = field(default_factory=list) # List of Character IDs
    audio_path: str = ""
    video_path: str = ""
    history_videos: List[str] = field(default_factory=list)  # Video version history
    duration: float = 3.0
    is_animated: bool = False
    prompt_params: dict = field(default_factory=dict)
    video_params: dict = field(default_factory=dict)
    reference_image_path: str = "" # Path to a specific reference image for this panel
    last_image_task_id: str = "" # Save task ID for retry
    last_video_task_id: str = "" # Save task ID for retry

@dataclass
class Storyboard:
    script_title: str
    panels: List[Panel] = field(default_factory=list)

    def to_json(self):
        return json.dumps(asdict(self), indent=4)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        panels_data = data.pop('panels', [])
        sb = cls(**data)
        sb.panels = [Panel(**p) for p in panels_data]
        return sb

    def save(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
