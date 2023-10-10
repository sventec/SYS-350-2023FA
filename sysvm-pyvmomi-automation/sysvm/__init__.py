# SYS-350 pyvmomi automation
import configparser
import ssl
from typing import cast

from pyVim.connect import SmartConnect
from pyVmomi import vim
from pyVmomi import vmodl

# pyVmomi vim import required in the above format, see https://github.com/vmware/pyvmomi/issues/1025


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

    # Adapted from github://vmware/pyvmomi-community-samples/tools/tasks.py
    # https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/tools/tasks.py
    def _wait_for_tasks(self, tasks):
        """Return after all tasks are complete."""
        property_collector = self.vcenter.content.propertyCollector
        task_list = [str(task) for task in tasks]
        # Create filter
        obj_specs = [
            vmodl.query.PropertyCollector.ObjectSpec(obj=task) for task in tasks
        ]
        property_spec = vmodl.query.PropertyCollector.PropertySpec(
            type=vim.Task, pathSet=[], all=True
        )
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = obj_specs
        filter_spec.propSet = [property_spec]
        pcfilter = property_collector.CreateFilter(filter_spec, True)
        try:
            version, state = "", None
            # Loop looking for updates till the state moves to a completed state.
            while task_list:
                update = property_collector.WaitForUpdates(version)
                for filter_set in update.filterSet:
                    for obj_set in filter_set.objectSet:
                        task = obj_set.obj
                        for change in obj_set.changeSet:
                            if change.name == "info":
                                state = change.val.state  # type: ignore
                            elif change.name == "info.state":
                                state = change.val
                            else:
                                continue

                            if str(task) not in task_list:
                                continue

                            if state == vim.TaskInfo.State.success:  # type: ignore
                                # Remove task from taskList
                                task_list.remove(str(task))
                            elif state == vim.TaskInfo.State.error:  # type: ignore
                                raise task.info.error
                # Move to next version
                version = update.version
        finally:
            if pcfilter:
                pcfilter.Destroy()

    def vms_power(self, vms: list[vim.VirtualMachine], power_state: bool):
        """Modify VMs power state.

        Args:
            vms: List of VirtualMachine objects to change the power state for.
            power_state: Desired power state. True to Power On, False to Power Off.
        """
        tasks = [vm.PowerOn() if power_state is True else vm.PowerOff() for vm in vms]  # type: ignore[reportGeneralTypeIssues]
        self._wait_for_tasks(tasks)

    def vms_snapshot(self, vms: list[vim.VirtualMachine], name: str):
        """Snapshot VMs.

        Args:
            vms: List of VirtualMachine objects to snapshot.
            name: Name to be used for the snapshot(s).
        """
        tasks = [
            vm.CreateSnapshot(
                name,
                description="Created with sysvm",
                memory=False,
                quiesce=False,
            )
            for vm in vms
        ]
        self._wait_for_tasks(tasks)
