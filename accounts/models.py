"""
No custom models are needed for the Login, Register, and Home screens.

Django's built-in User model (django.contrib.auth.models.User) is used for
authentication at this stage. A custom model can be introduced later if the
full SugarLert feature set requires one — for example, to store a user's
daily sugar limit or scan history.
"""

from django.db import models  # noqa: F401
