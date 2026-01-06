
def construct_veo_prompt(image_prompt, description, project_style=None, config_suffix=None):
    """
    Constructs an optimized prompt for Veo video generation.
    Structure: Subject + Action. Style. Camera. Composition. Focus. Atmosphere.
    """
    base_prompt = image_prompt.strip() if image_prompt else ""
    if not base_prompt:
        base_prompt = description # Fallback
        
    # Ensure base prompt ends with punctuation
    if base_prompt and not base_prompt[-1] in ".,;":
        base_prompt += "."
        
    parts = [base_prompt]
    
    # Style (from project or config)
    if project_style and project_style not in base_prompt:
        parts.append(f"{project_style} style.")
        
    # Camera & Movement (Default if not present)
    # Veo likes specific terms: "Aerial view", "Tracking shot", etc.
    camera_terms = ["camera", "shot", "view", "pan", "tilt", "zoom", "tracking", "angle"]
    if not any(term in base_prompt.lower() for term in camera_terms):
        parts.append("Slow cinematic camera movement.")
        
    # Composition & Focus
    focus_terms = ["focus", "dof", "depth of field", "blur", "lens"]
    if not any(term in base_prompt.lower() for term in focus_terms):
        # Heuristic: Landscapes usually need deep depth of field, characters need shallow
        if any(w in base_prompt.lower() for w in ["landscape", "city", "mountain", "forest", "view", "wide", "scenery"]):
            parts.append("Deep depth of field.")
        else:
            parts.append("Shallow depth of field.")
        
    # Atmosphere
    atmos_terms = ["lighting", "light", "atmosphere", "mood", "tone"]
    if not any(term in base_prompt.lower() for term in atmos_terms):
        parts.append("Cinematic lighting.")
        
    # User Suffix (from BatchVideoDialog)
    if config_suffix:
        parts.append(config_suffix)
        
    return " ".join(parts)
