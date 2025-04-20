# Geese Blueprint

**Geese** is special because it brings fun and whimsy to Open Swarm through animated bird prompts and playful interactions. Perfect for lightening the mood while you work!

## Special Feature
- **Fun Bird Animation Prompts:** Enjoy unique, animated geese interactions and prompts that make your workflow more enjoyable.

---

A collaborative story writing blueprint for Open Swarm that leverages multiple specialized agents to create, edit, and refine stories.

## Features

### Enhanced UI/UX
- 🎨 Rich ANSI/emoji boxes for operation feedback
- 📊 Dynamic result counts and search parameters
- ⏳ Intelligent progress spinners with state tracking
- ⚡ Real-time line number updates for long operations
- 🔄 Smart status messages for extended operations

### Core Capabilities
- 📋 Plan maintenance and tracking
- 📝 Multi-agent collaboration:
  - Planner Agent: Story structure and task delegation
  - Writer Agent: Content creation and development
  - Editor Agent: Review and refinement
  - Coordinator Agent: Process orchestration
- 🔍 Advanced search and analysis operations
- 🎯 Error handling and reflection

## Usage

```bash
# Basic story generation
swarm geese "Write a story about a magical forest"

# Interactive mode with file output
swarm geese -i input.txt -o output.txt --interactive

# Advanced mode with custom parameters
swarm geese --model gpt-4 --temperature 0.7 --max-tokens 4096 "Write an epic fantasy"
```

## Configuration

The blueprint supports various configuration options:
- Model selection (e.g., gpt-3.5-turbo, gpt-4)
- Temperature and token limits
- Input/output file handling
- Interactive mode for collaborative writing

## Operation Modes

1. **Generate Mode**: Create new stories from prompts
2. **Edit Mode**: Refine existing content
3. **Explain Mode**: Analyze story structure and elements
4. **Interactive Mode**: Real-time collaboration with the AI agents

## Implementation Details

The blueprint uses a multi-agent architecture where each agent has specialized roles:
- **Planner**: Structures stories and manages development flow
- **Writer**: Creates content based on outlines and context
- **Editor**: Reviews and improves content quality
- **Coordinator**: Orchestrates the entire process

## Notifier Abstraction & Reflection (New)

- All user-facing output (operation boxes, errors, info) is now handled through a Notifier abstraction, making it easy to redirect output to different UIs or for testing.
- The blueprint always displays the current plan, outputs of all operations, and any errors encountered, providing full transparency and reflection for users and agents.
- To customize output, pass a custom Notifier when instantiating the blueprint.

## Error Handling and Transparency
- Errors from agent operations are surfaced directly to the user in a styled error box, not just logged.
- The plan and tool outputs are always visible after each operation, mirroring the Goose agent’s reflection and transparency patterns.

## UI Elements

### Progress Indicators
- Custom spinner states: "Generating.", "Generating..", "Generating..."
- Extended operation indicator: "Taking longer than expected"
- Operation-specific emoji indicators

### Information Boxes
- 🔍 Search Results: Shows match counts and details
- 📊 Analysis: Displays content evaluation
- ✍️ Writing Progress: Shows current section status
- ✏️ Editing Updates: Shows improvement details
- 📋 Planning Status: Displays task completion

## Future Enhancements

- [ ] Enhanced error recovery
- [ ] Multi-format output support
- [ ] Advanced style configuration
- [ ] Custom agent templates
- [ ] Collaborative mode improvements
