# Open Swarm UX Patterns

## Spinner Messages
- `Generating.`, `Generating..`, `Generating...`, `Running...`
- If spinner takes longer than expected: `Generating... Taking longer than expected`

## ANSI/Emoji Boxes for Results
- Summarize operation (e.g., 'Searched filesystem', 'Analyzed code')
- Include result counts and search parameters
- Distinguish code vs. semantic search outputs
- Periodically update line numbers for long operations

## Async CLI Input Handler
- User can type while previous response streams
- Single Enter: warn user
- Double Enter: interrupt and submit new prompt

## TODO
- [ ] Implement spinner and box patterns in all blueprints
- [ ] Add code snippets and screenshots for each UX pattern
- [ ] Reference from blueprints/README.md and main README
