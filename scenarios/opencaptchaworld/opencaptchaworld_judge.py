import argparse
import contextlib
import uvicorn
import asyncio
import logging
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, FileResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    TaskState,
    Part,
    TextPart,
)
from a2a.utils import (
    new_agent_text_message
)

from agentbeats.green_executor import GreenAgent, GreenExecutor
from agentbeats.models import EvalRequest, EvalResult
from agentbeats.tool_provider import ToolProvider
from agentbeats.client import create_message, send_message, merge_parts

from opencaptchaworld_judge_common import (
    OpenCaptchaPuzzle,
    OpenCaptchaAttempt,
    TypeMetrics,
    OpenCaptchaEval,
    opencaptchaworld_judge_agent_card
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opencaptchaworld_judge")


# Base paths
ASSETS_DIR = Path(__file__).parent.parent.parent / 'assets' / 'opencaptchaworld'
DATA_DIR = ASSETS_DIR / 'data'
TEMPLATES_DIR = ASSETS_DIR / 'templates'
STATIC_DIR = ASSETS_DIR / 'static'


def load_ground_truth(captcha_type: str) -> dict:
    """Load ground truth data for a specific type."""
    path = DATA_DIR / captcha_type / 'ground_truth.json'
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading ground truth for {captcha_type}: {e}")
        return {}


def get_captcha_types() -> list[str]:
    """Get available CAPTCHA types."""
    if not DATA_DIR.exists():
        return []
    return [d.name for d in DATA_DIR.iterdir() if d.is_dir()]


async def api_get_puzzle(request):
    """API endpoint to get puzzle data."""
    puzzle_type = request.query_params.get('type')
    selected_puzzle = request.query_params.get('id')
    
    if not puzzle_type:
        return JSONResponse({'error': 'type parameter is required'}, status_code=400)
    
    if not selected_puzzle:
        return JSONResponse({'error': 'id parameter is required'}, status_code=400)
    
    # Check if puzzle type exists
    captcha_types = get_captcha_types()
    if puzzle_type not in captcha_types:
        return JSONResponse({'error': f'Invalid puzzle type: {puzzle_type}'}, status_code=400)
    
    # Load ground truth for the selected type
    ground_truth = load_ground_truth(puzzle_type)
    if not ground_truth:
        return JSONResponse({'error': f'No puzzles found for type: {puzzle_type}'}, status_code=404)
    
    # Check if puzzle exists
    if selected_puzzle not in ground_truth:
        return JSONResponse({'error': f'Puzzle not found: {selected_puzzle}'}, status_code=404)
    
    puzzle_data = ground_truth[selected_puzzle]
    
    # Get prompt based on puzzle type (simplified from app2.py)
    prompt = puzzle_data.get('prompt', 'Solve the CAPTCHA puzzle')
    
    # Determine input type
    input_type_map = {
        'Dice_Count': 'number',
        'Geometry_Click': 'click',
        'Rotation_Match': 'rotation',
        'Slide_Puzzle': 'slide',
        'Unusual_Detection': 'multiselect',
        'Image_Recognition': 'image_grid',
        'Bingo': 'bingo_swap',
        'Image_Matching': 'image_matching',
        'Patch_Select': 'patch_select',
        'Dart_Count': 'dart_count',
        'Object_Match': 'object_match',
        'Select_Animal': 'select_animal',
        'Coordinates': 'image_matching',
        'Path_Finder': 'image_matching',
        'Place_Dot': 'place_dot',
        'Connect_icon': 'connect_icon',
        'Click_Order': 'click_order',
        'Hold_Button': 'hold_button',
        'Misleading_Click': 'click',
        'Pick_Area': 'click',
    }
    
    input_type = input_type_map.get(puzzle_type, 'text')
    
    response_data = {
        'puzzle_type': puzzle_type,
        'image_path': f'/captcha_data/{puzzle_type}/{selected_puzzle}',
        'puzzle_id': selected_puzzle,
        'prompt': prompt,
        'input_type': input_type,
    }
    
    # Add additional data for specific puzzle types (simplified)
    if puzzle_type == 'Rotation_Match':
        response_data.update({
            'reference_image': f'/captcha_data/{puzzle_type}/{puzzle_data.get("reference_image")}',
            'object_image': f'/captcha_data/{puzzle_type}/{os.path.splitext(puzzle_data.get("object_base_image", ""))[0]}_0.png',
            'object_base': os.path.splitext(puzzle_data.get("object_base_image", ""))[0],
            'current_angle': 0
        })
    elif puzzle_type == 'Slide_Puzzle':
        component_image = puzzle_data.get('component_image')
        if not component_image:
            logger.error(f"Slide puzzle missing component image: {puzzle_type}/{selected_puzzle}")
            return JSONResponse({'error': f'Invalid slide puzzle data: {selected_puzzle}'}, status_code=500)
        response_data.update({
            'component_image': f'/captcha_data/{puzzle_type}/{component_image}',
            'background_image': f'/captcha_data/{puzzle_type}/{selected_puzzle}',
        })
    elif puzzle_type == 'Image_Recognition':
        images = puzzle_data.get('images', [])
        subfolder = puzzle_data.get('subfolder', selected_puzzle)
        response_data.update({
            'images': [f'/captcha_data/{puzzle_type}/{subfolder}/{img}' for img in images],
            'grid_size': [3, 3],
            'question': puzzle_data.get('question', 'Select matching images')
        })
    elif puzzle_type in ['Unusual_Detection', 'Patch_Select', 'Select_Animal']:
        response_data['grid_size'] = puzzle_data.get('grid_size', [2, 3])
    elif puzzle_type in ['Image_Matching', 'Dart_Count', 'Object_Match', 'Coordinates', 'Path_Finder', 'Connect_icon']:
        ref_img = puzzle_data.get('reference_image')
        options = puzzle_data.get('option_images', puzzle_data.get('options', []))
        response_data.update({
            'reference_image': f'/captcha_data/{puzzle_type}/{ref_img}',
            'option_images': [f'/captcha_data/{puzzle_type}/{img}' for img in options],
            'current_option_index': 0
        })
    elif puzzle_type == 'Click_Order':
        response_data['order_image'] = f'/captcha_data/{puzzle_type}/{puzzle_data.get("order_image")}'
    elif puzzle_type == 'Hold_Button':
        response_data['hold_time'] = puzzle_data.get('hold_time', 3)
    
    return JSONResponse(response_data)


def _safe_path(*parts: str) -> Path | None:
    """Resolve a path and ensure it stays within the dataset directory."""
    base = DATA_DIR.resolve()
    candidate = (base / Path(*parts)).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate


async def serve_captcha_file(request):
    """Serve CAPTCHA image files."""
    captcha_type = request.path_params['captcha_type']
    filename = request.path_params['filename']
    file_path = _safe_path(captcha_type, filename)
    
    if file_path and file_path.exists():
        return FileResponse(file_path)
    return JSONResponse({'error': 'File not found'}, status_code=404)


async def serve_captcha_subdir_file(request):
    """Serve CAPTCHA image files from subdirectories."""
    captcha_type = request.path_params['captcha_type']
    subdir = request.path_params['subdir']
    filename = request.path_params['filename']
    file_path = _safe_path(captcha_type, subdir, filename)
    
    if file_path and file_path.exists():
        return FileResponse(file_path)
    return JSONResponse({'error': 'File not found'}, status_code=404)


async def api_get_types(request):
    """API endpoint to get available CAPTCHA types."""
    return JSONResponse({'types': get_captcha_types()})


async def api_list_puzzles(request):
    """API endpoint to list all puzzles for a given type."""
    captcha_type = request.query_params.get('type')
    
    if not captcha_type:
        return JSONResponse({'error': 'type parameter is required'}, status_code=400)
    
    captcha_types = get_captcha_types()
    if captcha_type not in captcha_types:
        return JSONResponse({'error': f'Invalid puzzle type: {captcha_type}'}, status_code=400)
    
    ground_truth = load_ground_truth(captcha_type)
    if not ground_truth:
        return JSONResponse({'error': f'No puzzles found for type: {captcha_type}'}, status_code=404)
    
    return JSONResponse({
        'type': captcha_type,
        'puzzles': list(ground_truth.keys())
    })


async def serve_puzzle_page(request):
    """Serve the interactive puzzle page."""
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    return templates.TemplateResponse('index2.html', {'request': request})


def check_answer(puzzle_type: str, puzzle_id: str, user_answer, ground_truth_data: dict) -> tuple[bool, any]:
    """
    Check if the user's answer is correct.
    Ported from reference_app.py check_answer logic.
    """
    if puzzle_type == 'Dice_Count':
        correct_answer = ground_truth_data.get('sum')
        try:
            is_correct = int(user_answer) == int(correct_answer)
            return is_correct, correct_answer
        except (ValueError, TypeError):
            return False, correct_answer
    
    elif puzzle_type == 'Geometry_Click':
        correct_answer = ground_truth_data.get('answer')
        try:
            user_x, user_y = user_answer
            if isinstance(correct_answer, dict) and 'area' in correct_answer:
                top_left, bottom_right = correct_answer['area']
                min_x, min_y = top_left
                max_x, max_y = bottom_right
                is_correct = (min_x <= user_x <= max_x) and (min_y <= user_y <= max_y)
                return is_correct, correct_answer
            else:
                # Fallback to distance calculation
                correct_x, correct_y = correct_answer
                tolerance = 25
                distance = ((user_x - correct_x) ** 2 + (user_y - correct_y) ** 2) ** 0.5
                is_correct = distance <= tolerance
                return is_correct, correct_answer
        except (ValueError, TypeError, KeyError):
            return False, correct_answer
    
    elif puzzle_type == 'Rotation_Match':
        correct_angle = ground_truth_data.get('correct_angle')
        try:
            user_angle = int(user_answer)
            is_correct = user_angle % 360 == correct_angle % 360
            return is_correct, correct_angle
        except (ValueError, TypeError):
            return False, correct_angle
    
    elif puzzle_type == 'Slide_Puzzle':
        target_position = ground_truth_data.get('target_position')
        tolerance = ground_truth_data.get('tolerance', 10)
        try:
            user_x, user_y = user_answer
            target_x, target_y = target_position
            distance = ((user_x - target_x) ** 2 + (user_y - target_y) ** 2) ** 0.5
            is_correct = distance <= tolerance
            return is_correct, target_position
        except (ValueError, TypeError):
            return False, target_position
    
    elif puzzle_type in ['Unusual_Detection', 'Patch_Select', 'Select_Animal']:
        correct_cells = ground_truth_data.get('correct_patches', ground_truth_data.get('answer', []))
        try:
            logger.info(f"Checking {puzzle_type}: user_answer={user_answer} (type={type(user_answer)}), correct_cells={correct_cells} (type={type(correct_cells)})")
            is_correct = set(user_answer) == set(correct_cells)
            logger.info(f"Result: {is_correct}")
            return is_correct, correct_cells
        except (ValueError, TypeError) as e:
            logger.error(f"Error comparing answers for {puzzle_type}: {e}")
            return False, correct_cells
    
    elif puzzle_type == 'Image_Recognition':
        correct_selections = ground_truth_data.get('correct_selections', [])
        try:
            is_correct = set(user_answer) == set(correct_selections)
            return is_correct, correct_selections
        except (ValueError, TypeError):
            return False, correct_selections
    
    elif puzzle_type == 'Bingo':
        correct_swaps = ground_truth_data.get('answer', [])
        try:
            is_correct = False
            for correct_swap in correct_swaps:
                if set(user_answer) == set(correct_swap):
                    is_correct = True
                    break
            return is_correct, correct_swaps
        except (ValueError, TypeError):
            return False, correct_swaps
    
    elif puzzle_type in ['Image_Matching', 'Dart_Count', 'Object_Match', 'Coordinates']:
        correct_index = ground_truth_data.get('correct_option_index')
        try:
            user_index = int(user_answer)
            is_correct = user_index == correct_index
            return is_correct, correct_index
        except (ValueError, TypeError):
            return False, correct_index
    
    elif puzzle_type in ['Path_Finder', 'Connect_icon']:
        correct_option = ground_truth_data.get('correct_option')
        try:
            user_index = int(user_answer)
            is_correct = user_index == correct_option
            return is_correct, correct_option
        except (ValueError, TypeError):
            return False, correct_option
    
    elif puzzle_type == 'Place_Dot':
        target_position = ground_truth_data.get('target_position')
        tolerance = ground_truth_data.get('tolerance', 15)
        try:
            user_x, user_y = user_answer
            target_x, target_y = target_position
            distance = ((user_x - target_x) ** 2 + (user_y - target_y) ** 2) ** 0.5
            is_correct = distance <= tolerance
            return is_correct, target_position
        except (ValueError, TypeError, KeyError):
            return False, target_position
    
    elif puzzle_type == 'Click_Order':
        correct_positions = ground_truth_data.get('answer', [])
        tolerance = ground_truth_data.get('tolerance', 20)
        try:
            if len(user_answer) != len(correct_positions):
                return False, correct_positions
            
            is_correct = True
            for user_pos, correct_pos in zip(user_answer, correct_positions):
                user_x, user_y = user_pos
                correct_x, correct_y = correct_pos
                distance = ((user_x - correct_x) ** 2 + (user_y - correct_y) ** 2) ** 0.5
                if distance > tolerance:
                    is_correct = False
                    break
            return is_correct, correct_positions
        except (ValueError, TypeError, KeyError):
            return False, correct_positions
    
    elif puzzle_type == 'Hold_Button':
        hold_time = ground_truth_data.get('hold_time', 3)
        try:
            user_hold_time = float(user_answer)
            is_correct = user_hold_time >= hold_time
            return is_correct, hold_time
        except (ValueError, TypeError):
            return False, hold_time
    
    elif puzzle_type == 'Misleading_Click':
        avoid_area = ground_truth_data.get('avoid_area', {"x": 0, "y": 0, "width": 0, "height": 0})
        try:
            user_x, user_y = user_answer
            area_x = avoid_area["x"]
            area_y = avoid_area["y"]
            area_width = avoid_area["width"]
            area_height = avoid_area["height"]
            
            is_inside_avoid_area = (
                area_x <= user_x <= area_x + area_width and 
                area_y <= user_y <= area_y + area_height
            )
            is_correct = not is_inside_avoid_area
            return is_correct, avoid_area
        except (ValueError, TypeError, KeyError):
            return False, avoid_area
    
    elif puzzle_type == 'Pick_Area':
        correct_answer = ground_truth_data.get('answer')
        try:
            user_x, user_y = user_answer
            if isinstance(correct_answer, dict) and 'area' in correct_answer:
                top_left, bottom_right = correct_answer['area']
                min_x, min_y = top_left
                max_x, max_y = bottom_right
                is_correct = (min_x <= user_x <= max_x) and (min_y <= user_y <= max_y)
                return is_correct, correct_answer
            return False, correct_answer
        except (ValueError, TypeError, KeyError):
            return False, correct_answer
    
    # Default fallback
    correct_answer = ground_truth_data.get('answer')
    try:
        user_str = str(user_answer).lower()
        correct_str = str(correct_answer).lower()
        is_correct = user_str == correct_str
        logger.info(f"Default check for {puzzle_type}: user='{user_str}' vs correct='{correct_str}' => {is_correct}")
        return is_correct, correct_answer
    except Exception as e:
        logger.error(f"Error in default check for {puzzle_type}: {e}")
        return False, correct_answer


class OpenCaptchaWorldJudge(GreenAgent):
    def __init__(self, host: str, port: int):
        self._required_roles = ["opencaptcha_solver"]
        self._required_config_keys = []
        self._tool_provider = ToolProvider()
        self._host = host
        self._port = port

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        missing_roles = set(self._required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing roles: {missing_roles}"
        return True, "ok"

    async def run_eval(self, req: EvalRequest, updater: TaskUpdater) -> None:
        logger.info(f"Starting OpenCaptchaWorld evaluation: {req}")

        try:
            # Get puzzle types to test
            config_types = req.config.get("puzzle_types", [])
            if config_types:
                puzzle_types = config_types
            else:
                puzzle_types = get_captcha_types()
            
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(f"Testing {len(puzzle_types)} puzzle types")
            )
            logger.info(f"Testing puzzle types: {puzzle_types}")

            # Evaluate puzzles
            all_attempts = []
            type_metrics_list = []
            solver_url = str(req.participants["opencaptcha_solver"])
            previous_feedback = None  # Track feedback across all puzzle types

            for puzzle_type in puzzle_types:
                ground_truth = load_ground_truth(puzzle_type)
                if not ground_truth:
                    logger.warning(f"No ground truth found for {puzzle_type}")
                    continue
                
                puzzle_ids = list(ground_truth.keys())
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(f"Testing {puzzle_type}: {len(puzzle_ids)} puzzles")
                )
                
                type_attempts = []
                type_correct = 0
                type_total_time = 0.0

                for i, puzzle_id in enumerate(puzzle_ids):
                    # Create puzzle URL
                    puzzle_url = f"http://{self._host}:{self._port}/get_puzzle?type={puzzle_type}&id={puzzle_id}"

                    # Send to solver with previous feedback merged
                    attempt, feedback = await self.evaluate_puzzle(
                        puzzle_url, puzzle_type, puzzle_id,
                        ground_truth[puzzle_id], solver_url, previous_feedback
                    )

                    type_attempts.append(attempt)
                    all_attempts.append(attempt)

                    if attempt.correct:
                        type_correct += 1
                    type_total_time += attempt.elapsed_time

                    status = "✓" if attempt.correct else "✗"
                    logger.info(f"{status} {puzzle_type}/{puzzle_id}")

                    # Store feedback for next iteration
                    previous_feedback = feedback

                    # Update progress periodically
                    if (i + 1) % 5 == 0 or (i + 1) == len(puzzle_ids):
                        await updater.update_status(
                            TaskState.working,
                            new_agent_text_message(
                                f"{puzzle_type}: {i + 1}/{len(puzzle_ids)} - {type_correct} correct"
                            )
                        )

                # Calculate type metrics
                type_accuracy = (type_correct / len(type_attempts)) * 100 if type_attempts else 0
                type_avg_time = type_total_time / len(type_attempts) if type_attempts else 0
                
                type_metrics = TypeMetrics(
                    puzzle_type=puzzle_type,
                    total_attempts=len(type_attempts),
                    correct_predictions=type_correct,
                    accuracy=type_accuracy,
                    average_solve_time=type_avg_time
                )
                type_metrics_list.append(type_metrics)
                
                logger.info(f"{puzzle_type} metrics: {type_accuracy:.1f}% ({type_correct}/{len(type_attempts)})")

            # Send final feedback after all puzzle types are evaluated
            # Send if we have attempts (even if previous_feedback is None due to errors)
            if all_attempts:
                await self._send_final_feedback(previous_feedback, solver_url, all_attempts)

            # Calculate overall metrics
            total_correct = sum(1 for a in all_attempts if a.correct)
            overall_accuracy = (total_correct / len(all_attempts)) * 100 if all_attempts else 0
            overall_avg_time = sum(a.elapsed_time for a in all_attempts) / len(all_attempts) if all_attempts else 0

            eval_result = OpenCaptchaEval(
                total_attempts=len(all_attempts),
                correct_predictions=total_correct,
                overall_accuracy=overall_accuracy,
                average_solve_time=overall_avg_time,
                type_metrics=type_metrics_list,
                attempts=all_attempts
            )

            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    f"Evaluation complete! Overall: {overall_accuracy:.1f}% ({total_correct}/{len(all_attempts)})"
                )
            )
            logger.info(f"OpenCaptchaWorld Evaluation:\n{eval_result.model_dump_json(indent=2)}")

            # Create result
            result = EvalResult(
                winner="opencaptcha_solver" if overall_accuracy >= 50 else "baseline",
                detail=eval_result.model_dump()
            )

            # Create detailed summary
            summary = f"""OpenCaptchaWorld Benchmark Results
===================================
Total Attempts: {eval_result.total_attempts}
Correct: {eval_result.correct_predictions}
Overall Accuracy: {eval_result.overall_accuracy:.2f}%
Average Solve Time: {eval_result.average_solve_time:.2f}s

Per-Type Results:
"""
            for tm in eval_result.type_metrics:
                summary += f"\n{tm.puzzle_type}: {tm.accuracy:.1f}% ({tm.correct_predictions}/{tm.total_attempts}) - avg {tm.average_solve_time:.2f}s"

            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=summary)),
                    Part(root=TextPart(text=result.model_dump_json(indent=2))),
                ],
                name="Result",
            )
        finally:
            self._tool_provider.reset()

    def _validate_solver_response(self, response_text: str, puzzle_type: str, puzzle_id: str) -> tuple[bool, dict | None, str | None]:
        """
        Validate and parse solver's JSON response.

        Args:
            response_text: Raw text response from solver
            puzzle_type: Expected puzzle type
            puzzle_id: Expected puzzle ID

        Returns:
            Tuple of (is_valid, parsed_data, error_message)
            - is_valid: True if response is valid JSON with all required fields
            - parsed_data: Parsed JSON dict if valid, None otherwise
            - error_message: Error description if invalid, None otherwise
        """
        # Step 1: Parse JSON
        try:
            result_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON format: {str(e)}"

        # Step 2: Validate it's a dictionary
        if not isinstance(result_data, dict):
            return False, None, f"Response must be a JSON object, got {type(result_data).__name__}"

        # Step 3: Validate required fields exist
        required_fields = ['puzzle_type', 'puzzle_id', 'answer', 'elapsed_time', 'timestamp']
        missing_fields = [field for field in required_fields if field not in result_data]

        if missing_fields:
            return False, None, f"Missing required fields: {', '.join(missing_fields)}"

        # Step 4: Validate field types (basic type checking)
        if not isinstance(result_data.get('puzzle_type'), str):
            return False, None, "Field 'puzzle_type' must be a string"

        if not isinstance(result_data.get('puzzle_id'), str):
            return False, None, "Field 'puzzle_id' must be a string"

        if not isinstance(result_data.get('elapsed_time'), (int, float)):
            return False, None, "Field 'elapsed_time' must be a number"

        if not isinstance(result_data.get('timestamp'), str):
            return False, None, "Field 'timestamp' must be a string"

        # Step 5: Validate puzzle_type and puzzle_id match expectations
        if result_data['puzzle_type'] != puzzle_type:
            return False, None, f"Puzzle type mismatch: expected '{puzzle_type}', got '{result_data['puzzle_type']}'"

        if result_data['puzzle_id'] != puzzle_id:
            return False, None, f"Puzzle ID mismatch: expected '{puzzle_id}', got '{result_data['puzzle_id']}'"

        return True, result_data, None

    def _generate_feedback(
        self,
        status: str,
        puzzle_type: str,
        puzzle_id: str,
        error_message: str | None = None
    ) -> str:
        """
        Generate feedback message for the solver.

        Args:
            status: Feedback status identifier ("success", "invalid", "error")
            puzzle_type: The puzzle type
            puzzle_id: The puzzle ID
            error_message: Optional error/diagnostic message

        Returns:
            Formatted feedback string
        """
        header = f"Puzzle {puzzle_type}/{puzzle_id}"

        if status == "success":
            return f"✓ Submission accepted. {header} evaluated."

        if status == "invalid":
            details = f"Details: {error_message}" if error_message else "Please ensure your response matches the expected schema."
            feedback = (
                f"✗ We couldn't parse your answer for {header}.\n"
                f"{details}\n\n"
                "We've recorded this attempt as incorrect so we can keep moving forward.\n"
                "For the next puzzle, please send the JSON content exactly as downloaded:\n"
                "{\n"
                '  "puzzle_type": "string",\n'
                '  "puzzle_id": "string",\n'
                '  "answer": <any>,\n'
                '  "elapsed_time": <number>,\n'
                '  "timestamp": "string"\n'
                "}"
            )
            return feedback

        details = f"Details: {error_message}" if error_message else ""
        return (
            f"⚠️ We hit an error while processing {header}. "
            "To keep the evaluation on track we've marked this attempt as incorrect and will continue. "
            f"{details}".strip()
        )

    def _create_instruction_message(self, puzzle_url: str, puzzle_type: str, puzzle_id: str) -> str:
        """
        Create detailed instruction message for the solver.

        Args:
            puzzle_url: The puzzle URL
            puzzle_type: The puzzle type
            puzzle_id: The puzzle ID

        Returns:
            Formatted instruction string
        """
        instruction = f"""Open the URL below in a browser and solve the CAPTCHA puzzle (Type: {puzzle_type}, ID: {puzzle_id}):

{puzzle_url}

Instructions:
1. Open the URL in a browser
2. Follow the instructions shown on the page to resolve the puzzle
3. Click the "Download Result" button to get your answer (in a json file)
4. Send back the content of the json file in plain text without modification

The expected JSON format is:
{{
  "puzzle_type": "string",
  "puzzle_id": "string",
  "answer": <any>,
  "elapsed_time": <number>,
  "timestamp": "string"
}}"""
        return instruction

    async def _send_final_feedback(self, feedback_text: str | None, solver_url: str, all_attempts: list) -> None:
        """
        Send final feedback message with session summary to the solver (fire-and-forget).

        Args:
            feedback_text: The feedback message for the last puzzle (None if no puzzles completed)
            solver_url: The solver's A2A endpoint
            all_attempts: List of all puzzle attempts in this session
        """
        try:
            # Calculate session statistics
            total_puzzles = len(all_attempts)
            successful_submissions = sum(1 for a in all_attempts if a.user_answer is not None)
            submission_rate = (successful_submissions / total_puzzles * 100) if total_puzzles > 0 else 0

            # Build session summary
            session_summary = (
                f"{'='*60}\n"
                f"SESSION SUMMARY\n"
                f"{'='*60}\n"
                f"Total puzzles evaluated: {total_puzzles}\n"
                f"Successful submissions: {successful_submissions}/{total_puzzles} ({submission_rate:.1f}%)\n\n"
                f"Note: The submission rate reflects successfully parsed responses without\n"
                f"format or network errors. This is different from accuracy, which measures\n"
                f"correctness of answers.\n"
                f"{'='*60}\n"
                f"Thank you for participating in this evaluation session!"
            )

            # Prepend last puzzle feedback if available
            if feedback_text:
                summary = f"{feedback_text}\n\n{session_summary}"
            else:
                summary = session_summary

            logger.info(f"Sending final feedback with summary to solver")

            import httpx
            from a2a.client import A2ACardResolver, ClientConfig, ClientFactory

            async with httpx.AsyncClient(timeout=30) as httpx_client:
                resolver = A2ACardResolver(httpx_client=httpx_client, base_url=solver_url)
                agent_card = await resolver.get_agent_card()
                config = ClientConfig(httpx_client=httpx_client, streaming=False)
                factory = ClientFactory(config)
                client = factory.create(agent_card)

                feedback_message = create_message(text=summary, context_id=None)

                # Send and consume events but don't process response
                async for _ in client.send_message(feedback_message):
                    pass

            logger.info("Final feedback sent successfully")

        except Exception as e:
            # Don't fail the evaluation if feedback sending fails
            logger.warning(f"Failed to send final feedback to solver: {e}")

    async def evaluate_puzzle(self, puzzle_url: str, puzzle_type: str, puzzle_id: str,
                             ground_truth_data: dict, solver_url: str,
                             previous_feedback: str | None = None) -> tuple[OpenCaptchaAttempt, str]:
        """
        Evaluate a single puzzle.

        Args:
            puzzle_url: The puzzle URL
            puzzle_type: The puzzle type
            puzzle_id: The puzzle ID
            ground_truth_data: Ground truth data for this puzzle
            solver_url: The solver's A2A endpoint
            previous_feedback: Optional feedback from previous puzzle to prepend

        Returns:
            Tuple of (attempt, feedback) where feedback is for this puzzle
        """
        # Create instruction message
        instruction_text = self._create_instruction_message(puzzle_url, puzzle_type, puzzle_id)

        # Prepend previous feedback if provided
        if previous_feedback:
            full_message = f"{previous_feedback}\n\n---\n\n{instruction_text}"
        else:
            full_message = instruction_text

        message = create_message(text=full_message, context_id=None)

        logger.info(f"Sending puzzle to solver: {puzzle_type}/{puzzle_id}")

        try:
            import httpx
            from a2a.client import A2ACardResolver, ClientConfig, ClientFactory

            async with httpx.AsyncClient(timeout=300) as httpx_client:
                resolver = A2ACardResolver(httpx_client=httpx_client, base_url=solver_url)
                agent_card = await resolver.get_agent_card()
                config = ClientConfig(httpx_client=httpx_client, streaming=False)
                factory = ClientFactory(config)
                client = factory.create(agent_card)

                response_text = ""
                async for event in client.send_message(message):
                    if isinstance(event, tuple) and len(event) == 2:
                        task, status_event = event
                        if task and hasattr(task, 'artifacts') and task.artifacts:
                            for artifact in task.artifacts:
                                if hasattr(artifact, 'parts') and artifact.parts:
                                    response_text = merge_parts(artifact.parts).strip()
                                    break
                        elif task and hasattr(task, 'status') and task.status.message:
                            response_text = merge_parts(task.status.message.parts).strip()
                    elif hasattr(event, 'parts'):
                        response_text = merge_parts(event.parts).strip()

                # Validate and parse JSON response
                logger.info(f"Raw response from solver: {response_text[:200]}...")

                is_valid, result_data, error_msg = self._validate_solver_response(
                    response_text, puzzle_type, puzzle_id
                )

                if not is_valid:
                    logger.error(f"Invalid response for {puzzle_id}: {error_msg}")
                    # Generate error feedback
                    feedback = self._generate_feedback("invalid", puzzle_type, puzzle_id, error_msg)
                    # Mark as incorrect
                    user_answer = None
                    elapsed_time = 0.0
                else:
                    user_answer = result_data.get('answer')
                    elapsed_time = result_data.get('elapsed_time', 0.0)
                    logger.info(f"Parsed answer: {user_answer} (type: {type(user_answer)})")
                    # Generate success feedback
                    feedback = self._generate_feedback("success", puzzle_type, puzzle_id)

        except Exception as e:
            logger.error(f"Error getting solution for {puzzle_id}: {e}", exc_info=True)
            # Generate error feedback
            feedback = self._generate_feedback("error", puzzle_type, puzzle_id, f"Error processing response: {str(e)}")
            user_answer = None
            elapsed_time = 0.0

        # Check answer
        is_correct, correct_answer = check_answer(puzzle_type, puzzle_id, user_answer, ground_truth_data)

        attempt = OpenCaptchaAttempt(
            puzzle_type=puzzle_type,
            puzzle_id=puzzle_id,
            user_answer=user_answer,
            correct_answer=correct_answer,
            correct=is_correct,
            elapsed_time=elapsed_time
        )

        return attempt, feedback


