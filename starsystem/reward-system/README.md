# STARSYSTEM Reward System

Stats aggregation and fitness function for OMNISANC self-play.

## Features

- Reads event registries and computes statistics
- Calculates rewards per-event, per-session, per-mission
- Fitness function for overall usage reward
- XP/Level system

## Usage

```python
from starsystem_reward_system import compute_fitness
from heaven_base.registry.registry_service import RegistryService

registry_service = RegistryService()
fitness_data = compute_fitness(registry_service, "2025-10-09")

print(f"Fitness: {fitness_data['fitness']}")
print(f"Level: {fitness_data['level']}")
print(f"XP: {fitness_data['xp']}")
```

## Installation

```bash
pip install starsystem_reward_system
```

## Dependencies

- heaven-framework-toolbox (for RegistryService)
