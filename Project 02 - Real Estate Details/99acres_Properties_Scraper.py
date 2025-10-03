import time
import numpy as np
import pandas as pd
import pathlib
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class PropertyScraper:
    def __init__(self, url, timeout=10):
        """
        Initialize the PropertyScraper.

        Args:
            url (str): The website URL to scrape.
            timeout (int): WebDriverWait timeout for elements (seconds).
        """
        self.url = url
        self.data = []
        self.driver = self._initialize_driver()
        self.wait = WebDriverWait(self.driver, timeout=timeout)

    def _initialize_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-http2")
        chrome_options.add_argument("--enable-features=NetworkServiceInProcess")
        chrome_options.add_argument("--disable-features=NetworkService")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
        )
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        return driver

    def _wait_for_page_to_load(self):
        try:
            self.wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logging.info('Page loaded')
        except Exception:
            logging.warning('Page did not load completely')

    def access_website(self):
        self.driver.get(self.url)
        self._wait_for_page_to_load()

    def search_properties(self, city):
        """
        Fill the search bar and select city.
        """
        try:
            search_bar = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="keyword2"]'))
            )
            search_bar.send_keys(city)
            time.sleep(2)
            valid_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="0"]'))
            )
            valid_option.click()
            time.sleep(2)
            search_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="searchform_search_btn"]'))
            )
            search_button.click()
            self._wait_for_page_to_load()
        except Exception as e:
            logging.error(f"Error in search_properties: {e}")

    def adjust_budget_slider(self, offset):
        """
        Adjust the budget slider to the desired value.
        """
        try:
            slider = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="budgetLeftFilter_max_node"]'))
            )
            actions = ActionChains(self.driver)
            actions.click_and_hold(slider).move_by_offset(offset, 0).release().perform()
            time.sleep(2)
        except Exception as e:
            logging.error(f"Error adjusting budget slider: {e}")

    def apply_filters(self):
        """
        Apply page filters (Verified, Ready To Move, With Photos, With Videos).
        """
        try:
            filters = [
                ('Verified', '/html[1]/body[1]/div[1]/div[1]/div[1]/div[4]/div[3]/div[1]/div[3]/section[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/span[2]'),
                ('Ready To Move', '/html[1]/body[1]/div[1]/div[1]/div[1]/div[4]/div[3]/div[1]/div[3]/section[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[5]/span[2]'),
                ('With Photos', '/html[1]/body[1]/div[1]/div[1]/div[1]/div[4]/div[3]/div[1]/div[3]/section[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[6]/span[2]'),
                ('With Videos', '/html[1]/body[1]/div[1]/div[1]/div[1]/div[4]/div[3]/div[1]/div[3]/section[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[7]/span[2]')
            ]
            for name, xpath in filters[:2]:
                btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                time.sleep(1)
            # Move right for more filters
            while True:
                try:
                    right_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//i[contains(@class,'iconS_Common_24 icon_upArrow cc__rightArrow')]"))
                    )
                    right_btn.click()
                    time.sleep(1)
                except Exception:
                    break
            for name, xpath in filters[2:]:
                btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                time.sleep(1)
            time.sleep(2)
        except Exception as e:
            logging.error(f"Error in apply_filters: {e}")

    def _extract_text(self, row, by, value):
        try:
            return row.find_element(by, value).text
        except Exception:
            return np.nan

    def scrape_webpage(self):
        """
        Scrape property listings from the current page.
        """
        rows = self.driver.find_elements(By.CLASS_NAME, "tupleNew__TupleContent")
        for row in rows:
            property_ = {
                "name": self._extract_text(row, By.CLASS_NAME, "tupleNew__headingNrera"),
                "location": self._extract_text(row, By.CLASS_NAME, "tupleNew__propType"),
                "price": self._extract_text(row, By.CLASS_NAME, "tupleNew__priceValWrap")
            }
            try:
                elements = row.find_elements(By.CLASS_NAME, "tupleNew__area1Type")
                property_["area"], property_["bhk"] = [ele.text for ele in elements]
            except Exception:
                property_["area"], property_["bhk"] = [np.nan, np.nan]
            self.data.append(property_)

    def navigate_pages_and_scrape_data(self):
        """
        Visit multiple pages and scrape listings until there are no more pages left.
        """
        page_count = 0
        while True:
            page_count += 1
            self.scrape_webpage()
            try:
                next_btn = self.driver.find_element(By.XPATH, "//a[normalize-space()='Next Page >']")
                self.driver.execute_script(
                    "window.scrollBy(0, arguments[0].getBoundingClientRect().top - 100);", next_btn)
                time.sleep(2)
                self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Next Page >']"))
                ).click()
                time.sleep(3)
            except Exception:
                logging.info(f"No more pages after {page_count} pages.")
                break

    def clean_data_and_save_as_excel(self, file_name):
        """
        Clean raw data and save the output as an Excel file.
        """
        df = (
            pd.DataFrame(self.data)
            .drop_duplicates()
            .apply(lambda col: col.str.strip().str.lower() if col.dtype == "object" else col)
            .assign(
                is_starred=lambda d: d.name.str.contains("\n").astype(int),
                name=lambda d: d.name.str.replace("\n[0-9.]+", "", regex=True).str.strip(),
                location=lambda d: d.location.str.replace("chennai", "").str.strip().str.replace(",$", "", regex=True).str.split("in").str[-1].str.strip(),
                price=lambda d: d.price.str.replace("₹", "").apply(lambda v: float(v.replace("lac", "").strip()) if "lac" in v else float(v.replace("cr", "").strip())*100),
                area=lambda d: d.area.str.replace("sqft", "").str.replace(",", "").str.strip().pipe(pd.to_numeric, errors='coerce'),
                bhk=lambda d: d.bhk.str.replace("bhk", "").str.strip().pipe(pd.to_numeric, errors='coerce')
            )
            .rename(columns={"price": "price_lakhs", "area": "area_sqft"})
            .reset_index(drop=True)
        )
        excel_path = f"{file_name}.xlsx"
        df.to_excel(excel_path, index=False)
        logging.info(f"Saved cleaned data to {excel_path}")

    def run(self, city="gurugram", offset=-73, file_name="99acres_Properties"):
        """
        Orchestrate all steps to scrape and save properties.
        """
        try:
            self.access_website()
            self.search_properties(city)
            self.adjust_budget_slider(offset)
            self.apply_filters()
            self.navigate_pages_and_scrape_data()
            self.clean_data_and_save_as_excel(file_name)
        finally:
            time.sleep(2)
            self.driver.quit()


if __name__ == "__main__":
    scraper = PropertyScraper(url="https://www.99acres.com/")
    scraper.run(
        city="gurugram",
        offset=-73,
        file_name="99acres_Properties_Gurugram"
    )
