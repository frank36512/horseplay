from core.script.script_model import Scene, Dialogue

def generate_panel_params(scene: Scene, dialogue: Dialogue, next_scene: Scene = None, next_dialogue: Dialogue = None, char_descriptions: list = None, for_video: bool = False) -> dict:
    """
    Generates a dictionary of cinematic parameters for a storyboard panel.
    """
    if char_descriptions is None:
        char_descriptions = []

    # 1. Construct Subject Part
    subject_part = ""
    action_lower = dialogue.action.lower()
    
    if char_descriptions:
        # Main subject (Speaker)
        main_name, main_desc = char_descriptions[0]
        # Simplified subject part: Name + Description only
        if main_desc:
            subject_part = f"{main_name}, {main_desc}"
        else:
            subject_part = f"{main_name}"
        
        # Other characters present
        if len(char_descriptions) > 1:
            others_parts = []
            for name, desc in char_descriptions[1:]:
                if desc:
                    others_parts.append(f"{name}, {desc}")
                else:
                    others_parts.append(f"{name}")
            
            # Simplified connector
            subject_part += f"; {'; '.join(others_parts)}"
    else:
        # Fallback if no characters detected (e.g. Narrator only)
        if dialogue.role in ["旁白", "画外音", "Narrator", "Voiceover", "OS", "字幕"]:
             subject_part = "Empty scene"
        else:
             subject_part = f"{dialogue.role}"

    # Smart Transition & Continuity Injection
    camera_movement = ""
    
    # Dynamic Shot Type Detection
    shot_type = "Cinematic medium shot" # Default
    
    # Adjust default shot type if multiple characters are present
    if len(char_descriptions) > 1:
        # Check for interaction type to refine shot
        if any(v in action_lower for v in ["look", "see", "watch", "stare", "glance", "notice"]):
             # Observation -> Depth needed
            shot_type = "Over-the-shoulder shot"
        elif any(v in action_lower for v in ["talk", "speak", "argue", "chat"]):
            # Conversation -> Two shot
            shot_type = "Cinematic two-shot"
        elif len(char_descriptions) == 2:
             shot_type = "Cinematic two-shot"
        else:
             shot_type = "Cinematic group shot"
    
    if "close-up" in action_lower or "close up" in action_lower:
        shot_type = "Cinematic close-up shot"
    elif "wide shot" in action_lower or "long shot" in action_lower or "full shot" in action_lower:
        shot_type = "Cinematic wide shot"
    elif "extreme close" in action_lower:
        shot_type = "Extreme close-up shot"
    elif "cowboy shot" in action_lower:
        shot_type = "Cinematic cowboy shot"
    elif "over the shoulder" in action_lower:
        shot_type = "Over-the-shoulder shot"
    elif "pov" in action_lower:
        shot_type = "POV shot"
    
    # --- 3D Geometry & Composition Engine ---
    # User requested NO auto-generated prompts for parameters.
    # We default these to empty strings so the user can choose them manually if desired.
    viewpoint_instruction = ""
    gaze_instruction = ""
    composition_instruction = ""
    shot_type = "" 
    camera_movement = ""
    lighting_desc = ""
    texture_desc = ""

    # (Logic for auto-detection commented out / skipped to respect user request)
    # ... [Auto-detection logic removed] ...

    # 3. Action
    action_parts = []
    if dialogue.action:
        action_parts.append(f"{dialogue.action}")
    action_section = " ".join(action_parts)

    # 4. Context
    # Simplified context section
    context_section = f"{scene.description}, {scene.time}"

    # 5. Style & Ambiance
    # lighting_desc = "Cinematic lighting" ... (Skipped)
        
    # texture_desc = "photorealistic, 8k, movie scene aesthetic, high fidelity" ... (Skipped)

    # 6. Audio
    audio_section = ""
    if for_video:
        if dialogue.content:
            clean_content = dialogue.content.replace('"', "'")
            audio_section += f' Dialogue: {dialogue.role} says, "{clean_content}".'
        
        if "rain" in scene.description.lower():
            audio_section += " Ambient noise: Sound of rain falling."
        elif "city" in scene.description.lower() or "street" in scene.description.lower():
            audio_section += " Ambient noise: City street background noise."
        elif "forest" in scene.description.lower():
            audio_section += " Ambient noise: Nature sounds, birds chirping, wind in trees."
        
        if "scream" in action_lower or "shout" in action_lower:
            audio_section += " SFX: Loud shouting."
        elif "whisper" in action_lower:
            audio_section += " SFX: Soft whispering."
        elif "laugh" in action_lower:
            audio_section += " SFX: Laughter."

    return {
        "shot_type": shot_type,
        "camera_movement": camera_movement,
        "viewpoint": viewpoint_instruction,
        "composition": composition_instruction,
        "subject": subject_part,
        "action": action_section,
        "context": context_section,
        "style": "",
        "lighting": lighting_desc,
        "texture": texture_desc,
        "audio": audio_section
    }

