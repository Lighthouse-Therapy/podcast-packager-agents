# Brighter Together Podcast Packager - Multi-Subagent Architecture

## Overview

This architecture transforms podcast transcripts into complete marketing packages using a supervisor/subagent pattern. It solves the rate limit problem (10k tokens/min on Sonnet 4.5) by isolating transcript reading to a dedicated subagent and passing only structured summaries between agents.

## Quick Start

```bash
# 1. Set up MCP server (on VPS)
cd /srv/google-workspace-mcp-extended
docker-compose up -d

# 2. Configure auth (see Authentication section)

# 3. Deploy agents to BrightBot
# (Integration with BrightBot DeepAgents TBD)
```

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                                │
│              Provides folder link → Selects title → Receives package    │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      MAIN PACKAGER (Orchestrator)                       │
│                                                                        │
│  Phase 0: Pre-flight Check                                             │
│  • Detect new vs already-packaged episodes                             │
│  • Archive old content if re-packaging                                 │
│                                                                        │
│  Phase 1: Input & Discovery                                            │
│  • Confirm transcript, extract guest name                              │
│                                                                        │
│  Phase 5: Content Creation                                             │
│  • Generate episode description, social posts                          │
│                                                                        │
│  Phase 6: Google Drive Output                                          │
│  • Create folders, docs, organize files, create shortcuts              │
│                                                                        │
│  Phase 7: Delivery                                                     │
│  • Summary of all files created/moved/organized                        │
└────────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          │ Phase 2            │ Phase 3            │ Phase 4
          ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   TRANSCRIPT     │  │     TREND        │  │    TITLING       │
│   ANALYZER       │  │   RESEARCHER     │  │     AGENT        │
│                  │  │                  │  │                  │
│ Reads full       │  │ Web searches     │  │ Researches       │
│ transcript       │  │ all platforms    │  │ title strategies │
│                  │  │                  │  │                  │
│ Extracts:        │  │ Ranks:           │  │ Generates:       │
│ • Guest info     │  │ • Themes         │  │ • 5 titles       │
│ • Themes         │  │ • Quotes         │  │ • Rationales     │
│ • Quote bank     │  │ • Pain points    │  │ • Rankings       │
│ • Pain points    │  │                  │  │                  │
│ • Voice profile  │  │ Recommends:      │  │ Strategies:      │
│                  │  │ • Primary angle  │  │ • FOMO           │
│ Output: ~3k tok  │  │ • Hooks          │  │ • Reversal       │
│                  │  │ • Hashtags       │  │ • Challenge      │
│ Tools: Drive     │  │                  │  │ • Curiosity Gap  │
│ read only        │  │ Tools: Web       │  │ • Authority      │
│                  │  │ search           │  │ • Transformation │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Workflow Phases

