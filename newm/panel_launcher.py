from __future__ import annotations
from typing import Optional, cast

from threading import Thread
import subprocess
import psutil # type: ignore
import time
import logging

from .config import configured_value

logger = logging.getLogger(__name__)

all_panels: list[str] = [
    "lock",
    "launcher",
    "top_bar",
    "bottom_bar",
    "bar"
]

conf_cmds = {
    **{k: configured_value("panels.%s.cmd" % k, cast(Optional[str], None)) for k in all_panels},
    'lock': configured_value("panels.lock.cmd", cast(Optional[str], "alacritty -e newm-panel-basic lock")),
    'launcher': configured_value("panels.launcher.cmd", cast(Optional[str], "alacritty -e newm-panel-basic launcher")),
}

conf_cwds = {k: configured_value("panels.%s.cwd" % k, cast(Optional[str], None)) for k in all_panels}

class PanelLauncher:
    def __init__(self, panel: str) -> None:
        self.panel = panel

        self._proc: Optional[subprocess.Popen] = None

    def get_pid(self) -> Optional[int]:
        if self._proc is not None:
            return self._proc.pid
        else:
            return None

    def _start(self) -> None:
        self._proc = None

        cmd, cwd = conf_cmds[self.panel](), conf_cwds[self.panel]()
        if cmd is None:
            return

        logger.info("Starting %s in %s", cmd, cwd)
        try:
            self._proc = subprocess.Popen(cmd.split(" "), cwd=cwd)
        except:
            logger.exception("Subprocess")

    def check(self) -> None:
        cmd = conf_cmds[self.panel]()
        if cmd is None:
            return

        try:
            if self._proc is None or self._proc.poll() is not None:
                raise Exception()
        except Exception:
            logger.info("Subprocess for panel %s died", self.panel)
            self._start()

    def stop(self) -> None:
        try:
            if self._proc is not None:
                self._proc.kill()
            self._proc = None
        except:
            pass


class PanelsLauncher(Thread):
    def __init__(self) -> None:
        super().__init__()
        self._running = True
        self._panels = [PanelLauncher(k) for k in all_panels]

    def stop(self) -> None:
        self._running = False
        for p in self._panels:
            p.stop()

    def get_panel_for_pid(self, pid: int) -> Optional[str]:
        if pid is None:
            return None

        for p in self._panels:
            if pid == p.get_pid():
                return p.panel

        return None

    def run(self) -> None:
        i = 0
        while self._running:
            if i%50 == 0:
                for p in self._panels:
                    p.check()
            i += 1
            time.sleep(.5)

