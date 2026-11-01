# Documentation

## Overview

The Cups Dymo Label Printer project provides a modern, web-based interface for printing labels on a Dymo LabelWriter 450. The system uses CUPS (Common Unix Printing System) as the printing backend and offers a Flask-based web application for easy label design and printing.

## Architecture

### Components

1. **CUPS Server**: Handles communication with the Dymo printer
2. **Flask Web App**: Provides user interface and REST API
3. **Label Generator**: Creates label images with specified text and formatting
4. **Printer Service**: Interfaces with CUPS for print job submission

### Data Flow

```text
User -> Web Interface -> Flask Routes -> Label Generator -> Printer Service -> CUPS -> Dymo Printer
```

## Module Documentation

### config.py

Contains all configuration constants including:

- Label size definitions (LABEL_SIZES)
- Default values (DPI, font size, printer name)
- Font paths

### label_generator.py

Responsible for creating label images:

- `create_label_image()`: Main function for generating label PIL images
- Text positioning based on alignment
- Font loading with fallback to default
- DPI-based dimension calculations

### printer_service.py

Handles CUPS communication:

- `PrinterService` class for managing printer operations
- `print_image()`: Submit print jobs to CUPS
- Temporary file management
- Print options configuration

### web_app.py

Flask application with routes:

- `/`: Main label design interface
- `/print`: Submit print job (POST)
- `/preview`: Validate label parameters (POST)
- `/status`: Get printer status (GET)

## Deployment

The application is deployed using Docker with a multi-stage build:

**Stage 1 (Builder)**:

- Compiles Dymo SDK from source
- Downloads and extracts Dymo CUPS drivers
- Creates PPD files

**Stage 2 (Runtime)**:

- Minimal runtime dependencies
- Copies compiled artifacts from builder
- Installs Python packages
- Sets up CUPS configuration

## Environment Variables

- `CUPS_ADMIN_PASSWORD`: Password for CUPS admin user (default: "admin")

## Testing Strategy

Tests should cover:

1. Label image generation with various parameters
2. Text positioning calculations
3. Print job submission (mocked CUPS)
4. Flask route responses
5. Error handling

Use pytest with mocking for external dependencies (CUPS, filesystem).

## Future Enhancements

- Real-time preview image generation
- Barcode/QR code support
- Label templates
- Batch printing from CSV
- Mobile-responsive design improvements
