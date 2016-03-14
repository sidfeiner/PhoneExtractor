# -*- encoding: utf-8 -*-

##################################
#
# phone_formats.py
# contains phone formats
# and creates appropriate regexes
#
##################################

import re

GENERAL_SEPARATOR = r'[^\d\s,]{0,2}'
OBLIGATED_SEPARATOR = r'[^\d\t\r\n,]{1,2}'


def _stronger_value(original, replacement):
    """
    Fight between original value and replacement.
    Return replacement if it isn't null, else return original
    """
    if replacement is None:
        return original
    return replacement


class FormatList(list):
    """
    Custom class for containing phone regexes.
    Allows exporting to many different formats
    """

    def __init__(self, format_list=list(), country_code='', strict=True, canonized=True):
        super(FormatList, self).__init__(format_list)
        self._is_canonized = canonized
        self._is_strict = strict
        self.country_code = country_code

    def copy(self):
        return FormatList(self, country_code=self.country_code, strict=self._is_strict,
                          canonized=self._is_canonized)

    def to_find_regex(self, strict=False, country_code='', optional_country=False, canonized=True, stuck_zero=False):
        """
        Creates a final compiled regex that will find phone numbers
        """
        return self._create_full_regex(absolute_anchors=False, strict=strict, country_code=country_code,
                                       optional_country=optional_country,
                                       canonized=canonized, stuck_zero=stuck_zero)

    def to_exact_regex(self, strict=False, country_code='', optional_country=False, canonized=True, stuck_zero=False):
        """
        Creates a final compiled regex that will exactly match phone number (between anchors)
        if strict or country_code are given as params, replace they are used instead of self.country_code and self._is_strict
        """
        return self._create_full_regex(absolute_anchors=True, strict=strict, country_code=country_code,
                                       optional_country=optional_country,
                                       canonized=canonized, stuck_zero=stuck_zero)

    def _create_full_regex(self, absolute_anchors=True, strict=False, country_code='', optional_country=False,
                           canonized=True,
                           stuck_zero=False):
        """
        create full regex based on anchors.
        absolute_anchors True: ^ and $
        absolute_anchors False: normal anchors
        stuck_zero: allow zeroes between country and prefix
        """

        is_strict = _stronger_value(self._is_strict, strict)
        country_code = _stronger_value(self.country_code, country_code)
        is_canonized = _stronger_value(self._is_canonized, canonized)

        orred_regexes = self._create_orred_regexes(canonized=is_canonized)

        if absolute_anchors:
            start_anchor = '^'
            end_anchor = '$'
        else:
            start_anchor = '(?:\\b|\\D)'
            end_anchor = '(?:\\b|\\D)'

        if is_canonized:
            separator = ''
        else:
            separator = GENERAL_SEPARATOR

        if stuck_zero:
            optional_zero = '0*'
        else:
            optional_zero = ''

        if is_strict and country_code:  # with country code
            if is_canonized:
                final_regex = "{start_anchor}(?P<phone>0*{country}{alt}){end_anchor}".format(start_anchor=start_anchor,
                                                                                             end_anchor=end_anchor,
                                                                                             country=country_code,
                                                                                             alt=orred_regexes)
            else:
                if not optional_country:
                    final_regex = "{start_anchor}(?P<phone>{country}{sep}{zero}{alt}){end_anchor}".format(
                        start_anchor=start_anchor,
                        end_anchor=end_anchor,
                        sep=separator,
                        country=country_code,
                        alt=orred_regexes,
                        zero=optional_zero)
                else:
                    final_regex = "{start_anchor}(?P<phone>0*({country}{sep})?{zero}{alt}){end_anchor}".format(
                        start_anchor=start_anchor,
                        end_anchor=end_anchor,
                        sep=separator,
                        country=country_code,
                        alt=orred_regexes,
                        zero=optional_zero)
        elif not country_code:
            # No Country code given
            final_regex = "{start_anchor}(?P<phone>0*({alt})){end_anchor}".format(start_anchor=start_anchor,
                                                                                  end_anchor=end_anchor,
                                                                                  country=country_code,
                                                                                  alt=orred_regexes)
        elif country_code:
            # Country code given, but optional
            final_regex = "{start_anchor}(?P<phone>0*({country}{sep})?{zero}{alt}){end_anchor}".format(
                start_anchor=start_anchor,
                end_anchor=end_anchor,
                country=country_code,
                sep=separator,
                alt=orred_regexes,
                zero=optional_zero)
        else:
            final_regex = "{start_anchor}(?P<phone>(0*{country}{sep})?{zero}{alt}){end_anchor}".format(
                start_anchor=start_anchor,
                end_anchor=end_anchor,
                sep=separator,
                country=country_code,
                alt=orred_regexes,
                zero=optional_zero)

        return re.compile(final_regex)

    def _create_reversed_regex(self):
        """
        creates reversed regex. first alternative and then prefix. 
        for example: 794565-03 
        """

        basic_regexes = []

        for index, phone_format in enumerate(self):
            current_regex = "(?P<num{i}>(\\d{sep1}){{{min},{max}}}\\d)0*{sep2}(?P<pre{i}>{prefix})".format(
                prefix=phone_format.prefix, sep1=GENERAL_SEPARATOR, sep2=OBLIGATED_SEPARATOR,
                min=phone_format.min_length - 1, max=phone_format.max_length - 1, i=len(basic_regexes))
            basic_regexes.append(current_regex)

        return basic_regexes

    def _create_regexes(self, canonized=True):
        """
        Create a regex for every phone format in the list
        """
        basic_regexes = []

        for phone_format in self:
            if canonized:
                current_regex = "{prefix}\\d{{{min},{max}}}".format(prefix=phone_format.prefix,
                                                                          min=phone_format.min_length,
                                                                          max=phone_format.max_length)
            else:
                current_regex = "{prefix}{sep}(\\d{sep}){{{min},{max}}}\\d".format(prefix=phone_format.prefix,
                                                                                         sep=GENERAL_SEPARATOR,
                                                                                         min=phone_format.min_length - 1,
                                                                                         max=phone_format.max_length - 1)
            basic_regexes.append(current_regex)

        return basic_regexes

    def _or_regexes(self, regexes):
        """
        Creates a big regex or-ing between smaller regexes
        """

        with_bracks = map(lambda x: "({0})".format(x), regexes)  # Add brackets #Only add brackets
        regexes_orred = '|'.join(with_bracks)
        return "({0})".format(regexes_orred)

    def _create_orred_regexes(self, canonized=True):
        """
        create regexes for all phone formats, and OR them in a big regex
        """
        regexes = self._create_regexes(canonized)
        orred_regexes = self._or_regexes(regexes)
        return orred_regexes

    def _create_orred_reversed_regexes(self):
        """
        create regexes for all reversed phone formats (prefix at end), and OR them in big regex
        """
        reversed_regex = self._create_reversed_regex()
        orred_regexes = self._or_regexes(reversed_regex)
        return orred_regexes


