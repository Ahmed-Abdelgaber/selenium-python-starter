from __future__ import annotations

import os
import time
import json
from typing import Any, Dict, Iterable, List, Tuple, Optional

# --- Imports from Full_Code.py ---
import pyodbc

try:
    import google.generativeai as genai
except Exception:
    genai = None  # Only needed if you call Gemini

# --- Imports from Scrapping.py ---
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# ==============================================================================
# == PART 1: DATABASE LOGIC (from Full_Code.py)
# ==============================================================================

# ----------------------------
# Connection / Configuration
# ----------------------------

SERVER = "ec2-54-235-41-111.compute-1.amazonaws.com"
DATABASE = "reporting1"
USERNAME = "test1"
PASSWORD = "Welcome123!"
# Set default driver. User can override with an environment variable.
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")


def get_db_connection() -> pyodbc.Connection:
    """
    Open and return a SQL Server connection using pyodbc.
    Uses Driver 18 by default (set ODBC_DRIVER to override).
    """
    print("Attempting to connect to SQL Server...")
    conn_str = (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        f"Encrypt=Yes;"
        f"TrustServerCertificate=Yes;"
        f"Connection Timeout=30;"
    )
    conn = pyodbc.connect(conn_str)
    print("✅ SQL Server connection successful.")
    return conn


# ----------------------------
# Retrieval
# ----------------------------

# This is the table from your new code
SCRAPE_TABLE = "[dbo].[ADP_Emp_Scrape]"


def fetch_active_employees(
    conn: pyodbc.Connection, top_n: int = 1000
) -> List[Dict[str, Any]]:
    """
    Fetch top N active employees ordered by most recent Hire_Date.
    Returns a list[dict] (array-like) where keys are column names.
    """
    print(f"Fetching top {top_n} active employees...")
    # Sanitize top_n (embed as literal since TOP cannot be parameterized reliably)
    top_n = int(top_n) if top_n and int(top_n) > 0 else 1000

    # Using the query from your provided code
    sql = f"""
        SELECT TOP ({top_n})
            [First_Name],
            [Last_Name],
            [Email_Address],
            [Hire_Date],
            [Position_Status]
        FROM {SCRAPE_TABLE}
        WHERE [Position_Status] = 'active' AND [Scraped] = 0 AND CAST([Hire_Date] AS date) > '2025-08-14' 
        ORDER BY [Hire_Date] DESC, [Created_Date] DESC
    """
    cur = conn.cursor()
    cur.execute(sql)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    print(f"✅ Fetched {len(rows)} employee rows.")
    return rows


# ----------------------------
# Bulk insert into ADP_Hired_Emp_8850 (from Full_Code.py)
# ----------------------------

HIRED_TABLE = "[dbo].[ADP_Hired_Emp_8850]"
HIRED_COLUMNS = [
    "First Name",
    "Last Name",
    "Email",
    "Box1",
    "Box2",
    "Box3",
    "Box4",
    "Box5",
    "Box6",
    "Box7",
]


