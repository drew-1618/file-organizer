# 📁 File Organizer Utility
A customizable Python utility designed to automatically organize files in a specified directory by sorting them into dedicated folders based on their file extensions.

### Table of Contents
1.  [About The Project](#about-the-project)
2.  [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Installation](#installation)
4.  [Configuration](#configuration)
5.  [Contributing](#contributing)
---
### About The Project
This project serves as a practical application to utilize software development principles and become more comfortable with Python programming and Linux utilities. The core goal is to clean up cluttered directories (e.g., Dowloads/ tend to get messy) by moving files into structured categories.
**Key Features**
  - **Extension-Based Sorting:** Files are automatically moved into catehorized folders (e.g., Images, Documents, Videos, etc.)
  - **Customizable Mapping:** The sorting logic is easily configured via a simple file in `config/rules.json`. For the simple and default logic, update the file extension and corresponding folders in `config/config.json`.
  - **Robust Logging:** Detailed logs track every file movement for dry-run and troubleshooting active runs. Log file is overwritten with each execution.
      - If a continuous log across executions is preferred, simply replace the filemode 'w' with 'a' in the `logging.basicConfig()` near the top of `src/organize.py`.
  - **Safe Operation:** Designed to operate on a specified source directory without affecting other system files.
---
### Getting Started
Follow these steps to set up and run the file organizer on your local machine.
#### **Prerequisites**
You need to have **Python3** installed on your system.
  - Python 3.xx
    ```bash
    # check if Python3 is installed
    python3 --version
    # if Python3 is not installed, install based on your OS
    ```
#### **Installation**
  1. Clone the repository:
  ```bash
  git clone https://github.com/drew-1618/file-organizer.git
  cd file-organizer
  ```
  2. Create and activate a virtual environment (Optional):
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
---
### Usage
To run the file organizer, execute the `src/organize.py` script.
**Example Run**
You will need to specify the *source directory* you want to organize.
```bash
python3 src/organize.py /path/to/your/unorganized/folder --dry-run
```

>*Note:* Best practice to execute with the --dry-run flag and inspect `organizer.log` to ensure the organization logic meets your expectations. If not, consider updating the `config/config.json` and/or `config/rules.json`.
---
### Contributing
Contributions are what make the open-source community so powerful and such an amazing place to learn. Any contributions or comments you make are **_greatly appreciated._**
  1. Fork the Project
  2. Create your Feature Branch (`git checkout -b feature/NewFeatureName`
  3. Commit your Changes (`git commit -m 'Add some NewFeature`)
  4. Push to the Branch (`git push -u origin feature/NewFeatureName`)
  5. Open a Pull Request











