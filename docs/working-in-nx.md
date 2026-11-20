# Working together in NX

- The agent works in parts it created or opened. It never closes your parts, and
  changes or saves one only after you tick **Allow agent to change <part>** on the
  panel.
- It does not take over the part you are looking at: while your part is on screen,
  its parts open in the background or in a tab behind yours.
- The **NX MCP** panel shows what the agent is doing and lists its parts
  (**Show part** brings one up).
  - **Auto** (default): the agent's steps run while you work. A step that changes
    something waits while you are in an NX command or dialog (at most 2 minutes);
    reads run at once.
  - **Ask me first**: every agent step waits for your OK.
- Several agents can work in the same NX at once, each in its own parts; one agent
  does not close or bring up another's parts.
- Files go in the workspace folder `C:\Users\<you>\NX_MCP_WORKSPACE`; the agent reads
  and writes files only there. Its `.nx-mcp` subfolder holds the activity log and NX
  MCP's own state.

More about the panel: [INTERACTIVE-NX.md](https://github.com/MichaelHaldimann-png/NXonaut/blob/master/INTERACTIVE-NX.md).