def ensure_hired_table_exists(conn: pyodbc.Connection) -> None:
    """
    Create dbo.ADP_Hired_Emp_8850 if it doesn't exist.
    Columns: First Name, Last Name, Email (NVARCHAR) + Box1..Box7 (BIT, nullable), Inserted_At (DATETIME2)
    """
    ddl = f"""
    IF OBJECT_ID('{HIRED_TABLE}', 'U') IS NULL
    BEGIN
        CREATE TABLE {HIRED_TABLE} (
            [First Name] NVARCHAR(100) NOT NULL,
            [Last Name]  NVARCHAR(100) NOT NULL,
            [Email]      NVARCHAR(254) NULL,
            [Box1] BIT NULL, [Box2] BIT NULL, [Box3] BIT NULL, [Box4] BIT NULL,
            [Box5] BIT NULL, [Box6] BIT NULL, [Box7] BIT NULL,
            [Inserted_At] DATETIME2(0) NOT NULL CONSTRAINT DF_ADP_Hired_Emp_InsertedAt DEFAULT SYSUTCDATETIME()
        );
        CREATE INDEX IX_ADP_Hired_Emp_Email ON {HIRED_TABLE}([Email]);
    END
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()
    print(f"Ensured table {HIRED_TABLE} exists.")


def bulk_insert_hired_emps(
    conn: pyodbc.Connection,
    rows: Iterable[Dict[str, Any]],
) -> int:
    """
    Bulk insert the provided rows into dbo.ADP_Hired_Emp_8850.
    Each item must contain keys for: First Name, Last Name, Email, Box1..Box7
    Returns number of inserted rows.
    """
    rows = list(rows)
    if not rows:
        return 0

    placeholders = ",".join("?" for _ in HIRED_COLUMNS)
    col_list = ", ".join(f"[{c}]" for c in HIRED_COLUMNS)
    sql = f"INSERT INTO {HIRED_TABLE} ({col_list}) VALUES ({placeholders})"

    params: List[Tuple[Any, ...]] = []
    for r in rows:
        params.append(tuple(r.get(c) for c in HIRED_COLUMNS))

    with conn.cursor() as cur:
        cur.fast_executemany = True
        cur.executemany(sql, params)
        conn.commit()
    return len(rows)


# ----------------------------
# NEW: Update Scraped Status
# ----------------------------


def update_scraped_status(conn: pyodbc.Connection, processed_emails: List[str]) -> int:
    """
    Updates the [Scraped] flag to 1 for a list of processed employee emails.
    Uses a temporary table for efficient bulk updating.
    Returns the number of rows updated.
    """
    if not processed_emails:
        print("No emails to update, skipping scrape status update.")
        return 0

    # Use set for uniqueness, then create list of lists for pyodbc
    params = [[email] for email in set(processed_emails) if email]
    if not params:
        print("No valid emails to update, skipping scrape status update.")
        return 0

    print(f"Attempting to update [Scraped] = 1 for {len(params)} employees...")

    with conn.cursor() as cur:
        try:
            # 1. Create a temporary table
            cur.execute("CREATE TABLE #TempEmails (Email NVARCHAR(254) PRIMARY KEY);")

            # 2. Bulk insert emails into the temp table
            cur.fast_executemany = True
            cur.executemany("INSERT INTO #TempEmails (Email) VALUES (?)", params)

            # 3. Perform the UPDATE using a JOIN on the temp table
            # Note: Assumes the email column in ADP_Emp_Scrape is [Email_Address]
            update_sql = f"""
                UPDATE T1
                SET T1.[Scraped] = 1
                FROM {SCRAPE_TABLE} AS T1
                JOIN #TempEmails AS T2 ON T1.[Email_Address] = T2.[Email];
            """
            cur.execute(update_sql)
            updated_count = cur.rowcount

            # 4. Drop the temp table (optional, as it's session-scoped, but good practice)
            cur.execute("DROP TABLE #TempEmails;")

            conn.commit()
            print(f"✅ Successfully updated [Scraped] status for {updated_count} rows.")
            return updated_count

        except Exception as e:
            print(f"❌ ERROR during scrape status update: {e}")
            conn.rollback()  # Rollback changes on error
            # Clean up temp table if it exists
            try:
                cur.execute(
                    "IF OBJECT_ID('tempdb..#TempEmails') IS NOT NULL DROP TABLE #TempEmails;"
                )
            except Exception as e_cleanup:
                print(f"  Cleanup error: {e_cleanup}")
            return 0


# ----------------------------
# Gemini (PDF + query) (from Full_Code.py)
# ----------------------------


# This will work because your old library knows this model
def call_gemini_with_pdf(
    pdf_path: str, query: str, model_name: str = "gemini-2.5-flash"
) -> str:
    """
    Upload a PDF and send it to Gemini along with a query/prompt.
    Returns the model's text response.

    Requires:
      - pip install google-generativeai
      - GEMINI_API_KEY environment variable
    """
    if genai is None:
        raise RuntimeError(
            "google-generativeai is not installed. Run: pip install google-generativeai"
        )

    api_key = "AIzaSyACCeREg7zu2oDTnZONrNpazLSLQNdds80"
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    # Upload file (Gemini handles hosting). You can also pass mime_type explicitly.
    print(f"  Uploading file to Gemini: {pdf_path}")
    file = genai.upload_file(path=pdf_path, mime_type="application/pdf")

    # Wait briefly for processing (optional small loop)
    # In practice, you might poll until file.state.name == "ACTIVE"
    for _ in range(30):  # ~6 seconds max
        file = genai.get_file(file.name)
        state = getattr(file, "state", None)
        if not state or getattr(state, "name", "") == "ACTIVE":
            break
        time.sleep(0.2)

    if getattr(getattr(file, "state", None), "name", "") != "ACTIVE":
        raise RuntimeError(
            f"File {file.name} failed to process. State: {file.state.name}"
        )

    # Generate content, passing both the file and your text query
    print("  File uploaded. Sending query to Gemini...")
    resp = model.generate_content([file, query])

    # Clean up the file from Gemini's storage
    try:
        genai.delete_file(file.name)
        print("  Cleaned up temporary file from Gemini.")
    except Exception as e:
        print(f"  Warning: Could not delete file {file.name}. Error: {e}")

    # If you need citations or JSON, inspect resp.candidates, resp.prompt_feedback, etc.
    return resp.text or ""


# ==============================================================================
# == PART 2: SELENIUM SCRAPER LOGIC (from Scrapping.py)
# ==============================================================================


# ----------------------------
# Base Scraper Class
# ----------------------------
class BaseScraper:
    """Handles reusable Selenium logic for Edge."""

    def __init__(self, driver_path: str, download_dir: str = "downloads"):
        self.driver_path = driver_path
        self.download_dir = os.path.join(os.getcwd(), download_dir)
        self.driver = None
        self.wait = None

    def setup_driver(self):
        """Initializes Edge WebDriver with default options."""
        print("Initializing Edge driver...")

        os.makedirs(self.download_dir, exist_ok=True)
        print(f"Downloads directory: {self.download_dir}")

        options = Options()
        # options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        prefs = {
            "plugins.always_open_pdf_externally": True,
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        }
        options.add_experimental_option("prefs", prefs)

        try:
            service = Service(self.driver_path)
            self.driver = webdriver.Edge(service=service, options=options)
            self.driver.implicitly_wait(5)
            self.wait = WebDriverWait(self.driver, 20)
            print("✅ Edge driver initialized successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize driver: {e}")

    def close(self):
        """Safely closes the browser."""
        if self.driver:
            print("Closing browser...")
            self.driver.quit()

    def __enter__(self):
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ----------------------------
# ADP-Specific Scraper Class
# ----------------------------
class Scrapper(BaseScraper):
    """Contains the ADP portal automation logic."""

    def _find_maybe_in_shadow(self, css_selector: str, timeout: int = 20):
        """
        Try to find an element by CSS selector in the regular DOM first.
        If not found, execute a recursive JS search through shadow roots.
        Returns a Selenium WebElement or raises TimeoutException.
        """
        # 1) Try normal DOM lookup with explicit wait
        try:
            return WebDriverWait(self.driver, min(5, timeout)).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
        except TimeoutException:
            pass  # fallback to shadow search below

        # 2) Recursive Shadow DOM search (returns the first matching element)
        js = """
        const selector = arguments[0];
        function findIn(root){
            if(!root) return null;
            try {
                const el = root.querySelector(selector);
                if(el) return el;
            } catch(e) {}
            const nodes = (root === document ? Array.from(document.querySelectorAll('*')) : Array.from(root.querySelectorAll('*')));
            for (const n of nodes){
                if (n.shadowRoot){
                    const found = findIn(n.shadowRoot);
                    if (found) return found;
                }
            }
            return null;
        }
        return findIn(document);
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            result = self.driver.execute_script(js, css_selector)
            if result:
                return result
            time.sleep(0.5)

        raise TimeoutException(
            f"Element not found (normal DOM or Shadow DOM): {css_selector}"
        )

    def __init__(self, driver_path):
        # Changed download_dir to "downloads" per user request.
        super().__init__(driver_path, download_dir="downloads")

    def get_shadow_element(self, root_selector: str, element_selector: str):
        last = None
        for _ in range(5):
            try:
                # Pass args to avoid quoting issues; returns a fresh element handle
                el = self.driver.execute_script(
                    """
                    const host = document.querySelector(arguments[0]);
                    if (!host || !host.shadowRoot) { return null; }
                    return host.shadowRoot.querySelector(arguments[1]);
                    """,
                    root_selector,
                    element_selector,
                )
                if el:
                    return el
            except StaleElementReferenceException:
                last = "stale"
            time.sleep(0.3)
        raise TimeoutException(
            f"Shadow element not found: {root_selector} >> {element_selector} (last={last})"
        )

    def login(self, username: str, password: str) -> bool:
        """Logs into ADP, including handling 2FA verification screen."""
        url = "https://online.adp.com/signin/v1/?APPID=WFNPortal&productId=80e309c3-7085-bae1-e053-3505430b5495&returnURL=https://workforcenow.adp.com/&callingAppId=WFN&TARGET=-SM-https%3a%2f%2fworkforcenow%2eadp%2ecom%2ftheme%2findex%2ehtml%23/home"
        print(f"Navigating to ADP login page: {url}")

        try:
            self.driver.get(url)

            # === STEP 1: ENTER USERNAME ===
            print("Waiting for username field...")
            username_host = self.wait.until(
                EC.presence_of_element_located((By.ID, "login-form_username"))
            )
            shadow_root = self.driver.execute_script(
                "return arguments[0].shadowRoot", username_host
            )
            username_input = shadow_root.find_element(By.CSS_SELECTOR, "input#input")
            username_input.clear()
            username_input.send_keys(username)
            print("✅ Username entered.")

            # === STEP 2: CLICK NEXT ===
            next_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "verifUseridBtn"))
            )
            next_btn.click()
            print("Clicked Next button...")

            # === STEP 3: ENTER PASSWORD ===
            print("Waiting for password field...")
            password_host = self.wait.until(
                EC.presence_of_element_located((By.ID, "login-form_password"))
            )
            shadow_root_pass = self.driver.execute_script(
                "return arguments[0].shadowRoot", password_host
            )
            password_input = shadow_root_pass.find_element(
                By.CSS_SELECTOR, "input#input"
            )
            password_input.clear()
            password_input.send_keys(password)
            print("✅ Password entered.")

            # === STEP 4: CLICK SIGN IN ===
            sign_in_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "signBtn"))
            )
            sign_in_btn.click()
            print("Clicked Sign In button...")

            # === STEP 5: HANDLE 2FA VERIFICATION PAGE ===
            print("Checking for Verify Your Identity screen...")
            try:
                verify_title = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "login-layout_welcome"))
                )
                if "Verify Your Identity" in verify_title.text:
                    print(
                        "🔒 2FA verification detected — clicking 'Send me a text message'..."
                    )

                    # Locate shadow host for Send me a text message
                    sdf_box = self.wait.until(
                        EC.presence_of_element_located((By.ID, "mobileListButton"))
                    )

                    # Click via JS (Shadow DOM-safe)
                    self.driver.execute_script("arguments[0].click();", sdf_box)
                    print("✅ 'Send me a text message' clicked successfully.")

                    print("Waiting for SMS verification to complete...")
                    time.sleep(5)
                else:
                    print("No Verify Identity page detected — continuing.")
            except TimeoutException:
                print("No 2FA step appeared (skipping).")

            # === STEP 6: CONFIRM LOGIN SUCCESS ===
            print("Waiting for dashboard or post-login redirect...")
            # Wait until the URL no longer contains 'signin'
            self.wait.until(lambda d: "signin" not in d.current_url.lower())

            # Also wait for a known dashboard element to appear (e.g., the search input)
            print("Waiting for dashboard search field to be ready...")
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "sfc-shell-app-bar-search")
                )
            )

            print(f"✅ Login successful! Current URL: {self.driver.current_url}")
            return True

        except Exception as e:
            print(f"❌ Login failed: {e}")
            try:
                self.driver.save_screenshot("login_error.png")
                print("Saved screenshot to login_error.png")
            except:
                print("Could not save screenshot.")
            return False

    def navigate_to_home(self):
        """
        Navigates back to the main dashboard page to ensure the search bar is available.
        """
        print("Navigating back to main dashboard...")
        # This URL is based on the one used in login, pointing to the home/dashboard.
        home_url = "https://workforcenow.adp.com/theme/index.html#/home"
        self.driver.get(home_url)
        try:
            # Wait for the search bar to be present first
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "sfc-shell-app-bar-search")
                )
            )

            # --- MODIFIED: Wait for the pane to be gone ---
            PANE_SELECTOR = (By.ID, "EMPLOYMENTPROFILE_STATUS_CARD_SUPPORTDOC_SLIDEIN")
            WebDriverWait(self.driver, 10).until(
                EC.invisibility_of_element_located(PANE_SELECTOR)
            )

            print("✅ Dashboard ready for next search (pane is hidden).")
            return True
        except TimeoutException:
            # This exception means the pane was *still visible* after 10s.
            # OR the search bar was never found.
            # Let's check if the pane was the problem.
            try:
                pane_check = self.driver.find_element(*PANE_SELECTOR)
                if pane_check.is_displayed():
                    print("❌ ERROR: Pane was still visible. Navigation failed.")
                    return False
            except:
                # Pane was not found, which is good.
                # This means the search bar must have been the problem.
                pass

            # If the pane *wasn't* the problem, let's just assume the
            # timeout on invisibility was a good thing (it was already invisible).
            # Re-check for search bar presence just in case.
            try:
                self.driver.find_element(By.CSS_SELECTOR, "sfc-shell-app-bar-search")
                print("✅ Dashboard ready for next search (pane was not found).")
                return True
            except:
                print(
                    "❌ ERROR: Could not navigate back to dashboard or find search bar."
                )
                return False

    def search_with_candidate_name(self, name: str = "Test"):
        print(f"Searching for candidate: {name}")

        # --- ADDED: Extra safeguard wait for pane to be invisible ---
        try:
            PANE_SELECTOR = (By.ID, "EMPLOYMENTPROFILE_STATUS_CARD_SUPPORTDOC_SLIDEIN")
            WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located(PANE_SELECTOR)
            )
        except TimeoutException:
            # It might already be gone, that's fine.
            pass

        el = self.get_shadow_element(
            "sfc-shell-app-bar-search", "input[aria-label='Search']"
        )
        RESULT_LINK = (By.CSS_SELECTOR, "sdf-link[data-aoid]")

        # --- MODIFIED: Add a try/except for the click itself ---
        try:
            el.click()
        except Exception as e:
            print(f"❌ ERROR: Failed to click search bar: {e}")
            # Try a JS click as a fallback
            try:
                print("  Trying JS click as fallback...")
                self.driver.execute_script("arguments[0].click();", el)
            except Exception as js_e:
                print(f"  JS click also failed: {js_e}")
                return False

        time.sleep(1)
        el.clear()
        time.sleep(1)
        el.send_keys(name)
        try:
            el = self.wait.until(EC.presence_of_element_located(RESULT_LINK))
            el.click()
            print(f"✅ Clicked search result for {name}.")
            return True
        except TimeoutException:
            print(f"⚠️ No search result found for {name}.")
            return False

    def click_support_document_link(self):
        print("Clicking 'Support Documents' link...")
        SUPPORT_DOCUMENTS_LINK = (By.CSS_SELECTOR, "#statusSupDocsButton")
        try:
            el = self.wait.until(EC.element_to_be_clickable(SUPPORT_DOCUMENTS_LINK))
            el.click()
            print("✅ Clicked 'Support Documents'.")
            return True
        except TimeoutException:
            print("❌ Could not find 'Support Documents' button.")
            return False

    def has_documents(self):
        print("Checking for documents...")
        NO_RESULTS_MESSAGE = (By.CSS_SELECTOR, ".mdf-grid-noDataMessage")
        try:
            # Wait for either the no-results message OR the PDF link to appear
            WebDriverWait(self.driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located(NO_RESULTS_MESSAGE),
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[title='f8850.pdf']")
                    ),
                )
            )
        except TimeoutException:
            print("⚠️ Timed out waiting for document list to load.")
            return False  # Unsure, assume no

        elements = self.driver.find_elements(*NO_RESULTS_MESSAGE)
        if len(elements) > 0:
            print("No documents found for this candidate.")
            return False
        else:
            print("✅ Documents found.")
            return True

    def downlaod_f8850_pdf(self, first_name: str, last_name: str) -> Optional[str]:
        """
        Clicks the download link, waits for the file to complete,
        and renames it to a unique name.
        Returns the full path to the new file, or None on failure.
        """
        print(f"Attempting to download f8850.pdf for {first_name} {last_name}...")
        PDF_BUTTON = (By.CSS_SELECTOR, "a[title='f8850.pdf']")

        # Get list of files *before* clicking download
        files_before = set(os.listdir(self.download_dir))

        try:
            el = self.wait.until(EC.element_to_be_clickable(PDF_BUTTON))
            el.click()
            print("Download clicked. Waiting for file to complete...")
        except TimeoutException:
            print("❌ Could not find 'f8850.pdf' download link.")
            return None

        # Wait for download to complete
        end_time = time.time() + 30  # 30 second timeout
        downloaded_file_name = None

        while time.time() < end_time:
            files_after = set(os.listdir(self.download_dir))
            new_files = files_after - files_before

            # Check for incomplete download files
            crdownload_files = [f for f in new_files if f.endswith(".crdownload")]
            # Check for completed PDF files
            pdf_files = [f for f in new_files if f.endswith(".pdf")]

            if pdf_files and not crdownload_files:
                # Download is complete
                downloaded_file_name = pdf_files[0]  # Get the first new PDF
                break

            time.sleep(0.5)  # Poll every half second

        if not downloaded_file_name:
            print("❌ Download timed out or file was not found.")
            # Clean up any partial files if they exist
            for f in crdownload_files:
                try:
                    os.remove(os.path.join(self.download_dir, f))
                except Exception:
                    pass
            return None

        # --- File is downloaded, now rename it ---
        try:
            old_path = os.path.join(self.download_dir, downloaded_file_name)

            # Sanitize names to create a safe file name
            safe_first = "".join(
                c for c in first_name if c.isalnum() or c in "-_"
            ).strip()
            safe_last = "".join(
                c for c in last_name if c.isalnum() or c in "-_"
            ).strip()

            if not safe_first:
                safe_first = "FirstName"
            if not safe_last:
                safe_last = "LastName"

            # Add timestamp for uniqueness
            new_filename = f"{safe_last}_{safe_first}_{int(time.time())}.pdf"
            new_path = os.path.join(self.download_dir, new_filename)

            os.rename(old_path, new_path)

            print(f"✅ Download complete. Renamed to: {new_filename}")
            return new_path  # Return the full path to the new file

        except Exception as e:
            print(f"❌ Error renaming file {downloaded_file_name}: {e}")
            # Try to return the original path if rename failed
            if os.path.exists(old_path):
                print(f"  Using original downloaded file: {old_path}")
                return old_path
            return None

    def close_supporting_docs(self):
        print("Closing 'Supporting Docs' pane by refreshing the page...")
        try:
            self.driver.refresh()
            # After refreshing, we must wait for the dashboard to be ready again
            # This makes the function robust and ensures the next search can start.
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "sfc-shell-app-bar-search")
                )
            )
            # Also, ensure the pane is gone
            PANE_SELECTOR = (By.ID, "EMPLOYMENTPROFILE_STATUS_CARD_SUPPORTDOC_SLIDEIN")
            WebDriverWait(self.driver, 10).until(
                EC.invisibility_of_element_located(PANE_SELECTOR)
            )
            print("✅ Page refreshed, dashboard is ready and pane is hidden.")
        except Exception as e:
            print(f"⚠️ An error occurred while refreshing the page: {e}")
            # If refresh fails, try navigating home as a fallback
            self.navigate_to_home()


