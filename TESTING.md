# Test Mode

This document explains how to use the `--test` mode for interactively solving and saving CAPTCHA puzzles.

## Running Test Mode

To run the application in test mode, use the `--test` flag with the `agentbeats-run` command. You need to provide a comma-separated list of puzzles you want to solve, in the format `type:id`.

### Example

```bash
uv run agentbeats-run scenarios/opencaptchaworld/scenario.toml --test "Dice_Count:dice1.png,Rotation_Match:image_1.png"
```

This command will:
1.  Start the puzzle server.
2.  Open a web browser with the first puzzle (`Dice_Count:dice1.png`).

## Solving Puzzles

In the browser, you will see the puzzle interface.

1.  **Solve the Puzzle**: Interact with the interface to solve the CAPTCHA.
2.  **Buttons**: Instead of the usual "Download Result" button, you will see four buttons: **Print**, **Next**, **Test**, and **Reset**.
3.  **Print**: Clicking this button saves your answer to a JSON file in the `scenarios/opencaptchaworld/output/<Puzzle_Type>/` directory and displays the ground truth and your output JSONs at the bottom of the page.
4.  **Next**: Clicking this button loads the next puzzle from the list you provided in the command.
5.  **Test**: Clicking this button will:
    *   Replace the ground truth file in `scenarios/opencaptchaworld/pseudo_purple_data` with your last saved output.
    *   Update `scenarios/opencaptchaworld/scenario.toml` to only test the current puzzle type.
    *   Run the `opencaptchaworld_solver.py` in `ground_truth` mode.
    *   The output of the script will be logged to the server console.
6.  **Reset**: Clicking this button will:
    *   Run the `extract_ground_truth.py` script to restore the original ground truth data.
    *   Reset `scenarios/opencaptchaworld/scenario.toml` to test all puzzle types.
    *   The output of the script will be logged to the server console.

This process continues until all puzzles in the list have been solved.

## JSON Display

When you click the "Print" button, two JSON objects will be displayed at the bottom of the page:

*   **Ground Truth**: This is the correct answer for the puzzle, loaded from the `scenarios/opencaptchaworld/pseudo_purple_data` directory.
*   **User Output**: This is the answer you submitted, which is saved to the `scenarios/opencaptchaworld/output` directory.

This allows you to compare your answer with the correct one immediately.

## Output JSON Format

The output JSON file for each puzzle will be saved with the following structure:

```json
{
  "puzzle_type": "Dice_Count",
  "puzzle_id": "dice1.png",
  "answer": 89,
  "elapsed_time": 0.5,
  "timestamp": "2025-11-23T22:35:57.750874"
}
```

- `puzzle_type`: The category of the CAPTCHA puzzle.
- `puzzle_id`: The unique identifier for the specific puzzle.
- `answer`: The solution you provided.
- `elapsed_time`: The time taken to solve the puzzle, in seconds.
- `timestamp`: The time when the puzzle was solved.