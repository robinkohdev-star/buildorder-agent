#!/usr/bin/env python3
"""
BuildOrder Agent - Coding Agent with Opencode API
Uses Opencode MiniMax 2.5 for AI code generation
"""

import os
import json
import subprocess
import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiohttp
from dotenv import load_dotenv

# Load environment variables from .env file in agent directory
agent_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(agent_dir, '.env'))

# Sandboxed Ollama settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1:11435")
OLLAMA_URL = f"http://{OLLAMA_HOST}/api/generate"
WORKSPACE_ROOT = "/home/rk/.openclaw/workspace/main_workspace"

class BuildOrder:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Get webhook from env var first, fallback to config (resolving ${VAR} placeholders)
        config_webhook = self.config['output']['discord_webhook']
        if config_webhook.startswith('${') and config_webhook.endswith('}'):
            # It's a placeholder like ${DISCORD_WEBHOOK_BUILD}
            env_var_name = config_webhook[2:-1]  # Extract var name
            self.discord_webhook = os.getenv(env_var_name, '')
        else:
            self.discord_webhook = config_webhook
        
        # Also check explicit env var as override
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_BUILD", self.discord_webhook)
        self.model = "qwen2.5-coder:1.5b"  # Fast 1.5B model for CPU
        
    async def call_ollama(self, prompt: str, system: str = "") -> str:
        """Call local Ollama for AI generation"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 1500
            }
        }
        
        import json as json_mod
        payload_json = json_mod.dumps(payload)
        
        try:
            cmd = ['curl', '-s', '-X', 'POST', OLLAMA_URL,
                   '-H', 'Content-Type: application/json',
                   '-d', payload_json]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"Ollama curl error: {result.stderr[:200]}")
                return None
            
            try:
                data = json_mod.loads(result.stdout)
                return data.get('response', '')
            except json_mod.JSONDecodeError as e:
                print(f"Ollama JSON decode error: {e}")
                print(f"Response: {result.stdout[:200]}")
                return None
        except Exception as e:
            print(f"Ollama error: {e}")
            return None
    
    async def generate_plan(self, task: Dict[str, Any]) -> str:
        """Generate implementation plan using Ollama"""
        title = task.get('title', 'Untitled')
        description = task.get('description', task.get('details', 'No description'))
        
        system_prompt = "You are a senior software architect. Create detailed implementation plans."
        
        user_prompt = f"""Create a detailed implementation plan for this task:

Task: {title}
Description: {description}

Provide:
1. Overview of what needs to be built
2. Key files to create/modify (with specific paths)
3. Main components/modules needed
4. Dependencies or libraries to use
5. Step-by-step implementation order

Format as markdown with clear file paths."""

        plan = await self.call_ollama(user_prompt, system_prompt)
        return plan or self._plan_template(title, description)
    
    def _plan_template(self, title: str, description: str) -> str:
        """Fallback plan template"""
        return f"""# Implementation Plan: {title}

## Overview
{description}

## Files to Create/Modify
- TBD

## Approach
1. Analyze requirements
2. Design solution
3. Implement core functionality
4. Add tests
5. Review
"""
    
    async def generate_code(self, task: Dict[str, Any], plan: str) -> Dict[str, str]:
        """Generate actual code files using Ollama"""
        title = task.get('title', 'Untitled')
        
        system_prompt = "You are an expert software engineer. Write complete, working code."
        
        user_prompt = f"""Generate complete, working code for this task.

Task: {title}

Implementation Plan:
{plan}

Generate actual code files. For each file, use this exact format:

### FILE: path/to/filename.ext
```language
complete file content here
```

