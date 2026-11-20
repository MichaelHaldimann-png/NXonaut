# NXonaut button in NX (staged)

`nxonaut.men` adds an **NXonaut > Start NXonaut** menu, `nxonaut.rtb` an **NXonaut** ribbon
tab with the same button, and `nxonaut_start.py` is the journal the button plays (it runs
`journals/start.py`: starts the bridge, or reports that it already runs).

These files are not loaded yet: NX reads menu and ribbon files only from a `startup`
folder, and a wrong line there shows an error at every NX start. They move to
`nx_app/startup` (icons and the journal to `nx_app/application`) after a check on live NX:

1. Copy them there in a disposable copy of `nx_app` and start NX with `UGII_USER_DIR`
   pointing to that copy.
2. Check the NXonaut tab and menu, click the button, and confirm the panel appears.
