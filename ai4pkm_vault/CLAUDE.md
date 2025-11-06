**All generic rules are defined in @AGENTS.md 

Refer to that file for:
- Core Mission & Principles
- Prompts & Workflows
- Content Creation Requirements
- Link Format Standards
- File Management
- Core Operational Principles
- Properties & Frontmatter Standards
- Quality Standards

---
# Claude Code Specific Rules
## Voice Mode
### Language
- Support both English and Korean in voice mode
- Always use `tts_model="gpt-4o-mini-tts"` for both languages
	- This model provides natural pronunciation for both English and Korean
- Read additional setting from environment variables
- By default continue conversation from previous chat (`AI/Voice/` folder)

### Listening
- Listen patiently; wait 3-5 seconds before barging in
	- Unless user explicitly ended conversation
- Don't detect random things when not spoken
	- Things like '시청해주셔서 감사합니다.'

### Tasks within Conv
- For longer task, spawn a subagent to process the task and continue conversation
	- Respond to the user when the subagent is completed

### Conv Recording
- Save all voice conversations to `AI/Voice/` folder
	- Update the file throughout the conversation to maintain record
- Include full transcript with speaker labels and timestamps
	- **Only include conversation transcript - no summaries, notes, or other content**
	- When creating or referencing documents during conversation, add them as sub-bullets:
		- `생성된 문서: [[path/to/created/file]]`
		- `참고한 문서: [[path/to/referenced/file1]], [[path/to/referenced/file2]]`
- Use format: `YYYY-MM-DD Voice Conversation.md`
	- Detailed format below

```
# User and Claude's conversation
## Initial greetings and discussion of weekend plans
- User (10/10/25 7:54 AM): Hello!
- Claude (10/10/25 7:54 AM): I created a document for you.
  - 생성된 문서: [[AI/Tasks/2025-10-10 Task]]
  - 참고한 문서: [[Journal/2025-10-10]]
```

## 📋 Task Management
### TodoWrite Usage
- **Always use TodoWrite** for multi-step projects (3+ steps)
- Mark ONE task `in_progress` at a time
- Mark `completed` immediately after finishing

## Version Control
### Automatic Commit Policy
- Commit changes after completing regular workflow runs 
	- Don’t commit any other changes automatically
- This includes changes from:
	- DIR (Daily Ingestion and Roundup)
	- CKU (Continuous Knowledge Upkeep)
	- WRP (Weekly Roundup and Planning)
	- Any batch file modifications from prompts in `_Settings_/Prompts/`
	- Processing that creates/modifies multiple files

### Commit Message Format for Workflows
- Use format: `Workflow: [Name] - YYYY-MM-DD`
- Only include affected files (don’t commit unaffected files)
- Include brief summary of changes
- Add emoji and Co-Authored-By signature
- Example:
```
Workflow: DIR - 2025-08-28

Daily Ingestion and Roundup:
- Processed lifelog from Limitless
- Updated daily roundup
- Added topic knowledge updates

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Claude Code Tool Usage
### Task Tool Priority
- **Use Task tool** for comprehensive searches and "find all X" requests
- Leverage specialized agents when available

### 🔍 Search Strategy
- Use comprehensive search tools for "find all X" requests
- Use multiple languages (한글 / English) for max recall
- **Read multiple files in parallel** for efficiency
- Focus on meaningful content over metadata files

## Continuous Improvement Loop
### Find rooms for improvement
- By evaluating output based on prompt
- By using user feedback

### Suggest ways
- Improvement to existing prompts
- New or revised workflows

## Additional Guidelines
### Workflow Completion
- Run all steps (i.e. prompts) are run when running a workflow 
	- Keep input/output requirements (file path/naming)
- Ensure all workflow steps are completed

### Parallelization Opportunities
- 파일 고치기/찾기는 대부분 병렬화가 가능
- 병렬화를 통해 시간 단축할 수 있는 기회를 찾고 수행 

### Data Source Preferences
- Don't use git status for checking update; read actual files from folder
- Always use local time (usually in Seattle area) for processing requests