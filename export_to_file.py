__author__ = 'Sid'

################
#
# Write FB group
# users to file
#
################

_ACTION_AUTHOR = 1
_ACTION_COMMENTER = 2

_ACTION_DICT = {
	_ACTION_AUTHOR: 'author',
	_ACTION_COMMENTER: 'commenter'
}

def write_single_user(group, post, user, action_string, output_file):
	"""
	:param group: Group instance
	:param post: Post instance
	:param user: User instance
	:param action_string: string of action ('commenter'/'author')
	:return: True/False based on success
	"""
	user_name = user.user_name
	full_name = user.full_name
	user_id = user.id

	post_id = post.id
	post_datetime = post.date_time
	if post_datetime is None:
		formatted_string = ''
	else:
		formatted_string = post_datetime.strftime("%d/%m/%Y %H:%M")

	group_id = group.id
	group_name = group.name

	try:

		if not user.infos:
			# No infos, just write user
			output_file.write("{g_id}\t{g_name}\t{g_amount}\t{p_id}\t{p_time}\t{action}\t{u_f_name}\t{u_u_name}\t{u_id}\t{i_kind}\t{i_can_value}\t{i_ori_value}\r\n"
				.format(g_id=group_id,
			            g_name=group_name.encode('utf-8'),
			            g_amount=group.members,
			            p_id=post_id,
			            p_time=formatted_string,
			            action=action_string,
			            u_f_name=full_name.encode('utf-8'),
			            u_u_name=user_name,
			            u_id=user_id,
			            i_kind='',
			            i_can_value='',
			            i_ori_value=''))

		for info in user.infos:
			output_file.write("{g_id}\t{g_name}\t{g_amount}\t{p_id}\t{p_time}\t{action}\t{u_f_name}\t{u_u_name}\t{u_id}\t{i_kind}\t{i_can_value}\t{i_ori_value}\r\n"
				.format(g_id=group_id,
			            g_name=group_name.encode('utf-8'),
			            g_amount=group.members,
			            p_id=post_id,
			            p_time=formatted_string,
			            action=action_string,
			            u_f_name=full_name.encode('utf-8'),
			            u_u_name=user_name,
			            u_id=user_id,
			            i_kind=info[2],
			            i_can_value=info[1],
			            i_ori_value=info[0]))
	except UnicodeEncodeError:
		print 'COULDNT WRITE POST', post_id

def write_single_user_post(user_post, output_file):
	"""
	:param user: single UserInfo instance to write
	:param action_string: string of the user's action ('author'/'commenter')
	:param output_file: handle to the file to write to
	:return: True/False whether write was successful
	"""

	user = user_post.author
	commenters = user_post.commenters
	post = user_post.post
	group = user_post.group

	write_single_user(group, post, user, 'author', output_file)
	for commenter in commenters:
		write_single_user(group, post, commenter, 'commenter', output_file)

	# TODO: group member amount

def write_user_posts(user_posts, output_file):
	"""
	:param users: iterator of user_posts we want to save
	:param output_file: handle to the file to write to
	:return: amount of users it successfully wrote
	"""

	pass



