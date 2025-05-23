# beauty_app/utils.py

from django.contrib.auth import get_user_model


def generate_username(first_name, last_name):
    """
    Generate a username using the first letter of the first name combined with the last name.
    Handles duplicates by adding an incremental number suffix.
    :param first_name: First name of the user
    :param last_name: Last name of the user
    :return: A unique username

    """
    if not first_name or not last_name:
        return None

    # Create the base username (first letter of first name + last name, lowercase)
    base_username = (first_name[0] + last_name).lower()

    # Remove spaces and special characters
    import re
    base_username = re.sub(r'[^a-z0-9]', '', base_username)

    # Check if username exists
    User = get_user_model()
    username = base_username
    counter = 1

    # If username exists, add a number suffix and increment until unique
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    return username
