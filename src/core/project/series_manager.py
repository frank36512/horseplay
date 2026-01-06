import json
import os
from datetime import datetime
from core.rag.vector_store import SimpleVectorStore
from ai_engine.llm.llm_client import LLMClient
from ai_engine.prompts import (
    UPDATE_CHARACTER_STATE_PROMPT, 
    UPDATE_GLOBAL_SUMMARY_PROMPT, 
    SUMMARIZE_EPISODE_PROMPT
)

class SeriesManager:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.series_path = os.path.join(project_dir, "series.json")
        self.memory_path = os.path.join(project_dir, "memory.json")
        
        self.vector_store = SimpleVectorStore(self.memory_path)
        # self.llm_client = LLMClient() # Don't init LLMClient here without config!
        
        self.data = {
            "title": "New Series",
            "premise": "",
            "global_summary": "", # The "Story So Far"
            "character_state": "", # Dynamic tracking of characters
            "episodes": [] # List of {id, title, summary, script_path}
        }
        self.load()

    def load(self):
        if os.path.exists(self.series_path):
            try:
                with open(self.series_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Error loading series data: {e}")

    def save(self):
        with open(self.series_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def update_premise(self, premise, api_config=None):
        self.data["premise"] = premise
        self.save()
        # Embed premise as "World Context"
        # Skip embedding if no config provided, or handle it later
        if api_config:
            client = LLMClient(api_key=api_config.get("api_key"), base_url=api_config.get("base_url"), model=api_config.get("model"))
            emb = client.get_embedding(premise)
            if emb:
                self.vector_store.add_document("premise", premise, emb, {"type": "world_building"})

    def add_episode(self, title, script_content, summary=None, api_config=None):
        ep_id = len(self.data["episodes"]) + 1
        filename = f"episode_{ep_id}.json"
        script_path = os.path.join(self.project_dir, "scripts", filename)
        
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        
        # Save script file
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
            
        # If no API config is provided, we CANNOT generate summaries or update state
        # because we don't know which LLM to use.
        # So we skip the auto-update logic if api_config is missing.
        
        if api_config:
            client = LLMClient(api_key=api_config.get("api_key"), base_url=api_config.get("base_url"), model=api_config.get("model"))
            
            # 1. Generate Summary if missing
            if not summary:
                summary = client.generate_script(
                    SUMMARIZE_EPISODE_PROMPT.format(script_content=script_content)
                ) or "Summary generation failed."

            # 2. Update Character State
            current_state = self.data.get("character_state", "No character state yet.")
            new_state = client.generate_script(
                UPDATE_CHARACTER_STATE_PROMPT.format(
                    current_state=current_state,
                    script_content=script_content
                )
            )
            if new_state:
                self.data["character_state"] = new_state

            # 3. Update Global Summary
            current_global = self.data.get("global_summary", "")
            new_global = client.generate_script(
                UPDATE_GLOBAL_SUMMARY_PROMPT.format(
                    current_summary=current_global,
                    episode_summary=summary
                )
            )
            if new_global:
                self.data["global_summary"] = new_global
        else:
            if not summary:
                summary = "Summary not generated (No API Config)."

        episode_info = {
            "id": ep_id,
            "title": title,
            "summary": summary,
            "script_path": f"scripts/{filename}",
            "created_at": datetime.now().isoformat()
        }
        
        self.data["episodes"].append(episode_info)
        self.save()
        
        # Embed summary into vector store
        if api_config and summary:
             # Re-use client from above
             emb = client.get_embedding(summary)
             if emb:
                 self.vector_store.add_document(f"episode_{ep_id}", summary, emb, {"type": "episode_summary", "id": ep_id})

    def update_episode(self, ep_id, title, script_content, summary=None):
        # Find episode
        episode = next((e for e in self.data["episodes"] if e["id"] == ep_id), None)
        if not episode:
            print(f"Episode {ep_id} not found.")
            return False

        # Update file
        rel_path = episode.get("script_path")
        if not rel_path:
             filename = f"episode_{ep_id}.json"
             rel_path = f"scripts/{filename}"
             episode["script_path"] = rel_path

        script_path = os.path.join(self.project_dir, rel_path)
        os.makedirs(os.path.dirname(script_path), exist_ok=True)

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
            
        # Update metadata
        episode["title"] = title
        if summary:
            episode["summary"] = summary
        episode["updated_at"] = datetime.now().isoformat()
            
        self.save()
        return True

    def delete_episode(self, episode_id):
        """
        Deletes an episode by ID and re-indexes subsequent episodes.
        """
        # Find index
        idx = -1
        for i, ep in enumerate(self.data["episodes"]):
            if ep["id"] == episode_id:
                idx = i
                break
        
        if idx == -1:
            return False

        # Remove file
        ep_to_remove = self.data["episodes"][idx]
        script_path = os.path.join(self.project_dir, ep_to_remove["script_path"])
        if os.path.exists(script_path):
            try:
                os.remove(script_path)
            except Exception as e:
                print(f"Error deleting file {script_path}: {e}")

        # Remove from list
        self.data["episodes"].pop(idx)

        # Re-index subsequent episodes
        for i in range(idx, len(self.data["episodes"])):
            ep = self.data["episodes"][i]
            old_id = ep["id"]
            new_id = i + 1
            
            old_path = os.path.join(self.project_dir, ep["script_path"])
            new_filename = f"episode_{new_id}.json"
            new_path = os.path.join(self.project_dir, "scripts", new_filename)
            
            # Rename file
            if os.path.exists(old_path):
                try:
                    # Ensure target doesn't exist (it shouldn't if we process in order)
                    if os.path.exists(new_path):
                        os.remove(new_path)
                    os.rename(old_path, new_path)
                    ep["script_path"] = f"scripts/{new_filename}"
                except Exception as e:
                    print(f"Error renaming {old_path} to {new_path}: {e}")
            
            ep["id"] = new_id

        self.save()
        return True

    def get_full_context_data(self, query_idea, embedding_config=None):
        """
        Returns a dictionary with all context elements needed for generation.
        """
        # 1. Recent Episodes Summary (Last 3)
        recent_summaries = []
        for ep in self.data["episodes"][-3:]:
            recent_summaries.append(f"Episode {ep['id']} '{ep['title']}': {ep['summary']}")
        recent_context = "\n".join(recent_summaries)

        # 2. Previous Script Excerpt (Last 500 chars of last script)
        prev_excerpt = ""
        if self.data["episodes"]:
            last_ep = self.data["episodes"][-1]
            full_path = os.path.join(self.project_dir, last_ep["script_path"])
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        prev_excerpt = content[-800:] # Last 800 chars
                except:
                    pass

        # 3. RAG Retrieval
        rag_context = ""
        if query_idea:
            emb = None
            if embedding_config and embedding_config.get("api_key"):
                try:
                    temp_client = LLMClient(
                        api_key=embedding_config.get("api_key"),
                        base_url=embedding_config.get("base_url")
                    )
                    emb = temp_client.get_embedding(query_idea, model=embedding_config.get("model"))
                except Exception as e:
                    print(f"Custom embedding error: {e}")
            
            if not emb:
                # Fallback: Try to use default client if possible, or skip
                try:
                    fallback_client = LLMClient()
                    emb = fallback_client.get_embedding(query_idea)
                except:
                    pass

            if emb:
                results = self.vector_store.search(emb, top_k=3)
                rag_items = []
                for score, item in results:
                    if item['metadata'].get('ep_id') == len(self.data["episodes"]):
                        continue
                    rag_items.append(item['text'])
                rag_context = "\n---\n".join(rag_items)

        return {
            "premise": self.data.get("premise", ""),
            "genre": self.data.get("genre", ""),
            "total_episodes": self.data.get("total_episodes", 100),
            "words_per_episode": self.data.get("words_per_episode", 300),
            "main_characters": self.data.get("main_characters", ""),
            "global_summary": self.data.get("global_summary", ""),
            "character_state": self.data.get("character_state", ""),
            "recent_episodes_summary": recent_context,
            "previous_script_excerpt": prev_excerpt,
            "rag_context": rag_context,
            "episode_number": len(self.data["episodes"]) + 1
        }

    def get_context_for_next_episode(self, query_idea):
        # Legacy method wrapper
        data = self.get_full_context_data(query_idea)
        return f"Global Summary: {data['global_summary']}\n\nRecent: {data['recent_episodes_summary']}"

    def get_episodes(self):
        return self.data["episodes"]

