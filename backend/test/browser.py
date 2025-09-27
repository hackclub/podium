import asyncio
import contextlib
from browser_use import Agent, BrowserSession, Controller
from browser_use.config import CONFIG as browser_use_config
from test import settings, AiTestSettings
from loguru import logger
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


async def run_browser_agent(
    prompt: str,
    output_model: Type[T],
    failure_result: T,
    browser: BrowserSession,
    config: AiTestSettings = settings,
) -> T:
    try:
        agent_task = asyncio.create_task(
            Agent(
                llm=config.llm,
                controller=Controller(output_model=output_model),
                task=prompt,
                browser=browser,
                use_vision=settings.use_vision,
                max_actions_per_step=10,
            ).run(
                # max_steps=100
            )
        )
        results_raw = await asyncio.gather(agent_task)
        agent_result = results_raw[0]
        final_json = agent_result.final_result()
        logger.info(final_json)
        if final_json is not None:
            # Parse the agent result
            result = output_model.model_validate_json(final_json)
            return result
        else:
            return failure_result
    except KeyboardInterrupt:
        # Ensure the agent task is stopped so pytest can unwind fixtures cleanly
        try:
            agent_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await agent_task
        except Exception:
            pass
        raise
    except ValidationError as e:
        logger.error(f"Validation error occurred: {e}")
        return failure_result


browser_use_config.BROWSER_USE_LOGGING_LEVEL = "result"
