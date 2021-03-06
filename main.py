from random import randrange
import requests
import vk_api
import datetime
from database import *
from vk_api.longpoll import VkLongPoll, VkEventType

token_id = 'token'
token_group = 'token'
DSN = 'postgresql://postgres:password@localhost:5432/postgres'
vk = vk_api.VkApi(token=token_group)
longpoll = VkLongPoll(vk)

def write_msg(user_id, message):
    vk.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7), })


def write_img(user_id, message, photo_link):
    vk.method("messages.send",
              {"peer_id": user_id, "message": message, "attachment": photo_link, 'random_id': randrange(10 ** 7)})


def vk_username(id_vk):
    url = 'https://api.vk.com/method/users.get'
    params = {'user_ids': id_vk,
              'access_token': token_group,
              'fields': 'city, sex, status, bdate, relation',
              'v': '5.130',
              }
    response = requests.get(url, params=params)

    try:
        bdate = datetime.datetime.strptime(response.json()['response'][0]['bdate'], '%d.%m.%Y')
        age = datetime.datetime.now() - bdate
        age = int(age.total_seconds() // (365.25 * 24 * 60 * 60))
    except:
        age = 0
    try:
        sex = response.json()['response'][0]['sex']
    except:
        sex = 0
    try:
        relation = response.json()['response'][0]['relation']
    except:
        relation = 0
    try:
        city = response.json()['response'][0]['city']['id']
    except:
        city = 0
    user_name = response.json()['response'][0]['first_name']
    return age, sex, relation, city, user_name


def user_search(token_id, age_from, age_to, sex, relation, city):
    url = 'https://api.vk.com/method/users.search'
    params = {'access_token': token_id,
              'age_from': age_from,
              'age_to': age_to,
              'city': city,
              'sex': sex,
              'relation': relation,
              'fields': 'is_closed',
              'has_photo': 1,
              'online': 1,
              'sort': 0,
              'v': '5.131',
              }
    response = requests.get(url, params=params)
    return response


def vk_link_loader(token_id, user_id):
    photo_dict = {}
    url = 'https://api.vk.com/method/photos.get'
    params = {'user_id': user_id,
              'access_token': token_id,
              'v': '5.130',
              'extended': 1,
              'album_id': 'profile'  # wall, saved, profile
              }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        # ?????????????????? ?????????????? ?????????????????? json ?????????? ?????? ???????????????????? ????????????????????
        photo_counter = len(response.json()['response']['items'])
        for i in range(photo_counter):
            photo_id = response.json()['response']['items'][i]['id']
            popularity = (response.json()['response']['items'][i]['likes']['count'] + \
                          response.json()['response']['items'][i]['likes']['user_likes'] +
                          response.json()['response']['items'][i]['comments']['count'])
            photo_owner_id = response.json()['response']['items'][i]['owner_id']
            photo_url = f'photo{photo_owner_id}_{photo_id}'
            photo_dict[photo_url] = popularity
    else:
        print('????????????:', response)
    sorted_tuple = sorted(photo_dict.items(), key=lambda x: x[1], reverse=True)
    photo_url = []
    photo_counter = len(sorted_tuple)
    if photo_counter > 3:
        photo_counter = 3
    for i in range(photo_counter):
        photo_url.append(sorted_tuple[i][0])
    photo_url = ','.join(photo_url)
    return photo_url


# def black_list_SQL_recording(id, liked):
#     DSN = 'postgresql://postgres:gsxr1000@localhost:5432/postgres'
#     engine = sq.create_engine(DSN)
#     mydb = engine.raw_connection()
#     mycursor = mydb.cursor()
#     mycursor.execute(f'INSERT INTO parts (vk_id, liked) VALUES({id}, {liked})')
#     mydb.commit()
#
#
# def black_list_SQL_reading():
#     DSN = 'postgresql://postgres:gsxr1000@localhost:5432/postgres'
#     engine = sq.create_engine(DSN)
#     mydb = engine.raw_connection()
#     mycursor = mydb.cursor()
#     mycursor.execute(f'CREATE TABLE IF NOT EXISTS parts (vk_id integer NOT NULL default 0, liked boolean NOT NULL default False)')
#     mydb.commit()
#     mycursor.execute('SELECT vk_id FROM parts')
#     list = mycursor.fetchall()
#     black_list = []
#     for i in list:
#         black_list.append(i[0])
#     return black_list

def logic(sex):
    sex_r = 0
    if sex == 2:
        sex_r = 1
    if sex == 1:
        sex_r = 2
    age_from = 18
    age_to = age
    return sex_r, age_from, age_to


if __name__ == '__main__':
    exit = False
    for event in longpoll.listen():
        if exit:
            break
        else:
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:
                    age, sex, relation, city, user_name = vk_username(event.user_id)  # ?????????????????? ?????????? ????????????????????????
                    write_msg(event.user_id,
                              f"???????????? {user_name}, {age} ??????, ?????????????????? ?????? ???????????? ???????????? ?????????????????? (???????????? ??????"
                              f" ????????????????????????????????)")
                    sex_r, age_from, age_to = logic(sex)
                    response = user_search(token_id, age_from, age_to, sex_r, [1, 6], city)
                    for people in response.json()['response']['items']:
                        if exit:
                            break
                        else:
                            if not people['is_closed'] and people['id'] not in DB(DSN).black_list_SQL_reading():
                                url_list = vk_link_loader(token_id, people['id'])
                                write_img(event.user_id, '?????? ' + str(people['first_name'] + ' ' + people['last_name'] + \
                                                                      '\n???????? ?????????????????????? ???????????? +, ???????? ?????? - \n ?????? ???????????? ?????????? q'),
                                          url_list)

                                for event in longpoll.listen():
                                    if event.type == VkEventType.MESSAGE_NEW:
                                        if event.to_me:
                                            request = event.text
                                            if request.lower() == "+":
                                                write_msg(event.user_id, f"???????????? ???? vk.com/id{people['id']}")
                                                DB(DSN).black_list_SQL_recording(people['id'], True)
                                                break
                                            elif request.lower() == "q":
                                                exit = True
                                                break

                                            else:
                                                DB(DSN).black_list_SQL_recording(people['id'], False)
                                                break
