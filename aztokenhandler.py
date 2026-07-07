import requests
import urllib3
import json
import sys
import signal
import argparse
import pyperclip
import time
import base64
from urllib.parse import urlparse, parse_qs
import colorama
from colorama import Fore, Style
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
from cryptography.hazmat.primitives import serialization
import hashlib

# Initialize colors
colorama.init(autoreset=True)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Headers and user-agents
default_ua = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Edge/79.0.1451.30 Safari/537.36"
default_headers = {
    "User-Agent": default_ua
}

# Verbose token output variable
verbose = False

# ====================== COMMON RESOURCE URL's ======================
COMMON_RESOURCES = {
    # General
    "1":  {"name": "Microsoft Graph",           "resource": "https://graph.microsoft.com"},
    "2":  {"name": "Azure Resource Manager",    "resource": "https://management.azure.com"},
    "3":  {"name": "Azure Resource Manager (Legacy)",    "resource": "https://management.core.windows.net"},
    "4":  {"name": "Azure Key Vault",           "resource": "https://vault.azure.net"},
    "5":  {"name": "Azure Storage",             "resource": "https://storage.azure.com"},
    # Legacy / Azure AD
    "6":  {"name": "Azure AD Graph (Legacy)",   "resource": "https://graph.windows.net"},
    #Azure Data Services
    "7": {"name": "Azure SQL Database",         "resource": "https://database.windows.net"},
    "8": {"name": "Azure Cosmos DB",            "resource": "https://cosmos.azure.com"},
    "9": {"name": "Azure Event Hubs",           "resource": "https://eventhubs.azure.net"},
    "10": {"name": "Azure Service Bus",          "resource": "https://servicebus.azure.net"},
    # Azure DevOps
    "11": {"name": "Azure DevOps",              "resource": "499b84ac-1321-427f-aa17-267ca6975798"},
    # Other
    "99": {"name": "Custom Resource",           "resource": ""},
}

# ====================== COMMON CLIENT IDs ======================
COMMON_CLIENTS = {
    "1":    {"name": "Microsoft Graph PS",                  
             "common_resources": f"({COMMON_RESOURCES['1']['name']})",      
             "client_id": "14d82eec-204b-4c2f-b7e8-296a70dab67e"},
    "2":    {"name": "Microsoft Azure CLI",                 
             "common_resources": f"({COMMON_RESOURCES['2']['name']} / {COMMON_RESOURCES['1']['name']} / {COMMON_RESOURCES['4']['name']} / {COMMON_RESOURCES['5']['name']} / {COMMON_RESOURCES['7']['name']} / {COMMON_RESOURCES['11']['name']})",      
             "client_id": "04b07795-8ddb-461a-bbee-02f9e1bf7b46"},
    "3":    {"name": "Microsoft Azure PowerShell (Legacy)",          
             "common_resources": f"({COMMON_RESOURCES['2']['name']} / {COMMON_RESOURCES['6']['name']} / {COMMON_RESOURCES['1']['name']} / {COMMON_RESOURCES['4']['name']} / {COMMON_RESOURCES['5']['name']})",      
             "client_id": "1950a258-227b-4e31-a9cf-717495945fc2"},
    "4":    {"name": "Azure AD PowerShell (Even more legacy)",   
             "common_resources": f"({COMMON_RESOURCES['6']['name']} / {COMMON_RESOURCES['3']['name']} / {COMMON_RESOURCES['1']['name']})",      
             "client_id": "1b730954-1685-4b74-9bfd-dac224a7b894"},
    "5":    {"name": "Microsoft Office",                    
             "common_resources": f"({COMMON_RESOURCES['1']['name']})",      
             "client_id": "d3590ed6-52b3-4102-aeff-aad2292ab01c"},
    "6":    {"name": "Microsoft Teams",                     
             "common_resources": f"({COMMON_RESOURCES['1']['name']})",      
             "client_id": "1fec8e78-bce4-4aaf-ab1b-5451cc387264"},
    "7":    {"name": "Microsoft Copilot",                   
             "common_resources": f"({COMMON_RESOURCES['1']['name']})",      
             "client_id": "14638111-3389-403d-b206-a6a71d9f8f16"},
    "8":    {"name": "SharePoint Online",                   
             "common_resources": f"({COMMON_RESOURCES['1']['name']})",      
             "client_id": "08e18876-6177-487e-b8b5-cf950c1e598c"},
    "9":    {"name": "Microsoft Intune Company Portal",     
             "common_resources": f"({COMMON_RESOURCES['1']['name']} / {COMMON_RESOURCES['2']['name']})",      
             "client_id": "9ba1a5c7-f17a-4de9-a1f1-6178c8d51223"},
    "10":   {"name": "Microsoft Authentication Broker",     
             "common_resources": f"({COMMON_RESOURCES['1']['name']})",      
             "client_id": "29d9ed98-a469-4536-ade2-f981bc1d605e"},
    "99":   {"name": "Custom application",                  
             "common_resources": "(Custom application GUID)",               
             "client_id": ""},
}

