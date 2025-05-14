# BetterProposals Web Scraper

A Python-based web scraper designed to extract document information from BetterProposals.io. This tool automates the process of logging in, navigating to proposal documents, and extracting key information such as signing details and sender information.

## Features

- Automated authentication with BetterProposals.io
- Extracts document signature information including:
  - Signed by (name of signer)
  - Signed date (when the document was signed)
  - IP address (of the signature location)
  - Sent by (name of the sender)
- Batch processes multiple document URLs from a Google Sheet
- Saves results to a CSV file
- Handles already-authenticated browser sessions
- Includes fallback extraction methods if OpenAI API is unavailable

## Requirements

- Python 3.11
- Chrome browser
- Google Chrome user profile (for authentication persistence)
- OpenAI API key (for advanced HTML parsing)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/betterproposals-scraper.git
   cd betterproposals-scraper
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. Install required packages:
   ```
   pip install selenium undetected-chromedriver openai python-dotenv pandas gspread oauth2client
   ```

5. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Configuration

Edit the parameters in the `main()` function to match your environment:

```python
# Define parameters
login_url = "https://betterproposals.io/2/login/"
email = "your_email@example.com"
password = "your_password"
chrome_profile_path = r"[Your Own Chrome Profile Path]"
profile_directory = "Profile 2"
google_sheet_url = "https://docs.google.com/spreadsheets/d/your_sheet_id/edit?usp=sharing"
```

Make sure to update:
- `email` and `password` with your BetterProposals credentials
- `chrome_profile_path` with the path to your Chrome user data directory
- `profile_directory` with the profile you want to use
- `google_sheet_url` with the URL to your Google Sheet containing document URLs

## Google Sheet Format

Your Google Sheet should have the following columns:
- `Company`: Name of the company
- `Document type`: URL of the BetterProposals document (e.g., `https://betterproposals.io/2/proposals/view?id=2345530`)
- `Value`: Value of the proposal
- `Date Created`: Creation date
- `Signed On`: Signing date
- `Signed by`: Name of signer

## Usage

Run the script with the following command:

```
python main.py
```

By default, the script will:
1. Process the first 10 document URLs from the Google Sheet
2. Login to BetterProposals if not already authenticated
3. Navigate to each document URL
4. Extract the signature information
5. Save the results to `proposal.csv` in the current directory

To process all URLs in the Google Sheet, change `max_urls=10` to a higher number in the `process_urls_from_sheet()` function call.

## How It Works

1. **Authentication**: The script first checks if you're already logged in to BetterProposals by attempting to access a document directly. If not, it performs a login with the provided credentials.

2. **Document Processing**: For each URL, the script:
   - Navigates to the document page
   - Extracts HTML from the certificate section and timeline blocks
   - Identifies "Sent by" information directly from the HTML

3. **Data Extraction**: The script uses two methods to extract information:
   - Primary method: OpenAI API to intelligently parse the HTML content
   - Fallback method: Regular expressions and manual extraction if the API fails

4. **Results**: The extracted data is combined with the original Google Sheet data and saved to a CSV file.

## Troubleshooting

### Common Issues

1. **Authentication Failure**:
   - Make sure your email and password are correct
   - Check that the Chrome profile path is valid
   - Try manually logging in through the same Chrome profile

2. **OpenAI API Issues**:
   - Verify your API key is correct in the `.env` file
   - Check your OpenAI account has sufficient credits
   - The script will fall back to manual extraction if the API fails

3. **Google Sheet Access**:
   - Ensure the Google Sheet is shared with "Anyone with the link can view"
   - Try accessing the sheet URL in an incognito browser to verify access

### Logging

The script includes comprehensive logging to help diagnose issues. Look for messages in the console output or redirect to a file:

```
python main.py > log.txt 2>&1
```

## Example Output

The generated `proposal.csv` file will include all original columns from the Google Sheet, plus the following new columns:

- `Extracted Signed by`: The extracted name of the person who signed the document
- `Extracted Signed date`: The extracted date when the document was signed
- `Extracted IP address`: The extracted IP address from the signature location
- `Extracted Sent by`: The extracted name of the person who sent the document

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Make sure you have permission to access and extract data from BetterProposals before using this script.