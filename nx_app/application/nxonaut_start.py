# nx: threaded
"""The NXonaut ribbon button: start the bridge, or say it already runs (its panel shows).

Line 1 keeps NXonaut in NX's main interpreter (see nx_app/journals/start.py).
"""

import os
import runpy

runpy.run_path(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "journals", "start.py"
    )
)
