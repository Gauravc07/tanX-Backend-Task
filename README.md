Here's a `README.md` file for your repository:

```markdown
# tanX Backend

This repository contains the backend code for the tanX application. It is built using Flask and can be run using Docker for easy setup and deployment.

## Prerequisites

Before you begin, ensure you have the following installed on your machine:

- [Docker](https://www.docker.com/get-started)
- [Python 3.8+](https://www.python.org/downloads/)

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/Gauravc07/tanX_backend.git
cd tanX_backend
```

### Build and Run with Docker

1. **Build the Docker Image**

    ```bash
    docker build -t tanx-backend .
    or
    docker-compose up -d --build
    ```

2. **Run the Docker Container**

    ```bash
    docker run -d -p 5000:5000 tanx-backend
    ```

    This command runs the container in detached mode and maps port 5000 of the container to port 5000 on your host machine.

### Run Locally with Flask

1. **Create a Virtual Environment**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

2. **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

3. **Run the Flask Application**

    ```bash
    export FLASK_APP=app.py  # On Windows, use `set FLASK_APP=app.py`
    flask run
    ```

    By default, the application will be available at `http://127.0.0.1:5000/`.

## Project Structure

```
tanX_backend/
│
├── app.py                # Main application file
├── Dockerfile            # Docker configuration file
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## API Endpoints

Gist link for accessing endpoint : https://gist.github.com/Gauravc07/86ce1e8531b4f3e5a0ad148575b25eb3


## Contact

Gaurav Chindhe - [gaurav.thakabhau2021@vitstudent.ac.in](mailto:gaurav.thakabhau2021@vitstudent.ac.in)


```