class Phone(object):
    def __init__(self, comment='', is_strict=True, is_canonized=True):
        self.formats = FormatList(strict=is_strict, canonized=is_canonized)
        self.comment = comment

    def add_format(self, phone_format):
        """
        Adds PhoneFormat instance
        """

        self.formats.append(phone_format)

    def _get_abs_min_max(self):
        """
        :return: tuple of minimal and maximal length of all formats
        """

        min_lengths = [item.min_length for item in self.formats]
        max_lengths = [item.max_length for item in self.formats]

        return min(min_lengths), max(max_lengths)

    def is_valid(self, phone_number, country_code=''):
        """
        Checks if phone_number matches any of the current formats.
        if no country code is given, it doesnt look for any
        """
        phone_regex = self.formats.to_exact_regex(country_code=country_code)
        print phone_regex.pattern
        match = re.search(phone_regex, phone_number)
        if match:
            return True
        return False

    def __unicode__(self):
        return unicode(self.comment)

    def __repr__(self):
        return self.__unicode__()


class CountryPhone(object):
    def __init__(self, country='', country_code='', mobile_phone=Phone(), line_phone=Phone(),
                 is_strict=True, is_canonized=True, phones_dict=None):
        self.country = country
        self.country_code = country_code
        if phones_dict:
            # init with dict
            self.mobile_phone, self.line_phone = self._parse_phones_dict(phones_dict,
                                                                         is_strict=is_strict,
                                                                         is_canonized=is_canonized)
        else:
            # init with each Phone instance
            self.mobile_phone = mobile_phone
            self.line_phone = line_phone

        self.min_length, self.max_length = self._abs_min_max()

    def _abs_min_max(self):
        """
        :return: absolute min and max lengths
        """
        mobile_min, mobile_max = self.mobile_phone._get_abs_min_max()
        line_min, line_max = self.line_phone._get_abs_min_max()

        return min(mobile_min, line_min), max(mobile_max, line_max)

    def is_valid_mobile(self, phone_number, strict=True):
        """
        checks if phone_number is a valid mobile. strict flag adds mobile country code
        """
        if strict:
            return self.mobile_phone.is_valid(phone_number=phone_number, country_code=self.country_code)
        return self.mobile_phone.is_valid(phone_number)

    def is_valid_line(self, phone_number, strict=True):
        """
        checks if phone_number is a valid line. strict flag adds line country code
        """
        if strict:
            return self.line_phone.is_valid(phone_number=phone_number, country_code=self.country_code)
        return self.line_phone.is_valid(phone_number)

    def is_valid(self, phone_number, strict=True):
        """
        checks if phone_number is a valid mobile or line number
        """
        return self.is_valid_line(phone_number, strict) or self.is_valid_mobile(phone_number, strict)

    def get_phone_formats(self):
        formats = self.mobile_phone.formats.copy()
        formats.extend(self.line_phone.formats)
        return formats

    def to_find_regex(self, strict=False, with_country=True, optional_country=False, canonized=True, stuck_zero=False):
        """
        Creates a final compiled regex that will find phone numbers
        """
        return self._create_full_regex(absolute_anchors=False, strict=strict, with_country=with_country,
                                       optional_country=optional_country,
                                       canonized=canonized, stuck_zero=stuck_zero)

    def to_exact_regex(self, strict=False, with_country=True, optional_country=False, canonized=True, stuck_zero=False):
        """
        Creates a final compiled regex that will exactly match phone number (between anchors)
        if strict or country_code are given as params, replace they are used instead of self.country_code and self._is_strict
        """
        return self._create_full_regex(absolute_anchors=True, strict=strict, with_country=with_country,
                                       optional_country=optional_country,
                                       canonized=canonized, stuck_zero=stuck_zero)

    def _create_full_regex(self, absolute_anchors=True, strict=True, with_country=True, optional_country=False,
                           canonized=True, stuck_zero=False):
        """
        :param absolute_anchors:
        :param strict:
        :param with_country: flag to add country code or nor
        :param canonized: with or without separators
        :return: regex of country phone
        """
        format_list = FormatList(self.get_phone_formats())

        if with_country:
            return format_list._create_full_regex(absolute_anchors=absolute_anchors,
                                                  strict=strict,
                                                  country_code=self.country_code,
                                                  optional_country=optional_country,
                                                  canonized=canonized,
                                                  stuck_zero=stuck_zero)

        return format_list._create_full_regex(absolute_anchors=absolute_anchors,
                                              strict=strict,
                                              optional_country=optional_country,
                                              canonized=canonized,
                                              stuck_zero=stuck_zero)

    def _parse_phones_dict(self, phones_dict, is_strict=True, is_canonized=True):
        """
        Gets a dict of PhoneFormat instances. parses it to mobile and line phones_dict
        return: tuple (mobile_phone, line_phone)
        """
        mobile_phone = Phone(comment="{country} - {kind} number".format(country=self.country, kind="mobile"),
                             is_strict=is_strict,
                             is_canonized=is_canonized)
        line_phone = Phone(comment="{country} - {kind} number".format(country=self.country, kind="line"),
                           is_strict = is_strict,
                           is_canonized=is_canonized)

        for kind, phone_formats in phones_dict.iteritems():
            for phone_format in phone_formats:
                if 'mobile' in kind:
                    mobile_phone.add_format(phone_format)
                elif 'line' in kind:
                    line_phone.add_format(phone_format)

        return mobile_phone, line_phone

    def __unicode__(self):
        return unicode(self.country)

    def __repr__(self):
        return self.__unicode__()


