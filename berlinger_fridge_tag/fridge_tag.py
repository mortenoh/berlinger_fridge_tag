from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


def parse_history_line_to_dict(line_content: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single space-delimited history line into a dictionary.
    Expected format: Date MinT TSMinT MaxT TSMaxT AvrgT Alarm_tAcc Alarm_TSA Alarm_CA IST_tAccST Events Chk_TSAM Chk_TSPM
    Example: "2022-10-10 -12.3 08:10 +0.1 10:20 -10.0 10 00:00 --- --- 0 --- ---"
    """
    parts = line_content.split()

    if len(parts) < 13:
        logger.error(
            f"History line has too few parts ({len(parts)} expected at least 13): '{line_content}'"
        )
        return None

    def get_part(index: int) -> Optional[str]:
        try:
            val = parts[index]
            return None if val == "---" else val
        except IndexError:
            logger.warning(
                f"Missing part at index {index} in history line: '{line_content}'"
            )
            return None

    try:
        alarm_data = {
            "t Acc": get_part(6),
            "TS A": get_part(7),
            "C A": get_part(8),
        }
        int_sensor_timeout_data = {
            "t AccST": get_part(9),
        }
        checked_data = {
            "TS AM": get_part(11),
            "TS PM": get_part(12),
        }

        entry = {
            "Date": get_part(0),
            "Min T": get_part(1),
            "TS Min T": get_part(2),
            "Max T": get_part(3),
            "TS Max T": get_part(4),
            "Avrg T": get_part(5),
            "Alarm": alarm_data
            if any(v is not None for v in alarm_data.values())
            else None,
            "Int Sensor timeout": int_sensor_timeout_data
            if any(v is not None for v in int_sensor_timeout_data.values())
            else None,
            "Events": get_part(10),
            "Checked": checked_data
            if any(v is not None for v in checked_data.values())
            else None,
        }
        return entry
    except Exception as e:
        logger.error(f"Unexpected error parsing history line '{line_content}': {e}")
        return None


def parse_fridgetag_text_to_raw_dict(file_path: str) -> dict[str, Any]:
    """
    Parses a FridgeTag text file into a raw dictionary structure.
    This dictionary is intended to be validated by Pydantic Input models.
    """
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(0, result)]

    def insert(indent: int, key: str, value: Any, current_line_number: int) -> None:
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()

        parent_dict = stack[-1][1]

        if (
            key in parent_dict
            and isinstance(parent_dict[key], dict)
            and isinstance(value, dict)
        ):
            logger.debug(
                f"Line {current_line_number}: Updating existing dict key '{key}' in parent."
            )
            parent_dict[key].update(value)
        else:
            logger.debug(
                f"Line {current_line_number}: Setting key '{key}' in parent to value: {value}"
            )
            parent_dict[key] = value

        if isinstance(value, dict):
            # Avoid pushing simple string values for these keys if they are at top-level
            # (though current logic places them under 'Hist' initially)
            if not (
                key in ("TS Actv", "TS Report Creation") and not isinstance(value, dict)
            ):
                logger.debug(
                    f"Line {current_line_number}: Pushing new dict for key '{key}' onto stack."
                )
                stack.append((indent, value))
            else:
                logger.debug(
                    f"Line {current_line_number}: Key '{key}' is top-level, not pushing its value to stack."
                )

    file_content = Path(file_path).read_text(encoding="utf-8")
    for line_num, line_text in enumerate(file_content.splitlines(), 1):
        if not line_text.strip():
            logger.debug(f"Line {line_num}: Skipping empty line.")
            continue

        indent = len(line_text) - len(line_text.lstrip())
        content = line_text.strip()
        logger.debug(
            f"Line {line_num}: Processing line with indent {indent}: '{content}'"
        )

        if ":" in content:
            primary_key, value_part = map(str.strip, content.split(":", 1))

            if not value_part:
                logger.debug(
                    f"Line {line_num}: Primary key '{primary_key}' starts a new section (dictionary)."
                )
                insert(indent, primary_key, {}, line_num)
            else:
                is_section_header_key = primary_key.isdigit() or primary_key in (
                    "Conf",
                    "Cert",
                    "Alarm",
                    "Int Sensor",
                    "Hist",
                    "Checked",
                )

                if is_section_header_key and ": " in value_part:
                    logger.debug(
                        f"Line {line_num}: Key '{primary_key}' is a dict header. Parsing '{value_part}' for its items."
                    )
                    sub_dict_for_primary_key = {}
                    insert(indent, primary_key, sub_dict_for_primary_key, line_num)

                    sub_parts = [p.strip() for p in value_part.split(", ")]
                    for sub_part in sub_parts:
                        if ":" in sub_part:
                            sk, sv = map(str.strip, sub_part.split(":", 1))
                            logger.debug(
                                f"Line {line_num}: Adding sub-key '{sk}':'{sv}' to dict of '{primary_key}'."
                            )
                            sub_dict_for_primary_key[sk] = sv
                        else:
                            logger.warning(
                                f"Line {line_num}: Malformed segment '{sub_part}' in value for dict header '{primary_key}'. Expected key:value."
                            )
                else:
                    parts = [p.strip() for p in value_part.split(", ")]
                    logger.debug(
                        f"Line {line_num}: Assigning value '{parts[0]}' to primary key '{primary_key}'."
                    )
                    insert(indent, primary_key, parts[0], line_num)

                    if len(parts) > 1:
                        parent_for_siblings = stack[-1][1]
                        if isinstance(parent_for_siblings.get(primary_key), dict):
                            logger.debug(
                                f"Line {line_num}: Primary key '{primary_key}' is a dict. Sibling keys will be added to its parent."
                            )
                            correct_parent_indent = -1
                            for i in range(len(stack) - 1, -1, -1):
                                if stack[i][0] < indent:
                                    correct_parent_indent = stack[i][0]
                                    parent_for_siblings = stack[i][1]
                                    break
                            if correct_parent_indent == -1:
                                parent_for_siblings = result

                        for i in range(1, len(parts)):
                            part = parts[i]
                            if ":" in part:
                                sk, sv = map(str.strip, part.split(":", 1))
                                logger.debug(
                                    f"Line {line_num}: Adding sibling key '{sk}':'{sv}' to parent of '{primary_key}'."
                                )
                                parent_for_siblings[sk] = sv
                            else:
                                logger.warning(
                                    f"Line {line_num}: Malformed sibling segment '{part}' for '{primary_key}', expected key:value."
                                )
        else:
            logger.warning(
                f"Line {line_num}: Line without colon treated as unstructured data or value for previous key if applicable: '{content}'."
            )
            pass  # Explicitly do nothing for now

    # Post-processing for 'Hist' section (moving specific keys and converting day entries)
    logger.debug(
        f"State of result['Hist'] BEFORE post-processing: {result.get('Hist')}"
    )
    logger.debug(
        f"Type of result['Hist'] BEFORE post-processing: {type(result.get('Hist'))}"
    )

    raw_hist_data = result.get("Hist")
    processed_hist_list_for_days: List[Dict[str, Any]] = []

    if isinstance(raw_hist_data, dict):
        logger.info(
            "Post-processing 'Hist' dictionary: extracting specific fields and converting day entries to a list."
        )

        if "TS Actv" in raw_hist_data:
            key_from_text = "TS Actv"
            value = raw_hist_data.pop(key_from_text)
            result[key_from_text] = (
                value  # Use key with space, matching the alias for QTagDataInput
            )
            logger.debug(
                f"Moved '{key_from_text}' from Hist to top level: {result.get(key_from_text)}"
            )
        if "TS Report Creation" in raw_hist_data:
            key_from_text = "TS Report Creation"
            value = raw_hist_data.pop(key_from_text)
            result[key_from_text] = (
                value  # Use key with space, matching the alias for QTagDataInput
            )
            logger.debug(
                f"Moved '{key_from_text}' from Hist to top level: {result.get(key_from_text)}"
            )

        sorted_hist_keys = sorted(
            raw_hist_data.keys(),
            key=lambda k: int(k.rstrip(":"))
            if k.rstrip(":").isdigit()
            else float("inf"),
        )
        for key in sorted_hist_keys:
            history_entry_dict = raw_hist_data[key]
            if isinstance(history_entry_dict, dict):
                logger.debug(
                    f"Adding pre-parsed daily history entry for key '{key}' to list."
                )
                processed_hist_list_for_days.append(history_entry_dict)
            else:
                logger.error(
                    f"Hist item for key '{key}' is NOT a dictionary as expected for a day record and was not moved. Type: {type(history_entry_dict)}. Value: {history_entry_dict}"
                )

        logger.debug(
            f"Final list of daily history records: {processed_hist_list_for_days}"
        )
        result["Hist"] = processed_hist_list_for_days

    elif raw_hist_data is not None:
        logger.warning(
            f"'Hist' section found but is not a dictionary as expected for post-processing. Type: {type(raw_hist_data)}. Value: {raw_hist_data}. It will not be processed into a list of days, and 'TS Actv' etc. cannot be extracted."
        )
        result["Hist"] = []
    else:
        logger.info(
            "'Hist' section not found or is None. Initializing Hist to empty list for Pydantic model."
        )
        result["Hist"] = []

    return result
