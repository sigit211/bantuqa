import keyring

class AuthManager:
    SERVICE_NAME = 'BantuQa'

    @staticmethod
    def save_credentials(base_url: str, email: str, api_key: str):
        keyring.set_password(AuthManager.SERVICE_NAME, 'base_url', base_url)
        keyring.set_password(AuthManager.SERVICE_NAME, 'email', email)
        keyring.set_password(AuthManager.SERVICE_NAME, 'api_key', api_key)

    @staticmethod
    def load_credentials():
        base_url = keyring.get_password(AuthManager.SERVICE_NAME, 'base_url')
        email = keyring.get_password(AuthManager.SERVICE_NAME, 'email')
        api_key = keyring.get_password(AuthManager.SERVICE_NAME, 'api_key')
        return base_url, email, api_key

    @staticmethod
    def clear_credentials():
        try:
            keyring.delete_password(AuthManager.SERVICE_NAME, 'base_url')
            keyring.delete_password(AuthManager.SERVICE_NAME, 'email')
            keyring.delete_password(AuthManager.SERVICE_NAME, 'api_key')
        except Exception:
            pass
