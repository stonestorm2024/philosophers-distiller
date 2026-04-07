# Philosophers Distiller Framework

Distill any deceased philosopher into an AI Agent Skill.

## Supported Philosophers

| Philosopher | Repo | Core Concept |
|-------------|------|-------------|
| Martin Heidegger | heidegger-distill | Being, Dasein, Gestell |
| Herbert Marcuse | marcuse-distill | One-Dimensionality, False Needs |
| Günther Anders | anders-distill | Promethean Gap, Scham |
| Karl Marx | marx-distill | Alienation, Species-Being |

## Architecture

Each philosopher repo contains:
- `personality.md` - Core character with speech patterns, philosophy, quotes
- `memory.md` - Interactive memory
- `interaction.md` - Response patterns
- `quotes.md` - Famous quotes (original + translation)
- `SKILL.md` - OpenClaw skill entry
- `manifest.json` - Metadata

## Quick Start

```bash
# Import personality into your agent
cat heidegger/personality.md

# Use as OpenClaw skill
openclaw skills install heidegger-distill
```

## License

MIT
