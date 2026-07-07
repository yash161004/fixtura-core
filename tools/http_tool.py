import ipaddress
import socket
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
import urllib3
from pydantic import BaseModel, Field
from tools.base_tool import BaseTool
from typing import Dict, Any, Optional

class HttpArguments(BaseModel):
    method: str = Field(..., description="GET, POST, PUT, DELETE, etc.")
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    data: str = ""

class IPAdapter(HTTPAdapter):
    def __init__(self, ip: str, domain: str, **kwargs: Any) -> None:
        self.ip = ip
        self.domain = domain
        super().__init__(**kwargs)

    def init_poolmanager(self, connections: int, maxsize: int, block: bool = False, **pool_kwargs: Any) -> None:
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)
        
        orig_connection_from_host = self.poolmanager.connection_from_host
        
        def patched_connection_from_host(host: str, port: Optional[int] = None, scheme: str = 'http', pool_kwargs: Optional[Dict[str, Any]] = None) -> Any:
            if host == self.domain:
                host = self.ip
                if pool_kwargs is None:
                    pool_kwargs = {}
                if scheme == 'https':
                    pool_kwargs['server_hostname'] = self.domain
                    pool_kwargs['assert_hostname'] = self.domain
            return orig_connection_from_host(host, port=port, scheme=scheme, pool_kwargs=pool_kwargs)
            
        self.poolmanager.connection_from_host = patched_connection_from_host

class HttpTool(BaseTool):
    name = "http_tool"
    is_idempotent = False
    is_reversible = False
    schema_cls = HttpArguments
    
    def _is_private_ip(self, ip_str: str) -> bool:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local
        
    def _run(self, args: HttpArguments) -> Dict[str, Any]:
        parsed = urlparse(args.url)
        domain = parsed.hostname
        if not domain:
            raise ValueError("Invalid URL: missing domain")
            
        try:
            # Resolve domain to an IP before connecting
            ip_address = socket.gethostbyname(domain)
        except socket.gaierror:
            raise ValueError(f"Failed to resolve domain: {domain}")
            
        # Reject private/loopback/link-local ranges (SSRF protection)
        if self._is_private_ip(ip_address):
            raise ValueError(f"Refusing to connect to private/loopback IP: {ip_address}")
            
        # Eliminate TOCTOU (DNS Rebinding) by pinning the connection to the validated IP.
        # We use a custom HTTPAdapter so there's no shared global state mutated (thread-safe).
        session = requests.Session()
        adapter = IPAdapter(ip_address, domain)
        session.mount(f"http://{domain}", adapter)
        session.mount(f"https://{domain}", adapter)
        
        try:
            # Disable automatic redirect-following (allow_redirects=False)
            resp = session.request(
                method=args.method,
                url=args.url,
                headers=args.headers,
                data=args.data,
                allow_redirects=False,
                timeout=10
            )
            return {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "text": resp.text
            }
        except Exception as e:
            raise ValueError(f"Request failed: {str(e)}")
        finally:
            session.close()
