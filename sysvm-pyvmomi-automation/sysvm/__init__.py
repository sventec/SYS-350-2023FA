# SYS-350 pyvmomi automation
import configparser
import ssl
from typing import cast

from pyVim.connect import SmartConnect
# pyVmomi vim import required in this format, see https://github.com/vmware/pyvmomi/issues/1025
from pyVmomi import vim


class VConn:
    config_file: str = "config.ini"
    hostname: str
    username: str
    password: str
    vcenter: vim.ServiceInstance

    def __init__(self, config_file: str = "") -> None:
        """Instantiate vCenter connection object.

        Args:
            config_file (optional): If supplied, overrides default config file location of "config.ini".
        """
        if config_file:
            self.config_file = config_file
        self.read_config()

    # def __post_init__(self):
    #     """Connect after object instantiation."""
    #     self.connect()

    def read_config(self) -> None:
        """Read user-supplied config from file."""
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            self.hostname = config["vcenter"]["hostname"]
            self.username = config["vcenter"]["username"]
        except KeyError as e:
            print(f"[!] Failed to parse config file: {self.config_file}")
            print(e)

    def connect(self, password: str) -> None:
        """Connect to a vCenter server.

        Args:
            password(str): Password for use with config file username.
        """
        self.password = password
        s = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        s.verify_mode = ssl.CERT_NONE
        self.vcenter = SmartConnect(
            host=self.hostname,
            user=self.username,
            pwd=self.password,
            sslContext=s,
        )

    def get_vms(
        self, search: str = "", exact: bool = False
    ) -> list[vim.VirtualMachine]:
        """Get a list of all VMs on the connected server.

        Args:
            search (optional): If provided, only return VMs with names matching this string. Defaults to "".
            exact (optional): Only return VMs with name exactly matching the search string. Defaults to False.

        Returns:
            A list of VirtualMachine objects.
        """
        # Code adapted from vmware/pyvmomi-community-samples - tools.pchelper.search_for_obj()
        # https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/tools/pchelper.py#L103

        folder = self.vcenter.content.rootFolder
        # Recursively get references to all VMs, starting from the root folder
        container = self.vcenter.content.viewManager.CreateContainerView(
            folder, [vim.VirtualMachine], recursive=True
        )

        if not search:
            # Return all VMs if no search specified
            vms = container.view
        elif exact:
            # Exactly match VM name and return, if specified
            vms = [vm for vm in container.view if vm.name == search]
        else:
            # Search for VMs with name containing search string
            vms = [vm for vm in container.view if search in str(vm.name)]

        container.Destroy()
        # This can be cast to VirtualMachine objects (instead of ManagedObject) as the view is filtering on that type
        return cast(list[vim.VirtualMachine], vms)
