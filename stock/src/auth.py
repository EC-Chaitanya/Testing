# import logging
# from tradingapi_a.mconnect import MConnect

# # Setup internal logging for the API
# logging.basicConfig(level=logging.INFO)

# def get_session(api_key, user_id, password, dob):
#     """Logs in and returns the active mStock connection object."""
#     m_obj = MConnect(api_key=api_key)
    
#     # Step A: Initial Login
#     login_res = m_obj.login(user_id, password)
    
#     if login_res.get('status') == 'success':
#         # Step B: Generate Daily Session Token
#         # Note: Check if your version requires an OTP or manual interaction
#         print(f"Login successful for {user_id}")
#         return m_obj
#     else:
#         print(f"Error: {login_res.get('message')}")
#         return None
#  2nd bar paste 
# from tradingapi_a.mconnect import MConnect

# def get_session(api_key, user_id, password, dob):
#     """
#     Logs in to mStock and returns the session object.
#     Corrected for TypeA SDK parameter names and Response objects.
#     """
#     try:
#         # 1. Initialize the connection
#         m_obj = MConnect(api_key=api_key)
        
#         # 2. Login - The SDK uses 'user_id' and 'password' as positional arguments
#         # Note: We do NOT use userid=user_id here to avoid the TypeError
#         response_obj = m_obj.login(user_id, password)
        
#         # 3. Convert the 'Response' object to a JSON dictionary
#         login_res = response_obj.json()
        
#         if login_res.get('status') == 'success':
#             print(f"✅ Login successful for {user_id}")
            
#             # 4. Handle Session Generation (Mirae requires this for the token)
#             # You might need a request_token and checksum from login_res
#             # For now, we return the object if login is success
#             return m_obj
#         else:
#             print(f"❌ Login Failed: {login_res.get('message')}")
#             return None
            
#     except Exception as e:
#         print(f"⚠️ An error occurred during authentication: {e}")
#         return None


# 3rd one
# import logging
# from tradingapi_a.mconnect import MConnect

# def get_session(api_key, user_id, password, dob):
#     """
#     Logs in to mStock and handles the 2FA OTP process.
#     """
#     try:
#         m_obj = MConnect(api_key=api_key)
        
#         # Step 1: Login with ID and Password
#         # Note: Position arguments used based on your mconnect.py structure
#         response_obj = m_obj.login(user_id, password)
#         login_res = response_obj.json()
        
#         if login_res.get('status') == 'success':
#             # Extract the request token needed for the next step
#             request_token = login_res.get('data', {}).get('request_token')
            
#             print(f"\n✅ Password Accepted for {user_id}")
#             # Step 2: Manually enter the OTP you just received
#             otp_code = input("👉 Enter the 6-digit OTP from your phone: ")
            
#             # Step 3: Generate the actual session using the OTP
#             # In TypeA, 'dob' is often used as the checksum
#             gen_session_resp = m_obj.generate_session(
#                 _api_key=api_key, 
#                 _request_token=request_token, 
#                 _checksum=otp_code  # Some versions use OTP here, others use DOB
#             )
            
#             # If the above fails, your version might use verify_totp
#             if gen_session_resp.json().get('status') != 'success':
#                 print("Trying TOTP verification instead...")
#                 gen_session_resp = m_obj.verify_totp(_api_key=api_key, _tOtp=otp_code)

#             session_data = gen_session_resp.json()
            
#             if session_data.get('status') == 'success':
#                 print("🚀 Session generated! Market data is now active.")
#                 return m_obj
#             else:
#                 print(f"❌ Session Error: {session_data.get('message')}")
#                 return None
#         else:
#             print(f"❌ Login Error: {login_res.get('message')}")
#             return None
            
#     except Exception as e:
#         print(f"⚠️ Auth Failure: {e}")
#         return None
# 4th

# from tradingapi_a.mconnect import MConnect

# def get_session(api_key, user_id, password, dob):
#     try:
#         m_obj = MConnect(api_key=api_key)
        
#         # Step 1: Login
#         response_obj = m_obj.login(user_id, password)
#         login_res = response_obj.json()
        
#         if login_res.get('status') == 'success':
#             print(f"✅ Password Accepted for {user_id}")
#             otp_code = input("👉 Enter the 6-digit OTP from your phone: ")
            
#             # Step 2: Verify the OTP first (This is often required before session generation)
#             # The SDK method is verify_totp(_api_key, _tOtp)
#             verify_res = m_obj.verify_totp(_api_key=api_key, _tOtp=otp_code)
            
#             if verify_res.json().get('status') == 'success':
#                 # Step 3: Now generate the final session using DOB as checksum
#                 request_token = login_res.get('data', {}).get('request_token')
                
#                 final_res = m_obj.generate_session(
#                     _api_key=api_key, 
#                     _request_token=request_token, 
#                     _checksum=dob # Use your DOB (YYYYMMDD) here!
#                 )
                
#                 if final_res.json().get('status') == 'success':
#                     print("🚀 Session generated! Market data is active.")
#                     return m_obj
#                 else:
#                     print(f"❌ Session Error: {final_res.json().get('message')}")
#             else:
#                 print(f"❌ OTP Verification Failed: {verify_res.json().get('message')}")
#         return None
#     except Exception as e:
#         print(f"⚠️ Auth Failure: {e}")
#         return None

from tradingapi_a.mconnect import MConnect

def get_session(api_key, user_id, password, dob):
    """
    Logs in to mStock and handles the SMS OTP session generation.
    """
    try:
        m_obj = MConnect(api_key=api_key)
        
        # Step 1: Login to trigger the OTP
        # Based on your mconnect.py, parameters are (user_id, password)
        response_obj = m_obj.login(user_id, password)
        login_res = response_obj.json()
        
        if login_res.get('status') == 'success':
            print(f"✅ Password Accepted for {user_id}")
            
            # Step 2: The OTP you receive IS the 'request_token' for Step 3
            otp_from_phone = input("👉 Enter the 6-digit OTP from your phone: ")
            
            # Step 3: Generate the actual session
            # _request_token: Use the OTP here
            # _checksum: Use "L" as required for OTP-based logins
            final_res_obj = m_obj.generate_session(
                _api_key=api_key, 
                _request_token=otp_from_phone, 
                _checksum="L" 
            )
            
            final_res = final_res_obj.json()
            
            if final_res.get('status') == 'success':
                print("🚀 Session generated! Market data is now active.")
                return m_obj
            else:
                # If "L" fails, try using your DOB (YYYYMMDD) as the checksum
                print("Trying backup validation with DOB...")
                final_res_obj = m_obj.generate_session(
                    _api_key=api_key, 
                    _request_token=otp_from_phone, 
                    _checksum=dob
                )
                if final_res_obj.json().get('status') == 'success':
                    print("🚀 Session generated using DOB!")
                    return m_obj
                
                print(f"❌ Session Error: {final_res_obj.json().get('message')}")
        else:
            print(f"❌ Login Error: {login_res.get('message')}")
            
        return None
    except Exception as e:
        print(f"⚠️ Auth Failure: {e}")
        return None