def construct_prompt_from_params(params: dict) -> str:
    """
    Assembles a prompt string from a dictionary of parameters.
    Template: [Style] + [Composition/Viewpoint] + [Lighting/Color] + [Details/Texture]
    NOTE: Subject, Action, Context are handled by user input, not auto-generated.
    """
    # Skip subject, action, context (handled by user prompt)
    
    # 1. Style
    style_section = params.get("style", "")
    
    # 2. Composition / Viewpoint
    cinematography_parts = [params.get("shot_type", "")]
    if params.get("camera_movement"):
        cinematography_parts.append(params["camera_movement"])
    if params.get("viewpoint"):
        cinematography_parts.append(params["viewpoint"])
    if params.get("composition"):
        cinematography_parts.append(params["composition"])
    
    cinematography_section = ". ".join([p for p in cinematography_parts if p])
    
    # 3. Lighting
    lighting_section = params.get("lighting", "")
    
    # 4. Texture
    texture_section = params.get("texture", "")
    
    # 5. Audio (for video) - usually not for image generation
    audio_section = params.get("audio", "")

    parts = [
        style_section,
        cinematography_section,
        lighting_section,
        texture_section,
        audio_section
    ]
    
    prompt = ". ".join([p for p in parts if p])
    
    # Clean up double punctuation
    prompt = prompt.replace("..", ".").replace(" .", ".").strip()
    
    return prompt

def construct_video_prompt(image_params: dict, video_params: dict) -> str:
    """
    Constructs a video prompt optimized for Veo 3.1 using the 'Static Base + Dynamic Instructions' structure.
    
    Template:
    Based on original image: [Subject], [Style], [Context];
    Dynamic Instructions:
    - Subject Motion: [Action]
    - Camera Motion: [Camera Movement]
    - Environment: [Environment Dynamics]
    - Lighting: [Lighting Dynamics]
    - Audio: [Audio]
    - Parameters: [Video Config]
    """
    # 1. Static Base (From Image Params)
    base_parts = []
    if image_params.get("subject"):
        base_parts.append(f"Subject: {image_params['subject']}")
    if image_params.get("style"):
        base_parts.append(f"Style: {image_params['style']}")
    if image_params.get("context"):
        base_parts.append(f"Context: {image_params['context']}")
    if image_params.get("lighting"):
        base_parts.append(f"Lighting: {image_params['lighting']}")
        
    base_section = "Based on original image: " + "; ".join(base_parts)
    
    # 2. Dynamic Instructions (From Video Params)
    dynamic_parts = []
    
    # Subject Motion (Action)
    if video_params.get("action"):
        dynamic_parts.append(f"- Subject Motion: {video_params['action']}")
        
    # Camera Motion
    if video_params.get("camera_movement"):
        dynamic_parts.append(f"- Camera Motion: {video_params['camera_movement']}")
        
    # Environment Dynamics
    if video_params.get("environment_dynamics"):
        dynamic_parts.append(f"- Environment Dynamics: {video_params['environment_dynamics']}")
        
    # Lighting Dynamics
    if video_params.get("lighting_dynamics"):
        dynamic_parts.append(f"- Lighting Dynamics: {video_params['lighting_dynamics']}")
        
    # Audio (formatted for Veo 3 audio guidelines)
    # Veo 3 supports: Dialogue (引号), Sound Effects (explicit descriptions), Ambient Noise (soundscape)
    if video_params.get("audio"):
        audio_desc = video_params['audio']
        # Check if it contains dialogue (has quotes) or is pure SFX/ambient
        if '"' in audio_desc or "'" in audio_desc:
            # Already formatted as dialogue
            dynamic_parts.append(f"- Audio: {audio_desc}")
        else:
            # Treat as SFX or ambient noise - add descriptive context
            # Examples: "The tires emit a harsh scream", "A faint noise echoes in the background"
            dynamic_parts.append(f"- Audio: {audio_desc}")
        
    # Video Config / Parameters
    if video_params.get("video_config"):
        dynamic_parts.append(f"- Parameters: {video_params['video_config']}")
        
    dynamic_section = "Dynamic Instructions:\n" + "\n".join(dynamic_parts)
    
    # Combine
    full_prompt = f"{base_section}\n\n{dynamic_section}"
    
    return full_prompt

def generate_panel_prompt(scene: Scene, dialogue: Dialogue, next_scene: Scene = None, next_dialogue: Dialogue = None, char_descriptions: list = None, for_video: bool = False, return_params: bool = False):
    # Always generate params with for_video=True to capture audio info
    params = generate_panel_params(scene, dialogue, next_scene, next_dialogue, char_descriptions, for_video=True)
    
    # If returning params, we return the full set.
    # If returning string, we respect the for_video flag to filter the output if needed,
    # but since we are moving to separate params, we can just filter the params here if needed.
    
    if not for_video:
        # Create a temporary filtered view for string generation if needed
        temp_params = params.copy()
        temp_params['audio'] = ""
        # We might also want to clear camera_movement for static images, but let's leave it 
        # if the user specifically asked for a string (legacy behavior might expect it).
        # Actually, let's clear it to be consistent with the new philosophy.
        if "tracking" in temp_params.get("camera_movement", "").lower() or "zoom" in temp_params.get("camera_movement", "").lower():
             temp_params['camera_movement'] = ""
        prompt = construct_prompt_from_params(temp_params)
    else:
        prompt = construct_prompt_from_params(params)
    
    if return_params:
        return prompt, params
    return prompt
