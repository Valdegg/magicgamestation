# LLM Instructions for Documenting the Code Base

## General Guidelines
* Use the `docs/LLM` folder to store condensed insights from parsing this repo
* Files inside `docs/LLM/prompts/` are NEVER allowed to be modified by the LLM
* Keep a hierarchical `index.md` file in each subfolder
  * With a quick overview of the insights you have gathered
  * Always re-read the `index.md` files to be aware of the latest insights
  * Keep the `index.md` files minimal to not bloat your memory during future tasks
* Whenever finished with a task, update raw-memories, `index.md` files and a human-readable summary of the insights you made

## Structure
* Maintain the following folders:
  * `docs/LLM/extensive/` — continuously extending collection of insights, but keep it still shorter than the actual code-base
  * `docs/LLM/summarised/` — curated collection of insights
* Make extensive use of file hyperlinks to refer:
  * For every extensive insight → the actual code-base as a source
  * For every summarized insight → the extensive insights as a source
* **7-item limit rule:** No folder should contain more than 7 files or subfolders (excluding `index.md`)
  * When this limit is exceeded, reorganize by grouping related items into subfolders with their own `index.md` files
  * This ensures the cognitive load remains manageable for both humans and LLMs

## Style
* Use bullet points and structured text rather than full sentences
* Consider using mermaid diagrams if there are insights that might be quicker to read through a visual than through text
* Make the summarized insights at a level quick to parse by an expert software engineer working on this project who just wants to keep track of what was vibe coded
* Make the extensive insights at a level of detail an LLM would need to recap the code base if it was restarted and had not yet re-read the sections of code it is derived from

## Goal
* Have a place that can be parsed more quickly for both human engineers and LLMs to get up to speed without having to first skim the code base