# ====================== COMMON RESOURCE URL's ======================
COMMON_SCOPES = {
    "1":  {"name": "Default (Access token)                   ",     "scope": ".default"},
    "2":  {"name": "Extended Scope (Refresh and Access Token)",     "scope": ".default offline_access openid profile"},
    "99": {"name": "Custom Scope",                                  "scope": ""},
}

# Main logic
def main():
    parser = argparse.ArgumentParser(description="Azure Token Tool - Multi-Method + Resource Access")
    parser.add_argument("-i", "--interactive", action="store_true", default=True, help="Interactive selection of Client ID + Resource")    
    parser.add_argument("-m", "--method", choices=["cookie", "ropc", "secret", "refresh", "device", "certificate", "tap"], required=True, help="Authentication method")
    parser.add_argument("-tid", "--tenant-id", required=True, help="Tenant ID (required)")
    parser.add_argument("-pid", "--partner-tenant-id", help="Partner / cross-tenant ID")
    parser.add_argument("-cid", "--client-id", help="Client ID (overrides interactive)")
    parser.add_argument("-r", "--resource", help="Resource / Audience")
    parser.add_argument("-s", "--scope", help="Scope")
    parser.add_argument("-ru", "--redirect-uri", default="urn:ietf:wg:oauth:2.0:oob")
    parser.add_argument("-c", "--cookie", help="ESTSAUTHPERSISTENT cookie")
    parser.add_argument("-un", "--username", help="Username (ROPC)")
    parser.add_argument("-pw", "--password", help="Password (ROPC)")
    parser.add_argument("-tpw", "--tap", help="TAP Password (ROPC) [EXPERIMENTAL]")
    parser.add_argument("-cs", "--client-secret", help="Client secret")
    parser.add_argument("-rt", "--refresh-token", help="Refresh token")
    parser.add_argument("-cpfx", "--cert-pfx", help="Path to .pfx file")
    parser.add_argument("-cpw", "--cert-password", help="Password for .pfx")
    parser.add_argument("-ct", "--cert-thumbprint", help="Certificate thumbprint")
    parser.add_argument("-cpk", "--cert-private-key", help="Private key PEM path")
    parser.add_argument("-vn", "--vault-name", help="Key Vault name")
    parser.add_argument("-sa", "--storage-account", help="Storage account name")
    parser.add_argument("-sid", "--subscription-id", help="Subscription ID")
    parser.add_argument("-cp","--clipboard", action="store_true", help="Copy output accesstoken to clipboard variable")
    parser.add_argument("-p", "--proxy", help="Proxy host:port")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose token output")
    parser.add_argument("-t", "--test", action="store_true", help="Test token against resource")

    # Parse arguments
    args = parser.parse_args()

    # Parse global vars
    global verbose, clipboard
    verbose = args.verbose
    clipboard = args.clipboard

    # Interactive 
    if args.interactive:
        if args.client_id is None:
            args.client_id = Selection.interactive_client_selection(args.client_id)
        if args.resource is None:
            args.resource = Selection.interactive_resource_selection(args.resource)
        if args.scope is None:
            args.scope = Selection.interactive_scope_selection(args.scope)

    """
    if not args.client_id:
        print(f"{Fore.RED}[!] Client ID required{Style.RESET_ALL}")
        exit(1)
    """

    # Optional proxy settings
    # proxies = {"http": f"http://{args.proxy}", "https": f"http://{args.proxy}"} if args.proxy else {}
    proxies = Helpers.build_proxies(args.proxy)
    print(proxies)

    # Tenant or parner tenant check
    tenant = args.partner_tenant_id or args.tenant_id
    print(f"\n{Fore.CYAN}Target Tenant : {tenant}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Client ID     : {args.client_id}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Resource      : {args.resource}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Method        : {args.method}{Style.RESET_ALL}\n")

    token_data = Helpers.acquire_token(args, tenant, proxies)

    if token_data and args.test:
        Helpers.test_resource_access(token_data, args, proxies)

