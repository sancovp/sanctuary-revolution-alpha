from setuptools import setup, find_packages

setup(
    name="starship-mcp",
    version="0.1.10",
    packages=find_packages(),
    install_requires=[
        "fastmcp",
        "starlog-mcp",  # For internal functions
    ],
    python_requires=">=3.8",
    author="Isaac",
    description="STARSHIP MCP - Experiential Captain Identity Bridge",
    entry_points={
        "console_scripts": [
            "starship-mcp=starship_mcp.starship_mcp:main",
        ],
    },
)