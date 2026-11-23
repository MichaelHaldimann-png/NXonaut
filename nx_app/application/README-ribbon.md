# NXonaut button in NX

`startup/nxonaut.men` adds an **NXonaut > Start NXonaut** menu and `startup/nxonaut.rtb`
an **NXonaut** ribbon tab with the same button. The button plays
`application/nxonaut_start.py`, which runs `journals/start.py`: it starts the bridge, or
reports that it already runs. NX reads these files at start from `UGII_USER_DIR`, which
the Claude Desktop extension points at this `nx_app` folder (**Start with NX**).

When a site launcher sets `UGII_USER_DIR` and `UGII_GROUP_DIR` itself, playing
**Start NXonaut.py** once copies these files and a loader (`startup/nxonaut_autostart.py`)
into that launcher's personal `UGII_USER_DIR`; delete the `nxonaut*` files there to undo it.