### Phase 0: Pre-flight Check
Detects if episode is new or already packaged:
- **Transcript in root** → New episode, proceed
- **Transcript in Full Length Assets/** → Already packaged, offer re-package option
- **No transcript** → Error

### Phase 0b: Archive (if re-packaging)
- Creates `_Archive/` folder
- Moves existing generated files with date suffix
- Deletes existing shortcuts in Guest Package
- Proceeds with fresh packaging

### Phase 1-4: Analysis & Title Selection
Sequential subagent invocation with human-in-the-loop for title selection.

### Phase 5: Content Creation
Main agent generates all content using subagent outputs + selected title.

### Phase 6: Google Drive Output
```
{Episode Folder}/
├── {Guest Name} - Episode Description          [GENERATED]
├── {Guest Name} - Title Options                [GENERATED, selected marked]
├── {Guest Name} - LHT Social Posts             [GENERATED]
│
├── Full Length Assets/
│   ├── {Guest Name} FULL PODCAST 1.mp4         [MOVED from root]
│   ├── {Guest Name} FULL PODCAST 1.WAV         [MOVED from root]
│   ├── {Guest Name} FULL PODCAST 1.MP3         [MOVED from root]
│   └── {Guest Name} Notes & Transcript         [MOVED from root]
│
├── Podcast Artwork/                            [CREATED - for graphics team]
│
├── Social Assets/
│   ├── Short 1.mp4                             [MOVED from root]
│   ├── Short 2.mp4                             [MOVED from root]
│   ├── Short N.mp4                             [variable count]
│   └── {Guest Name} - Guest Social Posts       [GENERATED]
│
├── Guest Package - {Guest Name}/               [SHORTCUTS ONLY]
│   ├── {Guest Name} - Full Episode (Audio)     [SHORTCUT → Full Length Assets/]
│   ├── {Guest Name} - Full Episode (Video)     [SHORTCUT → Full Length Assets/]
│   ├── {Guest Name} - Episode Description      [SHORTCUT → root]
│   ├── {Guest Name} - Guest Social Posts       [SHORTCUT → Social Assets/]
│   ├── Short 1                                 [SHORTCUT → Social Assets/]
│   └── Short 2                                 [SHORTCUT → Social Assets/]
│
└── _Archive/                                   [CREATED on re-package only]
    ├── {Guest Name} - Episode Description (2025-01-08)
    └── {Guest Name} - Title Options (2025-01-08)
```

### Phase 7: Delivery
Summary of all operations performed.

## Files

```
/tmp/podcast-agents/
├── README.md                              # This file
│
├── main-packager/
│   ├── agent.json                         # Main orchestrator config
│   ├── system_prompt.txt                  # Embedded brand voice, persona, workflow
│   └── file_organization.json             # File movement/shortcut rules
│
├── transcript-analyzer/
│   ├── agent.json                         # Subagent config
│   └── system_prompt.txt                  # Analysis instructions
│
├── trend-researcher/
│   ├── agent.json                         # Subagent config
│   └── system_prompt.txt                  # Research instructions
│
├── titling-agent/
│   ├── agent.json                         # Subagent config
│   └── system_prompt.txt                  # Title generation instructions
│
└── google-workspace-mcp-extended/         # Extended MCP server
    ├── gdrive/drive_tools.py              # Includes shortcut tools
    ├── SHORTCUT_TOOLS.md                  # Shortcut tool documentation
    └── ...                                # Full MCP server
```

## MCP Server

### GitHub Repository
https://github.com/Lighthouse-Therapy/google-workspace-mcp-extended

### VPS Deployment
- **Location**: `/srv/google-workspace-mcp-extended`
- **Docker Image**: `lht/google-workspace-mcp:latest`

### Added Tools (beyond upstream)
| Tool | Description |
|------|-------------|
| `create_drive_shortcut` | Create shortcut to existing file |
| `delete_drive_shortcut` | Delete shortcut (safety-checked) |
| `list_drive_shortcuts` | List shortcuts in folder |

### All Drive Tools Available
```
mcp__google-workspace__list_drive_items
mcp__google-workspace__get_doc_content
mcp__google-workspace__create_doc
mcp__google-workspace__create_drive_file
mcp__google-workspace__update_drive_file
mcp__google-workspace__search_drive_files
mcp__google-workspace__create_drive_shortcut    ← ADDED
mcp__google-workspace__delete_drive_shortcut    ← ADDED
mcp__google-workspace__list_drive_shortcuts     ← ADDED
```

## Token Efficiency

| Approach | Tokens to Main Agent | Rate Limit Impact |
|----------|---------------------|-------------------|
| Old (read all docs at runtime) | ~80k+ tokens | Hits 10k/min limit |
| New (subagent isolation) | ~15k tokens | Within limits |

### How It Works
1. **Transcript Analyzer** reads 50k+ token transcript → returns ~3k token summary
2. **Trend Researcher** does web searches → returns ~2k token analysis
3. **Titling Agent** does research → returns ~2k token titles
4. **Main Agent** receives ~7k tokens structured data → generates content

The main agent never sees the full transcript.

## Key Design Decisions

### 1. Static Context Embedding
Brand voice, persona, and format specs are embedded in system prompt (not fetched at runtime):
- Eliminates API calls
- Enables Anthropic prompt caching
- Reduces token consumption

### 2. Quote Bank Pattern
Transcript Analyzer extracts verbatim quotes with metadata. Main agent uses this bank rather than re-reading transcript.

### 3. Structured Output Schemas
Each subagent has defined `output_schema` ensuring predictable data flows.

### 4. Human-in-the-Loop
Title selection creates natural checkpoint for user guidance.

### 5. Idempotent Re-packaging
Archive strategy allows safe re-runs without losing previous versions.

### 6. Guest Package Shortcuts
Shortcuts (not copies) protect original files while giving guests access.

## Authentication (TODO)

The MCP server requires Google API credentials. Options:
- **OAuth Client**: For interactive use
- **Service Account**: For automated agents (recommended for BrightBot)

See `/srv/google-workspace-mcp-extended/.env.oauth21` for configuration template.

## Deployment

### LangGraph Application Structure

```
/tmp/podcast-agents/
├── langgraph.json              # LangGraph deployment config
├── pyproject.toml              # Python dependencies
├── .env.example                # Environment variables template
│
├── src/                        # LangGraph Python implementation
│   ├── main_packager/
│   │   └── graph.py            # Supervisor graph with HITL
│   ├── transcript_analyzer/
│   │   └── graph.py            # Transcript analysis subagent
│   ├── trend_researcher/
│   │   └── graph.py            # Trend research subagent
│   └── titling_agent/
│       └── graph.py            # Title generation subagent
│
├── main-packager/              # Agent specs (source of truth)
│   ├── agent.json
│   ├── system_prompt.txt
│   └── file_organization.json
│
├── transcript-analyzer/
│   ├── agent.json
│   └── system_prompt.txt
│
├── trend-researcher/
│   ├── agent.json
│   └── system_prompt.txt
│
└── titling-agent/
    ├── agent.json
    └── system_prompt.txt
```

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Run local dev server
langgraph dev
```

### VPS Deployment

```bash
# On VPS (n8n.lighthouse-therapy.com)
cd /srv
git clone https://github.com/Lighthouse-Therapy/podcast-packager-agents.git
cd podcast-packager-agents

# Set up environment
cp .env.example .env
vim .env  # Add production credentials

# Build and run with Docker
langgraph build -t lht/podcast-packager:latest
docker run -d \
  --name podcast-packager \
  --env-file .env \
  -p 8125:8000 \
  lht/podcast-packager:latest
```

### Integration with BrightBot

The agents expose endpoints via LangGraph Agent Server:

| Endpoint | Description |
|----------|-------------|
| `POST /runs` | Start a new packaging run |
| `GET /threads/{thread_id}` | Get thread state (for HITL) |
| `POST /threads/{thread_id}/runs` | Resume after interrupt |
| `GET /assistants` | List available assistants |

BrightBot can invoke these agents via:
1. **Direct API calls** to the Agent Server
2. **MCP integration** using the `/mcp` endpoint
3. **n8n workflows** calling the API endpoints

### MCP Server Configuration

The Google Workspace MCP server must be running and accessible:

```bash
# On VPS
cd /srv/google-workspace-mcp-extended
docker-compose up -d

# MCP endpoint available at:
# http://localhost:8000/mcp
```

Configure in BrightBot's MCP settings or langgraph.json.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2025-01-08 | Added preflight check, archive workflow, file organization, shortcut tools |
| 2.0.0 | 2025-01-08 | Multi-subagent architecture |
| 1.x | Prior | Monolithic agent (rate limit issues) |