Provide complete, runnable code with proper imports and error handling."""

        response = await self.call_ollama(user_prompt, system_prompt)
        
        if not response:
            return {}
        
        # Parse file blocks from response
        files = self._parse_code_blocks(response)
        return files
    
    def _parse_code_blocks(self, text: str) -> Dict[str, str]:
        """Parse FILE: headers and code blocks from AI response"""
        files = {}
        
        # Pattern: ### FILE: path/to/file.ext followed by ```code```
        pattern = r'###\s*FILE:\s*(\S+)\s*```(?:\w+)?\s*(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for filepath, content in matches:
            files[filepath.strip()] = content.strip()
        
        return files
    
    def fetch_pending_tasks(self) -> List[Dict[str, Any]]:
        """Fetch tasks from Otter Mission Control"""
        tasks = []
        
        mission_control_tasks = os.path.join(WORKSPACE_ROOT, "state/phase2-tasks.json")
        if os.path.exists(mission_control_tasks):
            try:
                with open(mission_control_tasks, 'r') as f:
                    data = json.load(f)
                    for task in data:
                        if task.get('status') == 'in-progress':
                            tasks.append(task)
                    print(f"Loaded {len(tasks)} in-progress task(s) from Mission Control")
            except Exception as e:
                print(f"Error loading Mission Control tasks: {e}")
        
        return tasks
    
    def create_branch(self, task_id: str) -> str:
        """Create a new git branch for the task"""
        prefix = self.config['git']['feature_prefix']
        branch_name = f"{prefix}{task_id}"
        
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=WORKSPACE_ROOT,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"  Not a git repository: {WORKSPACE_ROOT}")
                return branch_name
            
            subprocess.run(
                ['git', 'checkout', '-b', branch_name],
                cwd=WORKSPACE_ROOT,
                check=True,
                capture_output=True
            )
            print(f"  Created and checked out branch: {branch_name}")
            return branch_name
            
        except subprocess.CalledProcessError:
            try:
                subprocess.run(
                    ['git', 'checkout', branch_name],
                    cwd=WORKSPACE_ROOT,
                    check=True,
                    capture_output=True
                )
                print(f"  Checked out existing branch: {branch_name}")
            except:
                pass
            return branch_name
        except Exception as e:
            print(f"  Error creating branch: {e}")
            return branch_name
    
    def write_files(self, files: Dict[str, str]) -> List[str]:
        """Write generated code to files"""
        written = []
        
        for filepath, content in files.items():
            try:
                full_path = os.path.join(WORKSPACE_ROOT, filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, 'w') as f:
                    f.write(content)
                
                written.append(filepath)
                print(f"  Written: {filepath}")
                
            except Exception as e:
                print(f"  Error writing {filepath}: {e}")
        
        return written
    
    def commit_changes(self, branch: str, task_title: str, files: List[str]) -> bool:
        """Commit changes to git"""
        if not files:
            return False
        
        try:
            subprocess.run(
                ['git', 'add'] + files,
                cwd=WORKSPACE_ROOT,
                check=True
            )
            
            commit_msg = f"buildorder: {task_title}\n\nFiles:\n" + "\n".join([f"- {f}" for f in files])
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=WORKSPACE_ROOT,
                check=True
            )
            
            print(f"  Committed {len(files)} file(s)")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"  Git commit error: {e}")
            return False
        except Exception as e:
            print(f"  Error committing: {e}")
            return False
    
    async def post_summary(self, task: Dict[str, Any], branch: str, files: List[str], plan: str):
        """Post implementation summary to Discord"""
        if not self.discord_webhook:
            return
        
        file_list = "\n".join([f"- `{f}`" for f in files]) if files else "_No files generated_"
        
        summary = f"""🛠️ **BuildOrder: Task Implementation**

**Task:** {task.get('title')}
**Branch:** `{branch}`
**Model:** {self.model}

**Files Created:**
{file_list}

**Plan Preview:**
```
{plan[:500]}...
```

Ready for review and testing.
"""
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.discord_webhook,
                json={"content": summary[:2000]}
            )
    
    async def post_heartbeat(self):
        """Post heartbeat when no tasks"""
        if not self.discord_webhook:
            return
        
        heartbeat = f"""✅ **BuildOrder Heartbeat**

**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M')} SGT
**Status:** No pending tasks
**Model:** {self.model} (local Ollama)

BuildOrder is running and ready to process tasks.
"""
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.discord_webhook,
                json={"content": heartbeat[:2000]}
            )
    
    async def run(self):
        """Main agent loop"""
        print(f"[{datetime.now()}] BuildOrder starting...")
        print(f"Workspace: {WORKSPACE_ROOT}")
        print(f"Ollama: {OLLAMA_HOST}")
        print(f"Model: {self.model}")
        
        tasks = self.fetch_pending_tasks()
        
        if not tasks:
            print("No pending tasks found")
            await self.post_heartbeat()
            print(f"[{datetime.now()}] BuildOrder complete - no tasks")
            return
        
        for task in tasks:
            title = task.get('title', 'Untitled')
            task_id = task.get('id', 'unknown')
            print(f"\nProcessing: {title}")
            
            # Step 1: Generate plan with Ollama
            print("  Generating plan with Ollama...")
            plan = await self.generate_plan(task)
            
            # Step 2: Generate code with Ollama
            print("  Generating code with Ollama...")
            files_content = await self.generate_code(task, plan)
            
            # Step 3: Create branch
            branch = self.create_branch(task_id)
            
            # Step 4: Write files
            files_written = []
            if files_content:
                files_written = self.write_files(files_content)
                print(f"  Written {len(files_written)} file(s)")
            else:
                print("  No files generated")
            
            # Step 5: Commit changes
            if files_written:
                committed = self.commit_changes(branch, title, files_written)
                if committed:
                    await self.update_task_status(task_id, "done")
            
            # Step 6: Post summary
            await self.post_summary(task, branch, files_written, plan)
            print("  Summary posted to Discord")
        
        print(f"\n[{datetime.now()}] BuildOrder complete")
    
    async def update_task_status(self, task_id: str, new_status: str):
        """Update task status in phase2-tasks.json"""
        try:
            tasks_file = os.path.join(WORKSPACE_ROOT, "state/phase2-tasks.json")
            with open(tasks_file, 'r') as f:
                tasks = json.load(f)
            
            for task in tasks:
                if task.get('id') == task_id:
                    task['status'] = new_status
                    task['updatedAt'] = datetime.now().isoformat()
                    break
            
            with open(tasks_file, 'w') as f:
                json.dump(tasks, f, indent=2)
            
            print(f"  Updated task {task_id} status to: {new_status}")
            
        except Exception as e:
            print(f"  Error updating task status: {e}")

if __name__ == "__main__":
    agent = BuildOrder()
    asyncio.run(agent.run())
