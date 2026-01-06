import os
import re
from datetime import timedelta

class SubtitleGenerator:
    def __init__(self):
        pass

    def format_timestamp(self, seconds):
        """Converts seconds to SRT timestamp format: HH:MM:SS,mmm"""
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        millis = int(td.microseconds / 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    def clean_subtitle_text(self, text):
        """
        Cleans subtitle text according to rules:
        1. No punctuation at the end, except ? and !
        2. Punctuation in the middle replaced by space.
        """
        if not text:
            return ""
            
        text = text.strip()
        
        # Define punctuation that should be handled
        punc_pattern = r"[.,;?:!，。；：？！、…—\"“”]"

        # 1. Separate trailing allowed punctuation (? ! ？！)
        # We want to keep the sequence of ?! at the end.
        allowed_end_pattern = r"([?!？！]+)$"
        match = re.search(allowed_end_pattern, text)
        
        trailing_allowed = ""
        content = text
        
        if match:
            trailing_allowed = match.group(1)
            content = text[:match.start()]
            
        # 2. Remove other trailing punctuation from content
        while content and re.search(punc_pattern + r"$", content):
             content = content[:-1].strip()
             
        # 3. Replace punctuation in middle of content with space
        content = re.sub(punc_pattern, ' ', content)
        
        # 4. Collapse spaces
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content + trailing_allowed

    def generate_srt(self, storyboard, output_path):
        """
        Generates an SRT file from the storyboard panels.
        Assumes panels have 'duration' set (derived from audio length).
        """
        current_time = 0.0
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, panel in enumerate(storyboard.panels):
                start_str = self.format_timestamp(current_time)
                
                # Duration should have been set during audio generation/probing
                # Default to 3.0 if missing
                duration = getattr(panel, 'duration', 3.0)
                end_time = current_time + duration
                end_str = self.format_timestamp(end_time)
                
                # Clean text: Remove "Role: " prefix if present for subtitles
                text = panel.description
                if ":" in text:
                    # Simple heuristic to remove "Alice: "
                    parts = text.split(":", 1)
                    if len(parts[0]) < 20: # It's likely a name
                        text = parts[1].strip()

                # Apply punctuation rules
                text = self.clean_subtitle_text(text)

                f.write(f"{i+1}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{text}\n\n")
                
                current_time = end_time
        
        return output_path
