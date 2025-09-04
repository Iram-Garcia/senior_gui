# senior_gui

<!-- ...existing code... -->

## Setting Up Python Virtual Environments

This project uses two separate Python virtual environments:

- One for the `interface` folder
- One for the `ml` folder

Follow these steps to set up each environment and install dependencies:

### 1. Interface Environment

1. Open a terminal and navigate to the `interface` folder:

    ```sh
    cd interface
    ```

2. Create a new virtual environment (e.g., named `venv_interface`):

    ```sh
    python -m venv venv_interface
    ```

3. Activate the environment:
    - **Windows:**

      ```sh
      venv_interface\Scripts\activate
      ```

    - **macOS/Linux:**

      ```sh
      source venv_interface/bin/activate
      ```

4. Install dependencies from `requirements.txt`:

    ```sh
    pip install -r requirements.txt
    ```

### 2. ML Environment

1. Open a new terminal and navigate to the `ml` folder:

    ```sh
    cd ml
    ```

2. Create a new virtual environment (e.g., named `venv_ml`):

    ```sh
    python -m venv venv_ml
    ```

3. Activate the environment:
    - **Windows:**

      ```sh
      venv_ml\Scripts\activate
      ```

    - **macOS/Linux:**

      ```sh
      source venv_ml/bin/activate
      ```

4. Install dependencies from `requirements.txt`:

    ```sh
    pip install -r requirements.txt
    ```

### Notes

- Make sure you have Python installed (preferably Python 3.8+).
- Always activate the correct environment before running code in its respective folder.
- To deactivate an environment, simply run:

    ```sh
    deactivate
    ```

## Running the Application

To run the Streamlit application:

1. Ensure you are in the `interface` folder and have activated the `venv_interface` environment (as described above).
2. Run the following command (replace `app.py` with the actual name of your main Streamlit file if different):

    ```sh
    streamlit run app.py
    ```

3. The application should open in your default web browser.

**Reminder:** Always activate the `venv_interface` environment before running the app to ensure the correct dependencies are used.

<!-- ...existing code... -->