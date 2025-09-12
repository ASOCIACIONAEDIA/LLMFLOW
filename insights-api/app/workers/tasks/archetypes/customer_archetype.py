import os
import json
import asyncio
import urllib.parse
from typing import Dict, Any, List, Union
from openai import OpenAI

from app.workers.tasks.archetypes.base_archetype import BaseArchetypeTask
from app.workers.base.progress import ProgressNotifier
from app.domain.types import WebSocketEventType, JobTargetType, JobStatus

class CustomerArchetypeTask(BaseArchetypeTask):
    """
    Customer archetype generation using LLM analysis of reviews.
    """

    def __init__(self):
        super().__init__("customer_archetype_generator")
    
    async def _execute_archetype_generation(
        self,
        job_id: str, 
        organization_id: int,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute the customer archetype generation.
        """
        self.logger.info(f"Starting customer archetype generation for job {job_id}")
        try:
            # Validate config
            if not await self.validate_config(config):
                raise ValueError("Invalid configuration for customer archetype generation")
            
            await ProgressNotifier.notify_job_progress(
            job_id=job_id,
            event_type=WebSocketEventType.ARCHETYPE_FETCHING,
            message="Fetching review samples for analysis",
            data={"step": "fetching_reviews"}
            )

            target_type = JobTargetType(config.get("target_type", JobTargetType.ORGANIZATION.value))
            target_id = config.get("target_id", organization_id)

            reviews = await self._fetch_reviews_for_analysis(
                organization_id=organization_id,
                target_type=target_type,
                target_id=target_id,
                config=config
            )

            if not reviews:
                raise ValueError("No review samples found for analysis")
            
            await ProgressNotifier.notify_job_progress(
                job_id=job_id,
                event_type=WebSocketEventType.ARCHETYPE_GENERATING,
                message=f"Generating archetypes from {len(reviews)} reviews using AI",
                data={"step": "generating", "review_count": len(reviews)}
            )

            archetypes = await asyncio.to_thread(
                self._generate_archetypes_with_llm,
                config.get("brand_name", "My Business"),
                reviews
            )
            self.logger.info(f"Generated {len(archetypes)} archetypes")
            return archetypes
        
        except Exception as e:
            error_msg = f"Error in customer archetype generation: {str(e)}"
            await ProgressNotifier.notify_task_error(
                job_id=job_id,
                task_name=self.task_name,
                error_msg=error_msg
            )
            await self._update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=error_msg
            )
            self.logger.error(error_msg)
            raise
        
    def _generate_archetypes_with_llm(self, brand_name: str, reviews: List[str]) -> List[Dict[str, Any]]:
        """
        Generate archetypes using LLM (OpenAI/Claude).
        """
        reviews_formatted = "\n".join(f"- {review.strip()}" for review in reviews[:100])  # Limit for API
        
        prompt = f"""Generate 3 behavioral archetypes for the brand {brand_name}, based on brand knowledge and user opinions. Base this on the methodology of Adele Revelle and Forrester.
---
REVIEWS
{reviews_formatted}
---

You must provide your response by calling the 'extract_customer_archetypes' tool.
Each archetype should have the following sections:
- name: The name of the archetype
- general_description: Essence of the archetype (3-4 lines max)
- pain_points: List of frustrations expressed in reviews (4-5 points max)
- fears_and_concerns: List of underlying worries and fears
- objections: List of rational barriers expressed
- goals_and_objectives: List of what users want to achieve
- expected_benefits: List of advantages users expect
- values: List of fundamental principles and beliefs
- social_behavior: Observable interaction patterns
- influence_factors: List of elements impacting decisions
- internal_narrative: Deep, unexpressed motivations

All content must derive from observable data in the reviews.
Insights must be actionable.
Avoid assumptions not supported by data.
Prioritize recurring patterns over isolated cases."""

        try:
            response = self._call_openai_api(prompt)
            return self._process_llm_response(response)
        except Exception as e:
            self.logger.error(f"Error calling LLM API: {e}")
            raise
        
    def _call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call OpenAI API with structured output for archetype generation.
        """
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )

        # Define the schema for archetype generation
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "extract_customer_archetypes",
                    "description": "Extracts 3 behavioral customer archetypes based on reviews and brand context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "archetypes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "general_description": {"type": "string"},
                                        "pain_points": {"type": "array", "items": {"type": "string"}},
                                        "fears_and_concerns": {"type": "array", "items": {"type": "string"}},
                                        "objections": {"type": "array", "items": {"type": "string"}},
                                        "goals_and_objectives": {"type": "array", "items": {"type": "string"}},
                                        "expected_benefits": {"type": "array", "items": {"type": "string"}},
                                        "values": {"type": "array", "items": {"type": "string"}},
                                        "social_behavior": {"type": "string"},
                                        "influence_factors": {"type": "array", "items": {"type": "string"}},
                                        "internal_narrative": {"type": "string"}
                                    },
                                    "required": ["name", "general_description", "pain_points", "fears_and_concerns", 
                                               "objections", "goals_and_objectives", "expected_benefits", "values",
                                               "social_behavior", "influence_factors", "internal_narrative"]
                                }
                            }
                        },
                        "required": ["archetypes"]
                    }
                }
            }
        ]

        completion = client.chat.completions.create(
            model="anthropic/claude-3.5-sonnet",
            messages=[
                {"role": "system", "content": "You are an expert market researcher specializing in consumer behavior analysis."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_customer_archetypes"}},
            max_tokens=4000,
            temperature=0.5,
        )

        message = completion.choices[0].message
        if message.tool_calls and message.tool_calls[0].function.name == "extract_customer_archetypes":
            function_arguments = message.tool_calls[0].function.arguments
            return json.loads(function_arguments)
        else:
            raise ValueError("LLM did not use the required tool for structured output")
    
    def _process_llm_response(self, llm_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process and validate LLM repsonse into archetype format.
        """
        if "archetypes" not in llm_response:
            raise ValueError("LLM response missing required 'archetypes' field")
        
        archetypes = llm_response["archetypes"]
        processed_archetypes = []
        for i, archetype in enumerate(archetypes):
            if not isinstance(archetype, dict):
                continue
        
            name_seed = archetype.get("name", f"archetype-{i+1}").lower().replace(' ', '-')
            name_seed_encoded = urllib.parse.quote(name_seed)
            avatar_url = f'https://api.dicebear.com/7.x/personas/svg?seed={name_seed_encoded}&backgroundColor=b7c7ff'
            
            # Structure the archetype data
            processed_archetype = {
                "name": archetype.get("name", f"Archetype {i+1}"),
                "description": archetype.get("general_description", ""),
                "pain_points": archetype.get("pain_points", []),
                "fears_and_concerns": archetype.get("fears_and_concerns", []),
                "objections": archetype.get("objections", []),
                "goals_and_objectives": archetype.get("goals_and_objectives", []),
                "expected_benefits": archetype.get("expected_benefits", []),
                "values": archetype.get("values", []),
                "social_behavior": archetype.get("social_behavior", ""),
                "influence_factors": archetype.get("influence_factors", []),
                "internal_narrative": archetype.get("internal_narrative", ""),
                "avatar_url": avatar_url
            }
            
            processed_archetypes.append(processed_archetype)
        return processed_archetypes

async def generate_customer_archetypes_task(
    ctx, 
    job_id: str, 
    organization_id: int, 
    config: Dict[str, Any]
):
    """ARQ task function for customer archetype generation"""
    task = CustomerArchetypeTask()
    return await task.execute(ctx, job_id, organization_id, config)