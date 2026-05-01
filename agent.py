#!/usr/bin/env python3
"""
BuildOrder Agent - Coding Agent
Planning: Kimi k2.5 via OpenCode
Implementation: Qwen 3.6 Plus via OpenCode
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiohttp

class BuildOrder:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.opencode_api_key = os.getenv("OPENCODE_API_KEY")
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_BUILD") or self.config['output']['discord_webhook']
        
    async def call_opencode(self, model: str, prompt: str, temperature: float = 0.4, max_tokens: int = 4096) -> str:
        """Call OpenCode API with specified model"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.opencode.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.opencode_api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a senior software engineer."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            ) as resp:
                result = await resp.json()
                return result['choices'][0]['message']['content']
    
    def fetch_pending_tasks(self) -> List[Dict[str, Any]]:
        """Fetch tasks from various sources"""
        tasks = []
        # TODO: Read from state/phase2-tasks.json, parse memory files
        return tasks
    
    async def plan_with_kimi(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Use Kimi k2.5 for architecture planning"""
        prompt = f"""Create a detailed implementation plan for this task:

Title: {task.get('title', '')}
Description: {task.get('description', '')}

Provide:
1. Architecture overview
2. File structure
3. Key functions/classes
4. Dependencies needed
5. Testing approach
6. Potential risks

Format as structured JSON."""
        
        model = self.config['models']['planning']['model']
        temp = self.config['models']['planning']['temperature']
        max_tokens = self.config['models']['planning']['max_tokens']
        
        plan_text = await self.call_opencode(model, prompt, temp, max_tokens)
        
        return {
            'task': task,
            'plan': plan_text,
            'model_used': 'kimi-k2.5',
            'timestamp': datetime.now().isoformat()
        }
    
    async def implement_with_qwen(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Use Qwen 3.6 Plus for code generation"""
        prompt = f"""Implement this plan in code:

Task: {plan['task'].get('title')}
Plan:
{plan['plan']}

Generate complete, production-ready code with:
- Clear comments
- Error handling
- Type hints where appropriate
- Docstrings for functions

Provide files as: FILENAME:\n```LANGUAGE\ncode\n```"""
        
        model = self.config['models']['implementation']['model']
        temp = self.config['models']['implementation']['temperature']
        max_tokens = self.config['models']['implementation']['max_tokens']
        
        code = await self.call_opencode(model, prompt, temp, max_tokens)
        
        return {
            'plan': plan,
            'code': code,
            'model_used': 'qwen-3.6-plus',
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
    
    async def post_summary(self, implementation: Dict[str, Any], files: List[str]):
        """Post implementation summary to Discord"""
        if not self.discord_webhook:
            print("No Discord webhook configured")
            return
        
        task = implementation['plan']['task']
        
        summary = f"""🛠️ **BuildOrder Complete**

**Task:** {task.get('title')}
**Branch:** {self.config['git']['feature_prefix']}{task.get('id', 'unknown')}
**Models:** Kimi k2.5 (plan) → Qwen 3.6 Plus (implement)

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
            return
        
        for task in tasks:
            print(f"Processing: {task.get('title')}")
            
            # Step 1: Plan with Kimi k2.5
            print("  Planning with Kimi k2.5...")
            plan = await self.plan_with_kimi(task)
            
            # Step 2: Implement with Qwen 3.6 Plus
            print("  Implementing with Qwen 3.6 Plus...")
            implementation = await self.implement_with_qwen(plan)
            
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
