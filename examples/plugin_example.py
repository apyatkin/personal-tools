"""Example hat plugin — add a custom 'hello' module."""

from hat.modules import Module, ModuleStatus


class HelloModule(Module):
    name = "hello"
    order = 99  # runs last

    def activate(self, config: dict, secrets: dict) -> None:
        import click

        msg = config.get("message", "Hello!")
        click.echo(f"    {msg}")

    def deactivate(self) -> None:
        pass

    def status(self) -> ModuleStatus:
        return ModuleStatus(active=False)
