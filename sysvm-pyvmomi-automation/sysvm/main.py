"""CLI application for SYS-350 pyvmomi automation."""
import enum
import sys
from abc import abstractmethod
from datetime import datetime
from textwrap import dedent

from pyVmomi import vim
from rich import print
from rich import prompt
from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint
from rich.table import Table

from sysvm import VConn

# pyright: reportInvalidStringEscapeSequence=false


class BaseCommand(enum.Enum):
    @staticmethod
    @abstractmethod
    def help_text() -> str:
        """Return command-type specific help text here."""
        ...

    @classmethod
    def get_command(cls):
        """Read and parse user commands."""
        while True:
            cmd = prompt.Prompt.ask(
                "\n[blue]\[?][/blue] Enter your command",
                default="?",
                choices=[v.value for v in cls],
            )
            if cmd == "?":
                print("\[-] Available commands:")
                print(cls.help_text())
            elif cmd == "q":
                print("[bold]Goodbye![/bold]")
                sys.exit()
            else:
                try:
                    return cls(cmd.lower().strip())
                except ValueError:
                    print(f"[red]\[!] {cmd.strip()} is not a valid command![/red]")


class Command(BaseCommand):
    LIST_INFO = "l"
    SEARCH = "s"
    QUIT = "q"
    _HELP = "?"

    def do_command(self, vc: VConn):
        """Perform operations for given command."""
        match self:
            case Command.LIST_INFO:
                list_info(vc)
            case Command.SEARCH:
                search_vms(vc)

    @staticmethod
    def help_text():
        return dedent(
            """\
            \[-] [bold]l[/bold]: [italic]List vCenter connection info[/italic]
            \[-] [bold]s[/bold]: [italic]Search for VM[/italic]
            \[-] [bold]q[/bold]: [italic]Quit[/italic]"""
        )


class VMCommand(BaseCommand):
    POWER_ON = "on"
    POWER_OFF = "off"
    SNAPSHOT = "s"
    RESTORE_LATEST = "r"
    # FULL_CLONE = "fc"
    # LINKED_CLONE = "lc"
    CHANGE_NETWORK = "n"
    DELETE_FROM_DISK = "d"
    VIEW_INFO = "v"
    COMMAND = "c"
    QUIT = "q"
    _HELP = "?"

    def do_command(self, vc: VConn, vms: list[vim.VirtualMachine]):
        """Perform operations on given VM(s)."""
        match self:
            case VMCommand.POWER_ON:
                if prompt.Confirm.ask("[blue]\[?][/blue] Really power on?"):
                    vc.vms_power(vms, True)
                    print("[green]\[+][/green] Powered on.")
            case VMCommand.POWER_OFF:
                if prompt.Confirm.ask("[blue]\[?][/blue] Really power off?"):
                    vc.vms_power(vms, False)
                    print("[green]\[+][/green] Powered off.")
            case VMCommand.SNAPSHOT:
                c = Console()
                # Check if any VMs aren't powered off
                if any(vm.runtime.powerState != "poweredOff" for vm in vms):
                    if not prompt.Confirm.ask(
                        "[blue]\[?][/blue] Not all VMs are powered off. Continuing will power off selected VMs."
                    ):
                        # Exit to command selection
                        c.print("\[-] Cancelling snapshot creation.")
                        vm_command = VMCommand.get_command()
                        vm_command.do_command(vc, vms)
                    # Power off VMs
                    vc.vms_power(vms, False)
                    c.print("[green]\[+][/green] Powered off.")
                # Create snapshot
                name = prompt.Prompt.ask(
                    "Name for the snapshot, defaults to ISO8601 date",
                    default=datetime.now().replace(microsecond=0).isoformat(),
                    show_default=True,
                )
                vc.vms_snapshot(vms, name)
                c.print(
                    f"[green]\[+][/green] Snapshot '{name}' created on {len(vms)} VMs.",
                    highlight=False,
                )
            case VMCommand.RESTORE_LATEST:
                vc.vms_restore_snapshot(vms)
                print("[green]\[+][/green] Restored latest snapshot.")
            case VMCommand.CHANGE_NETWORK:
                # Get available networks
                vmnets = [net.name for net in vc.get_vmnets()]
                for vm in vms:
                    print(f"\[-] Changing network adapter for {vm.name}")
                    # Get desired interface
                    nics = vc.vm_get_nics(vm)
                    interface = prompt.Prompt.ask(
                        "Select NIC to change",
                        choices=[nic.deviceInfo.label for nic in nics],
                    )
                    # Get desired network
                    dest_network = prompt.Prompt.ask(
                        "Select desired network",
                        default="VM Network",
                        show_default=True,
                        choices=vmnets,
                    )
                    # Change network
                    vc.vm_change_network(vm, interface, dest_network)
                    print(
                        f"[green]\[+][/green] Changed {vm.name} adapter {interface} to network {dest_network}."
                    )
            case VMCommand.DELETE_FROM_DISK:
                if prompt.Confirm.ask("[blue]\[?][/blue] Really delete?"):
                    vc.vms_destroy(vms)
                    print("[green]\[+][/green] Deleted from disk.")
            case VMCommand.VIEW_INFO:
                for vm in vms:
                    print()
                    _list_vm_info(vm)
            case VMCommand.COMMAND:
                cmd = Command.get_command()
                cmd.do_command(vc)
            case _:
                print("[red]\[!][/red] Command not yet implemented!")

        # Allow for multiple subsequent operations on same VM set, unless set was deleted
        if not self == VMCommand.DELETE_FROM_DISK:
            vm_command = VMCommand.get_command()
            vm_command.do_command(vc, vms)

    @staticmethod
    def help_text():
        return dedent(
            """\
            \[-] [b]on[/b]:  [i]Power on[/i]
            \[-] [b]off[/b]: [i]Power off[/i]
            \[-] [b]s[/b]:   [i]Snapshot[/i]
            \[-] [b]r[/b]:   [i]Restore latest snapshot[/i]
            \[-] [b]n[/b]:   [i]Change attached network[/i]
            \[-] [b]d[/b]:   [i]Delete from disk[/i]
            \[-] [b]v[/b]:   [i]View VM info[/i]
            \[-] [b]c[/b]:   [i]Back to top-level commands[/i]"""
        )


