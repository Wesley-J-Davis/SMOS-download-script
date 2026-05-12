import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import getpass
import os
import zipfile
import sys
# ==========================================
# 1. SEARCH SETTINGS & CREDENTIALS (ARGPARSE)
# ==========================================
parser = argparse.ArgumentParser(description="Download ESA SMOS data by date and product.")
parser.add_argument("-p", "--product", required=True, help="Product string (e.g., BWLF1C)")
parser.add_argument("-y", "--year", required=True, help="4-digit year (e.g., 2026)")
parser.add_argument("-m", "--month", required=True, help="2-digit month (e.g., 04)")
parser.add_argument("-d", "--day", required=True, help="2-digit day (e.g., 22)")
args = parser.parse_args()

PRODUCT = args.product
YEAR = args.year
MONTH = args.month
DAY = args.day

username = sys.argv[1]
password = sys.argv[2]

login_url = "https://smos-diss.eo.esa.int/oads/access/login"
search_url = "https://smos-diss.eo.esa.int/oads/access/collection/SMOS_Open_V7/searchbyfilename"
#search_url = "https://smos-diss.eo.esa.int/oads/access/collection/NRT_Open/searchbyfilename" 
# ==========================================
# 2. ESA SSO LOGIN FLOW
# ==========================================
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

print("\n1. Fetching login page to get session tokens...")
resp1 = session.get(login_url)
soup1 = BeautifulSoup(resp1.text, 'html.parser')

key_input = soup1.find('input', {'name': 'sessionDataKey'})
if not key_input:
    print("Error: Could not find sessionDataKey on the login page.")
    exit(1)
session_data_key = key_input.get('value')

post_url = urljoin(resp1.url, '../samlsso')
login_payload = {
    'tocommonauth': 'true',
    'username': username,
    'password': password,
    'sessionDataKey': session_data_key
}

print("2. Submitting credentials...")
resp2 = session.post(post_url, data=login_payload)
soup2 = BeautifulSoup(resp2.text, 'html.parser')

saml_response_input = soup2.find('input', {'name': 'SAMLResponse'})

if saml_response_input:
    print("3. SAML token intercepted! Forwarding back to ESA portal...")
    saml_value = saml_response_input.get('value')
    relay_state_input = soup2.find('input', {'name': 'RelayState'})
    relay_state = relay_state_input.get('value', '') if relay_state_input else ''
    
    saml_form = soup2.find('form')
    saml_post_url = saml_form.get('action')
    
    saml_payload = {'SAMLResponse': saml_value, 'RelayState': relay_state}
    resp3 = session.post(saml_post_url, data=saml_payload)

# ==========================================
# 3. VERIFY LOGIN
# ==========================================
print("4. Verifying login access...")
test_resp = session.get("https://smos-diss.eo.esa.int/oads/access/")
if "Not signed in" in test_resp.text:
    print("\nFAILED: Login did not succeed. Check your password.")
    exit(1)
print("SUCCESS! You are officially logged in and authenticated.")

# ==========================================
# 4. SUBMIT SEARCH FORM
# ==========================================
# Construct the search term with a wildcard at the end
search_term = f"*{PRODUCT}_{YEAR}{MONTH}{DAY}T*"

print(f"\nSearching for files matching: {search_term}")
search_payload = {
    'r': 'showAsUrlList',
    's': search_term
}

search_resp = session.post(search_url, data=search_payload)
search_soup = BeautifulSoup(search_resp.text, 'html.parser')

# Because we selected 'showAsUrlList', the results will likely be clickable <a> links.
all_links = search_soup.find_all('a')
zip_urls = []

for link in all_links:
    href = link.get('href')
    # Filter out navigation links, keep only links that look like data files
    if href and PRODUCT in href and href.endswith('.zip'):
        # Make sure it's a full URL
        full_url = urljoin(search_url, href)
        zip_urls.append(full_url)

zip_urls = list(set(zip_urls))

if not zip_urls:
    print(f"\nNo matching files found for {search_term}.")
    exit(0)

print(f"Found {len(zip_urls)} matching files to download.\n")

# ==========================================
# 5. DOWNLOAD AND EXTRACT
# ==========================================
for index, file_url in enumerate(zip_urls, start=1):
    local_zipname = os.path.basename(file_url)
    
    # Check if we already extracted the DBL file to prevent re-downloading
    base_name = local_zipname.replace('.zip', '')
    if os.path.exists(f"{base_name}.DBL"):
        print(f"[{index}/{len(zip_urls)}] Skipping {local_zipname}, already extracted.")
        continue

    print(f"[{index}/{len(zip_urls)}] Downloading: {local_zipname}...")
    
    try:
        file_resp = session.get(file_url, stream=True)
        file_resp.raise_for_status()
        
        with open(local_zipname, "wb") as f:
            for chunk in file_resp.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
                    
        print(f"  -> Extracting {local_zipname}...")
        with zipfile.ZipFile(local_zipname, 'r') as zip_ref:
            zip_ref.extractall(".")
            
        os.remove(local_zipname)
        print(f"  -> Cleaned up {local_zipname}.")
        
    except Exception as e:
        print(f"  -> ERROR downloading or extracting {local_zipname}: {e}")

print("\nAll downloads and extractions are complete!")
