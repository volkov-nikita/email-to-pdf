#!/usr/bin/env python

import json
import os
from pathlib import Path

import pdfkit
from imap_tools import MailBox, AND, MailMessageFlags


# Constants
OUTPUT_DIRECTORY = Path(os.environ.get("OUTPUT_DIRECTORY", "/tmp"))
PDF_CONTENT_ERRORS = (
    "ContentNotFoundError",
    "ContentOperationNotPermittedError",
    "UnknownContentError",
    "RemoteHostClosedError",
    "ConnectionRefusedError",
    "Server refused a stream",
)
BAD_CHARACTERS = ["/", "*", ":", "<", ">", "|", '"', "’", "–"]
DEFAULT_IMAP_TARGET_FOLDER = "Processed"

# Ensure output directory exists
OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)


class EmailProcessingError(Exception):
    """Custom exception for email processing errors."""
    pass


def sanitize_filename(filename: str) -> str:
    """Sanitizes a string to be a valid filename."""
    for char in BAD_CHARACTERS:
        filename = filename.replace(char, "_")
    return filename


def get_pdfkit_options() -> dict:
    """Retrieves and parses PDFKit options from environment variables."""
    options_str = os.environ.get("WKHTMLTOPDF_OPTIONS")
    return json.loads(options_str) if options_str else {}


def get_mail_message_flag() -> tuple[str, bool]:
    """Retrieves the mail message flag and its state (add/remove) from env."""
    flag_str = os.environ.get("MAIL_MESSAGE_FLAG", "SEEN").upper()
    flag_map = {
        "ANSWERED": (MailMessageFlags.ANSWERED, True),
        "FLAGGED": (MailMessageFlags.FLAGGED, True),
        "UNFLAGGED": (MailMessageFlags.FLAGGED, False),
        "DELETED": (MailMessageFlags.DELETED, True),
        "SEEN": (MailMessageFlags.SEEN, True),
    }
    # Default to SEEN if not a recognized flag
    return flag_map.get(flag_str, (MailMessageFlags.SEEN, True))


def get_imap_filter(mail_message_flag: tuple[str, bool]) -> AND:
    """Retrieves IMAP filter criteria from environment, or derives it."""
    filter_criteria = os.environ.get("IMAP_FILTER")
    if filter_criteria:
        return filter_criteria  # User-defined filter takes precedence

    flag, state = mail_message_flag
    if flag == MailMessageFlags.SEEN:
        return AND(seen=(not state))
    elif flag == MailMessageFlags.ANSWERED:
        return AND(answered=(not state))
    elif flag == MailMessageFlags.FLAGGED:
        return AND(flagged=(not state))
    elif flag == MailMessageFlags.DELETED and state:
        return AND(all=True)  # Searching for undeleted doesn't make sense
    else:
        raise ValueError(
            "Could not determine IMAP filter from mail message flag. "
            "You must specify the filter manually."
        )


def html_to_pdf(html_content: str, filename: str, pdfkit_options: dict) -> Path:
    """Converts HTML content to a PDF file.

    Args:
        html_content: The HTML content to convert.
        filename: The desired filename (without extension).
        pdfkit_options:  Options for pdfkit.

    Returns:
        The Path to the generated PDF file.

    Raises:
        EmailProcessingError: If PDF generation fails due to content errors.
    """
    sanitized_filename = sanitize_filename(filename)
    output_path = OUTPUT_DIRECTORY / f"{sanitized_filename[:50]}.pdf"

    try:
        pdfkit.from_string(
            html_content, output_path, options=pdfkit_options
        )  # Corrected options
        return output_path
    except OSError as e:
        if any(error in str(e) for error in PDF_CONTENT_ERRORS):
            msg = (
                f"Error generating PDF for '{filename}'.  "
                f"Likely content issue: {e}"
            )
            raise EmailProcessingError(msg) from e
        else:
            # Re-raise other OSErrors
            raise


