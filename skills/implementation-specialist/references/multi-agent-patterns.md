# Multi-Agent Architecture Patterns

## Core Concepts

Multi-agent systems coordinate multiple AI agents to solve complex tasks through specialization and collaboration.

### Agent Types

1. **Orchestrator Agent**: Coordinates other agents, routes tasks, aggregates results
2. **Specialist Agents**: Domain-specific agents (content creation, analysis, scheduling)
3. **Validator Agent**: Reviews and validates outputs from other agents

## Implementation Pattern

### Agent Base Class
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

class AgentMessage(BaseModel):
    role: str
    content: str
    metadata: Dict[str, Any] = {}

class Agent(ABC):
    def __init__(self, name: str, role: str, model: str = "gpt-4"):
        self.name = name
        self.role = role
        self.model = model
        self.conversation_history: List[AgentMessage] = []

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return output"""
        pass

    def add_to_history(self, message: AgentMessage):
        self.conversation_history.append(message)
```

### Orchestrator Pattern
```python
from typing import List, Dict, Any
import asyncio

class OrchestratorAgent(Agent):
    def __init__(self, specialist_agents: List[Agent]):
        super().__init__(name="orchestrator", role="coordinator")
        self.specialists = {agent.name: agent for agent in specialist_agents}

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Analyze task and determine required specialists
        task_plan = await self._plan_task(input_data)

        # 2. Execute specialists in parallel or sequence
        results = await self._execute_plan(task_plan)

        # 3. Aggregate and synthesize results
        final_output = await self._synthesize_results(results)

        return final_output

    async def _plan_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine which agents to use and in what order"""
        # Use LLM to analyze task and create execution plan
        prompt = f"""
        Analyze this task and determine which specialist agents to use:
        Task: {input_data['task']}
        Available agents: {list(self.specialists.keys())}

        Return a JSON plan with agent sequence and dependencies.
        """
        # Call LLM API here
        return {"agents": ["content_creator", "validator"], "mode": "sequential"}

    async def _execute_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute agents according to plan"""
        results = []

        if plan["mode"] == "sequential":
            context = {}
            for agent_name in plan["agents"]:
                agent = self.specialists[agent_name]
                result = await agent.process(context)
                context.update(result)
                results.append(result)

        elif plan["mode"] == "parallel":
            tasks = [
                self.specialists[agent_name].process({})
                for agent_name in plan["agents"]
            ]
            results = await asyncio.gather(*tasks)

        return results

    async def _synthesize_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine results from multiple agents"""
        # Use LLM to synthesize final output
        return {"final_output": results[-1], "all_results": results}
```

### Specialist Agent Example
```python
class ContentCreatorAgent(Agent):
    def __init__(self):
        super().__init__(name="content_creator", role="social_media_content")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
        Create social media content based on:
        Topic: {input_data.get('topic')}
        Platform: {input_data.get('platform')}
        Tone: {input_data.get('tone', 'professional')}
        """

        # Call LLM API
        content = await self._call_llm(prompt)

        return {
            "content": content,
            "platform": input_data.get('platform'),
            "created_by": self.name
        }

    async def _call_llm(self, prompt: str) -> str:
        # Implement LLM API call (OpenAI, Anthropic, etc.)
        pass
```

### Validator Agent Example
```python
class ValidatorAgent(Agent):
    def __init__(self):
        super().__init__(name="validator", role="quality_assurance")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        content = input_data.get('content')

        validation_prompt = f"""
        Review this content for:
        1. Grammar and spelling
        2. Brand voice consistency
        3. Platform-specific best practices
        4. Engagement potential

        Content: {content}

        Return: {{
            "approved": bool,
            "issues": [list of issues],
            "suggestions": [list of improvements]
        }}
        """

        validation_result = await self._call_llm(validation_prompt)

        return {
            "validated": True,
            "original_content": content,
            "validation_result": validation_result
        }
```

## FastAPI Integration

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

app = FastAPI()

# Initialize agents
content_creator = ContentCreatorAgent()
validator = ValidatorAgent()
orchestrator = OrchestratorAgent([content_creator, validator])

class TaskRequest(BaseModel):
    task: str
    platform: str
    topic: str

@app.post("/api/agents/execute")
async def execute_agent_task(request: TaskRequest):
    result = await orchestrator.process({
        "task": request.task,
        "platform": request.platform,
        "topic": request.topic
    })
    return result
```

## Communication Patterns

### 1. Sequential Pipeline
Agents process in order, each using previous agent's output.

### 2. Parallel Execution
Multiple agents work simultaneously on independent subtasks.

### 3. Hierarchical Delegation
Orchestrator delegates to specialists, who may delegate further.

### 4. Consensus Building
Multiple agents vote or reach consensus on decisions.

## State Management

```python
from typing import Dict, Any
import json

class AgentState:
    def __init__(self):
        self.shared_context: Dict[str, Any] = {}
        self.agent_outputs: Dict[str, Any] = {}

    def update_context(self, key: str, value: Any):
        self.shared_context[key] = value

    def store_output(self, agent_name: str, output: Any):
        self.agent_outputs[agent_name] = output

    def get_context(self) -> Dict[str, Any]:
        return self.shared_context
```

## Error Handling

```python
class AgentExecutionError(Exception):
    def __init__(self, agent_name: str, error: str):
        self.agent_name = agent_name
        self.error = error
        super().__init__(f"Agent {agent_name} failed: {error}")

async def safe_agent_execution(agent: Agent, input_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return await agent.process(input_data)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "agent": agent.name
        }
```
