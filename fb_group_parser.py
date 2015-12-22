__author__ = 'Sid'

##############################################
#
# Extract open facebook groups
#
# Extract anybody who posted/commented
# with the phone numbers/emails he posted
#
##############################################

import re
import time
from datetime import datetime
from base64 import b64encode
import json
from HTMLParser import HTMLParser

from selenium import webdriver
from lxml import html

import export_to_file
import canonization

# Constants
_USERNAME = 'username_from_url'
_FID = 'fid_from_url'
_POST_ID = 'post_id'

# Exceptions
class ClosedGroupException(Exception):
    def __init__(self, message):
        super(ClosedGroupException, self).__init__(message)


class GroupParser(object):
    def __init__(self, email, password, reload_amount, group_ids):
        self.email = email
        self.password = password
        self.reload_amount = reload_amount
        self.group_ids = group_ids
        self.driver = None
        self._regexes = self._init_regexes()
        self._xpaths = self._init_xpaths()
        self._canonizers = canonization.create_all_canonizers()
        self._html_parser = HTMLParser()
    
    def _init_regexes(self):
        """
        :return: dictionary of compiled regexes
        """
        
        regexes = {}
        
        # Extracts user id from facebook homepage
        regexes['my_id'] = re.compile(r'"USER_ID":"(?P<result>\d+)')
        
        # Doesn't extract fid if no username found. ON PURPOSE
        regexes['username_from_url'] = re.compile(r'facebook\.com/(?P<result>[\w.]+)')
        
        # Extracts fid from data-hover attribute (/ajax/hovercard/user.php?id=785737849&extragetparams=)
        regexes['fid_from_url'] = re.compile(r'\?id=(?P<result>\d+)')
        
        # Finds emails
        regexes['emails'] = re.compile(r'([\w.-]+(@|&#064;)[\w-]{2,}(\.[\w-]{2,}){1,4})')
        
        # Extract post_id from id attribute
        regexes['post_id'] = re.compile(r'mall_post_(?P<result>\d+)')
        
        # Extract json from page source
        regexes['json_from_html'] = re.compile(r'[^{]*(?P<json>.*\})[^}]*$')
        
        return regexes
    
    def _init_xpaths(self):
        """
        :return: dictionary of xpaths
        """
        
        xpaths = {}
        
        # xpath to full post, containing comments (a post has an attribute named 'data-ft' with a tl_objid key
        xpaths['full_post'] = "//div[contains(@data-ft,'tl_objid')]"
        
        # xpaths to the content itself and the comment section
        xpaths['post_content'] = ".//p/parent::*"
        
        # Author Xpath's. Relative to post
        xpaths['post_author'] = './/a[@data-hovercard][2]'  # First is link from picture, withour name
        xpaths['author_username'] = './@href'  # URL's need further parsing
        xpaths['author_fid'] = './@data-hovercard'
        xpaths['author_fullname'] = './text()'
        
        # Comment Xpath's
        xpaths['post_comments'] = ".//div[contains(@class, 'UFIContainer')]//div[@class='UFICommentContent']"
        xpaths['comment_meta'] = './/a[contains(@class,"UFICommentActorName")]'
        xpaths['comment_author_fid'] = './@data-hovercard'  # URL's need further parsing, relative to meta
        xpaths['comment_author_username'] = './@href'  # URL's need further parsing, relative to meta
        xpaths['comment_author_fullname'] = './span/text()'  # relative to meta
        
        xpaths['comment_text'] = './/span[contains(@class,"UFICommentBody")]'  # Relative to comment
        
        xpaths['post_timestamp'] = './/abbr/@data-utime[1]'  # Relative to post
        xpaths['post_id'] = './@id'  # Relative to post, needed further parsing
        
        return xpaths
    
    def init_connect(self):
        """
        Connect to facebook
        return True if successfull, False otherwise
        """
        self.driver.get('https://facebook.com')
        
        # set email
        email_element = self.driver.find_element_by_id('email')
        email_element.send_keys(self.email)
        
        # set password
        password_element = self.driver.find_element_by_id('pass')
        password_element.send_keys(self.password)
        
        # press login button
        self.driver.find_element_by_id('loginbutton').click()
        
        if 'attempt' in self.driver.current_url:
            # Failed to log in
            return None
        
        my_id_match = self._regexes['my_id'].search(self.driver.page_source)
        if my_id_match:
            return my_id_match.group('result')
        
        return None
    
    def _extract_group_info(self, group_id):
        """
        Extract group info.
        :return Group instance
        """
        group_name_xpath = '//input[@aria-label="Search Facebook" or @tabindex="-1"]/@value'
        group_members_xpath = '//span[@id="count_text"]/text()'
        group_members_amount_regex = re.compile(r'[\d,]+')
        
        group_url = 'https://facebook.com/{id}'
        self.driver.get(group_url.format(id=group_id))
        time.sleep(5)
        
        page_source = self.driver.page_source
        
        html_tree = html.fromstring(page_source)
        
        group_name = html_tree.xpath(group_name_xpath)[0]
        
        # Parse members amount, cast to int
        members_xpath_result = html_tree.xpath(group_members_xpath)
        if members_xpath_result:
            group_members_string = members_xpath_result[0]
            group_members_match = group_members_amount_regex.search(group_members_string)  # Number with commas
            if group_members_match:
                members_only_digits = re.sub(r'\D', '', group_members_match.group())  # Keep only numbers
                group_members = int(members_only_digits)
        else:
            group_members = None
        
        return Group(id=group_id, name=group_name, members=group_members)
    
    def _parse_from_xpath(self, xpath_result, target_parse):
        """
        :param xpath_result: List containing Url with username (should have only 1 string)
        :param target_parse: string of what you want to parse ('fid'/'username'/'post_id' or _USERNAME/_FID/_POST_ID)
        :return: Parsed username if exists
        """
        
        if not xpath_result:
            return ''
        
        regex = self._regexes[target_parse]
        
        match = regex.search(xpath_result[0])  # Choose only first result from list
        if not match:
            return ''
        
        result = match.group('result')
        
        if target_parse == _USERNAME and result == 'profile.php':
            return ''
        
        return result
    
    def _parse_user(self, post_node):
        """
        :param post_node: Html node representing the current post
        :return: UserInfo instance - only USER
        """
        
        post_author_nodes = post_node.xpath(self._xpaths['post_author'])
        if not post_author_nodes:
            return None
        
        post_author = post_author_nodes[0]
        
        user_name_url = post_author.xpath(self._xpaths['author_username'])
        user_name = self._parse_from_xpath(user_name_url, _USERNAME)
        
        fid_url = post_author.xpath(self._xpaths['author_fid'])
        fid = self._parse_from_xpath(fid_url, _FID)
        
        full_name_xpath = post_author.xpath(self._xpaths['author_fullname'])
        if full_name_xpath:
            full_name = full_name_xpath[0]
        else:
            # No full name exists
            full_name = ''
        
        return UserInfo(user_name=user_name, id=fid, full_name=full_name)
    
    def _parse_phones(self, text):
        """
        :param text: source to extract phone numbers from
        :return: set of tuples containig canonized phone number and country
        """
        info_tuples = set()
        
        for country, canonizer in self._canonizers.iteritems():
            # Find all phone numbers and canonize
            country_phone = canonizer._country_phone
            finding_regex = country_phone.to_find_regex(strict=False, canonized=False, optional_country=True,
                                                        stuck_zero=True)
            phone_matches = finding_regex.finditer(text)
            for phone_match in phone_matches:
                phone = phone_match.group('phone')
                canonized_phone_lst = canonizer.canonize(phone)
                for canonized_phone in canonized_phone_lst:
                    info_tuples.add((phone, canonized_phone, '{0}_phone'.format(country)))
        
        return info_tuples
    
    def _parse_emails(self, text):
        """
        :param text: source to extract emails from
        :return: set of emails
        """
        
        info_tuples = set()
        
        emails = self._regexes['emails'].findall(text)
        for email in emails:
            canonized_email = email[0].replace('#&064;', '@').lower()  # email is a tuple. email[0] is full email
            canonized_email = canonized_email.strip('.')
            info_tuples.add((canonized_email, canonized_email.lower(), 'email'))
        
        return info_tuples
    
    def _parse_info_from_text(self, text):
        """
        :param text: Text to extract info from
        :return: list of tuple info
        """
        
        info_tuples = self._parse_phones(text)
        emails = self._parse_emails(text)
        
        # Union all infos
        info_tuples.update(emails)
        
        return info_tuples
    
    def _parse_info_from_node(self, post_node):
        """
        :param post_node: Html node representing the current post
        :return: list of tuple info
        """
        
        post_content_lst = post_node.xpath(self._xpaths['post_content'])
        post_content = '\n'.join(map(lambda x: x.text_content(), post_content_lst))
        
        return self._parse_info_from_text(post_content)
    
    def _parse_user_info(self, post_node):
        """
        :param post_node: Html node representing the current post
        :return: UserInfo instance (names, info)
        """
        
        user = self._parse_user(post_node)
        infos = self._parse_info_from_node(post_node)
        user.infos = infos
        
        return user
    
    def _parse_user_from_comment(self, comment_xpath):
        """
        :param comment_xpath: xpath node to current comment
        :return:
        """
        
        comment_meta_lst = comment_xpath.xpath(self._xpaths['comment_meta'])
        
        if comment_meta_lst:
            comment_meta = comment_meta_lst[0]
            user_name_lst = comment_meta.xpath(self._xpaths['comment_author_username'])
            user_name = self._parse_from_xpath(user_name_lst, _USERNAME)
            
            fid_lst = comment_meta.xpath(self._xpaths['comment_author_fid'])
            fid = self._parse_from_xpath(fid_lst, _FID)
            
            full_name_lst = comment_meta.xpath(self._xpaths['comment_author_fullname'])
            if full_name_lst:
                full_name = full_name_lst[0]
            else:
                full_name = ''
            
            return UserInfo(user_name=user_name, id=fid, full_name=full_name)
        
        return None
    
    def _parse_user_infos_from_comment(self, comments_xpath):
        """
        :param comments_xpath: xpath containing all comments
        :return: distinct user_infos who commented
        """
        
        all_commenters = set()  # Set of user_info's
        
        for comment in comments_xpath:
            user_info = self._parse_user_from_comment(comment)
            comment_content_lst = self._xpaths['comment_text']
            if comment_content_lst:
                comment_content = comment_content_lst[0]
                infos = self._parse_info_from_text(comment_content)
                user_info.infos = infos
            
            all_commenters.add(user_info)
        
        return all_commenters
    
    def _parse_post(self, group, user, post_xpath):
        """
        :param post_xpath: xpath node for current post
        :return: Post instance
        """
        
        timestamp_unix_str = post_xpath.xpath(self._xpaths['post_timestamp'])
        
        if not timestamp_unix_str:
            timestamp = None
        else:
            timestamp = int(timestamp_unix_str[0])
        
        post_id_path = post_xpath.xpath(self._xpaths['post_id'])
        post_id = self._parse_from_xpath(post_id_path, _POST_ID)
        return Post(id=post_id, group_id=group.id, user_id=user.id, date_time=timestamp), timestamp
    
    def _parse_page(self, group, parse_src, output_file):
        """
        :param group: current Group instance
        :param parse_src: src text to parse from
        :param output_file: handle to file where to write the results
        """
        
        html_tree = html.fromstring(parse_src)
        
        all_posts = html_tree.xpath(self._xpaths['full_post'])
        if not all_posts:
            raise ClosedGroupException("Probably got to a Closed group")
        
        last_timestamp = None
        
        for post in all_posts:
            author_info = self._parse_user_info(post)
            comments = post.xpath(self._xpaths['post_comments'])
            commenters_infos = self._parse_user_infos_from_comment(comments)
            
            previous_timestamp = last_timestamp  # Save previous in case current is None
            current_post, last_timestamp = self._parse_post(post)

            if not last_timestamp:
                last_timestamp = previous_timestamp  # last_timestamp is previous again (which isn't None)
            
            current_user_post = UserPost(author=author_info, group=group, post=current_post,
                                         commenters=commenters_infos)

            export_to_file.write_user_post(current_user_post, output_file)

        return current_post.id, last_timestamp
    
    def _get_next_url(self, last_post_id, last_timestamp, group_id, user_id, reload_id):
        """
        :param last_post_id: id of the last post extracted
        :param last_timestamp: unix timestamp of the last pod extracted
        :param group_id: group_id of group we are currently extracting
        :param user_id: user id of current connected user
        :param reload_id: index of current reload (starts with 1)
        :return: formatted string
        """
        
        base_url = (
            'https://www.facebook.com/ajax/pagelet/generic.php/GroupEntstreamPagelet?__pc=EXP1:react_composer_pkg'
            '&ajaxpipe=1&ajaxpipe_token=AXhY1JWsfBFKhhsj&no_script_path=1'
            '&data={{"last_view_time":0,"is_file_history":null,"is_first_story_seen":true,"end_cursor":"{cursor}",'
            '"group_id":{g_id},"has_cards":true,"multi_permalinks":[],"post_story_type":null}}&__user={user_id}&__a=1'
            '&__dyn=7AmajEzUGBym5Q9UoHaEWC5ECiq2WbF3oyupFLFwxBxCbzES2N6y8-bxu3fzoaqwFUgx-y28b9J1efKiVWxe6okzEswLDz8Sm2uVUKmFAdAw'
            '&__req=jsonp_{reload}&__rev=2071590&__adt={reload}')
        
        cursor = "{timestamp}:{post_id}".format(timestamp=last_timestamp - 10 * 60,
                                                post_id=last_post_id)  # Remove 10 minutes fro timestamp to be sure
        encoded_cursor = b64encode(cursor)
        
        return base_url.format(cursor=encoded_cursor,
                               g_id=group_id,
                               user_id=user_id,
                               reload=reload_id)
    
    def _parse_payload_from_ajax_response(self, ajax_response):
        """
        :param ajax_response: full response
        """
        
        full_json_match = self._regexes['json_from_html'].search(ajax_response)  # Keep only json string
        if not full_json_match:
            return None
        
        full_json = full_json_match.group('json')
        json_dict = json.loads(full_json)
        if 'payload' in json_dict.keys():
            return json_dict['payload']
        return None
    
    def _fix_payload(self, payload):
        """
        :param payload: html payload
        :return: unescaped html
        """
        
        payload_html = payload.replace(r'\u003C', '<')
        return self._html_parser.unescape(payload_html)
    
    def _init_output_file(self, output_file):
        """
        :param output_file: handle to output file (ab+)
        :return: initialized headers if it isn't already. True if it got initiated now, False otherwise
        """
        
        first_line = output_file.readline().upper()
        output_file.seek(0)  # Set cursor to beginning
        
        if 'GROUP_ID' in first_line:
            return False
        
        output_file.write(("GROUP_ID\tGROUP_NAME\tGROUP_MEMBERS_AMOUNT\tPOST_ID\tPOST_TIME\tACTION\tFULL_NAME"
                           "\tUSER_NAME\tUSER_ID\tINFO_KIND\tINFO_CANONIZED_VALUE\tINFO_ORIGINAL_VALUE\r\n"
                           ))
        
        return True
    
    def _parse_group(self, group, user_id, output, reload_amount=400):
        """
        parse single group
        returns true if it got to a page there wasn't anything to extract (It got to the bottom)
        return false if it didn't get to the end
        """
        
        group_url = 'https://facebook.com/{id}'.format(id=group.id)
        if not group.id in self.driver.current_url:
            self.driver.get(group_url)
            time.sleep(5)
        
        reload_id = 2
        payload_html = self.driver.page_source

        self._init_output_file(output)
        for i in xrange(2, reload_amount + 1):
            # Parse reload_amount of pages
            try:
                result_tuple = self._parse_page(group, payload_html, output)
            except html.etree.XMLSyntaxError:
                # Probably got to the end
                return True, i

            last_post_id, last_timestamp = result_tuple

            if i % 10 == 0:
                # Flush each 10 pages
                output.flush()

            next_url = self._get_next_url(last_post_id, last_timestamp, group.id, user_id, reload_id)
            reload_id += 1
            self.driver.get(next_url)

            if reload_id >= 2:
                # First time isn't from an ajax request
                payload = self._parse_payload_from_ajax_response(self.driver.page_source)
                if payload is None:
                    raise Exception("Next json payload couldn't be loaded")
                payload_html = self._fix_payload(payload)

        return False

    def _parse_all_groups(self, user_id, reload_amount=400):
        """
        start parsing the groups
        """
        reload_amount = stronger_value(self.reload_amount, reload_amount)
        with open(r"C:\Users\Sid\Desktop\output.txt", 'ab+') as output:
            for group_id in self.group_ids:
                current_group = self._extract_group_info(group_id)
                print 'Starting to parse group: {0}'.format(current_group.name.encode('utf-8'))
                try:
                    export_to_file.write_group_start(current_group, output)
                    absolute_crawl = self._parse_group(current_group, user_id, output, reload_amount=reload_amount)
                except ClosedGroupException:
                    print "The group is closed. This script only parses open groups!"
                    continue
                finally:
                    export_to_file.write_group_end(current_group, output)
                print 'Done parsing group: {0}\nParsed everything: {1}'.format(current_group.name.encode('utf-8'),
                                                                               absolute_crawl)
    
    def run(self, reload_amount=None):
        """
        start running the parser
        """
        reload_amount = stronger_value(self.reload_amount, reload_amount)
        self.driver = webdriver.Chrome()
        my_id = self.init_connect()  # Connect to facebook
        
        if my_id is None:
            raise Exception("User id not found in homepage")
        try:
            self._parse_all_groups(user_id=my_id, reload_amount=reload_amount)
        finally:
            self.driver.quit()


