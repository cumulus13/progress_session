#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# progress_session.py
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 cumulus13 (cumulus13@gmail.com)
# A Python requests session with progress and retry capabilities
# SPDX-FileCopyrightText: 2025 cumulus13 <cumulus13@gmail.com>

from __future__ import annotations
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
import requests
import time
from rich.syntax import Syntax
console = Console()
import traceback
import os
import threading
import re

class ProgressSession(requests.Session):
    def request(self, method, url, *args, max_try=3, text="Connecting", theme='fruity', full_exception=False, retry_delay=1, show_url = False, **kwargs):
        attempt = 0
        last_exception = None
        exception = None
        dot_cycle = ['.', '..', '...']
        dot_index = 0
        show_url = show_url or True if os.getenv('SHOW_URL', '0') in ['1', 'true', 'True'] else False

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
            refresh_per_second=12  # smoother
        ) as progress:
            task = progress.add_task("[yellow]{text}[/]", total=None)
            while attempt < max_try:
                attempt += 1
                start_time = time.time()
                try:
                    # Animation of Spinner & Dot During Request
                    req_thread = None
                    response = None
                    exc = None

                    def do_request():
                        nonlocal response, exc
                        try:
                            response = super(ProgressSession, self).request(method, url, *args, **kwargs)
                        except Exception as e:
                            exc = e

                    req_thread = threading.Thread(target=do_request)
                    req_thread.start()

                    # Animation of Spinner & Dot During the Request Running
                    while req_thread.is_alive():
                        dots = dot_cycle[dot_index]
                        dot_index = (dot_index + 1) % len(dot_cycle)
                        progress.update(
                            task,
                            description=f"[yellow]Attempt[/] [#AA55FF]{attempt}[/]/[#0055FF]{max_try}[/]: [#FFFF00]{method.upper()}[/] [#FF5500]{url if show_url else ''}[/] [#00FFFF]{dots}[/]"
                        )
                        time.sleep(0.2)  # Smooth and Continue

                    req_thread.join()
                    # if exc:
                    #     raise exc
                    # response.raise_for_status()
                    # return response
                    if exc:
                        if not show_url:
                            # Masking Error Message Before Raise
                            err_str = str(exc)
                            err_str = re.sub(r'https?://[^\s]+', '[hidden-url]', err_str)
                            err_str = re.sub(r'([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}(:\d+)?(/[^\s]*)?', '[hidden-url]', err_str)
                            raise type(exc)(err_str).with_traceback(exc.__traceback__)
                        else:
                            raise exc
                    response.raise_for_status()
                    return response

                except requests.RequestException as e:
                    last_exception = e
                    exception = traceback.format_exc()
                    progress.update(task, description=f"[red]Attempt [/][#AA55FF]{attempt}[/]/[#0055FF]{max_try}[/]: [#FFFF00]{method.upper()}[/] [#FF5500]{url if show_url else ''}[/] [#00FFFF]{dots}[/] [#FF007F]Failed[/]")
                    if attempt < max_try:
                        time.sleep(retry_delay)

            progress.update(task, description=f"[red]Attempt [/][white on red]{max_try}[/]: [#FFFF00]{method.upper()}[/] [#FF5500]{url if show_url else ''}[/] [#00FFFF]{dots}[/] [#FF007F]Failed[/]")
            if (os.getenv('TRACEBACK') in ['1', 'true', 'True'] or full_exception) and exception:
                tb = Syntax(exception, 'python', line_numbers=False, theme=theme)
                console.print(tb)
            else:
                if not show_url:
                    # Hide/change the url in the error message
                    err_str = str(last_exception)
                    # Eliminate URL (Regex: http (s): // ... or domain)
                    err_str = re.sub(r'https?://[^\s]+', '[hidden-url]', err_str)
                    err_str = re.sub(r'([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}(:\d+)?(/[^\s]*)?', '[hidden-url]', err_str)
                    tb = Syntax(err_str, 'python', line_numbers=False, theme=theme)
                    console.print(f"[red bold]ERROR:[/] {err_str}")
                else:
                    tb = Syntax(str(last_exception), 'python', line_numbers=False, theme=theme)
                    console.print(f"[red bold]ERROR:[/] {last_exception}")
            
            raise type(last_exception)(err_str).with_traceback(last_exception.__traceback__)


# ✅ Contoh pakai
if __name__ == "__main__":
    session = ProgressSession()
    try:
        response = session.get("https://154.26.137.28", timeout=60, max_try=3)
        print("Status:", response.status_code)
    except Exception as e:
        print("Final failure:", e)
