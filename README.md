# Cups Dymo Label Printer

A web-based label printing solution for Dymo LabelWriter 450 using CUPS in a Docker container.

## Features

- 🎨 Beautiful web interface for designing labels
- 📏 Support for multiple Dymo label sizes (11354, 30252, 30323, 30256, 99012)
- ↔️ Text alignment options (left, center, right)
- 🔢 Customizable font size
- 🖨️ Multiple copy printing
- 🐳 Fully containerized with Docker
- 🔒 Secure CUPS admin authentication

## Architecture

This project runs CUPS (Common Unix Printing System) and a Flask web application in a Docker container on a Raspberry Pi (or any Linux host), making the Dymo LabelWriter 450 accessible over the network.

## Project Structure

```text
python-Cups-Dymo-LabelWriter450/
├── cups_dymo_label_printer/    # Main Python package
│   ├── __init__.py
│   ├── config.py               # Label sizes and configuration
│   ├── label_generator.py      # Label image generation
│   ├── printer_service.py      # CUPS interface
│   ├── web_app.py             # Flask web application
│   └── templates/             # HTML templates
├── tests/                      # Test suite (TDD)
├── docs/                       # Documentation
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml         # Container orchestration
├── cupsd.conf                 # CUPS configuration
├── setup.sh                   # Container startup script
├── pyproject.toml             # Poetry dependencies
└── README.md                  # This file
```

## Installation

### Prerequisites

- Docker and Docker Compose
- Dymo LabelWriter 450 connected via USB
- Linux host (tested on Raspberry Pi Zero W)

### Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd python-Cups-Dymo-LabelWriter450
   ```

2. Create environment file:

   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set your CUPS admin password:

   ```bash
   CUPS_ADMIN_PASSWORD=your_secure_password
   ```

4. Build and start the container:

   ```bash
   docker compose up -d --build
   ```

## Usage

### Web Interface

Access the label printing interface at:

```text
http://[raspberry-pi-ip]:5000
```

1. Enter your label text
2. Select label size (default: 11354 - 2-1/4" x 1-1/4")
3. Adjust font size (10-200)
4. Choose text alignment
5. Set number of copies
6. Click "Print Label"

### CUPS Admin Interface

Access CUPS administration at:

```text
http://[raspberry-pi-ip]:631
```

Login with:

- Username: `cupsadmin`
- Password: (from your `.env` file)

### Command Line Printing

Print from any computer on the network:

```bash
lp -h [pi-ip]:631 -d dymo -o media=w162h90 -o fit-to-page myfile.txt
```

## Development

### With Poetry (Local Development)

1. Install Poetry:

   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install dependencies:

   ```bash
   poetry install
   ```

3. Activate virtual environment:

   ```bash
   poetry shell
   ```

4. Run tests (when available):

   ```bash
   pytest
   pytest --cov  # With coverage
   ```

### Docker Development

Rebuild after code changes:

```bash
docker compose down
docker compose up --build -d
```

View logs:

```bash
docker logs -f Cups
```

## Testing

This project follows Test-Driven Development (TDD) principles. Tests will be located in the `tests/` directory and can be run with pytest.

```bash
poetry run pytest
poetry run pytest --cov=cups_dymo_label_printer
```

## Supported Label Sizes

| Code | Description | Dimensions |
| ------- | ------------- | ------------ |
| 11354 | Multipurpose | 2-1/4" x 1-1/4" (57x32mm) |
| 30252 | Address | 1-1/8" x 3-1/2" (28x89mm) |
| 30323 | Shipping | 2-1/8" x 4" (54x101mm) |
| 30256 | Shipping | 2-5/16" x 4" (59x101mm) |
| 99012 | Large Address | 3-1/2" x 1-1/8" (89x36mm) |

## API Endpoints

- `GET /` - Web interface
- `POST /preview` - Preview label (validation)
- `POST /print` - Print label
- `GET /status` - Printer status

## Security Notes

- CUPS admin interface requires authentication
- Admin pages restricted to local network
- Environment variables for sensitive configuration
- No hardcoded credentials

## Troubleshooting

### Printer not detected

1. Check USB connection:

   ```bash
   lsusb
   ```

2. Check CUPS backend:

   ```bash
   docker exec Cups lpinfo -v
   ```

3. Restart container:

   ```bash
   docker compose restart
   ```

### Power issues (Raspberry Pi Zero)

The Pi Zero may not provide enough USB power for the printer. Consider:

- Using a powered USB hub
- Upgrading to Pi 3/4

## Contributing

This project follows TDD principles. Before contributing:

1. Write failing tests for new features
2. Implement minimal code to pass tests
3. Refactor while keeping tests passing
4. Ensure all tests pass before committing

## License

[Specify your license here]

## Acknowledgments

- Based on [Cups_Dymo-450](https://github.com/ScottGibb/Cups_Dymo-450)
- Uses [DYMO SDK for Linux](https://github.com/ScottGibb/DYMO-SDK-for-Linux)
- CUPS printing system