class UserInfo(object):
    """
    class to contain user info
    """
    
    def __init__(self, user_name='', id='', full_name=''):
        self.user_name = user_name
        self.id = id
        self.full_name = full_name
        self.infos = set()  # will contain tuples containing (origina_info, canonized_info, info_kind). EX: (0475-864-285, 32475864285, 'belgian_phone')


class Post(object):
    """
    class to contain post about a post
    """
    
    def __init__(self, id='', group_id='', user_id='', date_time=''):
        self.id = id
        self.group_id = group_id
        self.user_id = user_id
        
        if type(date_time) == int:
            # timestamp unix
            post_datetime = datetime.fromtimestamp(date_time)
        elif type(date_time) == datetime:
            post_datetime = date_time
        else:
            post_datetime = None
        
        self.date_time = post_datetime


class Group(object):
    def __init__(self, id='', name='', members=None):
        self.id = id
        self.name = name
        self.members = members
    
    def __repr__(self):
        return "group name: {name}\ngroup id: {id}\nmembers: {amount}".format(name=self.name,
                                                                              id=self.id,
                                                                              amount=self.members)


class UserPost(object):
    """
    Class to contain POST info
    """
    
    def __init__(self, author, group, post, commenters):
        self.author = author  # UserInfo instance
        self.commenters = commenters
        self.post = post  # Post instance
        self.group = group  # Group instance


