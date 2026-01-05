# Agentified OpenCaptchaWorld Benchmark

Agent-based benchmark for interactive CAPTCHA solving using the A2A (Agent-to-Agent) protocol.

## Overview

This benchmark evaluates AI agents' ability to solve interactive visual CAPTCHA puzzles from the [OpenCaptchaWorld dataset](https://github.com/MetaAgentX/OpenCaptchaWorld). It tests 463 puzzles across 20 distinct types, each requiring different cognitive capabilities ranging from visual perception to spatial reasoning and interactive problem-solving.

The benchmark implements:
- **Green Agent (Judge)**: Embedded puzzle server with evaluation logic (port 9010)
- **Purple Agent (Solver)**: Baseline solver with two modes - *fixed mode* (naive baseline without vision/browser tools, ~13% accuracy) and *ground_truth mode* (verifies judge's evaluation logic, 100% accuracy)

Demo video:



https://github.com/user-attachments/assets/d84158dd-bc3c-4fac-ae99-d656d6404ce7



## Prerequisites

- **Python 3.13+**
- **Git LFS** (critical - 809MB puzzle data stored via LFS)
- **Docker** (for containerized deployment)

**Note:** No API keys required - the baseline solver runs in fixed mode (naive baseline) by default. Ground truth mode is available to verify the correctness of the judge's answer evaluation logic.

## Quick Start

### Option 1: Local Execution

```bash
# Install Git LFS
git lfs install

# Clone repository
git clone https://github.com/gmsh/agentified-opencaptchaworld.git
cd agentified-opencaptchaworld

# Pull LFS assets (809MB)
git lfs pull

# Install dependencies
uv sync

# Run benchmark
uv run agentbeats-run scenarios/opencaptchaworld/scenario.toml
```

### Option 2: Docker Execution (Recommended)

```bash
# Pull pre-built image
docker pull ghcr.io/gmsh/agentified-opencaptchaworld:latest
```

**Run Green Agent (Judge):**
```bash
# Start green agent on port 9010
docker run --network host ghcr.io/gmsh/agentified-opencaptchaworld:latest
# Green agent listens on http://localhost:9010
```

**Run Purple Agent (Solver):**
```bash
# In a separate terminal, start purple agent in fixed mode
docker run --network host --entrypoint uv ghcr.io/gmsh/agentified-opencaptchaworld:latest \
  run scenarios/opencaptchaworld/opencaptchaworld_solver.py \
  --host 0.0.0.0 --port 9020 --mode fixed
```

**Or Run Complete Scenario (Orchestrated):**
```bash
# Run both agents internally with automated evaluation
# Note: Uses the scenario.toml configuration baked into the Docker image
docker run --network host --entrypoint uv ghcr.io/gmsh/agentified-opencaptchaworld:latest \
  run python -m agentbeats.run_scenario scenarios/opencaptchaworld/scenario.toml
```

**Expected Output (when running purple agent in Fixed Mode):**
```
Starting opencaptcha_solver at 127.0.0.1:9020
Starting green agent at 127.0.0.1:9010
Waiting for 2 agent(s) to be ready...
  2/2 agents ready, waiting...

=== OpenCaptchaWorld Evaluation Results ===
Unusual_Detection: 6.7% (2/30)
Connect_icon: 20.0% (4/20)
Select_Animal: 16.7% (5/30)
Dice_Count: 5.0% (1/20)
Geometry_Click: 10.0% (2/20)
Rotation_Match: 12.5% (6/48)
[... all 20 puzzle types ...]
Overall Accuracy: 13.39% (62/463)
```

## Benchmark Details

### Puzzle Types

The benchmark includes 20 interactive puzzle types testing different cognitive capabilities:

**Visual Perception:**
- **Dice_Count**: Sum numbers shown on dice (20 puzzles)
- **Geometry_Click**: Click on specific geometric shapes (20 puzzles)
- **Image_Recognition**: Select images matching a description (20 puzzles)
- **Unusual_Detection**: Identify unusual items in a grid (30 puzzles)

**Spatial Reasoning:**
- **Rotation_Match**: Rotate object to match reference orientation (48 puzzles)
- **Slide_Puzzle**: Drag component to target position (31 puzzles)
- **Coordinates**: Move object to specified coordinates (18 puzzles)
- **Path_Finder**: Navigate to target position (10 puzzles)

**Pattern Matching:**
- **Bingo**: Swap positions to create matching lines (25 puzzles)
- **Image_Matching**: Match similar images (19 puzzles)
- **Patch_Select**: Select grid squares containing objects (20 puzzles)
- **Dart_Count**: Select image where darts sum to target (20 puzzles)
- **Object_Match**: Match number of objects to reference (20 puzzles)

**Interactive Logic:**
- **Select_Animal**: Identify specific animal in grid (30 puzzles)
- **Place_Dot**: Place dot at specific location (32 puzzles)
- **Connect_icon**: Connect matching icons (20 puzzles)
- **Click_Order**: Click items in specific sequence (20 puzzles)
- **Hold_Button**: Hold button for specified duration (10 puzzles)
- **Misleading_Click**: Click correct area, avoiding distractions (20 puzzles)
- **Pick_Area**: Select specific area in image (30 puzzles)

**Total**: 463 puzzles across 20 types

### Evaluation Metrics

- **Per-type accuracy**: Percentage of correctly solved puzzles for each type
- **Overall accuracy**: Percentage across all 463 puzzles
- **Results output**: Streamed to stdout in real-time

### Baseline Solver Modes

The included pseudo purple agent supports two modes:

**Fixed Mode** (default):
```bash
--mode fixed
```
- Returns same answer for all puzzles of each type
- Achieves ~13% accuracy (62/463 puzzles)
- Demonstrates naive baseline without vision models or browser automation tools

**Ground Truth Mode**:
```bash
--mode ground_truth
```
- Returns correct answers from pre-loaded metadata
- Achieves 100% accuracy (463/463 puzzles)
- Used to verify the correctness of the judge's answer evaluation logic

## Dataset Information

- **Location**: `assets/opencaptchaworld/`
- **Size**: 809MB (managed via Git LFS)
- **Structure**:
  - `data/`: 20 puzzle type directories with images and ground_truth.json
  - `templates/`: Jinja2 templates for interactive puzzle UI
  - `static/`: CSS/JavaScript for puzzle rendering
- **Source**: [MetaAgentX/OpenCaptchaWorld](https://github.com/MetaAgentX/OpenCaptchaWorld)


## Configuration

Edit `scenarios/opencaptchaworld/scenario.toml` to customize evaluation:

### Select Specific Puzzle Types

```toml
[config]
# Empty list tests all 20 types (463 puzzles)
puzzle_types = []

# Or test specific types:
# puzzle_types = ["Dice_Count", "Geometry_Click", "Image_Recognition"]
```

### Switch Solver Mode

```toml
[[participants]]
role = "opencaptcha_solver"
endpoint = "http://127.0.0.1:9020"
# Fixed mode (~13% accuracy):
cmd = "python3 scenarios/opencaptchaworld/opencaptchaworld_solver.py --host 0.0.0.0 --port 9020 --mode fixed"
# Ground truth mode (100% accuracy):
# cmd = "python3 scenarios/opencaptchaworld/opencaptchaworld_solver.py --host 0.0.0.0 --port 9020 --mode ground_truth"
```

## Project Structure

```
agentified-opencaptchaworld/
├── src/agentbeats/                     # A2A framework
│   ├── run_scenario.py                 # Scenario orchestration
│   ├── green_executor.py               # Base green agent executor
│   ├── client.py                       # A2A messaging
│   └── models.py                       # Evaluation models
│
├── scenarios/opencaptchaworld/         # Benchmark scenario
│   ├── opencaptchaworld_judge.py       # Green agent with puzzle server
│   ├── opencaptchaworld_solver.py      # Baseline purple agent
│   ├── opencaptchaworld_judge_common.py  # Shared models
│   ├── extract_ground_truth.py         # Ground truth extraction utility
│   ├── pseudo_purple_data/             # Pre-extracted answers
│   └── scenario.toml                   # Configuration
│
├── assets/opencaptchaworld/            # Puzzle data (809MB via Git LFS)
│   ├── data/                           # 20 puzzle types with images/JSON
│   ├── templates/                      # HTML templates for puzzle UI
│   └── static/                         # CSS/JavaScript assets
│
├── Dockerfile                          # Production Docker image
├── .dockerignore                       # Docker build exclusions
├── pyproject.toml                      # Project configuration
└── README.md                           # This file
```

## Development

### Running Agents Manually

For debugging, start agents in separate terminals:

```bash
# Terminal 1: Start green agent (judge with puzzle server)
python scenarios/opencaptchaworld/opencaptchaworld_judge.py --host 0.0.0.0 --port 9010

# Terminal 2: Start purple agent (baseline solver)
python scenarios/opencaptchaworld/opencaptchaworld_solver.py --host 0.0.0.0 --port 9020 --mode fixed

# Terminal 3: Run evaluation client
python -m agentbeats.client_cli scenarios/opencaptchaworld/scenario.toml

# Optional: View puzzle in browser
# http://localhost:9010/get_puzzle?type=Dice_Count&id=dice1.png
```

### Building Docker Image

If you want to build the Docker image locally instead of using the pre-built image:

```bash
# Ensure Git LFS files are downloaded first
git lfs pull

# Build the image
docker build -t agentified-opencaptchaworld:latest .

# Verify the build
docker run agentified-opencaptchaworld:latest --help
```

You can then use your locally built image by replacing `ghcr.io/gmsh/agentified-opencaptchaworld:latest` with `agentified-opencaptchaworld:latest` in the Docker commands.

### Extracting Ground Truth

Regenerate ground truth data for the pseudo agent:

```bash
python scenarios/opencaptchaworld/extract_ground_truth.py
```

This creates `scenarios/opencaptchaworld/pseudo_purple_data/` with answer files for each puzzle type.

### Implementing Your Own Solver

Replace the pseudo agent with a real solver that:
- Uses browser automation (Playwright, Selenium) to interact with puzzles
- Employs vision-enabled LLMs to analyze puzzle images
- Implements puzzle-specific solving strategies
- Handles different interaction types (clicks, swaps, rotations, etc.)

The solver must implement the A2A protocol and accept puzzle URLs via HTTP.

### Docker Interactive Debugging

For debugging the Docker container:

```bash
docker run -it --entrypoint /bin/bash agentified-opencaptchaworld:latest
```

## Troubleshooting

**Issue**: Git LFS files not downloaded (small placeholder files)
- **Solution**: Install Git LFS and pull files:
  ```bash
  git lfs install
  git lfs pull
  ```
- **Verification**: Check file sizes - images should be MB range, not bytes
  ```bash
  ls -lh assets/opencaptchaworld/data/Dice_Count/
  ```

**Issue**: `ImportError` or missing dependencies
- **Solution**: Run `uv sync` to install all dependencies

**Issue**: OpenCaptchaWorld shows 0% accuracy
- **Solution**: Ensure ground truth data exists:
  ```bash
  python scenarios/opencaptchaworld/extract_ground_truth.py
  ```

**Issue**: Connection errors or port conflicts
- **Solution**: Ensure ports 9010 and 9020 are not in use by other applications

**Issue**: Docker build fails
- **Solution**: Verify Git LFS files are present before building:
  ```bash
  git lfs pull
  ls -lh assets/opencaptchaworld/data/Dice_Count/dice1.png
  docker build --no-cache -t agentified-opencaptchaworld .
  ```

## Submission Components

This branch (agentbeats/submission-v1) is designed for submission to [AgentBeats](https://agentbeats.org):

1. **Abstract**: Brief description of 20 puzzle types and evaluation approach
2. **GitHub Repository**: Complete source code with README and Docker support
3. **Baseline Purple Agent**: Two modes (fixed: ~13% naive baseline, ground_truth: 100% for verification)
4. **Docker Image**: Fully automated green agent execution
5. **AgentBeats Registration**: Register green and baseline purple agents
6. **Demo Video on YouTube**: [https://www.youtube.com/watch?v=ZRC3U3HaJXo](https://www.youtube.com/watch?v=ZRC3U3HaJXo)

[![Watch the video](https://img.youtube.com/vi/ZRC3U3HaJXo/hqdefault.jpg)](https://www.youtube.com/watch?v=ZRC3U3HaJXo)

> [!NOTE]  
> For other source files that have not been submitted to AgentBeats yet (e.g., agentified OCR captcha), please refer to [the main branch](https://github.com/gmsh/agentified-opencaptchaworld/tree/main).

## References

- [A2A Protocol Documentation](https://a2a-protocol.org/latest/)
- [OpenCaptchaWorld Dataset](https://github.com/MetaAgentX/OpenCaptchaWorld)
- [AgentBeats Platform](https://agentbeats.org)

## License

MIT License - see LICENSE file for details

## Acknowledgments

This benchmark was built using the [Agentbeats framework](https://agentbeats.org). The original tutorial and multi-scenario demo can be found in the main branch (see `README.agentbeats.md` in earlier commits).
