from pathlib import Path


path = Path("/venv/src/ona-oidc/oidc/viewsets.py")
source = path.read_text()

old = """            if self.use_auth_backend:
                logout_backend(request)
            if self.use_sso:
                response.delete_cookie(SSO_COOKIE_NAME, domain=self.cookie_domain)
"""

new = """            if self.use_auth_backend:
                logout_backend(request)

                session_cookie = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
                session_path = getattr(settings, "SESSION_COOKIE_PATH", "/")
                configured_domain = getattr(settings, "SESSION_COOKIE_DOMAIN", None)
                response.delete_cookie(session_cookie, path=session_path, domain=configured_domain)

                response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
                response["Pragma"] = "no-cache"
            if self.use_sso:
                response.delete_cookie(SSO_COOKIE_NAME, domain=self.cookie_domain)
"""

if old not in source:
    raise SystemExit("OIDC logout block was not found")

path.write_text(source.replace(old, new, 1))
