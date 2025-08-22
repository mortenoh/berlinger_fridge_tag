import tempfile
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from berlinger_fridge_tag.fridge_tag import parse_fridgetag_text_to_raw_dict
from berlinger_fridge_tag.fridge_tag_models import HistoryRecordInput, QTagDataInput

app = FastAPI(
    title="Berlinger Fridge Tag API",
    version="0.1.0",
    description="REST API for parsing Berlinger Fridge-tag temperature monitoring data files and integrating with DHIS2 cold chain monitoring systems",
    contact={
        "name": "DHIS2 Core Team",
        "url": "https://dhis2.org",
    },
    license_info={
        "name": "BSD 3-Clause",
    },
)


def process_file_content(file_content: bytes, debug: bool = False) -> Dict[str, Any]:
    """
    Processes uploaded Berlinger Fridge-tag file content and returns structured temperature data.
    
    Takes raw file bytes, parses the Fridge-tag text format, validates the data using
    Pydantic models, and transforms it into a structured JSON format suitable for
    DHIS2 cold chain monitoring integration.
    
    Args:
        file_content (bytes): Raw bytes from uploaded Fridge-tag text file
        debug (bool): Enable detailed logging for debugging purposes
        
    Returns:
        Dict[str, Any]: Structured temperature monitoring data in camelCase format
        
    Raises:
        ValidationError: If the file content doesn't match expected Fridge-tag format
        Exception: If file processing fails for other reasons
    """
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    try:
        logger.info(f"Starting parsing for uploaded file")

        raw_dict = parse_fridgetag_text_to_raw_dict(temp_file_path)

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

        return output_model.model_dump(mode="python", exclude_none=True)

    finally:
        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)


@app.post("/parse-fridgetag/")
async def parse_fridgetag_file(file: UploadFile = File(...), debug: bool = False):
    """
    Upload and parse a Berlinger Fridge-tag temperature monitoring data file.
    
    Accepts a Fridge-tag TXT export file and processes it into structured JSON format
    suitable for integration with DHIS2 cold chain monitoring systems.
    
    Supported Fridge-tag models:
    - Fridge-tag 2: Ambient temperature monitoring with immediate alerts
    - Fridge-tag 2L: High precision data logger (3-year battery life)
    - Fridge-tag 2E: 30-day electronic temperature recorder for vaccines
    
    Args:
        file: Uploaded Fridge-tag text file (must have .txt extension)
        debug: Enable detailed validation logging and error reporting
        
    Returns:
        JSONResponse: Structured temperature data with device info, history records, 
                     alarm events, and configuration details
        
    Raises:
        HTTPException 400: If file is not a .txt file
        HTTPException 422: If file content fails validation
        HTTPException 500: If unexpected processing error occurs
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="File must be a .txt file")
    
    try:
        file_content = await file.read()
        result = process_file_content(file_content, debug=debug)
        
        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "data": result
        })
        
    except ValidationError as e:
        error_details = []
        for error_detail in e.errors():
            error_details.append({
                "field": '.'.join(map(str, error_detail['loc'])) if error_detail['loc'] else 'General',
                "message": error_detail['msg'],
                "input": str(error_detail['input'])
            })
        
        raise HTTPException(status_code=422, detail={
            "message": "Pydantic Validation failed",
            "errors": error_details
        })
        
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.get("/")
async def root():
    """
    API health check and information endpoint.
    
    Returns basic information about the Berlinger Fridge-tag API service
    and confirms that it's running and ready to process temperature monitoring files.
    
    Returns:
        dict: API status message and service information
    """
    return {
        "message": "Berlinger Fridge Tag API is running",
        "service": "Temperature monitoring data parser for DHIS2 cold chain integration",
        "supported_devices": ["Fridge-tag 2", "Fridge-tag 2L", "Fridge-tag 2E"],
        "version": "0.1.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)