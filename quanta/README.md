# Quanta AI

Quanta is the AI-powered orchestration microservice for UI Pay.

It interprets natural language and multimodal requests, coordinates approved tools, and prepares financial operations — while **never** authorizing or executing transactions itself.

## Core Principle

> Quanta may interpret, reason, prepare, and coordinate.  
> Final financial authorization and execution remain under the control of the UI Pay backend.

## Project Status

Prototype / Core Implementation – Day 1 foundation in progress.

## Tech Stack

- Python 3.12+
- FastAPI
- Pydantic
- Claude (Anthropic)
- Strict state machine + tool allowlist architecture

## Quick Start

```bash
# Create and activate virtual environment
py -3.12 -m venv .venv
source .venv/Scripts/activate          # Git Bash / Linux / macOS
# .\.venv\Scripts\Activate.ps1        # PowerShell

# Install dependencies
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env