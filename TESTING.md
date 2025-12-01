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
2.  **Print & Next**: Instead of the usual "Download Result" button, you will see a **Print & Next** button.
3.  **Save Output**: Clicking this button saves your answer to a JSON file in the `scenarios/opencaptchaworld/output/<Puzzle_Type>/` directory.
4.  **Load Next Puzzle**: The interface will automatically load the next puzzle from the list you provided in the command.

This process continues until all puzzles in the list have been solved.

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