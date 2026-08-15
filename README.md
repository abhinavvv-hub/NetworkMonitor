# Network Monitor

<div align="center">
  <video src="https://github.com/user-attachments/assets/82ab6972-1e9e-4860-ad98-6a011d9e9b2f" width="100%" autoplay loop muted playsinline></video>
</div>

A real-time terminal network monitor built with Python, Textual, and `psutil` for tracking active sockets, process IDs, and system bandwidth.

## Features

* Live measurement of download and upload transfer rates.
* Active IPv4 and IPv6 socket tracking mapped to system PIDs and process names.
* Table filtering by process name, PID, IP address, or connection state.
* Selected process termination (SIGTERM) directly from the TUI.
* Light and dark visual theme toggle.

## Python Libraries Used

- textual
- psutil

#### Download the libraries
> [!NOTE]
> I have used `uv` as the package manager in this project. You can use any other based on your liking.
```
uv pip install textual psutil
```
