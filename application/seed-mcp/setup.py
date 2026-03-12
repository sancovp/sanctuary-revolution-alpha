from setuptools import setup, find_packages

setup(
    name="seed-mcp",
    version="0.1.1",
    license='GNOSYS Personal Builder License (GPBL) v1.0',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "seed_mcp": ["*.hpi"],
    },
    install_requires=[
        "fastmcp>=2.0.0",
        "pydantic>=2.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "requests>=2.31.0"
    ],
    entry_points={
        'console_scripts': [
            'seed-mcp-server=seed_mcp.seed_mcp:main',
        ],
    },
    python_requires=">=3.8",
)