from setuptools import setup, find_packages

setup(
    name="conversation-ingestion-mcp",
    version="0.1.1",
    description="Semi-automated OpenAI conversation ingestion system with tagging and bundling",
    author="Isaac Wostrel-Rubin",
    author_email="isaac@sanctuary.systems",
    license="GNOSYS Personal Builder License (GPBL) v1.0",
    packages=find_packages(),
    install_requires=[
        "fastmcp>=2.0.0"
    ],
    entry_points={
        "console_scripts": [
            "conversation-ingestion-server=conversation_ingestion_mcp.main:main"
        ]
    },
    python_requires=">=3.8"
)
