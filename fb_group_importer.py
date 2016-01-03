__author__ = 'Sid'

##########################
#
# Import fb_grou_parser.py
# output file to MySql DB
#
##########################

from mysql import connector
from datetime import datetime
import os
from glob import glob


def nullify(value):
    """
    :param value: original value
    :return: None if value is empty string
    """
    if value.strip() != 'None' and value.strip():
        return value.strip()
    return None


def insert_group(values_array, db_cursor):
    """
    :param values_array: Array of relevant values (ID, NAME, MEMBERS_AMOUNT)
    :param db_cursor: Cursor to MySql DB
    :return: group_id
    """
    GROUP_INSERT = r"INSERT INTO GROUPS(ID, NAME_R, MEMBERS_AMOUNT, LAST_EXTRACTION) VALUES(%(id)s, %(name)s, %(members)s, %(last)s) ON DUPLICATE KEY UPDATE NAME_R=%(name)s, MEMBERS_AMOUNT=%(members)s, LAST_EXTRACTION=%(last)s"

    group_id, group_name, members_amount = values_array
    members_amount = nullify(members_amount)

    db_cursor.execute(GROUP_INSERT,
                             {'id': group_id, 'name': group_name, 'members': nullify(members_amount),
                              'last': datetime.now()})

    return group_id

def insert_post(values_array, db_cursor):
    """
    :param values_array: Array of relevant values (POST_ID, GROUP_ID, USER_ID, DATETIME)
    :param db_cursor: Cursor to MySql DB
    :return: post_id
    """

    POST_INSERT = r"INSERT INTO POSTS(ID, GROUP_ID, USER_ID, DATE_TIME) VALUES(%(id)s, %(group_id)s, %(user_id)s, %(datetime)s) ON DUPLICATE KEY UPDATE GROUP_ID=%(group_id)s, USER_ID=%(user_id)s, DATE_TIME=%(datetime)s"
    post_id, group_id, user_id, post_datetime = values_array
    try:
        date_time = datetime.strptime(post_datetime, '%d/%m/%Y %H:%M')
    except ValueError:
        date_time = None

    db_cursor.execute(POST_INSERT, {'id': post_id, 'group_id': group_id, 'user_id': user_id, 'datetime': date_time})

    return post_id

def insert_user(values_array, db_cursor):
    """
    :param values_array: Array of relevant values (ID, USER_NAME, FULL_NAME)
    :param db_cursor: Cursor to MySql DB
    :return: user_id
    """
    USER_INSERT = r"INSERT INTO USERS(ID, USER_NAME, FULL_NAME) VALUES(%(id)s, %(username)s, %(fullname)s) ON DUPLICATE KEY UPDATE USER_NAME=%(username)s, FULL_NAME=%(fullname)s"

    user_id, user_name, full_name = values_array

    db_cursor.execute(USER_INSERT, {'id': user_id, 'username': user_name, 'fullname': full_name})

    return user_id

def insert_info(values_array, post_id, db_cursor):
    """
    :param values_array: Array of relevant values (usere_id, action, info_kind, original_info, canonized_info)
    :param post_id: pos_id of current post
    :param db_cursor: cursot to MySql DB
    :return:
    """

    USER_INFO_INSERT = r"INSERT INTO USER_INFOS(USER_ID, POST_ID, ACTION_R, INFO_KIND, CANONIZED_INFO, ORIGINAL_INFO) VALUES(%s, %s, %s, %s, %s, %s)"

    user_id, action, info_kind, original_info, canonized_info = values_array

    db_cursor.execute(USER_INFO_INSERT, (
                user_id, post_id, action, nullify(info_kind), nullify(canonized_info), nullify(original_info)))

def update_abs_parse(values_array, db_cursor):
    """
    :param values_array: Value of arrays (just group id in this case)
    :param db_cursor: Cursor to MySQL DB
    :return:
    """

    UPDATE_STATEMENT = "UPDATE FACEBOOK.GROUPS SET EXTRACTED_ALL = TRUE WHERE ID = %s"

    group_id = values_array[0]

    db_cursor.execute(UPDATE_STATEMENT, (group_id,))


def import_file(file_path, delimiter='\t'):
    """
    :param file_path: Path to file you want to import
    :return:
    """
    print 'importing file:', file_path

    conn = connector.connect(user='root',
                             password='hujiko',
                             host='127.0.0.1',
                             database='facebook')

    cursor = conn.cursor()

    files_written = 0
    with open(file_path, 'rb') as input_file:
        for line in input_file.xreadlines():
            values = line.strip('\r\n').split(delimiter)
            cmd = values[0].lower().strip()  # First value is commands
            if cmd == 'start_group':
                group_id = insert_group(values[1:], cursor)  # Insert to db, and save group_id
            elif cmd == 'start_post':
                post_id = insert_post(values[1:], cursor)  # Insert post to DB and save post_id
            elif cmd == 'add_user':
                user_id = insert_user(values[1:], cursor)  # Insert user to DB and save user_id
            elif cmd == 'add_info':
                insert_info(values[1:], post_id, cursor)
            elif cmd == 'abs_parse':
                update_abs_parse(values[1:], cursor)

            files_written += 1
            if files_written % 1000 == 0:
                print 'processed {0} rows'.format(files_written)
                conn.commit()

        conn.commit()  # files that weren't committed because 1000 wasnt hit

    print 'DONE IMPORTING'


def get_dir_path():
    """
    :return: path to dir to import to database
    """

    path = raw_input("Enter path to Directory: ")
    while not os.path.isdir(path):
        path = raw_input("Enter path to Directory: ")
    return path


def main(dir_path=None):
    if dir_path is None:
        dir_path = get_dir_path()

    file_paths = glob("{path}/*.txt".format(path=dir_path))  # Choose only .txt files in dir
    for file_path in file_paths:
        import_file(file_path)

    raw_input('Press Enter to exit\n')


if __name__ == '__main__':
    main()