class PhoneFormat(object):
    def __init__(self, prefix, min_length, max_length, comment=''):
        """
        Creates a phone format. 
        prefix: any regex
        min_length and max_length: integers
        """
        self.prefix = prefix
        self.min_length = min_length
        self.max_length = max_length
        self.comment = comment


def create_israeli_phone(is_strict=True, is_canonized=True):
    """
    :return: Instance of israeli phone number
    """
    israeli_formats = {
        'line': [
            PhoneFormat(prefix='[23489]', min_length=7, max_length=7, comment=r'geographic prefixes'),
            PhoneFormat(prefix='7', min_length=8, max_length=8, comment=r'non geographic Landline and VoIP')
        ],

        'mobile': [PhoneFormat(prefix='5[^\\D]', min_length=7, max_length=7,
                               comment=r'55 prefix is for virtual network operators')]
    }
    return CountryPhone(country='israel', country_code='972', is_strict=is_strict,
                        is_canonized=is_canonized, phones_dict=israeli_formats)


def create_belgian_phone(is_strict=True, is_canonized=True):
    """
    :return: Create instance of belgian phone number
    """
    belgian_formats = {
        'line': [
            PhoneFormat(prefix='[^\\D0]', min_length=7, max_length=7, comment=r'geographic prefixes'),
            PhoneFormat(prefix='(70|78|90)', min_length=6, max_length=6,
                        comment=r'non geographic, mostly services'),
            PhoneFormat(prefix='800', min_length=7, max_length=7, comment=r'non geographic, mostly services')
        ],

        'mobile': [PhoneFormat(prefix='4[6789]', min_length=7, max_length=7)]
    }
    return CountryPhone(country='belgium', country_code='32', is_strict=is_strict,
                        is_canonized=is_canonized, phones_dict=belgian_formats)


def create_holland_phone(is_strict=True, is_canonized=True):
    """
    :return: Create instance of dutch phone number
    """
    france_formats = {
        'line': [
            PhoneFormat(prefix='[12345]', min_length=8, max_length=8, comment=r'geographic prefixes'),
            PhoneFormat(prefix='[89]', min_length=6, max_length=6, comment=r'non geographic, mostly services')
        ],

        'mobile': [PhoneFormat(prefix='[67]', min_length=8, max_length=8)]
    }
    return CountryPhone(country='france', country_code='33', is_strict=is_strict,
                        is_canonized=is_canonized, phones_dict=france_formats)


def create_all_phones(is_strict=True, is_canonized=True):
    """
    :return: dict of all phone formats
    """

    phone_formats = {'israel': create_israeli_phone(is_strict, is_canonized),
                     'belgium': create_belgian_phone(is_strict, is_canonized),
                     'holland': create_holland_phone(is_strict, is_canonized)}
    
    return phone_formats
