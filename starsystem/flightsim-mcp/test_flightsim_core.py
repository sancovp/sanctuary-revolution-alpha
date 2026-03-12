#!/usr/bin/env python3
"""
Test FlightSim core functions without MCP wrapper

Run this test after installing flightsim-mcp package:
cd /home/GOD/flightsim_mcp && pip install -e .
"""

import os
import json

# Set HEAVEN_DATA_DIR for testing
os.environ['HEAVEN_DATA_DIR'] = '/tmp/heaven_data'

from flightsim_mcp.flightsim_core import (
    add_flightsim,
    list_flightsims,
    get_flightsim,
    generate_mission_brief
)

def create_test_heaven_prompt_step():
    """Create a test HEAVEN prompt step for testing."""
    return {
        "name": "test_mission",
        "blocks": [
            {
                "type": "freestyle",
                "content": "Mission context: {mission_context}\nTarget: {target}\n\nExecute systematically!"
            }
        ]
    }

def test_add_flightsim():
    """Test adding a FlightSim model."""
    print("1. Testing add_flightsim()")
    
    heaven_prompt_step = create_test_heaven_prompt_step()
    
    result = add_flightsim(
        name="test_blog_sim",
        flight_config_name="blog_creation_workflow",
        heaven_prompt_step_data=heaven_prompt_step,
        description="Test FlightSim for blog creation",
        category="testing"
    )
    
    print(f"add_flightsim result: {result}")
    return result

def test_list_flightsims():
    """Test listing all FlightSims."""
    print("2. Testing list_flightsims()")
    
    flightsims = list_flightsims()
    print(f"list_flightsims result: {json.dumps(flightsims, indent=2)}")
    return flightsims

def test_get_flightsim():
    """Test getting a specific FlightSim."""
    print("3. Testing get_flightsim()")
    
    flightsim = get_flightsim("test_blog_sim")
    print(f"get_flightsim result: {json.dumps(flightsim, indent=2)}")
    return flightsim

def test_generate_mission_brief():
    """Test generating a mission brief."""
    print("4. Testing generate_mission_brief()")
    
    mission_result = generate_mission_brief(
        flightsim_name="test_blog_sim",
        mission_context="Create technical blog about STARSYSTEM",
        target="developers"
    )
    
    print(f"generate_mission_brief result: {json.dumps(mission_result, indent=2)}")
    return mission_result

def test_mission_file_content(mission_result):
    """Test reading the generated mission file content."""
    if "mission_file" not in mission_result:
        print("No mission file in result")
        return
        
    print(f"5. Checking generated mission file: {mission_result['mission_file']}")
    
    try:
        with open(mission_result['mission_file'], 'r') as f:
            mission_content = f.read()
        
        print("Mission file content:")
        print("-" * 30)
        print(mission_content)
        print("-" * 30)
        
    except Exception as e:
        print(f"Error reading mission file: {e}", exc_info=True)

def test_flightsim_core():
    """Run all FlightSim core tests."""
    print("🧪 Testing FlightSim Core Functions")
    print("=" * 50)
    
    # Run tests in sequence
    test_add_flightsim()
    print()
    
    test_list_flightsims()
    print()
    
    test_get_flightsim()
    print()
    
    mission_result = test_generate_mission_brief()
    print()
    
    test_mission_file_content(mission_result)
    
    print("\n✅ FlightSim core test complete!")

if __name__ == "__main__":
    test_flightsim_core()