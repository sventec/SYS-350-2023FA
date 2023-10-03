# SYS-350 pyVmomi Automation

This is a Python application to interface with a vCenter server using pyVmomi,
including the functionality required by the course's milestone.

## Installation & Usage

Python >= 3.10 is required. Clone this repository locally, and continue with
one of the following methods.

### Using pdm

If [pdm](https://pdm.fming.dev/latest/#installation) is already installed
and/or being used, simply run `pdm install` in the project root to create a
local virtual environment and install `sysvm` to it.

Source the virtual environment with the following command, and invoke the tool
with `sysvm`:

```bash
eval $(pdm venv activate)
```

### Using pip

It is recommended that the tool's dependencies are installed in a virtual
environment. Install the following:

- `pyvmomi`
- `pyvim`
- `rich`

Once installation is complete, invoke `python3 sysvm/main.py`.

