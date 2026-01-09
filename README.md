# CM4-NAS-Double-Deck

A Python-based display and monitoring system for Raspberry Pi Compute Module 4 (CM4) NAS enclosures. This project provides real-time system monitoring displayed on an attached screen, along with a web interface for remote monitoring.

## Features

- **Real-time System Monitoring**: Display CPU, memory, disk, and network statistics
- **OLED/LCD Display Support**: Visual status output on attached displays
- **Web Interface**: Remote monitoring via browser using Flask templates
- **Systemd Service**: Runs automatically on boot as a background service
- **Configurable**: JSON-based configuration for easy customization

## Project Structure

```
CM4-NAS-Double-Deck/
├── font/               # Display fonts
├── images/             # Icons and images for the display
├── lib/                # Python library modules
├── templates/          # Flask web interface templates
├── config.json         # Configuration file
├── display.service     # Systemd service unit file
├── image.py            # Image generation and processing
├── main.py             # Main application entry point
└── requirements.txt    # Python dependencies
```

## Requirements

- Raspberry Pi Compute Module 4
- Compatible NAS carrier board with display connector
- Python 3.x
- Required Python packages (see `requirements.txt`)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ghalpha/CM4-NAS-Double-Deck.git
   cd CM4-NAS-Double-Deck
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure the application:**
   Edit `config.json` to match your hardware setup and preferences.

4. **Install the systemd service:**
   ```bash
   sudo cp display.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable display.service
   sudo systemctl start display.service
   ```

## Usage

### Running Manually

```bash
python3 main.py
```

### Service Management

```bash
# Start the service
sudo systemctl start display.service

# Stop the service
sudo systemctl stop display.service

# Check status
sudo systemctl status display.service

# View logs
journalctl -u display.service -f
```

### Web Interface

Once running, access the web interface at:
```
http://<your-pi-ip>:5000
```

## Configuration

Edit `config.json` to customize:

- Display settings (resolution, refresh rate)
- Monitored metrics
- Network interface selection
- Web server port
- Update intervals

## Hardware Compatibility

This project is designed for CM4-based NAS enclosures featuring:

- Raspberry Pi Compute Module 4
- Integrated OLED/LCD display
- Multiple SATA drive bays

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source. Please check the repository for license details.

## Acknowledgments

- Raspberry Pi Foundation
- Python community
- Contributors to the display driver libraries
