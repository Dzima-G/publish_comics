import os
import requests
from dotenv import load_dotenv
from random import randint
from urllib.parse import urlparse
import sys


def get_random_comic_number():
    first_comic_number = 1
    response = requests.get('https://xkcd.com/info.0.json')
    response.raise_for_status()
    last_comic_number = int(response.json().get('num'))
    random_comic_number = randint(first_comic_number, last_comic_number)
    return random_comic_number


def get_comic(comic_number):
    comic_url = f'https://xkcd.com/{comic_number}/info.0.json'
    response = requests.get(comic_url)
    response.raise_for_status()
    comic = {
        'image_url': response.json().get('img'),
        'alt': response.json().get('alt'),
    }
    return comic


def get_comic_image(api_url):
    response = requests.get(api_url)
    response.raise_for_status()
    return response


def get_image_name(image_url, comic_number):
    path = urlparse(image_url).path
    extension = os.path.splitext(path)[1]
    name = os.path.splitext(path)[0].split('/')[-1]
    image_name = f'comic_{comic_number}_{name}.{extension}'
    return image_name


def save_comic_image(file_image, image_name):
    file_path = os.path.join(image_name)
    with open(file_path, 'wb') as file:
        file.write(file_image.content)


def get_photo_upload_url(access_token, api_version, group_id):
    payload = {
        'access_token': access_token,
        'v': api_version,
        'group_id': group_id,
    }
    response = requests.get('https://api.vk.com/method/photos.getWallUploadServer', params=payload)
    response.raise_for_status()
    upload_url = response.json().get('response').get('upload_url')
    return upload_url


def upload_comic_server(image_name, upload_url):
    with open(image_name, 'rb') as file:
        files = {
            'photo': file,
        }
        response = requests.post(upload_url, files=files)
        response.raise_for_status()
    return response.json().get('server'), response.json().get('photo'), response.json().get('hash')


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
    response = response.json()['response'][0]

    return response.get('owner_id'), response.get('id')


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


if __name__ == "__main__":
    load_dotenv()
    vk_client_id = os.environ['VK_CLIENT_ID']
    vk_access_token = os.environ['VK_ACCESS_TOKEN']
    vk_group_id = os.environ['VK_GROUP_ID']
    vk_api_version = os.environ['VK_API_VERSION']

    try:
        comic_number = get_random_comic_number()
    except requests.exceptions.HTTPError as error:
        print(error, file=sys.stderr)

    comic = get_comic(comic_number)
    comic_alt = comic.get('alt')
    comic_image = get_comic_image(comic.get('image_url'))
    image_name = get_image_name(comic.get('image_url'), comic_number)
    save_comic_image(comic_image, image_name)

    try:
        photo_upload_url = get_photo_upload_url(vk_access_token, vk_api_version, vk_group_id)
        server, photo, vk_hash = upload_comic_server(image_name, photo_upload_url)
        owner_id, media_id = save_comic_album(vk_access_token, vk_api_version, vk_group_id, server, photo, vk_hash)
        post_on_wall(vk_access_token, vk_api_version, vk_group_id, comic_alt, owner_id, media_id)
    except requests.exceptions.HTTPError as error:
        print(error, file=sys.stderr)

    os.remove(image_name)
    print("Комикс опубликован!")
