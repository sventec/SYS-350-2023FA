"""CLI application for SYS-350 pyvmomi automation."""
import enum
import sys

from pyVmomi import vim
from rich import print
from rich import prompt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sysvm import VConn

# pyright: reportInvalidStringEscapeSequence=false


class Command(enum.Enum):
    LIST_INFO = "l"
    SEARCH = "s"
    QUIT = "q"
    _HELP = "?"


def get_command() -> Command:
    """Read and parse user commands."""
    while True:
        cmd = prompt.Prompt.ask(
            "\n[blue]\[?][/blue] Enter your command",
            default="?",
            choices=[v.value for v in Command],
        )
        if cmd == "?":
            print("\[-] Available commands:")
            print("\[-] [bold]l[/bold]: [italic]List vCenter connection info[/italic]")
            print("\[-] [bold]s[/bold]: [italic]Search for VM[/italic]")
            print("\[-] [bold]q[/bold]: [italic]Quit[/italic]")
        else:
            try:
                return Command(cmd.lower().strip())
            except ValueError:
                print(f"[red]\[!] {cmd.strip()} is not a valid command![/red]")


def do_command(cmd: Command, vc: VConn):
    """Perform operations for given command."""
    match cmd:
        case Command.QUIT:
            print("[bold]Goodbye![/bold]")
            sys.exit()
        case Command.LIST_INFO:
            list_info(vc)
        case Command.SEARCH:
            search_vms(vc)


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
    print(f"[green]\[+][/green] {len(vms)} results returned, listing info.")
    for vm in vms:
        print()
        _list_vm_info(vm)


def main():
    """CLI application for SYS-350 pyvmomi automation."""
    print(Panel("[bold][cyan]sysvm[/cyan]: SYS-350 pyvmomi automation tool[/bold]", expand=False))
    vc = VConn()
    print("\[-] Connecting to vCenter, enter password below:")
    try:
        vc.connect(prompt.Prompt.ask("[blue]\[?][/blue] Password", password=True))
    except vim.fault.InvalidLogin:
        print("[red]\[!] Invalid login![/red]")
        sys.exit(1)
    print(f"[green]\[+][/green] Connection established to {vc.hostname}.")
    while True:
        cmd = get_command()
        do_command(cmd, vc)


if __name__ == "__main__":
    main()