class Gettoken:
    # Get the token by using the ESTSAUTHPERSISTENT cookie
    def get_token_with_cookie(args, tenant, proxies):
        if args.method == "cookie" and args.cookie is None:
            print("[!] Cookie is required, exiting...")
            exit(1)   

        print("[*] Using ESTSAUTHPERSISTENT cookie flow...")
        auth_url = f"https://login.microsoftonline.com/{tenant}/oauth2/authorize"
        params = {
            "client_id": args.client_id,
            "redirect_uri": args.redirect_uri,
            "response_type": "code",
            "response_mode": "query",
            # "resource": args.resource, # Old v1 endpoint
            "scope": args.scope,
        }

        # Get authorization code
        headers = {
            "User-Agent": default_ua,
            "Cookie": f"ESTSAUTHPERSISTENT={args.cookie}"
        }
        r = requests.get(auth_url, params=params, headers=headers, proxies=proxies, verify=False, allow_redirects=False)

        location = r.headers.get("Location", "")
        if "code=" not in location:
            print("[!] No authorization code received")
            sys.exit(1)

        code = parse_qs(urlparse(location).query).get("code")[0]
        return Helpers.exchange_code_for_token(args, tenant, code, proxies)

    # Login with username/password
    def get_token_ropc(args, tenant, proxies):
        if ((args.username is None) or (args.password is None)):
            print("[!] Username or password missing, exiting...")
            exit(1)    

        print("[*] Using ROPC...")
        payload = {
            "client_id": args.client_id,
            "grant_type": "password",
            "username": args.username,
            "password": args.password,
            # "resource": args.resource, # Old v1 endpoint
            "scope": args.resource + "/" + args.scope
        }
        r = requests.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=payload, headers=default_headers, proxies=proxies, verify=False)
        return Helpers.handle_token_response(r, "ROPC")

    def get_token_tap(args, tenant, proxies):
        if args.username is None:
            print("[!] Username missing, exiting...")
            exit(1)
        
        if args.tap is None: 
            print("[!] TAP code missing, exiting...")
            exit(1)

        print("[*] Using ROPC with Temporary Access Pass (TAP)...")
        
        payload = {
            "client_id": args.client_id,
            "grant_type": "password",
            "username": args.username,
            "password": args.tap,      
            "scope": f"{args.resource}/{args.scope}" if hasattr(args, 'resource') and args.resource else args.scope
        }
        
        print(f"[*] Authenticating as {args.username} using TAP")
        
        r = requests.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", 
            data=payload, 
            headers=default_headers, 
            proxies=proxies, 
            verify=False
        )
        
        return Helpers.handle_token_response(r, "ROPC_TAP")

    # Get token based on client creds using secret (app related)
    def get_token_client_credentials(args, tenant, proxies):
        if args.client_secret is None:
            print("[!] Client secret missing, exiting...")
            exit(1)    
        print("[*] Using Client Credentials...")
        payload = {
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "grant_type": "client_credentials",
            "scope": args.resource + "/" + args.scope
        }
        r = requests.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=payload, headers=default_headers, proxies=proxies, verify=False)
        return Helpers.handle_token_response(r, "Client Credentials")

    # Use refresh token to get access token
    def get_token_refresh(args, tenant, proxies):
        if args.refresh_token is None:
            print("[!] Refresh token missing, exiting...")
            exit(1)

        print("[*] Using Refresh Token...")
        payload = {
            "client_id": args.client_id,
            #"resource":args.resource, # Old v1 endpoint
            "grant_type": "refresh_token",
            "refresh_token": args.refresh_token,
            "scope": args.resource + "/" + args.scope
        }
        if args.client_secret:
            payload["client_secret"] = args.client_secret
        r = requests.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=payload, headers=default_headers, proxies=proxies, verify=False)
        return Helpers.handle_token_response(r, "Refresh")

    # Device code
    def get_token_device_code(args, tenant, proxies):
        print(f"{Fore.CYAN}[*] Device Code flow...{Style.RESET_ALL}")
        device_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

        r = requests.post(device_url, data={"client_id": args.client_id, "scope": args.resource + "/" + args.scope}, headers=default_headers, proxies=proxies, verify=False)
        data = r.json()

        print(f"\n{Fore.YELLOW}Go to: {data.get('verification_uri')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Code : {data.get('user_code')}{Style.RESET_ALL}")

        interval = data.get("interval", 5)
        expires = time.time() + data.get("expires_in", 900)

        while time.time() < expires:
            resp = requests.post(token_url, headers=default_headers, data={
                "client_id": args.client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": data["device_code"]
            }, proxies=proxies, verify=False)

            if resp.status_code == 200:
                print("\n[+] Token acquired!")
                return Helpers.handle_token_response(resp)
            time.sleep(interval)
        print("[!] Timeout")
        return None

    # Get token based on certificate; PFX support
    def get_token_certificate(args, tenant, proxies):
        try:
            from cryptography.hazmat.primitives import serialization
            import jwt
            import base64
            import uuid
        except ImportError:
            print("pip install cryptography pyjwt[crypto]")
            sys.exit(1)

        print(f"{Fore.CYAN}[*] Certificate flow...{Style.RESET_ALL}")

        try:
            if args.cert_pfx:
                cert_thumbprint, private_key = Helpers.load_pfx_certificate(
                    args.cert_pfx,
                    args.cert_password
                )

            elif args.cert_thumbprint and args.cert_private_key:
                cert_thumbprint = args.cert_thumbprint.strip()

                with open(args.cert_private_key, "rb") as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                    )

            else:
                print("[!] Missing certificate parameters")
                sys.exit(1)

        except Exception as e:
            print(f"[!] Failed to load certificate: {e}")
            sys.exit(1)

        if private_key is None:
            print("[!] Certificate does not contain a private key.")
            sys.exit(1)

        #
        # Azure expects x5t as a base64url-encoded SHA1 thumbprint,
        # not a hexadecimal string.
        #
        try:
            thumb_bytes = bytes.fromhex(cert_thumbprint)
            x5t = base64.urlsafe_b64encode(thumb_bytes).rstrip(b"=").decode()
        except ValueError:
            # Already base64url or otherwise provided
            x5t = cert_thumbprint

        now = int(time.time())

        jwt_payload = {
            "aud": f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "iss": args.client_id,
            "sub": args.client_id,
            "nbf": now,
            "exp": now + 300,
            "jti": str(uuid.uuid4()),
        }

        jwt_headers = {
            "alg": "RS256",
            "typ": "JWT",
            "x5t": x5t,
        }

        try:
            assertion = jwt.encode(
                jwt_payload,
                private_key,
                algorithm="RS256",
                headers=jwt_headers,
            )
        except Exception as e:
            print(f"[!] Failed to sign client assertion: {e}")
            sys.exit(1)

        payload = {
            "client_id": args.client_id,
            "grant_type": "client_credentials",
            "client_assertion_type": (
                "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
            ),
            "client_assertion": assertion,
            "scope": f"{args.resource}/{args.scope}",
        }

        r = requests.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data=payload,
            headers=default_headers,
            proxies=proxies,
            verify=False,
        )

        return Helpers.handle_token_response(r, "Certificate")

