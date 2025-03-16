# MailToPDF - Automatically Convert Emails to PDFs

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](optional_link_to_build_status)  <!-- Optional: Add a build status badge if you have CI/CD -->

MailToPDF is a Docker-based application that automatically fetches emails from an IMAP server, converts them to PDF documents, and saves them to a specified directory. This is useful for archiving, reporting, or any scenario where you need to convert email content into a portable, printable format.

## Features

*   **Automated Email Fetching:** Connects to an IMAP server and retrieves emails from a specified folder.
*   **PDF Conversion:** Converts email content (including HTML) to PDF using `wkhtmltopdf`.
*   **Configurable:** All settings, including IMAP credentials, folder names, and conversion options, are configurable via environment variables.
*   **Scheduled Processing:** Runs at regular intervals (configurable).
*   **Processed Folder:** Moves processed emails to a designated "Processed" folder on the IMAP server.
*   **Error Handling:**  Handles potential errors during email fetching and conversion.  Option to print detailed messages for failed conversions.
* **Host Blocking:** Allows specification of hosts to block.
* **Dockerized:**  Runs within a Docker container for easy deployment and portability.

## Prerequisites

*   **Docker:** You need to have Docker installed and running on your system.  [Get Docker](https://www.docker.com/get-started)
*   **Docker Compose:**  Docker Compose is also required. It usually comes bundled with Docker Desktop.
* **IMAP Access:** You need an email account with IMAP access enabled. For Gmail, you'll likely need to create an "App Password" since this application uses a password-based login.  *Do not use your regular Gmail password.*

## Getting Started

1.  **Clone the Repository:**

    ```bash
    git clone <your_repository_url>
    cd <your_repository_name>
    ```

2.  **Create `.env` File:**

    Create a file named `.env` in the project's root directory (same directory as `docker-compose.yml`). This file will contain your sensitive configuration.

    ```bash
    cp .env.example .env
    ```
    Now, open the `.env` file with a text editor and fill in your actual credentials and settings:

    ```dotenv
    IMAP_URL=imap.gmail.com  # Your IMAP server address
    IMAP_USERNAME=name@mail.com  # Your email address
    IMAP_PASSWORD=  # Your App Password (or email password)
    IMAP_FOLDER=PDF  # The folder to fetch emails from
    IMAP_TARGET_FOLDER=PDF/Processed # Where to move processed emails
    INTER_RUN_INTERVAL=600   # Interval in seconds between runs
    PRINT_FAILED_MSG=true  # Print detailed error messages for failed conversions
    HOSTS=127.0.0.1 tracking.paypal.com # Space-separated list of hosts to block
    WKHTMLTOPDF_OPTIONS={"load-media-error-handling":"ignore"}  # JSON object for wkhtmltopdf options
    OUTPUT_DIRECTORY=/data/pdfs    # Directory where PDFs will be saved (inside the container)
    ```

    **IMPORTANT:**
    *   Replace the placeholder values with your actual credentials.
    *   For Gmail, generate an App Password (search "Gmail App Password" for instructions).
    *   Do *not* commit the `.env` file to your repository! It contains sensitive information. It's already included in the `.gitignore`.

3.  **Build and Run the Container:**

    ```bash
    docker-compose up -d
    ```

    This command will:
    *   Build the Docker image (if it doesn't exist).
    *   Create and start the container in detached mode (`-d`).
    *   Use the settings from your `.env` file.

4.  **Check Logs:**

    To see the output and logs of the application:

    ```bash
    docker-compose logs -f mailtopdf
    ```
    The `-f` flag follows the log output, similar to `tail -f`.

5.  **Stop the Container:**

    ```bash
    docker-compose down
    ```

## Configuration

All configuration is done through environment variables in the `.env` file. Here's a breakdown of each variable:

| Variable Name        | Description                                                                   | Default Value |
|----------------------|-------------------------------------------------------------------------------|---------------|
| `IMAP_URL`           | The URL of your IMAP server.                                                   |               |
| `IMAP_USERNAME`      | Your email username (usually your full email address).                      |               |
| `IMAP_PASSWORD`      | Your email password (or App Password for Gmail).                              |               |
| `IMAP_FOLDER`        | The IMAP folder to fetch emails from.                                         | `Inbox`       |
| `IMAP_TARGET_FOLDER` | The IMAP folder to move processed emails to.                                  | `Processed`   |
| `INTER_RUN_INTERVAL` | The time interval (in seconds) between each run of the email processing.   | `60`          |
| `PRINT_FAILED_MSG` | Whether to print detailed error messages for failed conversions (`true` or `false`). | `false` |
| `HOSTS` | A space-separated list of hosts which will be mapped to 127.0.0.1| `127.0.0.1`          |
| `WKHTMLTOPDF_OPTIONS` | A JSON object containing options for `wkhtmltopdf`. See [wkhtmltopdf documentation](https://wkhtmltopdf.org/usage/wkhtmltopdf.txt) for details.  | `{}`        |
| `OUTPUT_DIRECTORY`   | The directory inside the container where PDFs will be saved.                 | `/data/pdfs`  |

**Example `WKHTMLTOPDF_OPTIONS`:**

To disable JavaScript execution and set a page size of A4:

```json
{"disable-javascript": true, "page-size": "A4"}