# -*- encoding: utf-8 -*-

##################################
#
# canonization
# Canonize phone numbers
# from different countries
#
##################################

import re, phone_formats

class CountryCanonizer(object):
    """
    Creates a canonizer from a CountryPhone object
    Has the ability to canonize phone numbers from any country
    """

    SIMPLE_CANON = 0
    EXTRACTED = 1
    NOTHING = 2

    def __init__(self, country_phone):
        self._country_phone = country_phone
        self._regexes_dict = {}
        self._regexes_lst = []
        self._init_regexes()

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return unicode(self.__str__())

    def __str__(self):
        return '{0} canonizer'.format(self._country_phone.country)

    def _create_alternatives(self):
        formats = self._country_phone.get_phone_formats()
        return formats._create_orred_regexes(canonized=True)

    def _create_reversed_regexes(self):
        """
        get reversed regexes (number and then prefix)
        """
        formats = self._country_phone.get_phone_formats()
        reversed_regex = formats._create_orred_reversed_regexes()
        return reversed_regex

    def _init_regexes(self):
        """
        initializes phone regexes
        canonizing regexes are tuples of regex and replacement
        """

        # Canonizing regexes (positive priority)
        # Every value in this dict is (search_regex, replace_regex, is_considered_canonizing, action_order)

        # Trims + and 0 from beginning, non numbers from end
        trim_regex = re.compile(r'^[\s+0]*(?P<phone>.+)\D*$')
        self._regexes_dict['trimmer'] = (trim_regex, r'\g<phone>', False, 0)

        # Reverse prefix and number
        # Comes as first canonization technique because when we remove all non-digits, this regex might be spammy
        reversing_regex = re.compile("^{0}$".format(self._create_reversed_regexes()))
        self._regexes_dict['reversed'] = (reversing_regex, '\\g<pre{i}>\\g<num{i}>', True, 1)  # many capturing names

        # Keep only numbers
        only_numbers_regex = re.compile(r'\D')
        self._regexes_dict['only_numbers'] = (only_numbers_regex, '', False, 2)

        alternatives = self._create_alternatives()

        # Removes 0 after country code
        stuck_zeroes_regex = re.compile("^({country})0*{alt}$".format(
            country=self._country_phone.country_code,
            alt=alternatives
        ))
        self._regexes_dict['stuck_zeroes'] = (stuck_zeroes_regex, r'\1\2', True, 3)  # remove zeroes

        # Adds country code
        no_country_code_regex = re.compile(r'^({alt})$'.format(alt=alternatives))
        self._regexes_dict['no_country_code'] = (
            no_country_code_regex, "{country}\\1".format(country=self._country_phone.country_code), True, 4)

        # END canonizing regexes

        temp_lst = sorted(self._regexes_dict.values(), lambda x, y: x[3] - y[3])
        self._regexes_lst = [(item[0], item[1], item[2]) for item in temp_lst if
                             item[3] >= 0]  # remove priority as its based on index

        # General rexes (negative priority)
        # Number parts
        self._regexes_dict['number_parts'] = re.compile(r'\d+')

        # Country phone regex (canonized)
        country_regex = self._country_phone.to_exact_regex()
        self._regexes_dict['country_regex'] = re.compile(country_regex)


    def _get_match_index(self, group_dict):
        """
        find the index of the first num/prefix pair that isnt null
        WILL ONLY FIND AN INDEX, because it comes after a match has been found
        """
        for key, value in group_dict.iteritems():
            # find correct capturing group index
            if value is not None:
                index = re.search(r'\d+$', key).group()
                return index

    def canonizemany(self, phone_numbers):
        """
        :param phone_numbers: List of phone numbers we want to canonize
        :return: List containing a set with every canonization possibily
        """
        return map(self.canonize, phone_numbers)

    def canonize(self, phone_number):
        """
        canonize a phone number (country_code+prefix+digits)
        """

        if phone_number is None:
            return None
            
        # Remove '+' and '0' from beginning and non-numbers from end
        trimmed_match = self._regexes_dict['trimmer'][0].search(phone_number)
        if trimmed_match:
            phone_number = trimmed_match.group('phone')
        else:
            return None

        simple_canon, success = self._canonize_simple(phone_number)
        simple_canon = {simple_canon}  # Save it into a set
        if not success:
            extracted, success = self._try_extract(phone_number)
        else:
            extracted = simple_canon

        return extracted

    def _try_extract(self, phone_number):
        """
        phone_number is already trimmed
        try extracting multiple phone number ("04754770383/4" will be "04754770383, 04754470384")
        :rtype: tuple
        :return: extracted_number_set, code (0-simple canonized, 1-extracted, 2-none)
        """

        phone_parts = self._regexes_dict['number_parts'].findall(phone_number)
        temp_number = ''

        for index, phone_part in enumerate(phone_parts):
            # Concat phone parts until it could be an actual phone number
            temp_number += phone_part
            if self._country_phone.min_length <= len(temp_number):
                canonized_number, success = self._canonize_simple(temp_number)
                if success:
                    base_number = canonized_number
                    break
        else:
            # no base number found
            return {phone_number}, self.NOTHING

        # From here on, it's based on the fact it found a base number
        if index == len(phone_parts) - 1:
            # No extras
            return {base_number}, self.SIMPLE_CANON

        extras = phone_parts[index + 1:]
        extracted_phones = self._extract_phones(base_number, extras)
        return extracted_phones, self.EXTRACTED

    def _extract_phones(self, base_number, extras):
        """
        :param base_number: basic phone number
        :param extras: alternative endings
        :return: set of all possible phones

        example: "04754770383/4" will be {"04754770383", "04754470384"}
        """

        all_phones = {base_number}

        for extra in extras:
            partial_base_num = base_number[:-len(extra)]
            new_num = partial_base_num + extra
            all_phones.add(new_num)

        return all_phones

    def _canonize_simple(self, phone_number):
        """
        canonize a phone number. returns tuple of canonized phone and a flag indicating whether the number
        was canonized or not.
        :rtype : tuple (canonized_phone, has_been_canonized)
        """

        canonize_success = False
        for index, regex_repl in enumerate(self._regexes_lst):
            # pass phone number through regexes (trimming, reversing, removing stuck zeroe, adding country code)
            regex, replace, should_canonize = regex_repl
            match = regex.search(phone_number)
            if match:
                if should_canonize:
                    canonize_success = True
                if index == 1:
                    # reversing
                    results = match.groupdict()
                    index = self._get_match_index(results)
                    phone_number = regex.sub(replace.format(i=index), phone_number)
                else:
                    phone_number = re.sub(regex, replace, phone_number)

        return phone_number, canonize_success

def create_israeli_canonizer(is_strict=True, is_canonized=True):
    """
    :return: israeli canonizer instance
    """
    return CountryCanonizer(phone_formats.create_israeli_phone(is_strict=True, is_canonized=True))

def create_belgian_canonizer(is_strict=True, is_canonized=True):
    """
    :return: belgian canonizer instance
    """
    return CountryCanonizer(phone_formats.create_belgian_phone(is_strict=True, is_canonized=True))

def create_holland_canonizer(is_strict=True, is_canonized=True):
    """
    :return: dutch canonizer instance
    """
    return CountryCanonizer(phone_formats.create_holland_phone(is_strict=True, is_canonized=True))

def create_all_canonizers(is_strict=True, is_canonized=True):
    """
    :return: dict of all canonizers
    """

    canonizers = {}
    all_formats = phone_formats.create_all_phones(is_strict=True, is_canonized=True)

    for country, phone_format in all_formats.iteritems():
        canonizers[country] = CountryCanonizer(phone_format)

    return canonizers

if __name__ == '__main__':
    isr = create_israeli_canonizer()
    print isr.canonizemany(['+00972-52-8197720/21/22', '+00972-03-456123', '+00972-03-4446123'])