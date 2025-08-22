import argparse
import os
import pprint
import sys
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from berlinger_fridge_tag.fridge_tag import parse_fridgetag_text_to_raw_dict
from berlinger_fridge_tag.fridge_tag_models import HistoryRecordInput, QTagDataInput


def setup_logging(debug_mode: bool = False):
    logger.remove()
    log_level = "DEBUG" if debug_mode else "INFO"
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
    )


def process_file(file_path_str: str, debug: bool = False):
    """
    Parses a FridgeTag TXT file, validates the data, transforms it to an output model,
    and prints the structured data.
    """
    setup_logging(debug_mode=debug)

    file_path = Path(file_path_str)
    if not file_path.exists():
        logger.error(f"Error: File path '{file_path_str}' does not exist.")
        sys.exit(1)
    if not file_path.is_file():
        logger.error(f"Error: File path '{file_path_str}' is not a file.")
        sys.exit(1)
    if not os.access(file_path, os.R_OK):
        logger.error(f"Error: File path '{file_path_str}' is not readable.")
        sys.exit(1)

    logger.info(f"Starting parsing for file: {file_path}")

    try:
        raw_dict = parse_fridgetag_text_to_raw_dict(str(file_path))

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

        logger.info("Validating parsed data against QTagDataInput model...")
        input_model = QTagDataInput.model_validate(raw_dict)
        logger.info("QTagDataInput validation successful.")

        logger.info("Transforming QTagDataInput to QTagDataOutput model...")
        output_model = input_model.to_output()
        logger.info("Transformation to QTagDataOutput successful.")

        print("\n--- Parsed and Transformed FridgeTag Data (Output Model) ---")
        output_data_str = pprint.pformat(
            output_model.model_dump(mode="python", exclude_none=True), width=120
        )
        print(output_data_str)

    except ValidationError as e:
        logger.error("❌ Pydantic Validation failed:")
        for error_detail in e.errors():
            logger.error(
                f"  Field: {'.'.join(map(str, error_detail['loc'])) if error_detail['loc'] else 'General'}"
            )
            logger.error(f"  Message: {error_detail['msg']}")
            logger.error(f"  Input: {error_detail['input']}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parses a FridgeTag TXT file.")
    parser.add_argument(
        "file_path_str",
        metavar="FILE_PATH",
        type=str,
        help="Path to the FridgeTag .txt file.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    process_file(args.file_path_str, args.debug)
