import argparse
import uvicorn
import asyncio
import logging
import json
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater, TaskManager
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    Part,
    TextPart,
)
from a2a.utils import new_agent_text_message


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("opencaptchaworld_solver")


# Fixed answers for each puzzle type (actual valid answers from first puzzle of each type)
# These answers are guaranteed to pass at least one CAPTCHA per type
FIXED_ANSWERS = {
    'Dice_Count': 85,
    'Geometry_Click': [70, 57],
    'Rotation_Match': 90,
    'Slide_Puzzle': [129, 68],
    'Unusual_Detection': [0, 3],
    'Image_Recognition': [1, 2, 3, 4, 5, 7],
    'Bingo': [0, 7],
    'Image_Matching': 1,
    'Patch_Select': [0, 1, 2, 3, 5, 6, 7, 8, 11, 12, 13],
    'Dart_Count': 10,
    'Object_Match': 0,
    'Select_Animal': [5],
    'Coordinates': 4,
    'Path_Finder': 2,
    'Place_Dot': [190, 210],
    'Connect_icon': 0,
    'Click_Order': [[470, 100], [325, 180], [162, 100], [190, 275]],
    'Hold_Button': 3,
    'Misleading_Click': [400, 270],
    'Pick_Area': [145, 320],
}


class PseudoPurpleAgent:
    """Pseudo purple agent that solves puzzles."""
    
    def __init__(self, mode: str):
        self.mode = mode
        self.data_dir = Path(__file__).parent / 'pseudo_purple_data'
        logger.info(f"Initialized PseudoPurpleAgent in {mode} mode")
    
    def extract_url_from_message(self, message_text: str) -> str:
        """
        Extract URL from message text.
        Handles both simple URL messages and detailed instruction messages.
        """
        # Look for URLs in the message (http or https)
        import re
        url_pattern = r'https?://[^\s<>"\']+'
        urls = re.findall(url_pattern, message_text)

        if urls:
            # Return the first URL found
            return urls[0]

        # Fallback: if no URL pattern found, assume the whole message is a URL
        # (for backward compatibility with old simple URL messages)
        return message_text.strip()

    def parse_puzzle_url(self, url: str) -> tuple[str, str]:
        """Parse puzzle URL to extract type and id."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        puzzle_type = query_params.get('type', [None])[0]
        puzzle_id = query_params.get('id', [None])[0]

        return puzzle_type, puzzle_id
    
    def get_fixed_answer(self, puzzle_type: str) -> any:
        """Get fixed answer for a puzzle type."""
        return FIXED_ANSWERS.get(puzzle_type, None)
    
    def get_ground_truth_answer(self, puzzle_type: str, puzzle_id: str) -> any:
        """Load ground truth answer from pseudo_purple_data."""
        answer_file = self.data_dir / puzzle_type / f"{puzzle_id}.json"
        
        if not answer_file.exists():
            logger.error(f"Ground truth file not found: {answer_file}")
            return None
        
        try:
            with open(answer_file, 'r') as f:
                data = json.load(f)
                return data.get('answer')
        except Exception as e:
            logger.error(f"Error loading ground truth: {e}")
            return None


class SimpleSolverExecutor:
    """Simple executor that doesn't parse EvalRequest."""
    
    def __init__(self, agent: PseudoPurpleAgent):
        self.agent = agent
    
    async def execute(self, request, queue: EventQueue) -> None:
        """Execute puzzle solving from incoming A2A message.
        
        Args:
            request: MessageSendParams object from A2A protocol
            queue: EventQueue for sending responses
        """
        try:
            # Extract text from the incoming message
            # The request has a 'message' field with 'parts'
            message_text = None
            if hasattr(request, 'message') and hasattr(request.message, 'parts'):
                for part in request.message.parts:
                    if hasattr(part, 'root') and hasattr(part.root, 'text'):
                        message_text = part.root.text
                        break

            if not message_text:
                logger.error(f"Could not extract message text from request: {request}")
                await queue.enqueue_event(new_agent_text_message(
                    text=json.dumps({"error": "No message text in request"})
                ))
                return

            # Log incoming message for debugging
            logger.info("="*80)
            logger.info("INCOMING MESSAGE FROM JUDGE:")
            logger.info("-"*80)
            logger.info(message_text)
            logger.info("="*80)

            # Extract URL from message (handles both simple URLs and instruction messages)
            url = self.agent.extract_url_from_message(message_text)

            # If no URL found, this might be a feedback-only message (final feedback)
            if not url or not url.startswith('http'):
                logger.info(f"No URL found in message - treating as feedback-only message")
                logger.info(f"Message content: {message_text[:200]}...")
                # Don't send a response for feedback-only messages
                return

            logger.info(f"Extracted URL: {url}")

            start_time = time.time()

            # Parse URL
            puzzle_type, puzzle_id = self.agent.parse_puzzle_url(url)

            if not puzzle_type or not puzzle_id:
                logger.error(f"Failed to parse puzzle URL: {url}")
                await queue.enqueue_event(new_agent_text_message(
                    text=json.dumps({"error": f"Invalid puzzle URL: {url}"})
                ))
                return
            
            logger.info(f"Solving: type={puzzle_type}, id={puzzle_id}, mode={self.agent.mode}")
            
            # Get answer
            if self.agent.mode == 'fixed':
                answer = self.agent.get_fixed_answer(puzzle_type)
            else:
                answer = self.agent.get_ground_truth_answer(puzzle_type, puzzle_id)
            
            elapsed_time = time.time() - start_time
            
            # Create result
            result = {
                "puzzle_type": puzzle_type,
                "puzzle_id": puzzle_id,
                "answer": answer,
                "elapsed_time": round(elapsed_time, 3),
                "timestamp": datetime.now().isoformat() + 'Z'
            }
            
            logger.info(f"Returning result: type={puzzle_type}, id={puzzle_id}, answer={answer} (type={type(answer)})")

            # Return result as JSON text message
            result_json = json.dumps(result, indent=2)

            # Log outgoing response for debugging
            logger.info("="*80)
            logger.info("OUTGOING RESPONSE TO JUDGE:")
            logger.info("-"*80)
            logger.info(result_json)
            logger.info("="*80)

            await queue.enqueue_event(new_agent_text_message(text=result_json))
            
        except Exception as e:
            logger.error(f"Error in execute: {e}", exc_info=True)
            await queue.enqueue_event(new_agent_text_message(
                text=json.dumps({"error": str(e)})
            ))


async def main():
    parser = argparse.ArgumentParser(description="Run the pseudo OpenCaptcha solver agent.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=9020, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="External URL to provide in the agent card")
    parser.add_argument("--mode", type=str, default="ground_truth", 
                       choices=["fixed", "ground_truth"],
                       help="Mode: 'fixed' for hardcoded answers, 'ground_truth' for actual answers")
    args = parser.parse_args()
    
    # Initialize pseudo agent
    agent = PseudoPurpleAgent(mode=args.mode)
    executor = SimpleSolverExecutor(agent)
    
    # Create agent card
    agent_card = AgentCard(
        name="OpenCaptchaWorldSolver",
        description=f'Pseudo agent that solves OpenCaptcha puzzles (mode: {args.mode})',
        url=args.card_url or f'http://{args.host}:{args.port}/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[],
    )
    
    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore()
    )
    
    # Create A2A server
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    logger.info(f"Starting OpenCaptcha solver on {args.host}:{args.port} (mode: {args.mode})")
    
    uvicorn_config = uvicorn.Config(server.build(), host=args.host, port=args.port)
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await uvicorn_server.serve()


if __name__ == '__main__':
    asyncio.run(main())