class Printing:
    """
    # Print interactive menu for client id selection
    def print_client_menu():
        print("\n=== Common Azure Client IDs ===")
        print("Lists common Azure clients, related GUID's and commonly used resources (as supported by this script)")
        print("For a full list, please visit: https://github.com/secureworks/family-of-client-ids-research/blob/main/known-foci-clients.csv\n")

        key_width = max(len(str(k)) for k in COMMON_CLIENTS)
        name_width = max(len(v["name"]) for v in COMMON_CLIENTS.values())
        id_width = max(len(v["client_id"]) for v in COMMON_CLIENTS.values())

        for k, v in COMMON_CLIENTS.items():
            print(
                f"  {k:>{key_width}}. "
                f"{v['name']:<{name_width}}\t"
                f"{v['client_id']:<{id_width}}\t"
                f"{v['common_resources']}"
            )
            #print(f"  {k}. {v['name']} - {v['client_id']} - {v['common_resources']}")
        print()
    """

    # Print interactive menu for client id selection
    def print_client_menu():
        print("\n=== Common Azure Client IDs ===")
        print("Lists common Azure clients, related GUID's and commonly used resources (as supported by this script)")
        print("\nFor a full list, please visit: \nhttps://github.com/secureworks/family-of-client-ids-research/blob/main/known-foci-clients.csv\n")

        key_width = max(len(str(k)) for k in COMMON_CLIENTS)
        name_width = max(len(v["name"]) for v in COMMON_CLIENTS.values())
        id_width = max(len(v["client_id"]) for v in COMMON_CLIENTS.values())

        # Header
        print(
            f"{'#':>{key_width}}  "
            f"{'Client':<{name_width}}  "
            f"{'Client ID':<{id_width}}  "
            "Common resources"
        )
        print("-" * (key_width + name_width + id_width + 20))

        indent = " " * (key_width + 2 + name_width + 2 + id_width + 2)

        for k, v in COMMON_CLIENTS.items():
            resources = [r.strip() for r in v["common_resources"].strip("()").split("/")]

            # First line
            print(
                f"{k:>{key_width}}  "
                f"{v['name']:<{name_width}}  "
                f"{v['client_id']:<{id_width}}  "
                f"{resources[0]}"
            )

            # Remaining resources
            for resource in resources[1:]:
                print(f"{indent}{resource}")
        print()

        # Print resource menu for resource URL selection
    def print_resource_menu():
        print("\n=== Common Azure Resource URL's ===")

        key_width = max(len(str(k)) for k in COMMON_RESOURCES)
        name_width = max(len(v["name"]) for v in COMMON_RESOURCES.values())
        id_width = max(len(v["resource"]) for v in COMMON_RESOURCES.values())

        for k, v in COMMON_RESOURCES.items():
            print(
                f"  {k:>{key_width}}. "
                f"{v['name']:<{name_width}}\t"
                f"{v['resource']:<{id_width}}"
            )            
            #print(f"  {k}. {v['name']} - {v['resource']}")
        print()

    # Print interactive menu for scope selection
    def print_scope_menu():
        print("\n=== Common Azure Scopes ===")
        for k, v in COMMON_SCOPES.items():
            print(f"  {k}. {v['name']} \t\t{v['scope']}")
        print("")