def stronger_value(original_value, new_value):
    """
    :param original_value: original value
    :param new_value: value to replace the original value
    :return: new_value if it isnt null, original_value otherwise
    """
    if new_value:
        return new_value
    return original_value


def get_group_ids():
    """
    get group ids. allow only number, allow many group ids in one time
    """
    pattern = re.compile(r'\d{6,}')
    group_ids = set()
    group_id = raw_input("Enter group id(s):\n")
    while group_id not in ['', 'done', 'exit']:
        current_ids = pattern.findall(group_id)  # Find all group ids entered
        map(lambda x: group_ids.add(x), current_ids)  # add them to set
        group_id = raw_input("Enter group id(s): ")
    
    return group_ids


def get_user_info():
    """
    Get user's email/password
    :return tuple of (email, password)
    :rtype TUPLE
    """
    email_pattern = re.compile(r'[\w.-]+@[\w-]{2,}(\.[\w-]{2,}){1,4}')
    email = raw_input("Enter you email: ")
    while not email_pattern.match(email.strip()):
        email = raw_input("Enter you email: ")
    
    password = raw_input("Enter your password: ")
    
    return email, password


def get_reload_amount():
    """
    get the maximal amount of time you want to load next page in group
    """
    
    amount = raw_input("Enter the amount of pages you want to load in each group: ")
    while not amount.isdigit():
        amount = raw_input("Enter the amount of pages you want to load in each group: ")
    return int(amount)


def main():
    """
    Gets input for script
    """
    group_ids = get_group_ids()  # gets a set
    email, password = get_user_info()
    amount = get_reload_amount()
    
    group_parser = GroupParser(email=email, password=password, reload_amount=amount, group_ids=group_ids)
    group_parser.run()
    raw_input('Enter anything to finish')


if __name__ == '__main__':
    main()