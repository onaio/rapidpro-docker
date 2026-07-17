"""Make ona-oidc logout a real OIDC RP-initiated logout.

ona-oidc v1.1.1 redirects to the bare end-session endpoint. Without
id_token_hint, CIAM (WSO2) asks the browser for logout consent and the SSO
session survives, so returning to RapidPro silently re-authenticates.
Keep the raw ID token in the Django session at login and send it as
id_token_hint together with post_logout_redirect_uri at logout.
"""
from pathlib import Path


def patch(path: Path, old: str, new: str) -> None:
    source = path.read_text()
    if old not in source:
        raise SystemExit(f"Patch anchor not found in {path}:\n{old}")
    path.write_text(source.replace(old, new, 1))


client_path = Path("/venv/src/ona-oidc/oidc/client.py")

patch(
    client_path,
    """import json
import secrets
from typing import Optional
""",
    """import json
import secrets
from typing import Optional
from urllib.parse import urlencode
""",
)

patch(
    client_path,
    """    def logout(self):
        return HttpResponseRedirect(self.end_session_endpoint)
""",
    """    def logout(self, id_token_hint=None):
        url = self.end_session_endpoint
        if id_token_hint:
            params = {"id_token_hint": id_token_hint}
            post_logout_redirect_uri = getattr(
                settings, "OPENID_CONNECT_POST_LOGOUT_REDIRECT_URI", None
            )
            if post_logout_redirect_uri:
                params["post_logout_redirect_uri"] = post_logout_redirect_uri
            url += ("&" if "?" in url else "?") + urlencode(params)
        return HttpResponseRedirect(url)
""",
)


viewsets_path = Path("/venv/src/ona-oidc/oidc/viewsets.py")

# The raw ID token must be stored after login() has rotated the session key.
patch(
    viewsets_path,
    """                else:
                    if user:
                        return self.generate_successful_response(
                            request, user, redirect_after=redirect_after
                        )
""",
    """                else:
                    if user:
                        response = self.generate_successful_response(
                            request, user, redirect_after=redirect_after
                        )
                        request.session["oidc_id_token"] = id_token
                        return response
""",
)

# The token must be read before logout_backend() flushes the session.
patch(
    viewsets_path,
    """            response = client.logout()
""",
    """            id_token_hint = request.session.get("oidc_id_token")
            response = client.logout(id_token_hint=id_token_hint)
""",
)


# The workspace menu submits Sign Out as a posterized (CSRF-protected) POST;
# frame.js never navigates non-posterized hrefs in the workspace popup.
urls_path = Path("/venv/src/ona-oidc/oidc/urls.py")

patch(
    urls_path,
    """        viewset_class.as_view({"get": "logout"}),
""",
    """        viewset_class.as_view({"get": "logout", "post": "logout"}),
""",
)
