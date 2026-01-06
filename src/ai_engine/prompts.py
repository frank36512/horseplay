# Prompts adapted from novel_maker for continuous script generation

SCRIPT_GENERATION_PROMPT = """
Create a script for the next episode of the series.

SERIES INFO:
Title: {episode_title} (Episode {episode_number} of {total_episodes})
Genre: {genre}
Target Length: ~{words_per_episode} words
Main Characters: {main_characters}

SERIES PREMISE:
{premise}

GLOBAL STORY SUMMARY (The story so far):
{global_summary}

CHARACTER STATE (Current status of characters):
{character_state}

IMMEDIATE CONTEXT (Summary of recent episodes):
{recent_episodes_summary}

PREVIOUS SCENE (Last few lines of the previous script):
{previous_script_excerpt}

RELEVANT MEMORY (RAG Retrieval):
{rag_context}

CURRENT EPISODE IDEA:
{user_idea}

REQUIREMENTS:
1. Format: Standard script format (Scene Heading, Action, Character Name, Dialogue).
2. Continuity: Ensure characters' emotional states and physical locations match the "Character State" and "Previous Scene".
3. Pacing: {duration}
4. Style: {style}
5. Visuals: Write detailed, cinematic action lines. Include lighting, atmosphere, and specific character expressions to aid video generation.
6. Visual Transitions: CRITICAL. Write action lines that bridge scenes visually.
   - If a character leaves a scene, describe them exiting frame.
   - If a new character appears next, have the current character look or react in that direction.
   - Use matching objects or motions to link distinct scenes (e.g., "Camera zooms in on the watch..." -> Next scene starts with a clock).
   - Ensure the end of one scene visually flows into the start of the next.
7. Cinematography: Use specific camera language to direct the video generation.
   - Shot Types: Specify "Close-up", "Medium Shot", "Wide Shot", "Extreme Close-up" in action lines.
   - Angles: Use "Low Angle" (power), "High Angle" (vulnerability), "Dutch Angle" (unease), "Eye Level" (neutral).
   - Movements: Include "Pan", "Tilt", "Dolly In/Out", "Zoom", "Tracking Shot".
   - Example: "Close-up of John's hand shaking. Camera tilts up to his sweating face."
8. Blocking & Positioning: CRITICAL. Define where characters are relative to each other and the environment.
   - Use spatial terms: "foreground", "background", "left", "right", "center", "next to", "opposite", "behind".
   - Specify relative positions: "Alice stands to the left of Bob", "John is in the background watching Mary in the foreground".
   - Ensure characters are not occupying the same space unless intended.

Generate the script for Episode {episode_number}.
"""

UPDATE_CHARACTER_STATE_PROMPT = """
Based on the newly generated script, update the character state.

CURRENT CHARACTER STATE:
{current_state}

NEW SCRIPT CONTENT:
{script_content}

INSTRUCTIONS:
1. Update the status of existing characters (Physical health, Emotional state, Inventory/Items, Relationships).
2. Add any new major characters introduced in this script.
3. Remove characters that are no longer relevant or deceased (optional).
4. Keep the format structured (JSON or clear text).

Return ONLY the updated character state description.
"""

UPDATE_GLOBAL_SUMMARY_PROMPT = """
Update the global story summary based on the new episode.

CURRENT GLOBAL SUMMARY:
{current_summary}

NEW EPISODE SUMMARY:
{episode_summary}

INSTRUCTIONS:
1. Integrate the key events of the new episode into the global summary.
2. Keep it concise but comprehensive enough to understand the overall narrative arc.
3. Focus on major plot points and character developments.

Return ONLY the updated global summary.
"""

SUMMARIZE_EPISODE_PROMPT = """
Summarize the following script into a concise paragraph (100-200 words).
Focus on: Key plot events, Character decisions, and Cliffhangers.

SCRIPT:
{script_content}
"""
