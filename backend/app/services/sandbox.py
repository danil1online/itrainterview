"""Docker-песочница: каждый тест выполняется в отдельном контейнере — без сети, read-only ФС, лимитами CPU/RAM/pids.

Языки python/javascript/java/cpp на собственных образах; параллельность ограничена семафором (sandbox_max_concurrent).
"""

import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings


class SandboxError(Exception):
    """Инфраструктурная ошибка песочницы (docker недоступен и т.п.)."""


# Лимит одновременных контейнеров: без него 25 параллельных сабмитов могут
# перегрузить хост, и корректный код получит ложный «timeout» из-за нехватки CPU/RAM.
_sem: threading.Semaphore | None = None
_sem_limit: int | None = None
_sem_lock = threading.Lock()


def _containers_limit() -> int:
    """Лимит одновременных контейнеров: настройка sandbox_max_concurrent (1–32), иначе min(cpu_count, 8)."""
    default = max(1, min(os.cpu_count() or 4, 8))
    try:
        from app.db import SessionLocal
        from app.models import get_setting

        db = SessionLocal()
        try:
            raw = get_setting(db, "sandbox_max_concurrent", "")
        finally:
            db.close()
        if raw:
            return max(1, min(32, int(raw)))
    except Exception:
        pass
    return default


def slot_acquire() -> None:
    """Ожидать слот на контейнер (лимит — sandbox_max_concurrent)."""
    global _sem, _sem_limit
    limit = _containers_limit()
    with _sem_lock:
        if _sem is None or _sem_limit != limit:
            _sem = threading.Semaphore(limit)
            _sem_limit = limit
        sem = _sem
    sem.acquire()


def slot_release() -> None:
    """Освобождает слот контейнера; без эффекта, если семафор ещё не инициализирован."""
    global _sem
    if _sem is not None:
        _sem.release()


@dataclass
class TestOutcome:
    name: str
    passed: bool = False
    status: str = "ok"  # ok|wrong_answer|runtime_error|timeout|compile_error|internal_error
    got_stdout: str = ""
    stderr: str = ""
    time_ms: int = 0


@dataclass
class RunOutcome:
    status: str = "internal_error"  # accepted|wrong_answer|runtime_error|timeout|compile_error|internal_error
    results: list[TestOutcome] = field(default_factory=list)
    time_ms: int = 0


@dataclass
class LanguageSpec:
    image: str
    filename: str
    run_cmd: str
    compile_cmd: str | None = None


LANGUAGES: dict[str, LanguageSpec] = {
    "python": LanguageSpec(
        image="itrainterview/runner-python:latest",
        filename="main.py",
        run_cmd="python3 main.py",
    ),
    "javascript": LanguageSpec(
        image="itrainterview/runner-node:latest",
        filename="main.js",
        run_cmd="node main.js",
    ),
    "java": LanguageSpec(
        image="itrainterview/runner-java:latest",
        filename="Main.java",
        run_cmd="java Main",
        compile_cmd="javac Main.java",
    ),
    "cpp": LanguageSpec(
        image="itrainterview/runner-cpp:latest",
        filename="main.cpp",
        run_cmd="./main",
        compile_cmd="g++ -O2 -std=c++17 main.cpp -o main",
    ),
}

MAX_OUTPUT_CHARS = 4096


