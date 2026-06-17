Update the Voice Assistant layout.

Current issue:
The page feels broken because the pipeline appears in the middle of the conversation area and the Agent Talk / Transcript panels are not behaving like one equal-height workspace.

New layout:
1. Header row at top:
   - Voice Assistant title
   - subtitle
   - Ready/Listening/Processing/Speaking pill on far right

2. Latest answer below header.

3. Move the Pipeline directly below Latest Answer.
   - Pipeline should be a compact horizontal row near the top.
   - It should NOT appear between or inside the Agent Talk / Transcript panels.
   - It should not be sticky, fixed, absolute, transformed, or overlaid.
   - Use normal document flow.

4. Below Pipeline, render Agent Talk and Transcript side-by-side.
   - Agent Talk and Transcript must have exactly equal height.
   - Use one grid row with two columns.
   - Suggested height: `h-[560px]` or `h-[calc(100vh-260px)]` with a min height.
   - Transcript should scroll internally.
   - Agent Talk should keep input pinned at the bottom.
   - Do not let the full page become a long weird scroll because transcript messages grew.

5. Backend connections:
   - Keep them tiny and secondary.
   - Place as a narrow rail on the far right.
   - It should not affect the main conversation width too much.

Pipeline visual:
- Use `grid grid-cols-5`.
- Each step should be compact.
- Titles should be short:
  - Identify
  - Understand
  - Check
  - Guard
  - Respond
- Details should be tiny and truncated.
- No wrapping into multiple rows.
- If space is tight, allow horizontal scroll inside the pipeline only.

Do not change:
- mock pipeline behavior
- agent logic
- answers
- backend code
- API calls
- transcript data

This is layout-only.