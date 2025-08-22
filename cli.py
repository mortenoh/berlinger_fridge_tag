import os
import pprint
import sys
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from pydantic import ValidationError

from berlinger_fridge_tag.fridge_tag import parse_fridgetag_text_to_raw_dict
from berlinger_fridge_tag.fridge_tag_models import HistoryRecordInput, QTagDataInput

app = typer.Typer(
    name="fridgetag-cli",
    help="Command-line tool for parsing Berlinger FridgeTag TXT files.",
    add_completion=False,
)


def setup_logging(debug_mode: bool = False):
    """Configure logging with appropriate level and formatting."""
    logger.remove()
    log_level = "DEBUG" if debug_mode else "INFO"
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
    )


def validate_file_path(file_path: Path) -> None:
    """Validate that the file path exists, is a file, and is readable."""
    if not file_path.exists():
        logger.error(f"Error: File path '{file_path}' does not exist.")
        raise typer.Exit(1)
    if not file_path.is_file():
        logger.error(f"Error: File path '{file_path}' is not a file.")
        raise typer.Exit(1)
    if not os.access(file_path, os.R_OK):
        logger.error(f"Error: File path '{file_path}' is not readable.")
        raise typer.Exit(1)


def process_history_items(raw_dict: dict, debug: bool) -> None:
    """Process and validate history items from the raw dictionary."""
    hist_list_from_parser = raw_dict.get("Hist", [])
    if isinstance(hist_list_from_parser, list):
        logger.info(
            f"Pre-validating {len(hist_list_from_parser)} history items individually (Input models)..."
        )
        validated_input_hist_items = []
        for i, hist_item_raw_dict in enumerate(hist_list_from_parser):
            try:
                hr_input_model = HistoryRecordInput.model_validate(
                    hist_item_raw_dict
                )
                validated_input_hist_items.append(
                    hr_input_model.model_dump(by_alias=True)
                )
                if debug:
                    logger.debug(
                        f"Hist item {i} (Input) validated successfully: {hr_input_model.model_dump(by_alias=True)}"
                    )
            except ValidationError as e_hist_item:
                logger.error(
                    f"❌ Pydantic Validation failed for Hist item {i} (Input model):"
                )
                for error_detail in e_hist_item.errors():
                    logger.error(
                        f"  Field: {'.'.join(map(str, error_detail['loc'])) if error_detail['loc'] else 'General'}"
                    )
                    logger.error(f"  Message: {error_detail['msg']}")
                    logger.error(f"  Input: {error_detail['input']}")
            except Exception as e_gen_hist:
                logger.error(
                    f"❌ Unexpected error validating Hist item {i} (Input model): {e_gen_hist}"
                )

        raw_dict["Hist"] = validated_input_hist_items
        logger.info(
            f"Finished pre-validating history items. {len(validated_input_hist_items)} successfully prepared for QTagDataInput."
        )


@app.command()
def parse(
    file_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the FridgeTag .txt file to parse.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Enable debug logging for detailed output.",
        ),
    ] = False,
) -> None:
    """
    Parse a FridgeTag TXT file and output the structured data.
    
    This command parses a Berlinger FridgeTag TXT file, validates the data
    against Pydantic models, transforms it to the output format, and prints
    the structured data to stdout.
    """
    setup_logging(debug_mode=debug)
    
    # Validate file accessibility
    validate_file_path(file_path)
    
    logger.info(f"Starting parsing for file: {file_path}")

    try:
        # Parse the file
        raw_dict = parse_fridgetag_text_to_raw_dict(str(file_path))

        # Process history items
        process_history_items(raw_dict, debug)

        # Validate against input model
        logger.info("Validating parsed data against QTagDataInput model...")
        input_model = QTagDataInput.model_validate(raw_dict)
        logger.info("QTagDataInput validation successful.")

        # Transform to output model
        logger.info("Transforming QTagDataInput to QTagDataOutput model...")
        output_model = input_model.to_output()
        logger.info("Transformation to QTagDataOutput successful.")

        # Print results
        typer.echo("\n--- Parsed and Transformed FridgeTag Data (Output Model) ---")
        output_data_str = pprint.pformat(
            output_model.model_dump(mode="python", exclude_none=True), width=120
        )
        typer.echo(output_data_str)

    except ValidationError as e:
        logger.error("❌ Pydantic Validation failed:")
        for error_detail in e.errors():
            logger.error(
                f"  Field: {'.'.join(map(str, error_detail['loc'])) if error_detail['loc'] else 'General'}"
            )
            logger.error(f"  Message: {error_detail['msg']}")
            logger.error(f"  Input: {error_detail['input']}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show the version information."""
    typer.echo("Berlinger FridgeTag CLI v0.1.0")


if __name__ == "__main__":
    app()