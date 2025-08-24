#!/usr/bin/env python3
"""
Setup script for DepScan - Dependency Vulnerability Scanner
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dep-scan",  # Changed from "depscan" to "dep-scan" to match the command
    version="1.0.0",
    author="DepScan Team",
    author_email="depscan@example.com",
    description="Dependency Vulnerability Scanner",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/therickybobbeh/dep-scanner",
    packages=find_packages(),  # Changed to find packages in the root directory
    entry_points={
        "console_scripts": [
            "dep-scan = backend.cli:app"
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "httpx>=0.25.2",
        "pydantic>=2.5.1",
        "typer[all]>=0.9.0",
        "rich>=13.7.0",
        "pipdeptree>=2.13.1",
        "packaging>=23.2",
        "tomli>=2.0.1",
        "pyyaml>=6.0.1",
        "aiosqlite>=0.19.0",
        "python-multipart>=0.0.6",
        "websockets>=12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-httpx>=0.26.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.7.0",
        ]
    },
)