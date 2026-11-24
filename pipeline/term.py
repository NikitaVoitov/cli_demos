"""A pyte screen that every replay of a cast uses.

pyte rejects the private form of the device status query (CSI ? 6 n) that GitHub Copilot CLI sends, and stops the
replay with a TypeError; the query only asks the terminal where its cursor is, so it is answered like the plain one.
"""

import pyte


class Screen(pyte.Screen):
    def report_device_status(self, mode, **_):
        return super().report_device_status(mode)
