from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
import requests
import time
from rich.syntax import Syntax
console = Console()
import traceback
import os

class ProgressSession(requests.Session):
    def request(self, method, url, *args, max_try=3, text="Connecting", theme='fruity', full_exception=False, retry_delay=1, **kwargs):
        attempt = 0
        last_exception = None
        exception = None
        dot_cycle = ['.', '..', '...']
        dot_index = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
            refresh_per_second=12  # lebih halus
        ) as progress:
            task = progress.add_task("[yellow]{text}[/]", total=None)
            while attempt < max_try:
                attempt += 1
                start_time = time.time()
                try:
                    # Animasi spinner & dot selama request
                    req_thread = None
                    response = None
                    exc = None

                    import threading

                    def do_request():
                        nonlocal response, exc
                        try:
                            response = super(ProgressSession, self).request(method, url, *args, **kwargs)
                        except Exception as e:
                            exc = e

                    req_thread = threading.Thread(target=do_request)
                    req_thread.start()

                    # Animasi spinner & dot selama request berjalan
                    while req_thread.is_alive():
                        dots = dot_cycle[dot_index]
                        dot_index = (dot_index + 1) % len(dot_cycle)
                        progress.update(
                            task,
                            description=f"[yellow]Attempt[/] [#AA55FF]{attempt}[/]/[#0055FF]{max_try}[/]: [#FFFF00]{method.upper()}[/] [#FF5500]{url}[/] [#00FFFF]{dots}[/]"
                        )
                        time.sleep(0.2)  # lebih halus dan continue

                    req_thread.join()
                    if exc:
                        raise exc
                    response.raise_for_status()
                    return response

                except requests.RequestException as e:
                    last_exception = e
                    exception = traceback.format_exc()
                    progress.update(task, description=f"[red]Attempt [/][#AA55FF]{attempt}[/]/[#0055FF]{max_try}[/]: [#FFFF00]{method.upper()}[/] [#FF5500]{url}[/] [#00FFFF]{dots}[/] [#FF007F]Failed[/]")
                    if attempt < max_try:
                        time.sleep(retry_delay)

            progress.update(task, description=f"[red]Attempt [/][white on red]{max_try}[/]: [#FFFF00]{method.upper()}[/] [#FF5500]{url}[/] [#00FFFF]{dots}[/] [#FF007F]Failed[/]")
            if (os.getenv('TRACEBACK') in ['1', 'true', 'True'] or full_exception) and exception:
                tb = Syntax(exception, 'python', line_numbers=False, theme=theme)
                console.print(tb)
            else:
                tb = Syntax(str(last_exception), 'python', line_numbers=False, theme=theme)
                console.print(f"[red bold]ERROR:[/] {last_exception}")

            raise last_exception


# ✅ Contoh pakai
if __name__ == "__main__":
    session = ProgressSession()
    try:
        response = session.get("https://154.26.137.28", timeout=10, max_try=10)
        print("Status:", response.status_code)
    except Exception as e:
        print("Final failure:", e)
