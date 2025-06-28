import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import Fore, Style, init as colorama_init
import json, base64, os, pytz

colorama_init(autoreset=True)
wib = pytz.timezone('Asia/Jakarta')

class Sparkchain:
    def __init__(self):
        self.headers = {
            "Accept": "application/json",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://sparkchain.ai",
            "Priority": "u=1, i",
            "Referer": "https://sparkchain.ai/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": FakeUserAgent().random
        }
        self.proxies = []

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    @staticmethod
    def mask_account(account):
        if "@" in account:
            local, domain = account.split('@', 1)
            mask_account = local[:3] + '*' * 3 + local[-3:]
            return f"{mask_account}@{domain}"
        return account

    @staticmethod
    def decode_token(token):
        try:
            header, payload, signature = token.split(".")
            decoded_payload = base64.urlsafe_b64decode(payload + "==").decode("utf-8")
            parsed_payload = json.loads(decoded_payload)
            email = parsed_payload.get("email", "unknown@sparkchain.ai")
            return email
        except Exception:
            return "unknown@sparkchain.ai"

    def detect_proxy_type(self, proxy):
        proxy = proxy.strip()
        if proxy.startswith("socks5://"):
            return proxy
        elif proxy.startswith("socks4://"):
            return proxy
        elif proxy.startswith("http://"):
            return proxy
        elif proxy.startswith("https://"):
            return proxy
        else:
            return f"http://{proxy}"

    async def load_proxies(self, proxy_source):
        filename = "proxy.txt"
        if proxy_source == 1:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt") as resp:
                    resp.raise_for_status()
                    content = await resp.text()
                    with open(filename, "w") as f:
                        f.write(content)
                    self.proxies = [self.detect_proxy_type(p) for p in content.splitlines() if p.strip()]
        else:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED}proxy.txt not found!{Style.RESET_ALL}")
                self.proxies = []
                return
            with open(filename, "r") as f:
                self.proxies = [self.detect_proxy_type(p) for p in f.read().splitlines() if p.strip()]
        if not self.proxies:
            self.log(f"{Fore.RED}No proxies found!{Style.RESET_ALL}")
        else:
            self.log(f"{Fore.GREEN}Loaded {len(self.proxies)} proxies.{Style.RESET_ALL}")

    async def poll_profile(self, email, token, node_index, proxy):
        url = "https://api.sparkchain.ai/profile"
        headers = {**self.headers, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        connector = None
        if proxy:
            try:
                connector = ProxyConnector.from_url(proxy)
            except Exception as e:
                self.log(f"{Fore.RED}Invalid proxy {proxy}: {e}{Style.RESET_ALL}")

        while True:
            try:
                async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            points = data.get("total_points", "N/A")
                            self.log(f"{Fore.GREEN}[{self.mask_account(email)}] Node:{node_index+1} via {proxy or 'no proxy'} | Points: {points}{Style.RESET_ALL}")
                        else:
                            self.log(f"{Fore.YELLOW}[{self.mask_account(email)}] Node:{node_index+1} via {proxy or 'no proxy'} | HTTP {resp.status}{Style.RESET_ALL}")
            except Exception as e:
                self.log(f"{Fore.RED}[{self.mask_account(email)}] Node:{node_index+1} via {proxy or 'no proxy'} | Poll error: {e}{Style.RESET_ALL}")
            await asyncio.sleep(30)  # Poll every 30s (medium-fast)

    async def main(self):
        # Load tokens
        try:
            with open('tokens.txt', 'r') as f:
                tokens = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.log(f"{Fore.RED}File 'tokens.txt' Not Found.")
            return
        # Ask proxy and nodes
        print("1. Run With Free Public Proxy (Monosans List)")
        print("2. Run With Your Own Proxy List (proxy.txt)")
        print("3. Run Without Proxy")
        while True:
            try:
                proxy_choice = int(input("Choose [1/2/3] -> ").strip())
                if proxy_choice in [1,2,3]: break
            except:
                continue
        nodes_count = 1
        if proxy_choice in [1,2]:
            while True:
                try:
                    nodes_count = int(input("How Many Nodes Do You Want to Run For Each Account? -> ").strip())
                    if nodes_count > 0: break
                except:
                    continue
        use_proxy = proxy_choice in [1,2]
        # Load proxies if needed
        if use_proxy:
            await self.load_proxies(proxy_choice)
            if not self.proxies:
                self.log(f"{Fore.RED}No proxies loaded. Exiting.")
                return
        self.log(f"{Fore.GREEN}Account's Total: {len(tokens)}")
        # Start nodes (pollers)
        tasks = []
        proxy_count = len(self.proxies) if self.proxies else 1
        for idx, token in enumerate(tokens):
            email = self.decode_token(token)
            for node_index in range(nodes_count):
                if use_proxy:
                    proxy = self.proxies[(idx * nodes_count + node_index) % proxy_count]
                else:
                    proxy = None
                tasks.append(self.poll_profile(email, token, node_index, proxy))
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        bot = Sparkchain()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(f"{Fore.CYAN}[ EXIT ] Sparkchain AI - BOT{Style.RESET_ALL}")