class Selection:
    # Select a client_id based on user interaction
    def interactive_client_selection(default_client="d3590ed6-52b3-4102-aeff-aad2292ab01c"):
        Printing.print_client_menu()
        choice = input(f"Select client (1-99) [default=1]: ").strip() or "1"

        if choice in COMMON_CLIENTS and choice != "99":
            selected = COMMON_CLIENTS[choice]
            client_id = selected["client_id"]
            print(f"{Fore.GREEN}Selected: {selected['name']}{Style.RESET_ALL}")
        else:
            client_id = input(f"Enter Client ID [{default_client}]: ").strip() or default_client

        return client_id

    # Select a client_id based on user interaction
    def interactive_resource_selection(default_resource="https://graph.microsoft.com"):
        Printing.print_resource_menu()
        choice = input(f"Select resource URL (1-99) [default=1]: ").strip() or "1"

        if choice in COMMON_RESOURCES and choice != "99":
            selected = COMMON_RESOURCES[choice]
            resource = selected["resource"]
            print(f"{Fore.GREEN}Selected: {selected['name']}{Style.RESET_ALL}")
        else:
            resource = input(f"Enter Resource [{default_resource}]: ").strip() or default_resource

        return resource

    # Select scope based on user interaction
    def interactive_scope_selection(default_scope=".default"):
        Printing.print_scope_menu()
        choice = input(f"Select scope (1-99) [default=1]: ").strip() or "1"

        if choice in COMMON_SCOPES and choice != "99":
            selected = COMMON_SCOPES[choice]
            scope = selected["scope"]
            print(f"{Fore.GREEN}Selected: {selected['name']}{Style.RESET_ALL}")
        else:
            scope = input(f"Enter Scope [{default_scope}]: ").strip() or default_scope

        return scope

