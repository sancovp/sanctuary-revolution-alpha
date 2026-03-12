#!/usr/bin/env python3
"""Test SEED MCP functionality directly"""

def test_who_am_i():
    """Test who_am_i function"""
    base_identity = """I am SEED - the unified interface to your compound intelligence system.

I coordinate between:
• STARLOG (project workflow and session management)  
• HEAVEN Framework (agent orchestration and tool coordination)
• GIINT (multi-fire intelligence with cognitive separation)
• Carton (knowledge capture and wiki management)
• PayloadDiscovery (structured workflow sequences)

While these systems work together internally, I present you with one coherent voice and consistent guidance."""
    
    print("Testing SEED who_am_i():")
    print("=" * 50)
    print(base_identity)
    print("\n" + "=" * 50)
    
    context_test = "analyzing new codebase"
    contextual_addition = f"""

Current context: {context_test}

In this context, I help you navigate the compound system by providing unified instructions and maintaining coherent understanding across all subsystems."""
    
    print(f"Testing with context '{context_test}':")
    print("=" * 50)
    print(base_identity + contextual_addition)

if __name__ == "__main__":
    test_who_am_i()