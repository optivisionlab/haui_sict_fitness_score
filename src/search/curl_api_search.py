import requests


def curl_post(url, payload=None, files=None, headers=None, method="POST"):
    """
    Gửi request (POST/PUT) đến một URL với payload, file upload và headers.

    Parameters:
        url (str): Địa chỉ API.
        payload (dict): Dữ liệu form (mặc định None).
        files (list): Danh sách file theo format của requests (mặc định None).
        headers (dict): Header tùy chỉnh (mặc định None).
        method (str): Phương thức HTTP ('POST' hoặc 'PUT').

    Returns:
        Response object: response từ server.
    """
    if headers is None:
        headers = {'accept': 'application/json'}

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            data=payload,
            files=files
        )
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Error: {e}")
        return None