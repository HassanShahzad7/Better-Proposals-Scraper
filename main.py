import os
import time
import logging
import json
import csv
import re
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import undetected_chromedriver as uc
import openai

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OpenAI API setup from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.warning("OPENAI_API_KEY not found in environment variables. Make sure to set it in your .env file.")

class BetterProposalsScraper:
    def __init__(self, login_url, document_url, email, password, chrome_profile_path, profile_directory):
        self.login_url = login_url
        self.document_url = document_url
        self.email = email
        self.password = password
        self.chrome_profile_path = chrome_profile_path
        self.profile_directory = profile_directory
        self.driver = None
        self.wait_time = 20  # Wait time for elements to appear
        self.page_load_wait = 10  # Wait time for page loads

    def setup_driver(self):
        """Set up Chrome driver with specified profile"""
        try:
            options = uc.ChromeOptions()
            options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
            options.add_argument(f"--profile-directory={self.profile_directory}")
            
            # Additional options for stability
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--window-size=1920,1080")
            
            # Initialize the driver
            logger.info("Initializing Chrome driver...")
            self.driver = uc.Chrome(options=options)
            self.driver.maximize_window()
            logger.info("Chrome driver initialized successfully")
            
            return True
        
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {str(e)}")
            return False

    def check_authentication_status(self):
        """Check if already authenticated by looking at the current URL or page elements"""
        current_url = self.driver.current_url
        logger.info(f"Current URL: {current_url}")
        
        # If we're already on the document page or dashboard, we're authenticated
        if "proposals/view" in current_url or "dashboard" in current_url:
            logger.info("Already authenticated (on document or dashboard page)")
            return True
            
        # If we're on the login page, we're not authenticated
        if "/login/" in current_url:
            # Double-check by looking for login form elements
            try:
                login_form = self.driver.find_element(By.ID, "form_login")
                logger.info("Not authenticated (login form found)")
                return False
            except NoSuchElementException:
                # If login form is not found but we're on login page URL, check further
                try:
                    # Look for elements that would indicate we're in an authenticated area
                    user_menu = self.driver.find_elements(By.CLASS_NAME, "user-menu")
                    if user_menu:
                        logger.info("Authenticated (user menu found)")
                        return True
                except:
                    pass
                
                logger.info("Authentication status unclear, assuming not authenticated")
                return False
        
        # For any other URL, we'll try to detect authentication by checking for authenticated elements
        try:
            # Look for elements that would typically be present in authenticated pages
            user_menu = self.driver.find_elements(By.CLASS_NAME, "user-menu")
            if user_menu:
                logger.info("Authenticated (user menu found)")
                return True
        except:
            pass
            
        logger.info("Authentication status unclear, assuming not authenticated")
        return False

    def navigate_directly_to_document(self):
        """Navigate directly to the document URL and check if we can access it"""
        try:
            logger.info(f"Navigating directly to document URL: {self.document_url}")
            self.driver.get(self.document_url)
            
            # Wait for page to load fully
            logger.info(f"Waiting for document page to load ({self.page_load_wait} seconds)...")
            time.sleep(self.page_load_wait)
            
            # Check if we can access the document (if we're on the document page)
            if "proposals/view" in self.driver.current_url:
                logger.info("Successfully accessed document directly - already authenticated")
                return True
            elif "/login/" in self.driver.current_url:
                logger.info("Redirected to login page - need to authenticate")
                return False
            else:
                logger.warning(f"Unexpected URL after navigation: {self.driver.current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating directly to document: {str(e)}")
            return False

    def login(self):
        """Perform login if needed"""
        try:
            # First, try to navigate directly to the document
            if self.navigate_directly_to_document():
                logger.info("Already authenticated - skipping login process")
                return True
                
            # If we're redirected to login page, we need to log in
            logger.info("Not authenticated, proceeding with login...")
            
            # Make sure we're on the login page
            if "/login/" not in self.driver.current_url:
                logger.info(f"Navigating to login page: {self.login_url}")
                self.driver.get(self.login_url)
                time.sleep(self.page_load_wait)
            
            # Wait for and fill email field
            logger.info("Looking for email field...")
            email_field = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "Email"))
            )
            email_field.clear()
            email_field.send_keys(self.email)
            logger.info("Email entered")
            
            # Wait for and fill password field
            logger.info("Looking for password field...")
            password_field = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "Password"))
            )
            password_field.clear()
            password_field.send_keys(self.password)
            logger.info("Password entered")
            
            # Find and click login button
            logger.info("Looking for login button...")
            try:
                login_buttons = self.driver.find_elements(By.XPATH, "//button[@type='submit']")
                if login_buttons:
                    login_button = login_buttons[0]
                    login_button.click()
                    logger.info("Login button clicked")
                else:
                    logger.error("No login button found")
                    return False
            except Exception as e:
                logger.error(f"Error clicking login button: {str(e)}")
                return False
            
            # Wait for post-login page to load
            logger.info(f"Waiting for post-login page to load ({self.page_load_wait} seconds)...")
            time.sleep(self.page_load_wait)
            
            # Check if login was successful
            if "/login/" not in self.driver.current_url:
                logger.info("Login successful!")
                return True
            else:
                logger.error("Login failed - still on login page")
                return False
                
        except TimeoutException as e:
            logger.error(f"Timeout during login: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False

    def navigate_to_document(self):
        """Navigate to the specific document URL if not already there"""
        try:
            current_url = self.driver.current_url
            
            # If we're already on the right document page, no need to navigate
            if self.document_url in current_url:
                logger.info("Already on the correct document page")
                return True
                
            # Otherwise, navigate to the document URL
            logger.info(f"Navigating to document URL: {self.document_url}")
            self.driver.get(self.document_url)
            
            # Wait for page to load fully
            logger.info(f"Waiting for document page to load ({self.page_load_wait} seconds)...")
            time.sleep(self.page_load_wait)
            
            # Simple check to verify we're on a proposal/document page
            if "proposals/view" in self.driver.current_url:
                logger.info("Successfully navigated to document page")
                return True
            else:
                logger.error(f"Navigation failed - unexpected URL: {self.driver.current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to document: {str(e)}")
            return False

    def extract_certificate_info(self):
        """Extract certificate information and timeline blocks"""
        try:
            logger.info("Extracting certificate information...")
            certificate_html = ""
            
            # Try to find the certificate section
            try:
                certificate_section = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "timeline-contentblock-certificate"))
                )
                certificate_html = certificate_section.get_attribute('outerHTML')
                logger.info("Certificate section found and HTML extracted")
                print("\n--- CERTIFICATE HTML ---")
                print(certificate_html)
                print("------------------------\n")
            except TimeoutException:
                logger.warning("Certificate section not found - document may not have been signed yet")
            
            # Extract timeline blocks for "sent by" information
            logger.info("Extracting timeline blocks...")
            timeline_blocks_html = ""
            timeline_blocks = self.driver.find_elements(By.CLASS_NAME, "timeline-block")
            
            # Store all timeline blocks that may contain "Sent by" information
            sent_by_blocks = []
            
            for block in timeline_blocks:
                block_html = block.get_attribute('outerHTML')
                timeline_blocks_html += block_html
                
                # Print each timeline block for debugging
                title_element = block.find_elements(By.CLASS_NAME, "timeline-title")
                if title_element:
                    title_text = title_element[0].text
                    print(f"Timeline Block: {title_text}")
                    
                    # Specifically look for blocks with "Sent by" in the title
                    if "Sent by" in title_text:
                        sent_by_blocks.append({
                            "html": block_html,
                            "text": title_text
                        })
            
            if timeline_blocks:
                logger.info(f"Found {len(timeline_blocks)} timeline blocks")
                # Print the FULL timeline HTML 
                print("\n--- FULL TIMELINE BLOCKS HTML ---")
                print(timeline_blocks_html)
                print("------------------------\n")
                
                # Print the specific "Sent by" blocks if found
                if sent_by_blocks:
                    logger.info(f"Found {len(sent_by_blocks)} blocks with 'Sent by' information")
                    print("\n--- SENT BY BLOCKS ---")
                    for i, block in enumerate(sent_by_blocks):
                        print(f"Block {i+1}: {block['text']}")
                        print(block['html'])
                    print("------------------------\n")
                else:
                    logger.warning("No 'Sent by' blocks found in timeline")
            else:
                logger.warning("No timeline blocks found")
            
            return {
                "certificate_html": certificate_html,
                "timeline_html": timeline_blocks_html,
                "sent_by_blocks": sent_by_blocks
            }
                
        except Exception as e:
            logger.error(f"Error extracting information: {str(e)}")
            return None

    def parse_with_openai(self, raw_data):
        """Use OpenAI to parse the extracted HTML data"""
        try:
            logger.info("Parsing data with OpenAI...")
            
            # Try to extract Sent by directly first using the sent_by_blocks if available
            sent_by = "Not found"
            if raw_data.get('sent_by_blocks'):
                for block in raw_data['sent_by_blocks']:
                    if 'text' in block and 'Sent by' in block['text']:
                        sent_by = block['text'].replace('Sent by', '').strip()
                        logger.info(f"Directly extracted 'Sent by': {sent_by}")
                        break
            
            # Create a simplified prompt to just extract the data directly
            prompt = f"""
            Extract specific information from these HTML sections from a BetterProposals document page.
            
            From the certificate HTML, extract:
            1. "Signed by" - The person who signed the document
            2. "Signed date" - When the document was signed
            3. "IP address" - IP address from signature location
            
            Certificate HTML: 
            {raw_data['certificate_html']}
            
            The output should be in simple JSON format like:
            {{
                "Signed by": "Name of signer",
                "Signed date": "Date of signature",
                "IP address": "IP Address",
                "Sent by": "{sent_by}"
            }}
            
            Note: I've already found the "Sent by" value for you: "{sent_by}". 
            Please keep this value in your response.
            
            If any other information is not found, use "Not found" as the value.
            """
            
            # Try using a simple implementation for OpenAI API
            logger.info("Calling OpenAI API...")
            
            try:
                # Manual extraction as fallback if API key isn't available or fails
                if not openai.api_key:
                    logger.warning("No OpenAI API key - performing manual extraction")
                    return self.manual_extract(raw_data, sent_by)
                
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",  # Using GPT-4o-mini for better extraction
                    messages=[
                        {"role": "system", "content": "You are a data extraction assistant. Extract structured data from HTML."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=500
                )
                
                # Extract the content and parse JSON
                response_content = response.choices[0].message.content
                logger.info(f"OpenAI response received")
                
                try:
                    parsed_data = json.loads(response_content)
                    logger.info("Data successfully parsed from OpenAI response")
                    
                    # Make sure we keep our directly extracted sent_by
                    parsed_data["Sent by"] = sent_by
                    
                    return parsed_data
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {str(e)}")
                    logger.error(f"Raw response content: {response_content}")
                    return self.manual_extract(raw_data, sent_by)
                
            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                return self.manual_extract(raw_data, sent_by)
            
        except Exception as e:
            logger.error(f"Error in parse_with_openai: {str(e)}")
            return self.manual_extract(raw_data)

    def manual_extract(self, raw_data, sent_by="Not found"):
        """Fallback manual extraction if OpenAI fails"""
        logger.info("Using manual extraction as fallback")
        result = {
            "Signed by": "Not found",
            "Signed date": "Not found",
            "IP address": "Not found",
            "Sent by": sent_by
        }
        
        # Extract signed by
        certificate_html = raw_data['certificate_html']
        timeline_html = raw_data['timeline_html']
        
        # Very basic extraction logic
        if "Accepted and Signed by" in certificate_html:
            try:
                # Try to find the value after "Accepted and Signed by" label
                signed_by_match = re.search(r'Accepted and Signed by.*?<div class="certificate-value">(.*?)</div>', 
                                           certificate_html, re.DOTALL)
                if signed_by_match:
                    result["Signed by"] = signed_by_match.group(1).strip()
            except:
                pass
        
        # Extract signed date
        if "Accepted and Signed on" in certificate_html:
            try:
                # Try to find the value after "Accepted and Signed on" label
                signed_date_match = re.search(r'Accepted and Signed on.*?<div class="certificate-value">(.*?)</div>', 
                                             certificate_html, re.DOTALL)
                if signed_date_match:
                    result["Signed date"] = signed_date_match.group(1).strip()
            except:
                pass
        
        # Extract IP address
        if "IP Address from signature location" in certificate_html:
            try:
                # Try to find the value after "IP Address from signature location" label
                ip_match = re.search(r'IP Address from signature location.*?<div class="certificate-value">(.*?)</div>', 
                                    certificate_html, re.DOTALL)
                if ip_match:
                    result["IP address"] = ip_match.group(1).strip()
            except:
                pass
        
        # Extract sent by directly from the blocks if not already found
        if result["Sent by"] == "Not found" and "sent_by_blocks" in raw_data and raw_data["sent_by_blocks"]:
            for block in raw_data["sent_by_blocks"]:
                if "text" in block and "Sent by" in block["text"]:
                    result["Sent by"] = block["text"].replace("Sent by", "").strip()
                    break
        
        # If still not found, try regex on the timeline HTML
        if result["Sent by"] == "Not found":
            try:
                # Look for "Sent by" text in the timeline HTML
                sent_by_match = re.search(r'<div class="timeline-title[^>]*">Sent by\s+(.*?)</div>', 
                                         timeline_html, re.DOTALL)
                if sent_by_match:
                    result["Sent by"] = sent_by_match.group(1).strip()
            except:
                pass
        
        return result

    def run(self):
        """Main method to run the scraper"""
        try:
            # Setup driver
            if not self.setup_driver():
                logger.error("Failed to set up Chrome driver. Exiting...")
                return None
            
            # Login directly to document (if already authenticated, this will skip login)
            if not self.navigate_directly_to_document():
                logger.info("Need to log in first")
                if not self.login():
                    logger.error("Failed to login. Exiting...")
                    self.cleanup()
                    return None
                
                # Now navigate to document after successful login
                if not self.navigate_to_document():
                    logger.error("Failed to navigate to document after login. Exiting...")
                    self.cleanup()
                    return None
            
            # Extract data
            raw_data = self.extract_certificate_info()
            if not raw_data:
                logger.error("Failed to extract information. Exiting...")
                self.cleanup()
                return None
            
            # Parse data with OpenAI or manual extraction
            parsed_data = self.parse_with_openai(raw_data)
            if not parsed_data:
                logger.error("Failed to parse data. Exiting...")
                self.cleanup()
                return None
            
            logger.info("Successfully extracted and parsed data")
            logger.info(f"Parsed data: {json.dumps(parsed_data, indent=2)}")
            
            self.cleanup()
            return parsed_data
            
        except Exception as e:
            logger.error(f"Unexpected error in run method: {str(e)}")
            self.cleanup()
            return None

    def cleanup(self):
        """Clean up resources"""
        try:
            if self.driver:
                logger.info("Closing Chrome driver...")
                self.driver.quit()
                logger.info("Chrome driver closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


def read_google_sheet(sheet_url):
    """Read data from Google Sheet using pandas read_csv"""
    try:
        # Convert Google Sheet URL to CSV export URL
        if 'edit?usp=sharing' in sheet_url:
            sheet_url = sheet_url.replace('edit?usp=sharing', 'export?format=csv')
        elif 'edit' in sheet_url:
            sheet_url = sheet_url.replace('edit', 'export?format=csv')
        else:
            sheet_url = sheet_url + '/export?format=csv'
            
        # Read the CSV into a pandas DataFrame
        df = pd.read_csv(sheet_url)
        logger.info(f"Successfully read Google Sheet with {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error reading Google Sheet: {str(e)}")
        return None


def download_google_sheet(sheet_url):
    """Alternative method to download the Google Sheet as CSV"""
    try:
        # Extract sheet ID from URL
        sheet_id = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url).group(1)
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        # Read the CSV into a pandas DataFrame
        df = pd.read_csv(export_url)
        logger.info(f"Successfully downloaded Google Sheet with {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error downloading Google Sheet: {str(e)}")
        return None


def process_urls_from_sheet(sheet_url, login_url, email, password, chrome_profile_path, profile_directory, max_urls=10):
    """Process URLs from Google Sheet and save results to CSV"""
    try:
        # Read the Google Sheet
        df = None
        
        # Try different methods to read the Google Sheet
        try:
            df = read_google_sheet(sheet_url)
        except:
            logger.warning("Failed to read Google Sheet directly, trying alternative download method")
            df = download_google_sheet(sheet_url)
            
        if df is None or len(df) == 0:
            logger.error("Failed to read data from Google Sheet")
            # As a fallback, create a sample DataFrame for testing
            logger.info("Creating sample DataFrame for testing")
            df = pd.DataFrame({
                'Company': ['BHA Strategy', 'Integrity Design', 'Providence Diamond'],
                'Document type': [
                    'https://betterproposals.io/2/proposals/view?id=2366358',
                    'https://betterproposals.io/2/proposals/view?id=2392944',
                    'https://betterproposals.io/2/proposals/view?id=2423564'
                ],
                'Value': ['$33,200.00', '$41,920.00', '$39,710.00'],
                'Date Created': ['18 Mar 2025', '04 Apr 2025', '29 Apr 2025'],
                'Signed On': ['08 May 2025', '30 Apr 2025', '30 Apr 2025'],
                'Signed by': ['Katy Sully', 'Brandon Earls', 'Daniel Pritsker']
            })
            
        # Create the results DataFrame with all columns from the original sheet
        results_df = df.copy()
        
        # Add new columns for the extracted data
        results_df['Extracted Signed by'] = ''
        results_df['Extracted Signed date'] = ''
        results_df['Extracted IP address'] = ''
        results_df['Extracted Sent by'] = ''
        
        # Process only the first max_urls entries
        urls_to_process = min(max_urls, len(df))
        logger.info(f"Processing {urls_to_process} URLs from the Google Sheet")
        
        # Use a single scraper instance for all URLs
        for i in range(urls_to_process):
            try:
                company = df.iloc[i]['Company']
                document_url = df.iloc[i]['Document type']
                
                logger.info(f"Processing URL {i+1}/{urls_to_process}: {document_url} for company: {company}")
                
                # Create a scraper instance for this URL
                scraper = BetterProposalsScraper(login_url, document_url, email, password, chrome_profile_path, profile_directory)
                result = scraper.run()
                
                if result:
                    # Update the results DataFrame with the extracted data
                    results_df.at[i, 'Extracted Signed by'] = result.get('Signed by', 'Not found')
                    results_df.at[i, 'Extracted Signed date'] = result.get('Signed date', 'Not found')
                    results_df.at[i, 'Extracted IP address'] = result.get('IP address', 'Not found')
                    results_df.at[i, 'Extracted Sent by'] = result.get('Sent by', 'Not found')
                    
                    logger.info(f"Successfully processed URL {i+1}/{urls_to_process}")
                else:
                    logger.error(f"Failed to process URL {i+1}/{urls_to_process}")
                    # Fill with 'Error' values
                    results_df.at[i, 'Extracted Signed by'] = 'Error'
                    results_df.at[i, 'Extracted Signed date'] = 'Error'
                    results_df.at[i, 'Extracted IP address'] = 'Error'
                    results_df.at[i, 'Extracted Sent by'] = 'Error'
                
                # Wait a bit between requests to avoid overwhelming the server
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing URL {i+1}: {str(e)}")
                # Fill with 'Error' values
                results_df.at[i, 'Extracted Signed by'] = f'Error: {str(e)}'
                results_df.at[i, 'Extracted Signed date'] = 'Error'
                results_df.at[i, 'Extracted IP address'] = 'Error'
                results_df.at[i, 'Extracted Sent by'] = 'Error'
        
        # Save the results to CSV
        csv_filename = "proposal.csv"
        results_df.to_csv(csv_filename, index=False)
        logger.info(f"Results saved to {csv_filename}")
        
        return results_df
        
    except Exception as e:
        logger.error(f"Error processing URLs from sheet: {str(e)}")
        return None


def main():
    # Define parameters
    login_url = "https://betterproposals.io/2/login/"
    email = os.getenv("email")
    password = os.getenv("password")
    if not email or not password:
        logger.error("Email and password must be set in environment variables")
        return
    chrome_profile_path = r"C://Users//hassa//AppData//Local//Google//Chrome for Testing//User Data"
    profile_directory = "Profile 2"
    google_sheet_url = "https://docs.google.com/spreadsheets/d/1TGjJziI8OTVekpBriyVpqcKb6z_bKOVSRaVxkLPhWYA/edit?usp=sharing"
    
    # Process URLs from the Google Sheet (limit to 10 for testing)
    results = process_urls_from_sheet(
        google_sheet_url,
        login_url,
        email,
        password,
        chrome_profile_path,
        profile_directory,
        max_urls=10
    )
    
    if results is not None:
        print("\n--- RESULTS SUMMARY ---")
        # Display the first few rows
        print(results.head())
    else:
        print("Failed to process URLs from Google Sheet")


if __name__ == "__main__":
    main()