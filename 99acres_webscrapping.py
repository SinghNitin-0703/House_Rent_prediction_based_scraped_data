from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import os

# --- CONFIGURATION ---
BASE_URL = "https://www.99acres.com/property-for-rent-in-greater-noida-ffid"
PAGES_TO_SCRAPE = 200  # Sets a high ceiling. Script will stop automatically if pages run out.
OUTPUT_FILE = 'greater_noida_rents_massive.csv'
all_properties = []

# --- SETUP DRIVER (Stealth Mode) ---
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled") 
options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
options.add_experimental_option("useAutomationExtension", False) 
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

print(f"Starting Marathon Scraping... Target: {PAGES_TO_SCRAPE} Pages.")
print(f"Data will be auto-saved to '{OUTPUT_FILE}' every 10 pages.")

try:
    for page_num in range(1, PAGES_TO_SCRAPE + 1):
        
        # 1. URL Construction
        if page_num == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}-page-{page_num}"
            
        print(f"\n--- Processing Page {page_num} of {PAGES_TO_SCRAPE} ---")
        driver.get(url)
        
        # 2. HUMAN CHECKPOINT
        if "human" in driver.title.lower() or "access denied" in driver.page_source.lower():
            print("\n!!! BLOCK DETECTED !!!")
            print("The script is paused. Please solve the CAPTCHA in the browser.")
            input("Press ENTER here once the CAPTCHA is solved and listings are visible...")
        
        # 3. SAFETY DELAY (30-40 Seconds)
        sleep_time = random.uniform(30, 40)
        print(f"  -> Waiting {sleep_time:.1f} seconds...")
        time.sleep(sleep_time)
        
        # 4. PARSE DATA
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        listings = soup.find_all('div', class_='tupleNew__outerTupleWrap')
        
        # STOPPING CONDITION: If page is empty, we reached the end
        if len(listings) == 0:
            print("  -> No listings found. Checking for CAPTCHA one last time...")
            # Brief check in case it was a loading glitch
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = soup.find_all('div', class_='tupleNew__outerTupleWrap')
            
            if len(listings) == 0:
                print("  -> Still 0 listings. We have reached the end of the results.")
                print("  -> Stopping script early.")
                break

        print(f"  -> Found {len(listings)} listings.")
        
        for item in listings:
            try:
                # Full text scan
                card_text = item.get_text(" ", strip=True).lower()
                
                # Title / BHK
                title_tag = item.find(lambda tag: tag.name in ['a', 'h2', 'div'] and tag.get('class') and any('tupleHeading' in c for c in tag.get('class')))
                full_title = title_tag.text.strip() if title_tag else "N/A"
                bhk_match = re.search(r'(\d+\s*BHK)', full_title, re.IGNORECASE)
                bhk = bhk_match.group(1) if bhk_match else "N/A"

                # Price
                price_tag = item.find(lambda tag: tag.get('class') and any('priceVal' in c for c in tag.get('class')))
                price = price_tag.text.strip() if price_tag else "N/A"

                # Location
                loc_tag = item.find(class_='tupleNew__locationName')
                location = loc_tag.text.strip() if loc_tag else "N/A"
                
                # Area
                area_tag = item.find(class_='tupleNew__totolAreaWrap')
                if not area_tag: area_tag = item.find(class_='tupleNew__areaWrap')
                area = area_tag.text.strip() if area_tag else "N/A"

                # Furnishing
                furnishing = "N/A"
                if "semi-furnished" in card_text or "semifurnished" in card_text or "semi furnished" in card_text:
                    furnishing = "Semi-Furnished"
                elif "unfurnished" in card_text:
                    furnishing = "Unfurnished"
                elif "fully furnished" in card_text:
                    furnishing = "Fully Furnished"
                elif "furnished" in card_text:
                    furnishing = "Furnished"

                # Tenant Preference
                tenant_pref = "Not Specified"
                if "family only" in card_text:
                    tenant_pref = "Family Only"
                elif "bachelors only" in card_text:
                    tenant_pref = "Bachelors Only"
                elif "bachelor" in card_text:
                    if "no bachelor" in card_text or "not allowed" in card_text:
                        tenant_pref = "No Bachelors"
                    else:
                        tenant_pref = "Bachelors Allowed"
                elif "family" in card_text:
                    tenant_pref = "Family Preferred"
                elif "girls" in card_text:
                    tenant_pref = "Girls Only"
                elif "boys" in card_text:
                    tenant_pref = "Boys Only"

                all_properties.append({
                    'BHK': bhk,
                    'Price': price,
                    'Location': location,
                    'Area': area,
                    'Furnishing': furnishing,
                    'Tenant_Pref': tenant_pref,
                    'Full_Title': full_title,
                    'Page_Found': page_num
                })
                
            except Exception:
                continue
        
        # --- AUTO-SAVE FEATURE ---
        # Save every 10 pages so we don't lose data if it crashes
        if page_num % 10 == 0:
            temp_df = pd.DataFrame(all_properties)
            temp_df.to_csv(OUTPUT_FILE, index=False)
            print(f"  -> [CHECKPOINT] Data saved to '{OUTPUT_FILE}' ({len(all_properties)} rows so far).")

except Exception as e:
    print(f"Critical Error: {e}")

finally:
    driver.quit()
    
    # Final Save
    if all_properties:
        df = pd.DataFrame(all_properties)
        print("\n" + "="*30)
        print(f"RUN COMPLETE. Total rows: {len(df)}")
        print("="*30)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Final dataset saved to '{OUTPUT_FILE}'")
    else:
        print("No data collected.")