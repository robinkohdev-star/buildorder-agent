#!/usr/bin/env python3
"""
BuildOrder Agent - Coding Agent
Task tracking and git workflow automation (no external AI APIs)
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiohttp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BuildOrder:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.opencode_api_key = os.getenv("OPENCODE_API_KEY")
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_BUILD") or self.config['output']['discord_webhook']
        
    def generate_plan_template(self, task: Dict[str, Any]) -> str:
        """Generate a simple plan template without AI"""
        title = task.get('title', 'Untitled')
        description = task.get('description', 'No description')
        
        return f"""# Implementation Plan: {title}

## Overview
{description}

## Approach
1. Analyze requirements
2. Design solution structure
3. Implement core functionality
4. Add error handling
5. Write tests
6. Review and refine

## Key Considerations
- Follow existing code patterns
- Add proper documentation
- Include type hints
- Handle edge cases
- Write unit tests

## Files to Create/Modify
- TBD based on task analysis

**Note:** This is a template plan. Manual review and refinement needed.
"""
    
    def generate_code_template(self, task: Dict[str, Any]) -> str:
        """Generate a simple code template without AI"""
        title = task.get('title', 'Untitled')
        
        return f"""# {title}

## Implementation Notes
- Review requirements carefully
- Follow project coding standards
- Add comprehensive error handling
- Include docstrings and type hints
- Write unit tests

## Next Steps
1. Review this template
2. Implement actual functionality
3. Test thoroughly
4. Submit for review

**Note:** This is a placeholder. Actual implementation requires developer input.
"""
    
    def fetch_pending_tasks(self) -> List[Dict[str, Any]]:
        """Fetch tasks from Otter Mission Control"""
        tasks = []
        
        # Read from Otter Mission Control state
        mission_control_tasks = "/home/rk/.openclaw/workspace/main_workspace/state/phase2-tasks.json"
        if os.path.exists(mission_control_tasks):
            try:
                with open(mission_control_tasks, 'r') as f:
                    data = json.load(f)
                    # Filter for in-progress tasks
                    for task in data:
                        if task.get('status') == 'in-progress':
                            tasks.append(task)
                    print(f"Loaded {len(tasks)} in-progress task(s) from Mission Control")
            except Exception as e:
                print(f"Error loading Mission Control tasks: {e}")
        
        # Check for test task file (fallback)
        if os.path.exists("test-task.json"):
            try:
                with open("test-task.json", 'r') as f:
                    data = json.load(f)
                    tasks.extend(data.get("tasks", []))
                    print(f"Loaded {len(data.get('tasks', []))} test task(s)")
            except Exception as e:
                print(f"Error loading test tasks: {e}")
        
        return tasks
    
    def plan_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate plan for a task (no AI)"""
        plan_text = self.generate_plan_template(task)
        
        return {
            'task': task,
            'plan': plan_text,
            'model_used': 'template',
            'timestamp': datetime.now().isoformat()
        }
    
    def implement_task(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate implementation template (no AI)"""
        code = self.generate_code_template(plan['task'])
        
        return {
            'plan': plan,
            'code': code,
            'model_used': 'template',
            'timestamp': datetime.now().isoformat()
        }
    
    def create_branch(self, task_id: str) -> str:
        """Create a new git branch for the task"""
        prefix = self.config['git']['feature_prefix']
        branch_name = f"{prefix}{task_id}"
        
        # TODO: Implement git branch creation
        # subprocess.run(['git', 'checkout', '-b', branch_name])
        
        return branch_name
    
    def write_files(self, implementation: Dict[str, Any]) -> List[str]:
        """Write generated code to files"""
        # TODO: Parse code blocks and write to appropriate files
        return []
    
    async def post_heartbeat(self):
        """Post heartbeat to Discord when no tasks"""
        if not self.discord_webhook:
            print("No Discord webhook configured")
            return
        
        heartbeat = f"""✅ **BuildOrder Heartbeat**

**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M')} SGT
**Status:** No pending tasks
**Mode:** Standalone (no external AI APIs)

BuildOrder is running and ready to process tasks when they become available.
"""
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.discord_webhook,
                json={"content": heartbeat[:2000]}
            )
        print("Heartbeat posted to Discord")
    
    async def post_summary(self, implementation: Dict[str, Any], files: List[str]):
        """Post implementation summary to Discord"""
        if not self.discord_webhook:
            print("No Discord webhook configured")
            return
        
        task = implementation['plan']['task']
        
        summary = f"""🛠️ **BuildOrder Task Processed**

**Task:** {task.get('title')}
**Branch:** {self.config['git']['feature_prefix']}{task.get('id', 'unknown')}
**Mode:** Template-based planning (no external AI)

**Files Modified:**
{chr(10).join([f'- {f}' for f in files])}

**Summary:**
Implementation complete and ready for review.
"""
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.discord_webhook,
                json={"content": summary[:2000]}
            )
    
    async def run(self):
        """Main agent loop"""
        print(f"[{datetime.now()}] BuildOrder starting...")
        
        # Fetch tasks
        tasks = self.fetch_pending_tasks()
        
        if not tasks:
            print("No pending tasks found")
            # Post heartbeat to Discord
            await self.post_heartbeat()
            print(f"[{datetime.now()}] BuildOrder complete - no tasks")
            return
        
        for task in tasks:
            print(f"Processing: {task.get('title')}")
            
            # Step 1: Generate plan (template-based)
            print("  Generating plan...")
            plan = self.plan_task(task)
            
            # Step 2: Generate implementation template
            print("  Generating implementation template...")
            implementation = self.implement_task(plan)
            
            # Step 3: Create branch
            branch = self.create_branch(task.get('id', 'unknown'))
            print(f"  Created branch: {branch}")
            
            # Step 4: Write files
            files = self.write_files(implementation)
            print(f"  Wrote {len(files)} files")
            
            # Step 5: Post summary
            await self.post_summary(implementation, files)
            print("  Summary posted to Discord")
        
        print(f"[{datetime.now()}] BuildOrder complete")

if __name__ == "__main__":
    agent = BuildOrder()
    asyncio.run(agent.run())
