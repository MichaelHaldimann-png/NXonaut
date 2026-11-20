# Troubleshooting

| Problem | Fix |
| --- | --- |
| The agent says NX is not running | Start NX (see [Install](install.md)) and check that the NX MCP panel is open. NX takes a while to start; the panel appears once NX's main window is up |
| The agent says NX is blocked by a dialog | Answer the dialog in NX; the agent never clicks NX dialogs. A dialog an agent step opened that stays unanswered for 20 s is flagged on the panel, and NX's taskbar button flashes |
| The agent says NX is busy (`NX_BUSY`) | Another step still runs in NX and nothing new was started; the agent waits and retries. A long step (a large export, a check on a very large body) can hold NX for minutes |
| The agent says you are busy in NX (`NX_UI_BUSY`) | Finish or cancel your NX command, then let the agent retry |
| The agent says a part is yours (`NX_PART_NOT_GRANTED`) | Tick **Allow agent to change <part>** on the panel if you want it to |
| The agent says a licence is missing (`NX_LICENSE_UNAVAILABLE`) | Some tools need extra NX licences. NX MCP lets NX decide: when NX refuses, nothing is changed, the error names the licence feature the command needs (`details.license`) so you know which one to ask for, and the agent stops offering that tool for 15 minutes, then asks NX again. Only the few commands where NX would otherwise block on its "License Not Available" dialog (switching applications, Topology Optimization, variational sweep) are checked first |
| No NX MCP panel | Play `Start NXonaut.py` again (see [Install](install.md)); with the optional auto-start, check `UGII_USER_DIR` and restart NX |
| Claude Desktop: **Save** stays grey in the extension's settings | Switch **Start with NX** off and on once; Claude Desktop only enables Save after a change. Usually there is nothing to set: an empty workspace field means `C:\Users\<you>\NX_MCP_WORKSPACE` |
| **nx** is not connected in the client | Check that the extension or plugin is installed and enabled, or the path to `nx-mcp.exe` |
