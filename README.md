# Berlinger Fridge-tag Parser

## What This Project Does

This Python library parses data files exported from Berlinger Fridge-tag temperature monitoring devices and converts them into structured JSON format. The parsed data can be integrated with DHIS2 (District Health Information System 2) for comprehensive cold chain monitoring in healthcare facilities.

The project provides both a command-line interface (CLI) for batch processing and a REST API for web-based integration, making it easy to incorporate Fridge-tag data into existing health information systems and workflows.

## About Berlinger Fridge-tags

Berlinger Fridge-tag devices are intelligent temperature monitors specifically designed for vaccine cold chain monitoring in healthcare facilities. These devices are critical for maintaining vaccine efficacy by ensuring proper storage temperatures.

### Key Features of Fridge-tag Devices:
- **Continuous Monitoring**: Measure temperature every minute with ±0.5°C accuracy
- **Programmable Alarms**: Immediate alerts when temperature exceeds safe ranges (+2°C to +8°C for vaccines)
- **Long Battery Life**: Up to 3 years of continuous operation (Fridge-tag 2L)
- **Compliance**: Meet CDC & VFC (Vaccines for Children) Program requirements
- **Data Logging**: Store up to 60 days of detailed temperature history
- **PDF Reports**: Generate automatic reports without additional software

### Supported Models:
- **Fridge-tag 2**: Basic ambient temperature monitoring with immediate alerts
- **Fridge-tag 2L**: High precision data logger with extended 3-year battery life
- **Fridge-tag 2E**: 30-day electronic temperature recorder optimized for vaccine storage

## Getting Started

### Installation

1. **Clone the repository** (if applicable) or ensure you have the project files
2. **Install dependencies** using one of these methods:

```bash
# Using uv (recommended)
uv sync
```

## Running with Command Line Interface (CLI)

### Step 1: Prepare Your Fridge-tag Data File
- Export data from your Berlinger Fridge-tag device as a TXT file
- Ensure the file is accessible on your local filesystem
- Example file might be named like: `160400343951_202506111034_20250611T083422Z.txt`

### Step 2: Process the File
```bash
# Basic processing
uv run cli.py process-file path/to/your/fridgetag_data.txt

# With debug output for detailed logging
uv run cli.py process-file path/to/your/fridgetag_data.txt --debug

# Example with the provided sample file
uv run cli.py process-file data/160400343951_202506111034_20250611T083422Z.txt
```

### Step 3: Review Output
The CLI will:
- Parse the Fridge-tag text file
- Validate the data structure
- Output structured JSON to the console
- Display any validation errors or warnings

## Running with REST API

### Step 1: Start the API Server
```bash
# Option 1: Using uv (recommended)
uv run run_api.py

# Option 2: Direct uvicorn command
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will start on `http://localhost:8000`

### Step 2: Verify API is Running
Open your browser and go to:
- **API docs**: `http://localhost:8000/docs` (interactive Swagger UI)
- **Health check**: `http://localhost:8000/` (basic status endpoint)

### Step 3: Upload and Process Fridge-tag Files

#### Using curl:
```bash
# Upload and parse a file
curl -X POST "http://localhost:8000/parse-fridgetag/" \
  -F "file=@path/to/your/fridgetag_data.txt" \
  -F "debug=false"

# With debug enabled
curl -X POST "http://localhost:8000/parse-fridgetag/" \
  -F "file=@data/160400343951_202506111034_20250611T083422Z.txt" \
  -F "debug=true"
```

#### Using the Interactive API Docs:
1. Go to `http://localhost:8000/docs`
2. Click on **POST /parse-fridgetag/**
3. Click **"Try it out"**
4. Click **"Choose File"** and select your Fridge-tag TXT file
5. Set debug to `true` or `false`
6. Click **"Execute"**

### Step 4: Process the Response
The API returns a JSON response with:
```json
{
  "success": true,
  "filename": "your_fridgetag_file.txt",
  "data": {
    "deviceType": "Q-Tag",
    "softwareVersion": "1.0",
    "historyRecords": [...],
    "configuration": {...},
    "certificate": {...}
  }
}
```

## Data Structure

The parser extracts and structures the following information:

- **Device Configuration**: Serial number, firmware version, alarm settings
- **Temperature History**: Daily min/max/average temperatures with timestamps
- **Alarm Records**: Temperature excursions and alarm events
- **Sensor Information**: Internal sensor data and calibration info
- **Certificate Data**: Device authentication and validation info

## DHIS2 Integration

This library is designed to integrate with DHIS2's cold chain equipment monitoring module. Berlinger Fridge-tags are validated compatible with DHIS2 platform and meet WHO PQS EMS standards for immunization programs.

The structured output format enables:
- Cold chain analytics and insights
- Compliance monitoring for vaccine storage
- Integration with existing health information workflows
- Real-time temperature monitoring alerts

## Python Library Usage

For programmatic use in your own applications:

```python
from berlinger_fridge_tag.fridge_tag import parse_fridgetag_text_to_raw_dict
from berlinger_fridge_tag.fridge_tag_models import QTagDataInput

# Parse raw text file
raw_data = parse_fridgetag_text_to_raw_dict("fridgetag_data.txt")

# Validate with Pydantic models
input_model = QTagDataInput.model_validate(raw_data)
output_model = input_model.to_output()

# Get structured data
structured_data = output_model.model_dump(exclude_none=True)
```

## Testing

```bash
# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=berlinger_fridge_tag
```

## Code Formatting

This project uses ruff for code formatting with a line width of 120 characters:

```bash
# Format code
uv run ruff format

# Check formatting
uv run ruff format --check

# Run linting
uv run ruff check
```

## File Format Support

Supports Berlinger Fridge-tag text export files from:
- Fridge-tag 2: Ambient temperature monitoring with immediate alerts
- Fridge-tag 2L: High precision data logger (3-year battery life)  
- Fridge-tag 2E: 30-day electronic temperature recorder for vaccines

## Requirements

- Python 3.13+
- FastAPI for REST API
- Pydantic for data validation
- Loguru for logging
- Typer for CLI interface

## License

[Add license information]

## Contributing

[Add contribution guidelines]