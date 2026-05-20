import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

import subprocess, argparse, json, re, asyncio, os, yaml, gc, time, random, requests, shutil, sys, hashlib
from colorama import Fore, Style, init
from tqdm import tqdm

with_subs = True
VERBOSE = False

BATCH_SIZE = 5000 
cookie = ""
VERSION = open("version.txt", "r").read().strip()
GITHUB_VERSION = requests.get("https://raw.githubusercontent.com/bigzooooz/KeyHunter/refs/heads/main/version.txt", verify=False).text.strip()
if GITHUB_VERSION == "404: Not Found":
    GITHUB_VERSION = VERSION

X_REQUEST_FOR = ""
HTTPX_PATH = None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko"
]

REQUIRED_TOOLS = {
    "subfinder": {
        "check_paths": ["subfinder"],
        "install_go": "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        "install_apt": "apt-get install -y subfinder"
    },
    "waybackurls": {
        "check_paths": ["waybackurls"],
        "install_go": "go install github.com/tomnomnom/waybackurls@latest",
        "install_apt": "apt-get install -y waybackurls"
    },
    "httpx": {
        "check_paths": ["/usr/bin/httpx", "httpx"],
        "install_go": "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest",
        "install_apt": "apt-get install -y httpx"
    },
    "katana": {
        "check_paths": ["katana"],
        "install_go": "go install -v github.com/projectdiscovery/katana/cmd/katana@latest",
        "install_apt": "apt-get install -y katana"
    }
}

def is_root():
    """Check if the script is running as root."""
    return os.geteuid() == 0 if hasattr(os, 'geteuid') else False

def check_tool(tool_name):
    """Check if a tool exists in the system."""
    tool_info = REQUIRED_TOOLS.get(tool_name)
    if not tool_info:
        return None, None
    
    for path in tool_info["check_paths"]:
        full_path = shutil.which(path)
        if full_path:
            return True, full_path
        if os.path.exists(path) and os.access(path, os.X_OK):
            return True, path
    
    return False, None

