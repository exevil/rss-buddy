#!/usr/bin/env python3
"""Setup script for RSS Buddy."""
from setuptools import find_packages, setup

# Read version from package
with open("src/rss_buddy/__init__.py", "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break

# Read long description from README
with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="rss-buddy",
    version=version,
    description="AI-powered RSS feed processor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="RSS Buddy Team",
    author_email="example@example.com",
    url="https://github.com/example/rss-buddy",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
    install_requires=[
        "feedparser>=6.0.0",
        "python-dateutil>=2.8.2",
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "rss-buddy=rss_buddy.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary",
    ],
) 
