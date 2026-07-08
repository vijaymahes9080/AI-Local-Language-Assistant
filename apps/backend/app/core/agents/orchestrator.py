import os
import sys
import json
import logging
from typing import Dict, Any, List

# Setup path configuration to import from packages/
current_dir = os.path.dirname(os.path.abspath(__file__))
monorepo_root = os.path.abspath(os.path.join(current_dir, "../../../../../"))
sys.path.insert(0, monorepo_root)

from packages.prompts import prompts
from app.core.agents.llm import call_llm

logger = logging.getLogger("lingosphere.orchestrator")

class AgentOrchestrator:
    @staticmethod
    async def route_and_execute(
        user_query: str,
        user_id: str,
        session_id: str,
        rag_context: str = ""
    ) -> Dict[str, Any]:
        """
        Determines the appropriate agent for the user query, executes it, and returns the response.
        """
        # 1. Intent routing
        routing_response = await call_llm(
            system_prompt=prompts.ORCHESTRATOR_SYSTEM_PROMPT,
            user_prompt=user_query,
            json_mode=True
        )
        
        try:
            route_data = json.loads(routing_response)
            selected_agent = route_data.get("agent", "GENERAL_ASSISTANT")
            reason = route_data.get("reason", "Default fallback")
        except Exception:
            logger.error("Failed to parse orchestrator routing response. Defaulting to general.")
            selected_agent = "GENERAL_ASSISTANT"
            reason = "Failed to parse json routing payload."

        logger.info(f"Routed query to {selected_agent}. Reason: {reason}")
        
        # 2. Execute selected agent
        agent_response = ""
        if selected_agent == "TRANSLATOR":
            agent_response = await call_llm(
                system_prompt=prompts.TRANSLATOR_SYSTEM_PROMPT,
                user_prompt=user_query
            )
        elif selected_agent == "PLANNER":
            agent_response = await call_llm(
                system_prompt=prompts.PLANNER_SYSTEM_PROMPT,
                user_prompt=user_query
            )
        elif selected_agent == "SEARCH":
            agent_response = await call_llm(
                system_prompt=prompts.SEARCH_SYSTEM_PROMPT,
                user_prompt=user_query
            )
        elif selected_agent == "TUTOR":
            agent_response = await call_llm(
                system_prompt=prompts.TUTOR_SYSTEM_PROMPT,
                user_prompt=user_query
            )
        elif selected_agent == "KNOWLEDGE_RAG":
            # Append context to query for RAG model
            prompt_with_context = f"Retrieved Context:\n{rag_context}\n\nUser Question:\n{user_query}"
            agent_response = await call_llm(
                system_prompt=prompts.KNOWLEDGE_RAG_SYSTEM_PROMPT,
                user_prompt=prompt_with_context
            )
        else:
            agent_response = await call_llm(
                system_prompt=prompts.GENERAL_ASSISTANT_SYSTEM_PROMPT,
                user_prompt=user_query
            )

        return {
            "routed_agent": selected_agent,
            "routing_reason": reason,
            "content": agent_response
        }
