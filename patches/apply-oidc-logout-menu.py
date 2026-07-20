from pathlib import Path


path = Path("/rapidpro/temba/orgs/views.py")
source = path.read_text()

old = """                                posterize=True,
                                href=f"{reverse('users.user_logout')}?next={reverse('users.user_login')}",
"""

new = """                                posterize=True,
                                href=(
                                    reverse(
                                        "oidc:openid_connect_logout",
                                        kwargs={"auth_server": settings.OPENID_CONNECT_DEFAULT_AUTH_SERVER},
                                    )
                                    if getattr(settings, "ENABLE_OIDC", "off") == "on"
                                    else f"{reverse('users.user_logout')}?next={reverse('users.user_login')}"
                                ),
"""

if old not in source:
    raise SystemExit("RapidPro logout menu target was not found")

path.write_text(source.replace(old, new, 1))
