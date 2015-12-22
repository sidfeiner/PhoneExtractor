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
    if value.strip() != 'None':
        return value.strip()
    return None


def import_file(file_path, delimiter='\t'):
    """
	:param file_path: Path to file you want to import
	:return:
	"""
    print 'importing file:', file_path

    USER_INSERT = r"INSERT INTO USERS(ID, USER_NAME, FULL_NAME) VALUES(%(id)s, %(username)s, %(fullname)s) ON DUPLICATE KEY UPDATE USER_NAME=%(username)s, FULL_NAME=%(fullname)s"

    POST_INSERT = r"INSERT INTO POSTS(ID, GROUP_ID, DATE_TIME) VALUES(%(id)s, %(group_id)s, %(datetime)s) ON DUPLICATE KEY UPDATE GROUP_ID=%(group_id)s, DATE_TIME=%(datetime)s"
    GROUP_INSERT = r"INSERT INTO GROUPS(ID, NAME_R, MEMBERS_AMOUNT, LAST_EXTRACTION) VALUES(%(id)s, %(name)s, %(members)s, %(last)s) ON DUPLICATE KEY UPDATE NAME_R=%(name)s, MEMBERS_AMOUNT=%(members)s, LAST_EXTRACTION=%(last)s"
    USER_INFO_INSERT = r"INSERT INTO USER_INFOS(USER_ID, POST_ID, ACTION_R, INFO_KIND, CANONIZED_INFO, ORIGINAL_INFO) VALUES(%s, %s, %s, %s, %s, %s)"

    conn = connector.connect(user='root',
                             password='hujiko',
                             host='127.0.0.1',
                             database='facebook')

    cursor = conn.cursor()

    previous_group_id = previous_post_id = previous_user_id = None
    files_written = 0
    try:
        with open(file_path, 'rb') as input_file:
            input_file.readline()  # Skip headers line
            for line in input_file.xreadlines():
                values = line.split(delimiter)
                group_id, group_name, members_amount, post_id, post_datetime, action, full_name, \
                user_name, user_id, info_kind, canonized_value, original_value = values

                # Insert group
                if previous_group_id != group_id:
                    cursor.execute(GROUP_INSERT,
                                   {'id': group_id, 'name': group_name, 'members': nullify(members_amount),
                                    'last': datetime.now()})
                    previous_group_id = group_id

                # Insert Post
                if previous_post_id != post_id:
                    try:
                        date_time = datetime.strptime(post_datetime, '%d/%m/%Y %H:%M')
                    except ValueError:
                        date_time = None
                    cursor.execute(POST_INSERT, {'id': post_id, 'group_id': group_id, 'datetime': date_time})
                    previous_post_id = post_id

                # Insert User
                if previous_user_id != user_id:
                    cursor.execute(USER_INSERT, {'id': user_id, 'username': user_name, 'fullname': full_name})
                    previous_user_id = user_id

                # Insert UserInfo
                cursor.execute(USER_INFO_INSERT, (
                    user_id, post_id, action, nullify(info_kind), nullify(canonized_value), nullify(original_value)))

                # Commit each 500 entries
                files_written += 1
                if files_written == 500:
                    files_written = 0
                    conn.commit()
    except ValueError:
        pass

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