def process_email(
    imap_url: str,
    imap_username: str,
    imap_password: str,
    imap_folder: str,
    mail_msg_flag: tuple[str, bool],
    filter_criteria: AND,
    num_emails_limit: int = 50,
    print_failed_message: bool = False,
) -> None:
    """Processes emails from an IMAP server, converting HTML content to PDF.

    Args:
        imap_url: IMAP server URL.
        imap_username: IMAP username.
        imap_password: IMAP password.
        imap_folder: IMAP folder to process.
        mail_msg_flag:  Tuple of (MailMessageFlag, bool) for flagging messages.
        filter_criteria: IMAP filter criteria.
        num_emails_limit: Maximum number of emails to process.
        print_failed_message: Whether to print the body of failed emails.

    Raises:
        EmailProcessingError:  If an unhandled exception occurs, or if moving the processed email fails.
    """
    print("Starting mail processing run", flush=True)
    if print_failed_message:
        print("*On failure, the Body of the email will be printed*")

    pdfkit_options = get_pdfkit_options()
    target_folder = os.environ.get("IMAP_TARGET_FOLDER", DEFAULT_IMAP_TARGET_FOLDER)

    try:
        with MailBox(imap_url).login(
            imap_username, imap_password, imap_folder
        ) as mailbox:
            for msg in mailbox.fetch(
                criteria=filter_criteria, limit=num_emails_limit, mark_seen=False
            ):
                if msg.attachments:
                    # Skip emails that contain attachments
                    continue

                print(f"\nProcessing: {msg.subject}")
                pdf_content = (
                    '<meta http-equiv="Content-type" content="text/html; charset=utf-8"/>'
                    + msg.html
                    if msg.html.strip()
                    else msg.text
                )

                try:
                    output_path = html_to_pdf(
                        pdf_content, msg.subject, pdfkit_options
                    )
                    print(f"Saved PDF: {output_path}")
                except EmailProcessingError as e:
                    print(f"\n**** HANDLED EXCEPTION ****\n{e}")
                    if print_failed_message:
                        print(f"\n{pdf_content}\n")
                    continue  # Continue to the next email
                except Exception as e:
                    print(f"\n!!!! UNHANDLED EXCEPTION !!!!\n{e}")
                    if print_failed_message:
                        print(f"\n{pdf_content}\n")
                    raise EmailProcessingError("Unhandled exception during PDF creation") from e

                if mail_msg_flag and mail_msg_flag[0] in MailMessageFlags.all:
                    mailbox.flag(msg.uid, mail_msg_flag[0], mail_msg_flag[1])
                try:
                    mailbox.move(msg.uid, target_folder)
                    print(f"Moved email '{msg.subject}' to folder '{target_folder}'.")
                except Exception as e:
                    raise EmailProcessingError(f"Failed to move email '{msg.subject}' to folder '{target_folder}': {e}")


    except Exception as e: # Catch any other exception during the IMAP connection
        raise EmailProcessingError(f"An error occurred during IMAP processing: {e}")

    print("FIN Completed mail processing run\n\n", flush=True)


def main():
    """Main function to drive the email processing."""
    imap_url = os.environ.get("IMAP_URL")
    imap_username = os.environ.get("IMAP_USERNAME")
    imap_password = os.environ.get("IMAP_PASSWORD")
    imap_folder = os.environ.get("IMAP_FOLDER")
    print_failed_message = os.environ.get("PRINT_FAILED_MSG", "False") == "True"

    mail_msg_flag = get_mail_message_flag()
    filter_criteria = get_imap_filter(mail_msg_flag)

    print("Running emails-html-to-pdf")

    try:
        process_email(
            imap_url=imap_url,
            imap_username=imap_username,
            imap_password=imap_password,
            imap_folder=imap_folder,
            mail_msg_flag=mail_msg_flag,
            filter_criteria=filter_criteria,
            print_failed_message=print_failed_message,
        )
    except EmailProcessingError as e:
        print(f"Error during email processing: {e}")
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:  # Catch-all for unexpected errors.
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()