async def main():
    parser = argparse.ArgumentParser(description="Run the A2A OpenCaptchaWorld judge.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=9010, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="External URL to provide in the agent card")
    parser.add_argument("--cloudflare-quick-tunnel", action="store_true", 
                       help="Use a Cloudflare quick tunnel")
    args = parser.parse_args()

    if args.cloudflare_quick_tunnel:
        from agentbeats.cloudflare import quick_tunnel
        agent_url_cm = quick_tunnel(f"http://{args.host}:{args.port}")
    else:
        agent_url_cm = contextlib.nullcontext(args.card_url or f"http://{args.host}:{args.port}/")

    async with agent_url_cm as agent_url:
        agent = OpenCaptchaWorldJudge(host=args.host, port=args.port)
        executor = GreenExecutor(agent)
        agent_card = opencaptchaworld_judge_agent_card("OpenCaptchaWorldJudge", agent_url)

        request_handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=InMemoryTaskStore(),
        )

        # Create A2A server
        a2a_server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )
        
        # Build the app and add puzzle server routes
        app = a2a_server.build()
        
        # Add puzzle server routes
        app.add_route('/get_puzzle', serve_puzzle_page)
        app.add_route('/api/get_puzzle', api_get_puzzle)
        app.add_route('/api/types', api_get_types)
        app.add_route('/api/list_puzzles', api_list_puzzles)
        app.add_route('/captcha_data/{captcha_type}/{filename:path}', serve_captcha_file)
        
        # Mount static files
        app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')
        
        logger.info(f"Starting OpenCaptchaWorld judge on {args.host}:{args.port}")
        logger.info(f"Puzzle server available at http://{args.host}:{args.port}/get_puzzle")
        
        uvicorn_config = uvicorn.Config(app, host=args.host, port=args.port)
        uvicorn_server = uvicorn.Server(uvicorn_config)
        await uvicorn_server.serve()

if __name__ == '__main__':
    asyncio.run(main())
