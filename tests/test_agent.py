"""A2A conformance tests for OpenCaptchaWorld judge agent."""

import json
import pytest
import httpx
from uuid import uuid4


@pytest.mark.asyncio
async def test_agent_card_accessible(agent_url):
    """Test that the agent card is accessible via the well-known endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{agent_url}/.well-known/agent-card.json")
        assert response.status_code == 200, f"Agent card endpoint returned {response.status_code}"

        card = response.json()
        assert "name" in card, "Agent card missing 'name' field"
        assert "skills" in card, "Agent card missing 'skills' field"
        assert "version" in card, "Agent card missing 'version' field"


@pytest.mark.asyncio
async def test_agent_card_structure(agent_url):
    """Test that the agent card has the correct structure."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{agent_url}/.well-known/agent-card.json")
        card = response.json()

        # Check basic fields
        assert card["name"] == "OpenCaptchaWorldJudge", "Incorrect agent name"
        assert len(card["skills"]) > 0, "Agent should have at least one skill"

        # Check first skill structure
        skill = card["skills"][0]
        assert "id" in skill, "Skill missing 'id' field"
        assert "name" in skill, "Skill missing 'name' field"
        assert "description" in skill, "Skill missing 'description' field"
        assert "examples" in skill, "Skill missing 'examples' field"
        assert len(skill["examples"]) > 0, "Skill should have at least one example"


@pytest.mark.asyncio
async def test_puzzle_server_accessible(agent_url):
    """Test that the puzzle server endpoints are accessible."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test API get types endpoint
        response = await client.get(f"{agent_url}/api/types")
        assert response.status_code == 200, f"Puzzle types endpoint returned {response.status_code}"

        types_data = response.json()
        assert "types" in types_data, "Response missing 'types' field"
        assert len(types_data["types"]) > 0, "Should have at least one puzzle type"


@pytest.mark.asyncio
async def test_puzzle_types_available(agent_url):
    """Test that all expected puzzle types are available."""
    expected_types = [
        "Dice_Count", "Geometry_Click", "Rotation_Match", "Slide_Puzzle",
        "Unusual_Detection", "Image_Recognition", "Bingo", "Image_Matching",
        "Patch_Select", "Dart_Count", "Object_Match", "Select_Animal",
        "Coordinates", "Path_Finder", "Place_Dot", "Connect_icon",
        "Click_Order", "Hold_Button", "Misleading_Click", "Pick_Area"
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{agent_url}/api/types")
        types_data = response.json()
        available_types = types_data["types"]

        # Check that we have all expected types
        assert len(available_types) == 20, f"Expected 20 puzzle types, got {len(available_types)}"

        for expected_type in expected_types:
            assert expected_type in available_types, f"Missing puzzle type: {expected_type}"


@pytest.mark.asyncio
async def test_list_puzzles_endpoint(agent_url):
    """Test that the list puzzles endpoint works for a specific type."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test with Dice_Count type
        response = await client.get(f"{agent_url}/api/list_puzzles?type=Dice_Count")
        assert response.status_code == 200, f"List puzzles endpoint returned {response.status_code}"

        data = response.json()
        assert "puzzles" in data, "Response missing 'puzzles' field"
        assert len(data["puzzles"]) > 0, "Should have at least one Dice_Count puzzle"


@pytest.mark.asyncio
async def test_get_puzzle_endpoint(agent_url):
    """Test that a specific puzzle can be retrieved."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First get the list of puzzles
        response = await client.get(f"{agent_url}/api/list_puzzles?type=Dice_Count")
        data = response.json()

        if data["puzzles"]:
            puzzle_id = data["puzzles"][0]

            # Now try to get the specific puzzle
            response = await client.get(
                f"{agent_url}/get_puzzle?type=Dice_Count&id={puzzle_id}"
            )
            assert response.status_code == 200, f"Get puzzle endpoint returned {response.status_code}"
            assert len(response.content) > 0, "Puzzle content should not be empty"


@pytest.mark.asyncio
async def test_a2a_protocol_supported(agent_url):
    """Test that the agent exposes A2A protocol capabilities."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check that agent card indicates A2A support
        response = await client.get(f"{agent_url}/.well-known/agent-card.json")
        card = response.json()

        # Verify agent has skills (indicating A2A capability)
        assert "skills" in card, "Agent should expose skills for A2A protocol"
        assert len(card["skills"]) > 0, "Agent should have at least one skill"

        # Verify skill has required fields
        skill = card["skills"][0]
        assert "id" in skill, "Skill should have ID"
        assert "examples" in skill, "Skill should have examples showing expected format"


@pytest.mark.asyncio
async def test_invalid_puzzle_type(agent_url):
    """Test that invalid puzzle types are handled gracefully."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{agent_url}/api/get_puzzle?type=Invalid&id=test")
        assert response.status_code == 400, "Should return 400 for invalid puzzle type"


@pytest.mark.asyncio
async def test_missing_puzzle_id(agent_url):
    """Test that missing puzzle ID is handled gracefully."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{agent_url}/api/get_puzzle?type=Dice_Count")
        assert response.status_code == 400, "Should return 400 when puzzle ID is missing"


@pytest.mark.asyncio
async def test_agent_health(agent_url):
    """Test that the agent is healthy and responding."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try to access the agent card as a health check
        response = await client.get(f"{agent_url}/.well-known/agent-card.json")
        assert response.status_code == 200, "Agent should be healthy and responding"

        # Verify response time is reasonable (< 5 seconds)
        assert response.elapsed.total_seconds() < 5.0, \
            f"Agent response too slow: {response.elapsed.total_seconds()}s"


@pytest.mark.asyncio
async def test_puzzle_count_consistency(agent_url):
    """Test that puzzle counts are consistent across endpoints."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get all puzzle types
        response = await client.get(f"{agent_url}/api/types")
        types_data = response.json()

        total_puzzles = 0
        for puzzle_type in types_data["types"]:
            # Get puzzles for each type
            response = await client.get(f"{agent_url}/api/list_puzzles?type={puzzle_type}")
            data = response.json()
            puzzle_count = len(data["puzzles"])
            total_puzzles += puzzle_count

            assert puzzle_count > 0, f"Puzzle type {puzzle_type} should have at least one puzzle"

        # Total should be 463 puzzles
        assert total_puzzles == 463, f"Expected 463 total puzzles, got {total_puzzles}"
