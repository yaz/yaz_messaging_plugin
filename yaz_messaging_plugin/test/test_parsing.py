import yaz
from .tester import ClassTestCase


class TestParsingWithColon(ClassTestCase):
    """
    The message should not contain an unquoted colon (:), this results in a parser error
    """
    files = {
        "colon.nl.yml": """
message: this line has a colon at : the end
""".lstrip()
    }

    def test_010_check(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"mapping values are not allowed here"):
            caller("check")

    def test_020_fix(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"mapping values are not allowed here"):
            caller("fix")


class TestParsingWithExclamationMark(ClassTestCase):
    """
    If the message starts with an exclamation mark, this results in a parser error
    """
    files = {
        "exclamation.nl.yml": """
message: !foo should be quoted
""".lstrip()
    }

    def test_010_check(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"could not determine a constructor for the tag .!foo."):
            caller("check")

    def test_020_fix(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"could not determine a constructor for the tag .!foo."):
            caller("fix")


class TestEmptyFile(ClassTestCase):
    """
    Empty files should pass though the 'check' and not result in any changes
    """
    files = {
        "empty.nl.yml": ""
    }

    def test_010_check(self):
        caller = self.get_caller()
        self.assertTrue(caller("check"))

    def test_020_fix(self):
        caller = self.get_caller()
        self.assertTrue(caller("fix"))
        self.assertEqual("", self.get_file_content("empty.nl.yml"))


class TestBooleanAsString(ClassTestCase):
    """
    YAML 1.1 supports type conversions for several types,
    in Symfony translations we want that disabled

    Finally, we *will* output in valid YAML 1.1 format, hence all
    special type values will be properly quoted.
    """
    files = {
        "type.nl.yml": """
false: False
maybe.yes.or.no: Maybe
no: No
true: True
yes: Yes
""".lstrip()
    }

    def test_010_check(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"changes detected in file"):
            caller("check")

    def test_020_fix(self):
        expected = """
'false': 'False'
maybe:
    'yes':
        or:
            'no': Maybe
'no': 'No'
'true': 'True'
'yes': 'Yes'
""".lstrip()

        caller = self.get_caller()
        caller("fix", "--changes", "overwrite")
        self.assertEqual(expected, self.get_file_content("type.nl.yml"))

    def test_030_check(self):
        caller = self.get_caller()
        self.assertTrue(caller("check"))

class TestFloatAsString(ClassTestCase):
    """
    YAML 1.1 supports type conversions for several types,
    in Symfony translations we want that disabled

    Finally, we *will* output in valid YAML 1.1 format, hence all
    special type values will be properly quoted.
    """
    files = {
        "type.nl.yml": """
canonical: 6.8523015e+5
exponentioal: 685.230_15e+03
fixed: 685_230.15
negative infinity: -.inf
not a number: .NaN
sexagesimal: 190:20:30.15
""".lstrip()
    }

    def test_010_check(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"changes detected in file"):
            caller("check")

    def test_020_fix(self):
        expected = """
canonical: '6.8523015e+5'
exponentioal: '685.230_15e+03'
fixed: '685_230.15'
negative infinity: '-.inf'
not a number: '.NaN'
sexagesimal: '190:20:30.15'
""".lstrip()

        caller = self.get_caller()
        caller("fix", "--changes", "overwrite")
        self.assertEqual(expected, self.get_file_content("type.nl.yml"))

    def test_030_check(self):
        caller = self.get_caller()
        self.assertTrue(caller("check"))

class TestIntAsString(ClassTestCase):
    """
    YAML 1.1 supports type conversions for several types,
    in Symfony translations we want that disabled

    Finally, we *will* output in valid YAML 1.1 format, hence all
    special type values will be properly quoted.
    """
    files = {
        "type.nl.yml": """
binary: 0b1010_0111_0100_1010_1110
canonical: 685230
decimal: +685_230
hexadecimal: 0x_0A_74_AE
octal: 02472256
sexagesimal: 190:20:30
""".lstrip()
    }

    def test_010_check(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"changes detected in file"):
            caller("check")

    def test_020_fix(self):
        expected = """
binary: '0b1010_0111_0100_1010_1110'
canonical: '685230'
decimal: '+685_230'
hexadecimal: '0x_0A_74_AE'
octal: '02472256'
sexagesimal: '190:20:30'
""".lstrip()

        caller = self.get_caller()
        caller("fix", "--changes", "overwrite")
        self.assertEqual(expected, self.get_file_content("type.nl.yml"))

    def test_030_check(self):
        caller = self.get_caller()
        self.assertTrue(caller("check"))

class TestNullAsString(ClassTestCase):
    """
    YAML 1.1 supports type conversions for several types,
    in Symfony translations we want that disabled

    Finally, we *will* output in valid YAML 1.1 format, hence all
    special type values will be properly quoted.
    """
    files = {
        "type.nl.yml": """
canonical: ~
empty:
english: null
~: null key
""".lstrip()
    }

    def test_010_check(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"changes detected in file"):
            caller("check")

    def test_020_fix(self):
        expected = """
canonical: '~'
empty: ''
english: 'null'
'~': null key
""".lstrip()

        caller = self.get_caller()
        caller("fix", "--changes", "overwrite")
        self.assertEqual(expected, self.get_file_content("type.nl.yml"))

    def test_030_check(self):
        caller = self.get_caller()
        self.assertTrue(caller("check"))

class TestTimestampAsString(ClassTestCase):
    """
    YAML 1.1 supports type conversions for several types,
    in Symfony translations we want that disabled

    Finally, we *will* output in valid YAML 1.1 format, hence all
    special type values will be properly quoted.
    """
    files = {
        "type.nl.yml": """
canonical:        2001-12-15T02:59:43.1Z
date (00:00:00Z): 2002-12-14
no time zone (Z): 2001-12-15 2:59:43.10
space separated:  2001-12-14 21:59:43.10 -5
valid iso8601:    2001-12-14t21:59:43.10-05:00
""".lstrip()
    }

    def test_010_check(self):
        caller = self.get_caller()
        with self.assertRaisesRegex(yaz.Error, r"changes detected in file"):
            caller("check")

    def test_020_fix(self):
        expected = """
canonical: '2001-12-15T02:59:43.1Z'
date (00:00:00Z): '2002-12-14'
no time zone (Z): '2001-12-15 2:59:43.10'
space separated: '2001-12-14 21:59:43.10 -5'
valid iso8601: '2001-12-14t21:59:43.10-05:00'
""".lstrip()

        caller = self.get_caller()
        caller("fix", "--changes", "overwrite")
        self.assertEqual(expected, self.get_file_content("type.nl.yml"))

    def test_030_check(self):
        caller = self.get_caller()
        self.assertTrue(caller("check"))
