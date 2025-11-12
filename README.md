# senior_gui

## Overview

This repository contains two main parts that require separate Python virtual environments:

- interface (Streamlit front-end)
- ml (machine learning code)

Below are concise, cross-platform instructions to create and use virtual environments for each folder and to run the Streamlit app.

## Prerequisites

- Python 3.8+ installed and on your PATH.
- Optional but recommended: upgrade pip:

  ```sh
  python -m pip install --upgrade pip
  ```

## Creating and using virtual environments

General notes:

- Use distinct environments for `interface` and `ml`.
- Recommended naming: `.venv_interface` and `.venv_ml` (dot-prefixed keeps them hidden on Unix-like systems).

1. Interface environment
   - Open a terminal and navigate to the interface folder:

     ```sh
     cd interface
     ```

   - Create the venv:

     ```sh
     python -m venv .venv_interface
     ```

   - Activate the environment:
     - Windows Command Prompt (cmd.exe):

       ```sh
       .venv_interface\Scripts\activate
       ```

     - Windows PowerShell:

       ```powershell
       .\.venv_interface\Scripts\Activate.ps1
       ```

     - macOS / Linux (bash / zsh):

       ```sh
       source .venv_interface/bin/activate
       ```

   - Install dependencies:

     ```sh
     pip install -r requirements.txt
     ```

2. ML environment
   - Open a new terminal and navigate to the ml folder:

     ```sh
     cd ml

     ```

   - Create the venv:

     ```sh
     python -m venv .venv_ml
     ```

   - Activate the environment (same variants as above, substituting `.venv_ml`).
   - Install dependencies:

     ```sh
     pip install -r requirements.txt
     ```

## Running the Streamlit application

1. Activate the interface environment as shown above.

2. Run the Streamlit app (choose one):

   - From the interface folder (current behavior in this doc):

     ```sh
     cd interface
     streamlit run app.py
     ```

   - From the repository root (explicit path, safer if you run from the repo root):

     ```sh
     streamlit run interface/app.py
     ```

3. By default Streamlit opens a browser; if not, check the terminal for the local URL (usually http://localhost:8501).

If you prefer a specific port:

```sh
# from interface folder
streamlit run app.py --server.port 8502

# or from repo root
streamlit run interface/app.py --server.port 8502
```

Note: If your Streamlit entrypoint filename is different (e.g., app.py or main.py), replace "app.py" above with the actual filename.

## Troubleshooting & tips

- If activation fails on PowerShell, you may need to change the execution policy (run PowerShell as Admin):

  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

- If dependencies fail, ensure you are using the correct Python version and that the venv is activated.
- To deactivate an environment:

  ```sh
  deactivate
  ```

- If Streamlit reports missing packages, re-check `requirements.txt` and reinstall inside the activated venv:

  ```sh
  pip install -r requirements.txt
  ```

## Notes

- Keep the correct venv activated for the folder you're working in.
- Use separate terminals for interface and ml environments if you need to run both simultaneously.
