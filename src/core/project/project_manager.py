import os
import shutil
import json
from datetime import datetime

class ProjectManager:
    def __init__(self, projects_root):
        self.projects_root = projects_root
        os.makedirs(self.projects_root, exist_ok=True)

    def create_project(self, project_name, extra_data=None):
        """
        Creates a new project folder structure.
        """
        # Sanitize name
        safe_name = "".join([c for c in project_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        project_dir = os.path.join(self.projects_root, safe_name)
        
        if os.path.exists(project_dir):
            raise ValueError(f"Project '{safe_name}' already exists.")

        # Create subdirectories
        os.makedirs(os.path.join(project_dir, "audio"))
        os.makedirs(os.path.join(project_dir, "images"))
        os.makedirs(os.path.join(project_dir, "clips"))
        os.makedirs(os.path.join(project_dir, "scripts")) # Ensure scripts dir exists
        
        # Create metadata
        metadata = {
            "name": project_name,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
        
        if extra_data:
            metadata.update(extra_data)
        
        with open(os.path.join(project_dir, "project.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
            
        # Initialize series.json with the provided data
        series_data = {
            "title": project_name,
            "premise": extra_data.get("theme", "") if extra_data else "",
            "genre": extra_data.get("genre", "") if extra_data else "",
            "total_episodes": extra_data.get("total_episodes", 100) if extra_data else 100,
            "words_per_episode": extra_data.get("words_per_episode", 300) if extra_data else 300,
            "main_characters": extra_data.get("main_characters", "") if extra_data else "",
            "global_summary": "",
            "character_state": "",
            "episodes": []
        }
        
        with open(os.path.join(project_dir, "series.json"), 'w', encoding='utf-8') as f:
            json.dump(series_data, f, indent=4, ensure_ascii=False)

        return project_dir

    def list_projects(self):
        """
        Returns a list of project dictionaries.
        """
        projects = []
        if not os.path.exists(self.projects_root):
            return projects

        for dirname in os.listdir(self.projects_root):
            dir_path = os.path.join(self.projects_root, dirname)
            if os.path.isdir(dir_path):
                meta_path = os.path.join(dir_path, "project.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            meta['path'] = dir_path
                            projects.append(meta)
                    except Exception as e:
                        print(f"Error loading project {dirname}: {e}")
                        continue
        return projects
