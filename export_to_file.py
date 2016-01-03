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


def write_user_posts(user_posts, output_file):
    """
    :param users: iterator of user_posts we want to save
    :param output_file: handle to the file to write to
    :return: amount of users it successfully wrote
    """

    pass

def write_user_start(user, output_file):
    """
    :param user: User we start parsing
    :param output_file: File to write to
    :return:
    """
    _write_user_action(user, 'start', output_file)

def write_user_end(user, output_file):
    """
    :param user: User we ended parsing
    :param output_file: File to write to
    :return:
    """
    _write_user_action(user, 'end', output_file)

def _write_user_action(user, action, output_file):
    """
    :param user: UserInfo we write an action (start/end)
    :param action: start/end
    :param output_file: File to write to
    :return:
    """

    output_file.write("{action}_user\t{u_id}\t{u_u_name}\t{u_f_name}\r\n".format(action=action,
                                                                             u_id=user.id,
                                                                             u_u_name=user.user_name,
                                                                             u_f_name=user.full_name))

def write_group_start(group, output_file):
    """
    :param group: Group we start to parse
    :param output_file: File to write to
    :return:
    """
    _write_group_action(group, 'start', output_file)

def write_group_end(group, output_file):
    """
    :param group: Group we ended parsing
    :param output_file: File to write to
    :return:
    """
    _write_group_action(group, 'end', output_file)

def write_post_start(post, output_file):
    """
    :param post: Post we start parsing
    :param output_file: file to write to
    :return:
    """
    _write_post_action(post, 'start', output_file)

def write_post_end(post, output_file):
    """
    :param post: Post we end parsing
    :param output_file: file to write to
    :return:
    """
    _write_post_action(post, 'end', output_file)

def _write_post_action(post, action, output_file, encoding='utf-8'):
    """
    :param post: Post we have an action for (start/end parsing)
    :param action: start/end
    :param output_file: file to write to
    :return:
    """

    if post.date_time is None:
        date_time = ''
    else:
        date_time = post.date_time.strftime("%d/%m/%Y %H:%M")


    output_file.write("{action}_post\t{p_id}\t{g_id}\t{u_id}\t{p_time}\r\n".format(action=action.encode(encoding),
                                                                               p_id=post.id.encode(encoding),
                                                                               g_id=post.group_id.encode(encoding),
                                                                               u_id=post.user_id.encode(encoding),
                                                                               p_time=date_time.encode(encoding)
                                                                               )
                      )

def _write_group_action(group, action, output_file, encoding='utf-8'):
    """
    :param group: Group we have an action for (start/end parsing)
    :param action: start/end
    :param output_file: file to write to
    :return:
    """
    output_file.write("{action}_group\t{g_id}\t{g_name}\t{g_member}\r\n".format(action=action.encode(encoding),
                                                                                g_id=group.id.encode(encoding),
                                                                                g_name=group.name.encode(encoding),
                                                                                g_member=group.members
                                                                                )
                      )

def write_user_post(user_post, output_file):
    """
    :param user_post: User post to write
    :param output_file: File to write to
    :return:
    """

    write_post_start(user_post.post, output_file)  # user_id of author is written there

    write_user_infos(user_post.author, 'author', output_file)
    for commenter in user_post.commenters:
        write_user_infos(commenter, 'commenter', output_file)

    write_post_end(user_post.post, output_file)

def write_user_infos(user, action, output_file, encoding='utf-8'):
    """
    :param user: UserInfo we want to write
    :param action: author/commenter
    :param output_file: file to write to
    We MUST also write user_id because of the commenters. Author's user_id can be found be joining to the post
    """

    output_file.write("add_user\t{id}\t{user_name}\t{full_name}\r\n".format(id=user.id.encode(encoding),
                                                                            user_name=user.user_name.encode(encoding),
                                                                            full_name=user.full_name.encode(encoding)
                                                                            )
                      )
    if not user.infos:
        user.infos.add(('', '', ''))  # At least the user will be written

    for info in user.infos:
        output_file.write("add_info\t{u_id}\t{action}\t{i_kind}\t{i_canonized}\t{i_original}\r\n".format(
            u_id=user.id.encode(encoding),
            action=action.encode(encoding),
            i_kind=info[2].encode(encoding),
            i_canonized=info[0].encode(encoding),
            i_original=info[1].encode(encoding))
        )

def write_absolute_parse(group, output_file):
    """
    :param group: Group instance we have absolutely parsed
    :param output_file: File to write to
    :return:
    Writes a command that group has absolutely been parsed
    """

    output_file.write("abs_parse\t{id}\r\n".format(id=group.id))