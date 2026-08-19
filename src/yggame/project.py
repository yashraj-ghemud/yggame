# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Project scaffolding and environment validation helpers."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectTemplate:
    name: str
    description: str
    modules: tuple[str, ...]
    entrypoint: str


TEMPLATES = {
    "minimal": ProjectTemplate("minimal", "A small headless yggame project", ("core",), "main.py"),
    "platformer": ProjectTemplate(
        "platformer",
        "A platformer game foundation",
        ("core", "physics", "camera", "input", "anim", "ui"),
        "main.py",
    ),
    "topdown": ProjectTemplate(
        "topdown",
        "A top-down game foundation",
        ("core", "physics", "camera", "input", "ai", "world", "inventory", "ui"),
        "main.py",
    ),
    "rpg": ProjectTemplate(
        "rpg",
        "An RPG foundation with data-driven narrative",
        ("core", "scenes", "world", "inventory", "dialogue", "ai", "save", "ui", "i18n"),
        "main.py",
    ),
}


class ProjectScaffolder:
    def __init__(self, *, templates: dict[str, ProjectTemplate] | None = None) -> None:
        self.templates = templates or dict(TEMPLATES)

    def template(self, name: str) -> ProjectTemplate:
        try:
            return self.templates[name]
        except KeyError as exc:
            raise KeyError(f"unknown project template: {name}") from exc

    def create(
        self, directory: str | Path, *, template: str = "minimal", force: bool = False
    ) -> Path:
        root = Path(directory)
        selected = self.template(template)
        if root.exists() and any(root.iterdir()) and not force:
            raise FileExistsError(f"project directory is not empty: {root}")
        root.mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text(self._readme(selected), encoding="utf-8")
        (root / selected.entrypoint).write_text(self._entrypoint(selected), encoding="utf-8")
        (root / "pyproject.toml").write_text(self._pyproject(root.name), encoding="utf-8")
        (root / ".gitignore").write_text(self._gitignore(), encoding="utf-8")
        for module in selected.modules:
            (root / "game" / module).mkdir(parents=True, exist_ok=True)
            (root / "game" / module / "__init__.py").write_text(
                f'"""{module} systems for {root.name}."""\n', encoding="utf-8"
            )
        return root

    def list_templates(self) -> tuple[ProjectTemplate, ...]:
        return tuple(sorted(self.templates.values(), key=lambda item: item.name))

    @staticmethod
    def _readme(template: ProjectTemplate) -> str:
        modules = ", ".join(template.modules)
        return textwrap.dedent(f"""
            # Game project

            {template.description} created with yggame.

            The project is organized around these subsystems: {modules}.

            Run the game with:

            ```bash
            python main.py
            ```
        """).lstrip()

    @staticmethod
    def _entrypoint(template: ProjectTemplate) -> str:
        return textwrap.dedent(f"""
            from yggame import Game


            def main() -> None:
                game = Game()
                game.run(frames=1)
                print("{template.name} project booted")


            if __name__ == "__main__":
                main()
        """).lstrip()

    @staticmethod
    def _pyproject(name: str) -> str:
        return textwrap.dedent(f"""
            [project]
            name = "{name}"
            version = "0.1.0"
            requires-python = ">=3.10"
            dependencies = ["yggame>=0.1"]
        """).lstrip()

    @staticmethod
    def _gitignore() -> str:
        return "__pycache__/\n.venv/\n*.egg-info/\n.pytest_cache/\n"


@dataclass(frozen=True, slots=True)
class EnvironmentCheck:
    name: str
    available: bool
    detail: str


class EnvironmentDoctor:
    def check(self) -> tuple[EnvironmentCheck, ...]:
        checks: list[EnvironmentCheck] = []
        for package in ("pygame", "pymunk", "websockets", "babel"):
            try:
                module = __import__(package)
            except ImportError:
                checks.append(
                    EnvironmentCheck(package, False, "optional dependency is not installed")
                )
            else:
                checks.append(
                    EnvironmentCheck(
                        package, True, str(getattr(module, "__version__", "available"))
                    )
                )
        return tuple(checks)

    def summary(self) -> str:
        return "\n".join(
            f"{check.name}: {'available' if check.available else 'missing'} ({check.detail})"
            for check in self.check()
        )