def install_tool(tool_name):
    """Install a tool using available package manager."""
    tool_info = REQUIRED_TOOLS.get(tool_name)
    if not tool_info:
        return False
    
    go_available = shutil.which("go") is not None
    apt_available = shutil.which("apt-get") is not None
    
    if go_available:
        print(Fore.YELLOW + f"[*] Installing {tool_name} using Go...")
        try:
            result = subprocess.run(
                tool_info["install_go"].split(),
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                found, path = check_tool(tool_name)
                if found:
                    print(Fore.GREEN + f"[+] Successfully installed {tool_name} at {path}")
                    return True
                else:
                    gopath = os.environ.get("GOPATH", os.path.expanduser("~/go"))
                    go_bin_path = os.path.join(gopath, "bin", tool_name)
                    if os.path.exists(go_bin_path):
                        print(Fore.GREEN + f"[+] Successfully installed {tool_name} at {go_bin_path}")
                        print(Fore.YELLOW + f"[!] Make sure {gopath}/bin is in your PATH")
                        return True
            else:
                print(Fore.RED + f"[-] Failed to install {tool_name} via Go: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(Fore.RED + f"[-] Timeout while installing {tool_name} via Go")
        except Exception as e:
            print(Fore.RED + f"[-] Error installing {tool_name} via Go: {e}")
    
    if apt_available:
        print(Fore.YELLOW + f"[*] Installing {tool_name} using apt-get...")
        try:
            result = subprocess.run(
                tool_info["install_apt"].split(),
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                found, path = check_tool(tool_name)
                if found:
                    print(Fore.GREEN + f"[+] Successfully installed {tool_name} at {path}")
                    return True
                else:
                    print(Fore.YELLOW + f"[!] {tool_name} installed but not found in PATH")
                    return True
            else:
                print(Fore.RED + f"[-] Failed to install {tool_name} via apt-get: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(Fore.RED + f"[-] Timeout while installing {tool_name} via apt-get")
        except Exception as e:
            print(Fore.RED + f"[-] Error installing {tool_name} via apt-get: {e}")
    
    return False

def check_dependencies(install=False):
    """Check all required dependencies and optionally install if missing."""
    missing_tools = []
    
    for tool_name in REQUIRED_TOOLS.keys():
        found, path = check_tool(tool_name)
        if not found:
            print(Fore.YELLOW + f"[-] {tool_name} not found")
            missing_tools.append(tool_name)
    
    if not missing_tools:
        if install:
            print(Fore.GREEN + "[+] All dependencies are already installed!")
        return True
    
    print("")
    if install:
        if not is_root():
            print(Fore.RED + "[-] Installation requires root privileges. Please run with sudo.")
            print(Fore.YELLOW + "[!] Example: sudo python3 Keyhunter.py --install")
            return False
        
        print(Fore.CYAN + "[*] Installing missing dependencies...")
        print(Fore.CYAN + "[*] This may take a few minutes...")
        print("")
        
        failed_tools = []
        for tool_name in missing_tools:
            if not install_tool(tool_name):
                failed_tools.append(tool_name)
        
        if failed_tools:
            print("")
            print(Fore.RED + f"[-] Failed to install: {', '.join(failed_tools)}")
            print(Fore.YELLOW + "[!] Please install them manually and try again.")
            return False
        
        print("")
        print(Fore.WHITE + "[+] Re-checking dependencies...")
        all_found = True
        for tool_name in missing_tools:
            found, path = check_tool(tool_name)
            if not found:
                print(Fore.RED + f"[-] {tool_name} still not found after installation")
                all_found = False
        
        if all_found:
            print(Fore.GREEN + "[+] All dependencies are now installed!")
            return True
        else:
            print(Fore.YELLOW + "[!] Some tools may need to be added to PATH. Please restart your terminal or add them manually.")
            return False
    else:
        print(Fore.RED + f"[-] Missing dependencies: {', '.join(missing_tools)}")
        print(Fore.YELLOW + "[!] Run with --install flag to automatically install missing dependencies (requires sudo).")
        print(Fore.YELLOW + "[!] Or install them manually:")
        for tool_name in missing_tools:
            tool_info = REQUIRED_TOOLS[tool_name]
            if shutil.which("go"):
                print(Fore.WHITE + f"    {tool_info['install_go']}")
            elif shutil.which("apt-get"):
                print(Fore.WHITE + f"    sudo {tool_info['install_apt']}")
        return False


def run_subfinder(domain):
    try:
        cmd = ["subfinder", "-d", domain, "-all", "-recursive"]
        if not VERBOSE:
            cmd.append("-silent")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return (line.strip() for line in result.stdout.splitlines()) 
    except Exception as e:
        print(f"Error running subfinder: {e}")
        return iter([])

def run_waybackurls(domain):
    try:
        if with_subs:
            cmd = f'echo {domain} | waybackurls'
        else:
            cmd = f'echo {domain} | waybackurls -no-subs'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        filtered_urls = result.stdout.splitlines()
        filtered_urls = [url for url in filtered_urls if not any(url.lower().endswith(ext) for ext in excluded_extensions)]
        filtered_urls = [remove_version_param(url) for url in filtered_urls]
        filtered_urls = list(set(filtered_urls))


        return filtered_urls

    except Exception as e:
        print(f"Error running WaybackURLs: {e}")
        return []

def run_katana(target, depth=5):
    try:
        ef = ",".join(ext.lstrip(".") for ext in excluded_extensions) if excluded_extensions else ""
        cmd = ["katana", "-u", target, "-jc", "-d", str(depth)]
        if ef:
            cmd.extend(["-ef", ef])
        if not VERBOSE:
            cmd.append("-silent")
        result = subprocess.run(cmd, capture_output=True, text=True)
        urls = result.stdout.splitlines()
        urls = [u.strip() for u in urls if u.strip()]
        urls = [u for u in urls if not any(u.lower().endswith(ext) for ext in excluded_extensions)]
        urls = [remove_version_param(u) for u in urls]
        urls = list(set(urls))
        return urls
    except Exception as e:
        print(f"Error running katana: {e}")
        return []

def remove_version_param(url):
    return re.sub(r'(\?v=|ver=|version=|rev=|timestamp=|build=|_token=)[^&]+', '', url).rstrip('?')


def batched(iterable, size):
    """Yields chunks of the iterable in batches of the given size."""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch

def load_api_key_patterns(yaml_file):
    try:
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)

        api_key_patterns = {}

        def extract_patterns(d, parent_key=""):
            """ Recursively extract regex patterns from nested dictionaries. """
            for key, value in d.items():
                new_key = f"{parent_key} - {key}" if parent_key else key
                if isinstance(value, str):
                    api_key_patterns[new_key] = re.compile(r"{}".format(value))
                elif isinstance(value, dict):
                    extract_patterns(value, new_key)

        extract_patterns(data.get("api_keys", {}))
        return api_key_patterns

    except Exception as e:
        if VERBOSE:
            print(Fore.YELLOW + f"[-] Error loading API key patterns: {e}")
        return {}

def load_excluded_extensions(yaml_file):
    try:
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
        
        excluded_extensions = data.get("excluded_extensions", [])
        return excluded_extensions

    except Exception as e:
        if VERBOSE:
            print(Fore.YELLOW + f"[-] Error loading excluded extensions: {e}")
        return []

api_key_patterns = load_api_key_patterns("api_patterns.yaml")

excluded_extensions = load_excluded_extensions("excluded_extensions.yaml")

def search_for_api_keys(content, url, domain, output_file):
    keys_found = {}
    for provider, pattern in api_key_patterns.items():
        matches = pattern.findall(content)
        if matches:
            unique_matches = []
            seen = set()
            for match in matches:
                if match not in seen:
                    seen.add(match)
                    unique_matches.append(match)
            
            keys_found[provider] = {'keys': unique_matches}
            
            print(Fore.GREEN + f"[+] Found {provider}:")
            for key in unique_matches:
                print(Fore.GREEN + f"    - {key}")
            print(Fore.GREEN + f"    URL: {url}")
            print(Fore.GREEN + "-"*50)

            save_results(domain, {url: keys_found}, output_file, incremental=True)
    return keys_found


def fetch_url(url):
    global cookie
    global X_REQUEST_FOR

    if not url or not isinstance(url, str) or not url.strip():
        if VERBOSE:
            print(Fore.YELLOW + f"[-] Invalid URL (empty or None): {url}")
        return None, None
    
    url = url.strip()
    
    try:
        if ' ' in url and not url.startswith("http://") and not url.startswith("https://"):
            if VERBOSE:
                print(Fore.YELLOW + f"[-] URL contains spaces, might be malformed: {url[:100]}")
    except:
        pass
    
    if not (url.startswith("http://") or url.startswith("https://")):
        if VERBOSE:
            print(Fore.YELLOW + f"[-] Invalid URL format (missing http/https): {url[:100]}")
        return None, None

    try:
        global HTTPX_PATH
        if HTTPX_PATH is None:
            found, path = check_tool("httpx")
            if not found:
                if VERBOSE:
                    print(Fore.RED + f"[-] httpx not found")
                return None, None
            HTTPX_PATH = path
        
        cmd = [HTTPX_PATH, "-u", url, "-json", "-irr", "-fr", "-timeout", "5", "-nc"]
        if VERBOSE:
            cmd.append("-v")
        
        user_agent = random.choice(USER_AGENTS)
        cmd.extend(["-H", f"User-Agent: {user_agent}"])
        cmd.extend(["-H", "Accept-Language: en-US,en;q=0.9"])
        cmd.extend(["-H", "Referer: https://www.google.com/"])
        cmd.extend(["-H", "Accept: */*"])
        cmd.extend(["-H", "Connection: keep-alive"])
        
        if X_REQUEST_FOR:
            cmd.extend(["-H", f"X-Request-For: {X_REQUEST_FOR}"])
        
        if cookie:
            cmd.extend(["-H", f"Cookie: {cookie}"])

        if VERBOSE:
            print(Fore.CYAN + f"[httpx] Executing: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if VERBOSE:
            if result.stdout:
                print(Fore.CYAN + f"[httpx stdout] {url}: {result.stdout.strip()[:500]}")
            if result.stderr:
                print(Fore.CYAN + f"[httpx stderr] {url}: {result.stderr.strip()[:500]}")
            print(Fore.CYAN + f"[httpx] Return code: {result.returncode}")
        
        if result.returncode != 0:
            error_parts = []
            if result.stderr and result.stderr.strip():
                error_parts.append(f"stderr: {result.stderr.strip()}")
            if result.stdout and result.stdout.strip():
                stdout_lines = result.stdout.strip().split('\n')
                error_lines = [line for line in stdout_lines if any(keyword in line.lower() for keyword in ['error', 'failed', 'invalid', 'unable', 'cannot'])]
                if error_lines:
                    error_parts.append(f"stdout errors: {'; '.join(error_lines[:3])}")
                elif len(stdout_lines) < 5:
                    error_parts.append(f"stdout: {result.stdout.strip()[:200]}")
            
            error_msg = "; ".join(error_parts) if error_parts else "Unknown error (no output in stderr or stdout)"
            
            if VERBOSE:
                print(Fore.YELLOW + f"[-] httpx error for {url}: {error_msg}")
                print(Fore.YELLOW + f"    Return code: {result.returncode}")
                if result.stdout:
                    print(Fore.YELLOW + f"    Full stdout: {result.stdout[:500]}")
                if result.stderr:
                    print(Fore.YELLOW + f"    Full stderr: {result.stderr[:500]}")
            return None, None

        if not result.stdout.strip():
            if VERBOSE:
                print(Fore.YELLOW + f"[-] No output from httpx for {url}")
                print(Fore.YELLOW + f"    Return code: {result.returncode}")
                if result.stderr:
                    print(Fore.YELLOW + f"    stderr: {result.stderr.strip()[:200]}")
            return None, None

        try:
            output_lines = result.stdout.strip().split('\n')
            if not output_lines:
                return None, None
            
            json_line = output_lines[-1].strip()
            if not json_line:
                return None, None
            
            httpx_output = json.loads(json_line)
            
            status_code = (httpx_output.get("status_code") or 
                          httpx_output.get("status-code") or 
                          httpx_output.get("status") or 0)
            
            try:
                status_code = int(status_code)
            except (ValueError, TypeError):
                status_code = 0
            
            if status_code != 200:
                if VERBOSE:
                    print(Fore.YELLOW + f"[-] Non-200 status {status_code} for {url}")
                return None, None

            content_type = (httpx_output.get("content_type") or 
                          httpx_output.get("content-type") or 
                          "").lower()
            
            if not any(t in content_type for t in ["text/html", "application/javascript", "text/javascript", "application/json"]):
                if VERBOSE:
                    print(Fore.YELLOW + f"[-] Skipping {url} - content type: {content_type}")
                return None, None

            content = ""
            
            if "response" in httpx_output:
                response_data = httpx_output.get("response", {})
                if isinstance(response_data, dict):
                    content = (response_data.get("body") or 
                              response_data.get("response-body") or 
                              response_data.get("body_decoded") or "")
                elif isinstance(response_data, str):
                    content = response_data
            else:
                content = (httpx_output.get("body") or 
                          httpx_output.get("response-body") or 
                          httpx_output.get("body_decoded") or 
                          httpx_output.get("response") or "")
            
            if not content:
                if VERBOSE:
                    print(Fore.YELLOW + f"[-] No content body for {url}")
                return None, None
            
            if len(content) > 500_000:
                content = content[:500_000]

            return url, content

        except json.JSONDecodeError as e:
            if VERBOSE:
                print(Fore.YELLOW + f"[-] Failed to parse httpx JSON output for {url}: {e}")
                print(Fore.YELLOW + f"    Return code: {result.returncode}")
                print(Fore.YELLOW + f"    stdout (first 500 chars): {result.stdout[:500]}")
                print(Fore.YELLOW + f"    stderr (first 500 chars): {result.stderr[:500] if result.stderr else '(empty)'}")
                if result.stdout and not result.stdout.strip().startswith('{'):
                    print(Fore.YELLOW + f"    Note: stdout doesn't appear to be JSON - might be an error message")
            return None, None
        except Exception as e:
            if VERBOSE:
                print(Fore.YELLOW + f"[-] Unexpected error parsing httpx output for {url}: {e}")
                print(Fore.YELLOW + f"    Return code: {result.returncode}")
                print(Fore.YELLOW + f"    stdout: {result.stdout[:500] if result.stdout else '(empty)'}")
                print(Fore.YELLOW + f"    stderr: {result.stderr[:500] if result.stderr else '(empty)'}")
            return None, None

    except subprocess.TimeoutExpired:
        if VERBOSE:
            print(Fore.YELLOW + f"[-] Timeout for {url}")
    except Exception as e:
        if VERBOSE:
            print(Fore.YELLOW + f"[-] Unexpected error for {url}: {e}")

    return None, None


async def visit_and_check_for_keys(urls, domain, output_file, announce_urls=False):
    api_keys_found = 0
    for batch in batched(urls, BATCH_SIZE):
        tasks = [asyncio.to_thread(fetch_url, url) for url in batch]
        results = await asyncio.gather(*tasks)
        for url, content in results:
            if VERBOSE or announce_urls:
                print(Fore.WHITE + f"[+] Checking {url}")
            if content:
                keys = search_for_api_keys(content, url, domain, output_file)
                if keys:
                    api_keys_found += 1
        gc.collect()

    return api_keys_found

def save_results(domain, api_keys_found, output_file, incremental=False):
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    if incremental:
        try:
            with open(output_file, "r") as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {"domain": domain, "api_keys_found": {}}

        for url, key_data in api_keys_found.items():
            if url not in existing_data["api_keys_found"]:
                existing_data["api_keys_found"][url] = {}

            for provider, data in key_data.items():
                if provider not in existing_data["api_keys_found"][url]:
                    existing_data["api_keys_found"][url][provider] = {'keys': []}

                if isinstance(data['keys'], list):
                    existing_data["api_keys_found"][url][provider]['keys'].extend(data['keys'])
                else:
                    existing_data["api_keys_found"][url][provider]['keys'].append(data['keys'])

        with open(output_file, "w") as f:
            json.dump(existing_data, f, indent=4)

    else:
        output_data = {"domain": domain, "api_keys_found": api_keys_found}
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=4)

        print(Fore.WHITE + f"[+] Results saved to ./{output_file}")


async def main():
    global with_subs
    global cookie
    global X_REQUEST_FOR
    global VERBOSE

    init(autoreset=True)

    print(Fore.CYAN + f"""

    ██╗  ██╗███████╗██╗   ██╗                           
    ██║ ██╔╝██╔════╝╚██╗ ██╔╝                           
    █████╔╝ █████╗   ╚████╔╝                            
    ██╔═██╗ ██╔══╝    ╚██╔╝                             
    ██║  ██╗███████╗   ██║                              
    ╚═╝  ╚═╝╚══════╝   ╚═╝                              
                                                        
    ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗ 
    ██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
    ███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝
    ██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
    ██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║
    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝   v{VERSION}      
                                    
    A tool to discover API key leaks from subdomains and archived URLs.  
                                
    """ + Style.RESET_ALL)

    time.sleep(1)
    print(Fore.YELLOW + "-"*50)
    print(Fore.YELLOW + "If you find this tool useful, consider supporting me:")
    print(Fore.YELLOW + "PayPal: https://paypal.me/b4zb0z")
    print(Fore.YELLOW + "Ko-fi: https://ko-fi.com/b4zb0z")
    print(Fore.YELLOW + "Thank you, your support is greatly appreciated! ❤️")
    print(Fore.YELLOW + "-"*50)
    print("")
    time.sleep(2)

    if VERSION < GITHUB_VERSION:
        print(Fore.YELLOW + f"[!] A new version of KeyHunter is available. Please update to v{GITHUB_VERSION} using '--update' flag.") 
        print("")

    parser = argparse.ArgumentParser(description="KeyHunter - A tool to discover API key leaks from subdomains and archived URLs.")

    parser.usage = "Keyhunter.py -d TARGET_DOMAIN | -f DOMAINS_FILE | -l URLS_FILE [--cookie COOKIE] [--no-subs]"

    parser.add_argument("-d", "--domain", help="Target domain for scanning.")
    parser.add_argument("-f", "--file", help="File containing a list of domains to scan.")
    parser.add_argument("-l", "--urls-file", help="File containing a list of URLs to scan directly.")
    parser.add_argument("-ns", "--no-subs", help="Disable subdomain enumeration.", action="store_true")
    parser.add_argument("--cookie", help="Cookie to use for requests.")
    parser.add_argument("--x-request-for", help="X-Request-For header to use for requests. (i.e. --x-request-for HackerOne)")
    parser.add_argument("--update", help="Update KeyHunter to the latest version.", action="store_true")
    parser.add_argument("--version", help="Show KeyHunter version.", action="store_true")
    parser.add_argument("-v","--verbose", help="Enable verbose output.", action="store_true")
    parser.add_argument("--install", "--setup", help="Install missing dependencies (requires sudo).", action="store_true", dest="install")

    args = parser.parse_args()

    if args.verbose:
        VERBOSE = True
    if args.update:
        if VERSION != GITHUB_VERSION:
            print(Fore.WHITE + "[+] Updating KeyHunter to the latest version...")
            subprocess.run(["git", "fetch", "origin", "main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "reset", "--hard", "origin/main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(Fore.GREEN + "[+] KeyHunter updated successfully. Please re-run the tool.")
            print(Fore.YELLOW + "[!] Exiting...")
            exit(0)
            return
        else:
            print(Fore.GREEN + "[+] KeyHunter is already up-to-date.")
            print(Fore.YELLOW + "[!] Exiting...")
            exit(0)

    if args.x_request_for:
        X_REQUEST_FOR = args.x_request_for

    if args.version:
        print(Fore.WHITE + f"[+] KeyHunter version: {VERSION}")
        print(Fore.YELLOW + "[!] Exiting...")
        exit(0)
        return

    if args.cookie:
        cookie = args.cookie

    if args.no_subs:
        with_subs = False

    if not check_dependencies(install=args.install):
        print("")
        if args.install:
            print(Fore.RED + "[-] Installation failed or incomplete. Cannot proceed.")
        else:
            print(Fore.RED + "[-] Cannot proceed without required dependencies.")
            print(Fore.YELLOW + "[!] Run with --install flag to automatically install missing dependencies (requires sudo).")
        sys.exit(1)
    
    if args.install:
        print("")
        print(Fore.GREEN + "[+] Installation completed successfully!")
        print(Fore.WHITE + "[+] You can now run KeyHunter with a domain or URLs file.")
        print("")
        sys.exit(0)
    
    global HTTPX_PATH
    found, path = check_tool("httpx")
    if found:
        HTTPX_PATH = path
    else:
        print(Fore.RED + "[-] httpx not found even after dependency check. Exiting.")
        sys.exit(1)
    
    print("")

    if args.urls_file:
        try:
            with open(args.urls_file, 'r') as file:
                urls = [line.strip() for line in file if line.strip()]
        except Exception as e:
            print(Fore.RED + f"[-] Error reading URLs from file: {e}")
            exit(1)
        
        if not urls:
            print(Fore.RED + "[-] No URLs found in the file.")
            exit(1)
        
        print(Fore.WHITE + "-"*50)
        print("")
        print(Fore.WHITE + f"- URLs file: {args.urls_file}")
        print(Fore.WHITE + f"- Total URLs: {len(urls)}")
        print(Fore.WHITE + f"- Cookie: {'✔️'  if cookie else '❌'}")
        print(Fore.WHITE + f"- X-Request-For: {X_REQUEST_FOR if X_REQUEST_FOR else '❌'}")
        print("")
        
        print(Fore.GREEN + f"[+] Loaded {len(urls)} URLs from file 🎯")
        print(Fore.WHITE + "[+] Scanning URLs for API key leaks... This may take a while.")
        print("")
        
        file_hash = hashlib.md5(args.urls_file.encode()).hexdigest()[:8]
        output_file = f"output/urls_{file_hash}_results.json"
        api_keys_found = await visit_and_check_for_keys(urls, "urls_file", output_file, announce_urls=True)
        
        print(Fore.WHITE + f"[+] Scanned {len(urls)} URLs.")

        if api_keys_found:
            print(Fore.GREEN + f"[+] Found {api_keys_found} URLs with API keys.")
        else:
            print(Fore.YELLOW + "[-] No API keys found.")
        
        print(Fore.WHITE + "[+] Done! 🎉")
        print("")
    
    else:
        domains = []
        if args.domain:
            domains.append(args.domain)
        elif args.file:
            try:
                with open(args.file, 'r') as file:
                    domains = [line.strip() for line in file if line.strip()]
            except Exception as e:
                print(Fore.RED + f"[-] Error reading domains from file: {e}")
                exit(1)
        else:
            print(Fore.RED + "[-] Please provide either a domain (-d), a file containing domains (-f), or a file containing URLs (-l).")
            exit(1)

        for domain in domains:
            urls = []
            print(Fore.WHITE + "-"*50)
            print("")
            print(Fore.WHITE + f"- Target: {domain}")
            print(Fore.WHITE + f"- Subdomains: {'✔️' if with_subs else '❌'}")
            print(Fore.WHITE + f"- Cookie: {'✔️'  if cookie else '❌'}")
            print(Fore.WHITE + f"- X-Request-For: {X_REQUEST_FOR if X_REQUEST_FOR else '❌'}")
            print("")

            if with_subs:
                print(Fore.WHITE + "[+] Looking for subdomains ...")
                subdomains = [domain] + list(run_subfinder(domain))
                print(Fore.GREEN + f"[+] Found {len(subdomains)} subdomains 🎯")
                print(Fore.WHITE + "[+] Looking for URLs ...")
                for subdomain in subdomains:
                    urls.extend(run_waybackurls(subdomain))
                    urls.extend(run_katana(subdomain, depth=5))

                subdomains = None
                gc.collect()
            else:
                print(Fore.WHITE + "[+] Looking for URLs ...")
                urls.extend(run_waybackurls(domain))
                urls.extend(run_katana(domain, depth=5))

            urls = list(set(urls))
            print(Fore.GREEN + f"[+] Found {len(urls)} URLs 🎯")

            print(Fore.WHITE + "[+] Scanning URLs for API key leaks... This may take a while.")

            output_file = f"output/{domain}_results.json"
            api_keys_found = await visit_and_check_for_keys(urls, domain, output_file)

            print(Fore.WHITE + f"[+] Scanned {len(urls)} URLs.")

            if api_keys_found:
                print(Fore.GREEN + f"[+] Found {api_keys_found} URLs with API keys.")
            else:
                print(Fore.YELLOW + "[-] No API keys found.")
            
            print(Fore.WHITE + "[+] Done! 🎉")
            print("")

if __name__ == "__main__":
    asyncio.run(main())
