# # CreateCred.py
# # Creates a credential file.
# import ctypes
# import json
# import os
# import subprocess
# import sys
# import time
#
# from cryptography.fernet import Fernet
#
#
# class Credentials:
#
#     def __init__(self, **kwargs):
#         self.__sonarr_url = ""
#         self.__sonarr_api_key = ''
#         self.__radarr_url = ""
#         self.__radarr_api_key = ''
#         self.__plex_url = ""
#         self.__plex_api_key = ''
#         self.__key = Fernet.generate_key()
#         self.__password = ""
#         self.__key_file = 'key.key'
#         self.__time_of_exp = -1
#
#         if kwargs is not None:
#             json_creds = json.loads(kwargs)
#
#             with Fernet(self.__key) as f:
#                 f.encrypt(json_creds.encode()).decode()
#
#     # ----------------------------------------
#     # Getter setter for attributes
#     # ----------------------------------------
#
#     @property
#     def sonarr_url(self):
#         return self.__sonarr_url
#
#     @sonarr_url.setter
#     def sonarr_url(self, sonarr_url):
#         self.__key = Fernet.generate_key()
#         f = Fernet(self.__key)
#         self.__password = f.encrypt(sonarr_url.encode()).decode()
#         del f
#     @property
#     def sonarr_api_key(self, sonarr_api_key):
#         while sonarr_api_key == '':
#             sonarr_api_key = input('Enter sonarr ')
#     @property
#     def password(self):
#         return self.__password
#
#     @password.setter
#     def password(self, password):
#         self.__key = Fernet.generate_key()
#         f = Fernet(self.__key)
#         self.__password = f.encrypt(password.encode()).decode()
#         del f
#
#     @property
#     def expiry_time(self):
#         return self.__time_of_exp
#
#     @expiry_time.setter
#     def expiry_time(self, exp_time):
#         if (exp_time >= 2):
#             self.__time_of_exp = exp_time
#
#     def create_cred(self):
#         """
#         This function is responsible for encrypting
#         the password and create key file for
#         storing the key and create a credential
#         file with user name and password
#         """
#
#         cred_filename = 'CredFile.ini'
#
#         with open(cred_filename, 'w') as file_in:
#             file_in.write("# Credential file:\nUsername ={}\nPassword ={}\nExpiry ={}\n"
#                           .format(self.__sonarr_url, self.__password, self.__time_of_exp))
#             file_in.write("++" * 20)
#
#         # If there exists an older key file,
#         # This will remove it.
#         if (os.path.exists(self.__key_file)):
#             os.remove(self.__key_file)
#
#         # Open the Key.key file and place the key in it.
#         # The key file is hidden.
#         try:
#
#             os_type = sys.platform
#             if (os_type == 'linux'):
#                 self.__key_file = '.' + self.__key_file
#
#             with open(self.__key_file, 'w') as key_in:
#                 key_in.write(self.__key.decode())
#                 # Hidding the key file.
#                 # The below code snippet finds out which current os
#                 # the scrip is running on and does the taks base on it.
#                 if (os_type == 'win32'):
#                     ctypes.windll.kernel32.SetFileAttributesW(self.__key_file, 2)
#                 else:
#                     pass
#
#         except PermissionError:
#             os.remove(self.__key_file)
#             print("A Permission error occurred.\n Please re run the script")
#             sys.exit()
#
#         self.__sonarr_url = ""
#         self.__password = ""
#         self.__key = ""
#         self.__key_file
#
#
# def main():
#     # Creating an object for Credentials class
#     creds = Credentials()
#
#     # Accepting credentials
#     creds.sonarr_url = input("Enter UserName:")
#     creds.password = input("Enter Password:")
#     print("Enter the epiry time for key file in minutes, [default:Will never expire]")
#     creds.expiry_time = int(input("Enter time:") or '-1')
#
#     # calling the Credit
#     creds.create_cred()
#     print("**" * 20)
#     print("Cred file created successfully at {}"
#           .format(time.ctime()))
#
#     if not (creds.expiry_time == -1):
#         # For linux
#         opener = "open" if sys.platform == "darwin" else "xdg-open"
#         subprocess.call([opener, 'expire.py'])
#
#     # For windows use
#     # os.startfile('expire.py')
#
#     print("**" * 20)
#
#
# if __name__ == "__main__":
#     main()
