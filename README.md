# Webpage PDF Downloader

A Python GUI application that allows you to download webpages as individual PDF files. Enter a URL, optionally provide credentials, and the app will scan the website for pages, allowing you to select which ones to download as PDFs.

**🆕 Now supports JavaScript-heavy websites using Selenium!**

## Features

- **URL Input**: Enter any website URL to scan
- **Credential Support**: Optional username/password for sites requiring authentication
- **JavaScript Rendering**: Toggle support for modern JavaScript-heavy websites (SPAs, Angular, React, etc.)
- **Page Discovery**: Automatically finds all pages within the same domain
- **Selective Download**: Choose which pages to download with checkboxes
- **Bulk Operations**: Select all pages at once
- **PDF Generation**: Converts webpages to individual PDF files with full rendering
- **Progress Tracking**: Visual progress bar and status updates
- **Safe File Naming**: Automatically handles duplicate filenames

## Installation

1. Make sure you have Python 3.7+ installed
2. Install Google Chrome (required for JavaScript rendering)
3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

**Note**: The application will automatically download ChromeDriver when first using JavaScript rendering.

## Usage

1. Run the application:

```bash
python webpage_pdf_downloader.py
```

2. Enter the URL of the website you want to download
3. **For modern JavaScript websites**: Check "Enable JavaScript rendering"
4. If the site requires authentication, enter your username and password
5. Click "Scan Website" to discover all pages
6. Select the pages you want to download (or use "Select All")
7. Click "Download Selected" and choose an output directory
8. Wait for the downloads to complete

## JavaScript vs Static Mode

### Static Mode (Default)
- ✅ Fast scanning and downloading
- ✅ Works with traditional HTML websites
- ✅ Low resource usage
- ❌ Cannot handle JavaScript-rendered content
- ❌ Won't work with Single Page Applications (SPAs)

### JavaScript Mode (Selenium)
- ✅ Handles modern JavaScript websites
- ✅ Works with SPAs (Angular, React, Vue.js)
- ✅ Fully renders dynamic content
- ✅ Can handle complex authentication flows
- ❌ Slower scanning and downloading
- ❌ Higher resource usage
- ❌ Requires Chrome browser

## Requirements

### Core Dependencies
- Python 3.7+
- tkinter (usually included with Python)
- requests
- beautifulsoup4
- weasyprint
- lxml

### JavaScript Support (Optional)
- selenium
- webdriver-manager
- Google Chrome browser

## Example Websites

**Works with Static Mode:**
- Wikipedia
- News websites
- Documentation sites
- Traditional HTML sites

**Requires JavaScript Mode:**
- AllData (my.alldata.com)
- Modern web applications
- Sites with `#/` URLs (client-side routing)
- React/Angular/Vue.js applications

## Notes

- The app only downloads pages from the same domain as the entered URL
- PDF files are saved with the page title as the filename
- Duplicate filenames are automatically handled by adding a number suffix
- JavaScript mode automatically handles many common login forms
- Large websites may take some time to scan and download
- JavaScript mode runs Chrome in headless mode (invisible)

## Troubleshooting

If you encounter issues with weasyprint installation:

### On Ubuntu/Debian:
```bash
sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

### On macOS:
```bash
brew install cairo pango gdk-pixbuf libffi
```

### On Windows:
Install GTK+ from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer

## License

This project is open source and available under the MIT License.