class Helpers:
    # Proxy parameter handling
    def build_proxies(proxy: str):
        if not proxy:
            return {}

        proxy = proxy.strip()

        if "://" not in proxy:
            proxy = "http://" + proxy

        return {
            "http": proxy,
            "https": proxy,
        }

    # Get the token via handlers
    def acquire_token(args, tenant, proxies):
        handlers = {
            "cookie": Gettoken.get_token_with_cookie,
            "ropc": Gettoken.get_token_ropc,
            "tap": Gettoken.get_token_tap,
            "secret": Gettoken.get_token_client_credentials,
            "refresh": Gettoken.get_token_refresh,
            "device": Gettoken.get_token_device_code,
            "certificate": Gettoken.get_token_certificate,
        }
        return handlers[args.method](args, tenant, proxies)    
    
    # Handle the response
    def handle_token_response(response, context=""):
        try:
            print(f"\n{Fore.CYAN}{'='*85}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[{context}] Status Code: {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*85}{Style.RESET_ALL}")

            if response.status_code == 400:
                raise ValueError

            data = response.json()

            # === Summary ===
            print(f"\n{Fore.GREEN}{'='*85}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}GOT TOKEN{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*85}{Style.RESET_ALL}")
            if "access_token" in data:
                print(f"   • {Fore.WHITE}Access Token : {len(data['access_token'])} characters{Style.RESET_ALL}")
            if "refresh_token" in data:
                print(f"   • {Fore.WHITE}Refresh Token: Available{Style.RESET_ALL}")
            if "expires_in" in data:
                print(f"   • {Fore.WHITE}Expires in   : {data['expires_in']} seconds{Style.RESET_ALL}")
            if "token_type" in data:
                print(f"   • {Fore.WHITE}Token Type   : {data['token_type']}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*85}{Style.RESET_ALL}")

            # === Clean Extracted Tokens Section ===
            print(f"\n{Fore.GREEN}=== TOKENS (Ready to Copy) ==={Style.RESET_ALL}")

            if "access_token" in data:
                access_token = data["access_token"]

                # Verbose: decode JWT
                if verbose:
                    try:
                        header_b64, payload_b64, _ = access_token.split(".")
                        header = json.loads(base64.urlsafe_b64decode(header_b64 + "==").decode('utf-8'))
                        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "==").decode('utf-8'))

                        print(f"\n{Fore.MAGENTA}[ACCESS TOKEN - HEADER]{Style.RESET_ALL}")
                        print(json.dumps(header, indent=2))

                        print(f"\n{Fore.MAGENTA}[ACCESS TOKEN - PAYLOAD]{Style.RESET_ALL}")
                        print(json.dumps(payload, indent=2))

                        print(f"\n{Fore.MAGENTA}[ACCESS TOKEN - SCOPES / ROLES]{Style.RESET_ALL}")
                        
                        scopes = payload.get("scp")
                        roles = payload.get("roles")

                        if scopes:
                            for scope in sorted(scopes.split()):
                                print(f" - {scope}")
                        elif roles:
                            for role in sorted(roles):
                                print(f" - {role}")
                        else:
                            print(" - None")

                    except Exception as e:
                        print(f"{Fore.RED}   (Failed to decode JWT: {e}){Style.RESET_ALL}")
                
                print(f"\n{Fore.YELLOW}[ACCESS TOKEN]{Style.RESET_ALL}")
                print(access_token)

                # Clipboard: copy access_token to clipboard
                if clipboard:
                    pyperclip.copy(access_token)
                    print("\n[i] Access token copied to clipboard.")

            if "refresh_token" in data:
                print(f"\n{Fore.YELLOW}[REFRESH TOKEN]{Style.RESET_ALL}")
                print(data["refresh_token"])

            if "id_token" in data:
                print(f"\n{Fore.YELLOW}[ID TOKEN]{Style.RESET_ALL}")
                print(data["id_token"])

            return data

        except ValueError:
            # Non-JSON response
            print(f"\n{Fore.RED}=== RAW RESPONSE ==={Style.RESET_ALL}")
            print(response.text[:1200])
            return None
        except Exception as e:
            print(f"{Fore.RED}[!] Error processing response: {e}{Style.RESET_ALL}")
            return None

    # Load the PFX cert
    def load_pfx_certificate(pfx_path, password=None):
        with open(pfx_path, "rb") as f:
            pfx = f.read()

        pwd = password.encode() if password else None

        pkcs12 = load_pkcs12(pfx, pwd)

        private_key = pkcs12.key
        cert = pkcs12.cert.certificate

        thumbprint = hashlib.sha1(
            cert.public_bytes(serialization.Encoding.DER)
        ).hexdigest().upper()

        print(f"[+] .pfx Thumbprint: {thumbprint}")
        return thumbprint, private_key    

    # Get token based on authorization code
    def exchange_code_for_token(args, tenant, code, proxies):
        payload = {
            "client_id": args.client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": args.redirect_uri,
            # "resource": args.resource,
            "scope": args.resource + "/" + args.scope,
        }
        r = requests.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=payload, headers=default_headers, proxies=proxies, verify=False)
        return Helpers.handle_token_response(r, "Auth Code")

    # Testing resource access
    def test_resource_access(token_data, args, proxies):
        if not token_data or "access_token" not in token_data:
            return
        token = token_data["access_token"]
        headers = {
            "User-Agent": default_ua,
            "Authorization": f"Bearer {token}"
        }
        resource = args.resource.lower()

        print(f"\n{Fore.CYAN}{'='*90}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}[*] Testing Resource: {args.resource}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*90}{Style.RESET_ALL}")

        try:
            if "graph.microsoft.com" in resource:
                r = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, proxies=proxies, verify=False)
                print(f"Graph /me → {r.status_code}")
            elif "management.azure.com" in resource:
                url = f"https://management.azure.com/subscriptions?api-version=2022-12-01"
                if args.subscription_id:
                    url = f"https://management.azure.com/subscriptions/{args.subscription_id}/resources?api-version=2021-04-01"
                r = requests.get(url, headers=headers, proxies=proxies, verify=False)
                print(f"ARM → {r.status_code}")
            elif "vault.azure.net" in resource and args.vault_name:
                url = f"https://{args.vault_name}.vault.azure.net/secrets?api-version=7.4"
                r = requests.get(url, headers=headers, proxies=proxies, verify=False)
                print(f"Key Vault → {r.status_code}")
            elif "storage.azure.com" in resource and args.storage_account:
                url = f"https://{args.storage_account}.blob.core.windows.net/?restype=account&comp=list"
                r = requests.get(url, headers=headers, proxies=proxies, verify=False)
                print(f"Storage → {r.status_code}")
            else:
                print(f"{Fore.YELLOW}No specific test for this resource.{Style.RESET_ALL}")
                return

            if r.status_code == 401:
                print(f"{Fore.RED}401 - Likely Audience Mismatch!{Style.RESET_ALL}")
                print(f"   Try using Azure PowerShell client (option 2) for management.azure.com")
        except Exception as e:
            print(f"{Fore.RED}Test error: {e}{Style.RESET_ALL}")

    # Handle CTRL-C during script
    def handle_ctrl_c(signum, frame):
        print("\n\nCtrl+C detected. Exiting...")
        sys.exit(0)

# Main logic
if __name__ == "__main__":
    signal.signal(signal.SIGINT, Helpers.handle_ctrl_c)
    main()

