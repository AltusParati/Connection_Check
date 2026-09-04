# Connection Check

Connection Check is a lightweight Windows internet connection monitor developed by **G-SOFTWARE**.

It continuously checks real internet access, detects outages, records outage start/restoration times, and keeps daily logs.

Current version: **v1.0.0**

## Features

- Real internet connectivity checks instead of relying on the Windows network icon
- TCP checks against multiple public endpoints
- Automatic monitoring when the application starts
- Detects an outage after 3 consecutive failed checks
- Records outage start and restoration times
- Records outage duration
- Daily log files
- Resettable daily outage counter without deleting previous logs
- Turkish and English interface
- Log language follows the selected interface language
- Minimize to system tray
- Optional Windows startup
- Single-instance protection: a second copy cannot be opened
- Responsive / scrollable interface for smaller screens
- Dark Windows desktop interface

## Connectivity Check

Connection Check currently tests TCP connectivity against:

- Cloudflare — `1.1.1.1:443`
- Google DNS — `8.8.8.8:53`
- Quad9 — `9.9.9.9:53`

The default check interval is 2 seconds.

## User Data

Connection Check stores user settings and logs outside the program directory:

```text
%LOCALAPPDATA%\G-SOFTWARE\Connection Check\
├── settings.json
└── logs\
```

This keeps private outage logs and local settings out of the GitHub repository and allows the application to run from different folders.

## Source

Main source file:

```text
src\Connection_Check.py
```

## Run From Source

### Requirements

- Windows
- Python 3
- Pillow
- pystray

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run:

```powershell
python src\Connection_Check.py
```

## Build

Install PyInstaller:

```powershell
pip install -r requirements-build.txt
```

The official Connection Check application icon is already included in the repository at:

```text
icon\icon.ico
```

You do **not** need to add or choose an icon to run or build the official project.
If you fork the project and intentionally want different branding, you may replace this file in your own fork.

### Portable single-file build

```powershell
python -m PyInstaller --onefile --windowed --clean --noconfirm --name "Connection Check" --icon "icon\icon.ico" --add-data "icon\icon.ico;icon" src\Connection_Check.py
```

Output:

```text
dist\Connection Check.exe
```

### Faster one-directory build

```powershell
python -m PyInstaller --onedir --windowed --clean --noconfirm --name "Connection Check" --icon "icon\icon.ico" --add-data "icon\icon.ico;icon" src\Connection_Check.py
```

Output:

```text
dist\Connection Check\
├── Connection Check.exe
└── _internal\
```

When distributing the `--onedir` build, keep the whole folder together.

## Privacy

Connection Check does not need a user account and its outage logs are stored locally on the user's computer.

The repository intentionally ignores runtime logs and local settings.

## Author

Developed by **G-SOFTWARE**

https://www.g-software.org

## License

Connection Check is released under the **MIT License**.

See the [`LICENSE`](LICENSE) file for the full license text.
