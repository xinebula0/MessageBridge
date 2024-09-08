import base64

from cryptography.fernet import Fernet
from sqlalchemy.sql.util import clause_is_present

MASTER_KEY = b"thisisthemasterkeythisisthemaste"
key = base64.urlsafe_b64encode(MASTER_KEY)
print(key)
cipher_suite = Fernet(key)
data = bytes("JzAhchNSLjB6ziJTz3NdfyOHmNXyjd9F".encode("utf-8"))
encrypted_data = cipher_suite.encrypt(data)
print(encrypted_data.decode("utf-8"))
