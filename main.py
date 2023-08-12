import os
import requests
from dotenv import load_dotenv
from random import randint
from urllib.parse import urlparse


class VkApiError(requests.HTTPError):
    """Отлавливает ошибки VK api"""
    pass


def check_vk_api_error(response_json):
    if response_json.get('error'):
        response_error = response_json.get('error')
        error_code = response_error.get('error_code')
        error_msg = response_error.get('error_msg')
        raise VkApiError(f'Код ошибки VK api {error_code} - {error_msg}')


def download_random_comic():
    first_comic_number = 1
    response = requests.get('https://xkcd.com/info.0.json')
    response.raise_for_status()
    last_comic_number = int(response.json().get('num'))
    random_comic_number = randint(first_comic_number, last_comic_number)

    comic_url = f'https://xkcd.com/{random_comic_number}/info.0.json'
    response = requests.get(comic_url)
    response.raise_for_status()
    response_json = response.json()
    comic_image_url = response_json.get('img')
    comic_alt = response_json.get('alt')

    response = requests.get(comic_image_url)
    response.raise_for_status()
    comic_image = response

    path = urlparse(comic_image_url).path
    extension = os.path.splitext(path)[1]
    name = os.path.splitext(path)[0].split('/')[-1]
    image_name = f'comic_{random_comic_number}_{name}.{extension}'

    file_path = os.path.join(image_name)
    with open(file_path, 'wb') as file:
        file.write(comic_image.content)
    return image_name, comic_alt


def get_photo_upload_url(access_token, api_version, group_id):
    payload = {
        'access_token': access_token,
        'v': api_version,
        'group_id': group_id,
    }
    response = requests.get('https://api.vk.com/method/photos.getWallUploadServer', params=payload)
    response.raise_for_status()
    response_json = response.json()
    check_vk_api_error(response_json)
    upload_url = response_json.get('response').get('upload_url')
    return upload_url


def upload_comic_server(image_name, upload_url):
    with open(image_name, 'rb') as file:
        files = {
            'photo': file,
        }
        response = requests.post(upload_url, files=files)
    response.raise_for_status()
    response_json = response.json()
    check_vk_api_error(response_json)
    return response_json.get('server'), response_json.get('photo'), response_json.get('hash')


def save_comic_album(access_token, api_version, group_id, server, photo, vk_hash):
    payload = {
        'access_token': access_token,
        'v': api_version,
        'group_id': group_id,
        'photo': photo,
        'server': server,
        'hash': vk_hash,
    }
    response = requests.post('https://api.vk.com/method/photos.saveWallPhoto', params=payload)
    response.raise_for_status()
    response_json = response.json()
    check_vk_api_error(response_json)
    response_json = response_json['response'][0]
    return response_json.get('owner_id'), response_json.get('id')


def post_on_wall(access_token, api_version, group_id, comments, owner_id, media_id):
    payload = {
        'access_token': access_token,
        'v': api_version,
        'owner_id': f'-{group_id}',
        'from_group': '1',
        'message': comments,
        'attachments': f'photo{owner_id}_{media_id}',
    }
    response = requests.post('https://api.vk.com/method/wall.post', params=payload)
    response.raise_for_status()
    check_vk_api_error(response.json())


if __name__ == "__main__":
    load_dotenv()
    vk_access_token = os.environ['VK_ACCESS_TOKEN']
    vk_group_id = os.environ['VK_GROUP_ID']
    vk_api_version = os.environ['VK_API_VERSION']

    try:
        image_name, comic_alt = download_random_comic()
        photo_upload_url = get_photo_upload_url(vk_access_token, vk_api_version, vk_group_id)
        server, photo, vk_hash = upload_comic_server(image_name, photo_upload_url)
        owner_id, media_id = save_comic_album(vk_access_token, vk_api_version, vk_group_id, server, photo, vk_hash)
        post_on_wall(vk_access_token, vk_api_version, vk_group_id, comic_alt, owner_id, media_id)
        print("Комикс опубликован!")
    except VkApiError as error:
        print(error)
    finally:
        os.remove(image_name)