# ==============================================================================
# == PART 3: INTEGRATED EXECUTION
# ==============================================================================
if __name__ == "__main__":

    # --- Config ---
    EDGE_DRIVER_PATH = r"C:\Users\Max Madden\OneDrive - cuicable.com\Documents\Mahmoud\edgedriver_win64\msedgedriver.exe"
    ADP_USERNAME = "maddenxmax"
    ADP_PASSWORD = "Ncaa12ncaa12!"

    employees_to_process = []
    hired_rows_to_insert = []  # For collecting Gemini results
    emails_to_update = []  # NEW: For collecting emails to mark as [Scraped] = 1
    conn = None

    # --- Define the "Checkbox Prompt" for Gemini ---
    checkbox_prompt = """
    Analyze the attached PDF form (Form 8850). I need to know the status 
    of the 7 main qualification checkboxes.

    Respond ONLY with a single JSON object.
    The keys must be "Box1", "Box2", "Box3", "Box4", "Box5", "Box6", and "Box7".
    The value for each key must be a boolean: true if the box is checked, 
    and false if it is unchecked.

    Example of a perfect response:
    {
      "Box1": false,
      "Box2": true,
      "Box3": false,
      "Box4": false,
      "Box5": false,
      "Box6": true,
      "Box7": false
    }
    """

    # --- Step 1: Fetch Names from Database ---
    try:
        conn = get_db_connection()
        active_rows = fetch_active_employees(conn, top_n=1000)

        for row in active_rows:
            first = row.get("First_Name")
            last = row.get("Last_Name")
            email = row.get("Email_Address")
            if first and last:
                full_name = f"{first.strip()} {last.strip()}"
                employees_to_process.append(
                    {
                        "first": first.strip(),
                        "last": last.strip(),
                        "email": email.strip() if email else None,
                        "full_name": full_name,
                    }
                )

        print(
            f"\nSuccessfully prepared {len(employees_to_process)} employees for scraping."
        )
        # print(f"Employees: {employees_to_process}") # Uncomment to debug

    except Exception as e:
        print(f"❌ CRITICAL: Failed to fetch names from database: {e}")
        employees_to_process = []  # Ensure list is empty so scraper doesn't run
    finally:
        if conn:
            conn.close()
            print("SQL Server connection closed.")

    # --- Step 2: Run Scraper, Download PDFs, and Process with Gemini ---
    if not os.path.exists(EDGE_DRIVER_PATH):
        print("=" * 60)
        print(f"❌ Error: EdgeDriver not found at:\n{EDGE_DRIVER_PATH}")
        print(
            "Download it here: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/"
        )
        print("=" * 60)

    # Only run scraper if we successfully got employees
    elif employees_to_process:
        print("\nStarting ADP Scraper...")
        try:
            with Scrapper(EDGE_DRIVER_PATH) as scraper:
                if scraper.login(ADP_USERNAME, ADP_PASSWORD):
                    print("\n✅ Login confirmed! Starting employee processing loop.")

                    # This loop will process ALL employees fetched from the DB
                    for employee in employees_to_process:
                        print("-" * 40)
                        name = employee["full_name"]
                        first_name = employee["first"]
                        last_name = employee["last"]
                        email = employee["email"]

                        print(f"Processing candidate: {name}")

                        if not scraper.search_with_candidate_name(name):
                            # Search failed (no result), skip to next name
                            continue

                        if not scraper.click_support_document_link():
                            # Failed to find docs link, skip to next name
                            # (May need to navigate back to search here if state is bad)
                            continue

                        downloaded_pdf_path = None
                        if scraper.has_documents():
                            print(f"Found documents for {name}.")
                            downloaded_pdf_path = scraper.downlaod_f8850_pdf(
                                first_name, last_name
                            )
                        else:
                            print(f"Candidate {name} has no documents.")

                        # This is the corrected close function. It will no longer hang.
                        scraper.close_supporting_docs()
                        print(f"Finished ADP scraping for {name}.")

                        # --- NEW: Process the downloaded file ---
                        if downloaded_pdf_path:
                            try:
                                print(f"Processing file: {downloaded_pdf_path}")
                                # 5) Call Gemini for this specific PDF
                                gemini_response_text = call_gemini_with_pdf(
                                    downloaded_pdf_path, checkbox_prompt
                                )

                                # 6) Clean and parse the JSON response
                                if gemini_response_text.strip().startswith("```json"):
                                    gemini_response_text = gemini_response_text.strip()[
                                        7:-3
                                    ].strip()

                                checkbox_data = json.loads(gemini_response_text)

                                # 7) Create the final row using data from DB + Gemini
                                new_row = {
                                    "First Name": first_name,
                                    "Last Name": last_name,
                                    "Email": email,
                                    "Box1": checkbox_data.get("Box1"),
                                    "Box2": checkbox_data.get("Box2"),
                                    "Box3": checkbox_data.get("Box3"),
                                    "Box4": checkbox_data.get("Box4"),
                                    "Box5": checkbox_data.get("Box5"),
                                    "Box6": checkbox_data.get("Box6"),
                                    "Box7": checkbox_data.get("Box7"),
                                }
                                hired_rows_to_insert.append(new_row)

                                # NEW: Add email to the list for DB update
                                if email:
                                    emails_to_update.append(email)

                                print(f"✅ Successfully processed PDF for {name}.")

                            except Exception as e:
                                print(
                                    f"❌ ERROR: Failed to process PDF for {name}. Error: {e}"
                                )

                            finally:
                                # Clean up the local file
                                try:
                                    os.remove(downloaded_pdf_path)
                                    print(
                                        f"  Cleaned up local file: {downloaded_pdf_path}"
                                    )
                                except Exception as e:
                                    print(
                                        f"  Warning: Could not delete local file {downloaded_pdf_path}. Error: {e}"
                                    )

                        # --- REMOVED: Redundant navigate_to_home call ---
                        # The close_supporting_docs function now handles refreshing
                        # and waiting for the dashboard to be ready.

                        time.sleep(2)  # Small delay between candidates

                else:
                    print(
                        "❌ Login failed — check credentials or MFA prompt. Cannot proceed."
                    )

        except Exception as e:
            print(f"❌ An unexpected error occurred during scraping: {e}")

    else:
        print("\nScraper not started: No employees were fetched from the database.")

    # --- Step 3: Bulk Insert All Processed Rows ---
    if hired_rows_to_insert:
        print("\n" + "=" * 60)
        print(
            f"Attempting to insert {len(hired_rows_to_insert)} processed rows into {HIRED_TABLE}..."
        )
        try:
            conn = get_db_connection()
            ensure_hired_table_exists(conn)  # Ensure table exists before insert
            inserted = bulk_insert_hired_emps(conn, hired_rows_to_insert)
            print(f"✅ Successfully inserted {inserted} rows into {HIRED_TABLE}.")
        except Exception as e:
            print(f"❌ CRITICAL: Failed to insert rows into database: {e}")
        finally:
            if "conn" in locals() and conn:
                conn.close()
                print("SQL Server connection closed.")
    else:
        print("\nNo new rows were processed to be inserted into the database.")

    # --- NEW: Step 4: Update Scraped Status in DB ---
    if emails_to_update:
        print("\n" + "=" * 60)
        print(
            f"Attempting to update [Scraped] status for {len(emails_to_update)} employees..."
        )
        try:
            conn = get_db_connection()
            update_scraped_status(conn, emails_to_update)
        except Exception as e:
            print(f"❌ CRITICAL: Failed to update [Scraped] status in database: {e}")
        finally:
            if "conn" in locals() and conn:
                conn.close()
                print("SQL Server connection closed.")
    else:
        print("\nNo employee statuses to update in the database.")

    print("\nScript finished. Closing in 5 seconds...")
    time.sleep(5)