def _pprint_dict(d: dict, title: str = "") -> None:
    """Pretty print dictionary key/value pairs by padding the keys to a constant length."""
    # Replaced by 'rich' pretty print functionality, retaining in the event that dependency is removed
    # key_max = max(len(k) for k in d.keys()) + 1
    # for item in d.items():
    #     print(f"{item[0]:<{key_max}}: {item[1]!s}")
    # pprint(d, expand_all=True)
    table = Table(title=title, show_header=False)
    table.add_column("Key")
    table.add_column("Value")
    for k, v in d.items():
        table.add_row(k, str(v))
    console = Console()
    console.print(table)


def list_info(vc: VConn):
    """List vCenter connection info."""
    # Retrieve desired info
    vc_info = {
        "Username": vc.vcenter.content.sessionManager.currentSession.userName,
        "vCenter Server": vc.hostname,
        "vCenter Version": vc.vcenter.content.about.version,
        "Source IP": vc.vcenter.content.sessionManager.currentSession.ipAddress,
    }
    # Format and print info, padding keys to consistent length
    print()
    _pprint_dict(vc_info, title="vCenter Connection Info")


def _list_vm_info(vm: vim.VirtualMachine) -> None:
    """Internal function to print information for a given VM."""
    vm_info = {
        "VM Name": vm.name,
        "State": vm.runtime.powerState,
        "CPUs": vm.config.hardware.numCPU,
        "RAM (GB)": f"{(vm.config.hardware.memoryMB / 1024):0.2}",
        "IP Address": vm.guest.ipAddress,
    }
    _pprint_dict(vm_info, title=f"'{vm.name}' VM Info")


def search_vms(vc: VConn, query: str | None = None):
    """Search vCenter VMs by name."""
    if not query:
        query = prompt.Prompt.ask(
            "[blue]\[?][/blue] Search query, or <Enter> to list all VMs",
            default="",
            show_default=False,
        )
    # This is kept as list[ManagedObject] for later functionality, e.g. returning VMs or performing operations on them
    vms = vc.get_vms(query.strip() or "", exact=False)

    # Check that we got results back
    print(f"[green]\[+][/green] {len(vms)} results returned.")
    if len(vms) == 0:
        print("\[-] No operations possible on empty VM set.")
        return

    # Print a list of matched VM names, if a reasonable size
    if len(vms) <= 50:
        print("[green]\[+][/green] Matched VMs: ")
        pprint([vm.name for vm in vms])
        print()
    else:
        print("\[-] More than 50 VMs, skipping display of names...")

    # List VM info if desired
    if prompt.Confirm.ask(
        f"[blue]\[?][/blue] List VM details for all {len(vms)} result(s)?",
        default=False,
    ):
        for vm in vms:
            print()
            _list_vm_info(vm)

    # Optionally perform tasks on VM(s)
    vm_command = VMCommand.get_command()
    vm_command.do_command(vc, vms)


def main():
    """CLI application for SYS-350 pyvmomi automation."""
    print(
        Panel(
            "[bold][cyan]sysvm[/cyan]: SYS-350 pyvmomi automation tool[/bold]",
            expand=False,
        )
    )
    vc = VConn()
    print("\[-] Connecting to vCenter, enter password below:")
    try:
        vc.connect(prompt.Prompt.ask("[blue]\[?][/blue] Password", password=True))
    except vim.fault.InvalidLogin:
        print("[red]\[!] Invalid login![/red]")
        sys.exit(1)
    print(f"[green]\[+][/green] Connection established to {vc.hostname}.")
    while True:
        cmd = Command.get_command()
        cmd.do_command(vc)


if __name__ == "__main__":
    main()
