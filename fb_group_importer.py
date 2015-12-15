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

def import_file(file_path, delimiter='\t'):
	"""
	:param file_path: Path to file you want to import
	:return:
	"""

	USER_INSERT = r"INSERT INTO USERS(ID, USER_NAME, FULL_NAME) VALUES(%(id)s, %(username)s, %(fullname)s) ON DUPLICATE KEY UPDATE USER_NAME=%(username)s, FULL_NAME=%(username)s"
	POST_INSERT = r"INSERT INTO POSTS(ID, GROUP_ID, DATE_TIME) VALUES(%(id)s, %(group_id)s, %(datetime)s) ON DUPLICATE KEY UPDATE GROUP_ID=%(group_id)s, DATE_TIME=%(datetime)s"
	GROUP_INSERT = r"INSERT INTO GROUPS(ID, NAME_R, MEMBERS_AMOUNT, LAST_EXTRACTION) VALUES(%(id)s, %(name)s, %(members)s, %(last)s) ON DUPLICATE KEY UPDATE NAME_R=%(name)s, MEMBERS_AMOUNT=%(members)s, LAST_EXTRACTION=%(last)s"
	USER_INFO_INSERT = r"INSERT INTO USER_INFOS(USER_ID, POST_ID, ACTION_R, INFO_KIND, CANONIZED_INFO, ORIGINAL_INFO) VALUES(%s, %s, %s, %s, %s, %s)"

	conn = connector.connect(user='root',
	                         password='hujiko',
	                         host='127.0.0.1',
	                         database='facebook')

	cursor = conn.cursor()

	previous_group_id = previous_post_id = previous_user_id = None

	with open(file_path, 'rb') as input_file:
		input_file.readline()  # Skip headers line
		for line in input_file.xreadlines():
			values = line.split(delimiter)
			group_id, group_name, members_amount, post_id, post_datetime, action, full_name, \
			user_name, user_id, info_kind, canonized_value, original_value = values

			# Insert group
			if previous_group_id != group_id:
				cursor.execute(GROUP_INSERT, {'id': group_id, 'name': group_name, 'members': members_amount, 'last': datetime.now()})
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
			cursor.execute(USER_INFO_INSERT, (user_id, post_id, action, info_kind, canonized_value, original_value))

			conn.commit()

	print 'DONE IMPORTING'

def get_file_path():
	"""
	:return: path to file to import to database
	"""

	path = raw_input("Enter path to file: ")
	while not os.path.isfile(path) and path.endswith('.txt'):
		path = raw_input("Enter path to file: ")
	return path


def main(file_path=None):
	if file_path is None:
		file_path = get_file_path()

	import_file(file_path)

	raw_input('Press Enter to exit')

if __name__ == '__main__':
	main()