def normalize_output(s: str) -> str:
    """Нормализация вывода для сравнения: CRLF→LF, хвостовые пробелы строк и пустые строки в конце убираются."""
    lines = [line.rstrip() for line in s.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


class DockerSandbox:
    """Запуск каждого теста в отдельном контейнере: без сети, с лимитами CPU/RAM/pids."""

    def _client(self):
        """Docker-клиент из окружения; SandboxError, если пакет не установлен или Docker недоступен."""
        try:
            import docker
        except ImportError as e:  # pragma: no cover
            raise SandboxError("Пакет docker не установлен") from e
        try:
            return docker.from_env()
        except Exception as e:
            raise SandboxError(f"Docker недоступен: {e}") from e

    def _run_container(
        self, spec: LanguageSpec, cmd: str, host_dir: str, timeout: int, memory_mb: int
    ):
        """Запускает detached-контейнер с лимитами (без сети, read_only, tmpfs /tmp, user 65534)."""
        client = self._client()
        try:
            container = client.containers.run(
                spec.image,
                command=["sh", "-c", cmd],
                volumes={host_dir: {"bind": "/work", "mode": "rw"}},
                working_dir="/work",
                environment={"HOME": "/tmp"},
                network_disabled=True,
                mem_limit=f"{memory_mb}m",
                memswap_limit=f"{memory_mb}m",
                nano_cpus=int(settings.sandbox_cpus * 1_000_000_000),
                pids_limit=128,
                read_only=True,
                tmpfs={"/tmp": "size=64m"},
                user="65534:65534",
                detach=True,
                labels={"itrainterview.sandbox": "1"},
            )
        except Exception as e:
            raise SandboxError(
                f"Не удалось запустить контейнер ({spec.image}): {e}. "
                "Проверьте, что образы собраны: docker compose --profile runner build"
            ) from e
        return container

    @staticmethod
    def _wait_container(container, timeout: int) -> tuple[int | None, int]:
        """Возвращает (exit_code или None при таймауте, время в мс); сбой docker-демона — SandboxError."""
        start = time.monotonic()
        try:
            # python-docker при истечении timeout возвращает {"StatusCode": None, "Error": {...}}
            result = container.wait(timeout=timeout)
            code = result.get("StatusCode") if isinstance(result, dict) else None
        except Exception as e:
            raise SandboxError(f"Сбой взаимодействия с docker-демоном (не таймаут): {e}") from e
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            try:
                container.remove(force=True)
            except Exception:
                pass
        return code, elapsed_ms

    def run(
        self,
        language: str,
        code: str,
        tests: list[dict],
        timeout_sec: int | None = None,
        memory_mb: int | None = None,
    ) -> RunOutcome:
        """Прогоняет все тесты последовательно, каждый в отдельном контейнере; временный каталог удаляется в finally."""
        spec = LANGUAGES.get(language)
        if spec is None:
            raise SandboxError(f"Неподдерживаемый язык: {language}")

        timeout = timeout_sec or settings.sandbox_timeout_sec
        memory = memory_mb or settings.sandbox_memory_mb

        sub = uuid.uuid4().hex
        local_dir = Path(settings.sandbox_local_dir) / sub
        host_dir = str(Path(settings.sandbox_host_dir) / sub)
        local_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(local_dir, 0o777)

        try:
            src = local_dir / spec.filename
            src.write_text(code, encoding="utf-8")
            os.chmod(src, 0o666)

            outcome = RunOutcome()

            if spec.compile_cmd:
                build_log = local_dir / "build.log"
                slot_acquire()
                try:
                    container = self._run_container(
                        spec,
                        f"{spec.compile_cmd} > build.log 2>&1",
                        host_dir,
                        max(timeout * 6, 60),
                        memory,
                    )
                    code_, _ms = self._wait_container(container, max(timeout * 6, 60))
                finally:
                    slot_release()
                log = build_log.read_text(errors="replace")[:MAX_OUTPUT_CHARS] if build_log.exists() else ""
                if code_ != 0:
                    outcome.status = "compile_error"
                    outcome.results = [
                        TestOutcome(name=t.get("name", f"test{i}"), status="compile_error", stderr=log)
                        for i, t in enumerate(tests)
                    ]
                    return outcome

            overall = "accepted"
            total_ms = 0
            for i, test in enumerate(tests):
                name = test.get("name", f"test{i}")
                (local_dir / "in.txt").write_text(test.get("stdin", ""), encoding="utf-8")
                os.chmod(local_dir / "in.txt", 0o666)
                cmd = f"{spec.run_cmd} < in.txt > out.txt 2> err.txt"
                slot_acquire()
                try:
                    container = self._run_container(spec, cmd, host_dir, timeout, memory)
                    exit_code, elapsed = self._wait_container(container, timeout)
                finally:
                    slot_release()
                total_ms += elapsed

                got = ""
                stderr = ""
                out_file = local_dir / "out.txt"
                err_file = local_dir / "err.txt"
                if out_file.exists():
                    got = out_file.read_text(errors="replace")[:MAX_OUTPUT_CHARS]
                if err_file.exists():
                    stderr = err_file.read_text(errors="replace")[:MAX_OUTPUT_CHARS]

                if exit_code is None:
                    status = "timeout"
                elif exit_code == 137:
                    status = "timeout"
                    stderr = stderr or "Превышен лимит памяти (OOM) или время выполнения"
                elif exit_code != 0:
                    status = "runtime_error"
                elif normalize_output(got) == normalize_output(test.get("expected_stdout", "")):
                    status = "ok"
                else:
                    status = "wrong_answer"

                outcome.results.append(
                    TestOutcome(
                        name=name,
                        passed=status == "ok",
                        status=status,
                        got_stdout=normalize_output(got),
                        stderr=stderr,
                        time_ms=elapsed,
                    )
                )
                if status != "ok" and overall == "accepted":
                    overall = status

            outcome.status = overall
            outcome.time_ms = total_ms
            return outcome
        finally:
            shutil.rmtree(local_dir, ignore_errors=True)

    def run_script(
        self,
        language: str,
        code: str,
        timeout_sec: int | None = None,
        memory_mb: int | None = None,
    ) -> dict:
        """Одиночный прогон собранного скрипта (вайб-кодинг): без stdin, вывод парсит вызывающий.

        Возвращает {status: ok|runtime_error|timeout, exit_code, stdout, stderr}.
        """
        spec = LANGUAGES.get(language)
        if spec is None:
            raise SandboxError(f"Неподдерживаемый язык: {language}")
        if language != "python":
            raise SandboxError("run_script поддерживает только python")

        timeout = timeout_sec or settings.sandbox_timeout_sec
        memory = memory_mb or settings.sandbox_memory_mb

        sub = uuid.uuid4().hex
        local_dir = Path(settings.sandbox_local_dir) / sub
        host_dir = str(Path(settings.sandbox_host_dir) / sub)
        local_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(local_dir, 0o777)

        try:
            src = local_dir / spec.filename
            src.write_text(code, encoding="utf-8")
            os.chmod(src, 0o666)

            cmd = f"{spec.run_cmd} > out.txt 2> err.txt"
            slot_acquire()
            try:
                container = self._run_container(spec, cmd, host_dir, timeout, memory)
                exit_code, _elapsed = self._wait_container(container, timeout)
            finally:
                slot_release()

            stdout = ""
            stderr = ""
            out_file = local_dir / "out.txt"
            err_file = local_dir / "err.txt"
            if out_file.exists():
                stdout = out_file.read_text(errors="replace")[:MAX_OUTPUT_CHARS * 2]
            if err_file.exists():
                stderr = err_file.read_text(errors="replace")[:MAX_OUTPUT_CHARS]

            if exit_code is None:
                status = "timeout"
            elif exit_code == 137:
                status = "timeout"
                stderr = stderr or "Превышен лимит памяти (OOM) или время выполнения"
            elif exit_code != 0:
                status = "runtime_error"
            else:
                status = "ok"
            return {"status": status, "exit_code": exit_code, "stdout": stdout, "stderr": stderr}
        finally:
            shutil.rmtree(local_dir, ignore_errors=True)


_sandbox: DockerSandbox | None = None


def get_sandbox() -> DockerSandbox:
    """Синглтон экземпляра DockerSandbox."""
    global _sandbox
    if _sandbox is None:
        _sandbox = DockerSandbox()
    return _sandbox
